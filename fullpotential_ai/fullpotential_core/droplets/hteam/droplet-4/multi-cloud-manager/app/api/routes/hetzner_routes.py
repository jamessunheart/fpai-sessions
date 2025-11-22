"""
Hetzner Cloud API routes
Manages Hetzner Cloud servers with auto-registry integration
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.models.domain import HetznerCreateRequest, PowerActionRequest
from app.utils.auth import verify_jwt_token
from app.utils.logging import log, log_event, record_action
from app.utils.helpers import get_trace_id
from app.services.registry import register_instance_with_registry, deregister_instance_from_registry

router = APIRouter()


@router.get("/list")
async def list_hetzner_servers(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """List all Hetzner Cloud servers"""
    trace_id = get_trace_id(request)
    
    if not settings.hetzner_token:
        raise HTTPException(status_code=503, detail="Hetzner Cloud not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.hetzner.cloud/v1/servers",
                headers={"Authorization": f"Bearer {settings.hetzner_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                servers = data.get("servers", [])
                
                log_event("hetzner_list_success", {"count": len(servers)}, trace_id)
                
                return {
                    "provider": "hetzner",
                    "count": len(servers),
                    "servers": [
                        {
                            "id": str(s["id"]),
                            "name": s["name"],
                            "status": s["status"],
                            "ip": s["public_net"]["ipv4"]["ip"] if s.get("public_net", {}).get("ipv4") else None,
                            "region": s["datacenter"]["location"]["name"],
                            "size": s["server_type"]["name"],
                            "created_at": s["created"]
                        }
                        for s in servers
                    ]
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("hetzner_list_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def create_hetzner_server(
    req: HetznerCreateRequest,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Create Hetzner Cloud server and auto-register with Registry"""
    trace_id = get_trace_id(request)
    
    if not settings.hetzner_token:
        raise HTTPException(status_code=503, detail="Hetzner Cloud not configured")
    
    try:
        payload = {
            "name": req.name,
            "server_type": req.size,
            "location": req.region,
            "image": req.image,
            "start_after_create": True
        }
        
        if req.user_data:
            payload["user_data"] = req.user_data
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.hetzner.cloud/v1/servers",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.hetzner_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code in [200, 201, 202]:
                result = response.json()
                server = result.get("server", {})
                
                # Extract details
                server_id = str(server.get("id"))
                ip = None
                if server.get("public_net", {}).get("ipv4"):
                    ip = server["public_net"]["ipv4"].get("ip")
                
                log_event("hetzner_create_success", {
                    "name": req.name,
                    "id": server_id,
                    "region": req.region,
                    "size": req.size
                }, trace_id)
                record_action(f"create_hetzner_server_{req.name}", trace_id)
                
                # Auto-register with Registry
                registry_success = await register_instance_with_registry(
                    name=req.name,
                    provider="hetzner",
                    instance_id=server_id,
                    ip=ip,
                    region=req.region,
                    size=req.size,
                    trace_id=trace_id
                )
                
                # Add registry status to response
                result["registry_registered"] = registry_success
                
                return result
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("hetzner_create_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/action/{server_id}")
async def hetzner_server_action(
    server_id: str,
    req: PowerActionRequest,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Perform power action on Hetzner Cloud server"""
    trace_id = get_trace_id(request)
    
    if not settings.hetzner_token:
        raise HTTPException(status_code=503, detail="Hetzner Cloud not configured")
    
    # Map our standard actions to Hetzner API actions
    action_map = {
        "reboot": "reboot",
        "power_off": "poweroff",
        "power_on": "poweron"
    }
    
    hetzner_action = action_map.get(req.action)
    if not hetzner_action:
        raise HTTPException(status_code=400, detail=f"Invalid action: {req.action}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.hetzner.cloud/v1/servers/{server_id}/actions/{hetzner_action}",
                headers={
                    "Authorization": f"Bearer {settings.hetzner_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                log_event("hetzner_action_success", {
                    "server_id": server_id,
                    "action": req.action
                }, trace_id)
                record_action(f"hetzner_{req.action}_{server_id}", trace_id)
                return result
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("hetzner_action_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{server_id}")
async def delete_hetzner_server(
    server_id: str,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Delete Hetzner Cloud server and deregister from Registry"""
    trace_id = get_trace_id(request)
    
    if not settings.hetzner_token:
        raise HTTPException(status_code=503, detail="Hetzner Cloud not configured")
    
    server_name = None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, get the server info to extract the name
            get_response = await client.get(
                f"https://api.hetzner.cloud/v1/servers/{server_id}",
                headers={"Authorization": f"Bearer {settings.hetzner_token}"}
            )
            
            if get_response.status_code == 200:
                server_data = get_response.json().get("server", {})
                server_name = server_data.get("name")
            
            # Delete the server
            response = await client.delete(
                f"https://api.hetzner.cloud/v1/servers/{server_id}",
                headers={"Authorization": f"Bearer {settings.hetzner_token}"}
            )
            
            if response.status_code == 200:
                log_event("hetzner_delete_success", {
                    "server_id": server_id,
                    "name": server_name
                }, trace_id)
                record_action(f"delete_hetzner_server_{server_id}", trace_id)
                
                # Auto-deregister from Registry (if we got the name)
                registry_deregistered = False
                if server_name:
                    registry_deregistered = await deregister_instance_from_registry(
                        name=server_name,
                        provider="hetzner",
                        trace_id=trace_id
                    )
                
                return {
                    "status": "deleted",
                    "server_id": server_id,
                    "name": server_name,
                    "registry_deregistered": registry_deregistered
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("hetzner_delete_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sizes")
async def list_hetzner_sizes(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """List available Hetzner server sizes"""
    trace_id = get_trace_id(request)
    
    if not settings.hetzner_token:
        raise HTTPException(status_code=503, detail="Hetzner Cloud not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.hetzner.cloud/v1/server_types",
                headers={"Authorization": f"Bearer {settings.hetzner_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                server_types = data.get("server_types", [])
                
                return {
                    "provider": "hetzner",
                    "sizes": [
                        {
                            "id": st["id"],
                            "name": st["name"],
                            "description": st["description"],
                            "cores": st["cores"],
                            "memory": st["memory"],
                            "disk": st["disk"],
                            "price_monthly": st["prices"][0]["price_monthly"]["gross"] if st.get("prices") else None
                        }
                        for st in server_types
                    ]
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("hetzner_sizes_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images")
async def list_hetzner_images(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """List available Hetzner images"""
    trace_id = get_trace_id(request)
    
    if not settings.hetzner_token:
        raise HTTPException(status_code=503, detail="Hetzner Cloud not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.hetzner.cloud/v1/images?type=system",
                headers={"Authorization": f"Bearer {settings.hetzner_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                images = data.get("images", [])
                
                return {
                    "provider": "hetzner",
                    "images": [
                        {
                            "id": img["id"],
                            "name": img["name"],
                            "description": img["description"],
                            "os_flavor": img["os_flavor"],
                            "os_version": img["os_version"]
                        }
                        for img in images
                    ]
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("hetzner_images_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations")
async def list_hetzner_locations(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """List available Hetzner locations/regions"""
    trace_id = get_trace_id(request)
    
    if not settings.hetzner_token:
        raise HTTPException(status_code=503, detail="Hetzner Cloud not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.hetzner.cloud/v1/locations",
                headers={"Authorization": f"Bearer {settings.hetzner_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                locations = data.get("locations", [])
                
                return {
                    "provider": "hetzner",
                    "locations": [
                        {
                            "id": loc["id"],
                            "name": loc["name"],
                            "description": loc["description"],
                            "city": loc["city"],
                            "country": loc["country"]
                        }
                        for loc in locations
                    ]
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("hetzner_locations_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))
