"""
DigitalOcean API routes
Manages DigitalOcean droplets with auto-registry integration
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.models.domain import DOCreateRequest, PowerActionRequest
from app.utils.auth import verify_jwt_token
from app.utils.logging import log, log_event, record_action
from app.utils.helpers import get_trace_id
from app.services.registry import register_instance_with_registry, deregister_instance_from_registry

router = APIRouter()


@router.get("/list")
async def list_do_droplets(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """List all DigitalOcean droplets"""
    trace_id = get_trace_id(request)
    
    if not settings.do_token:
        raise HTTPException(status_code=503, detail="DigitalOcean not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.digitalocean.com/v2/droplets",
                headers={"Authorization": f"Bearer {settings.do_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                droplets = data.get("droplets", [])
                
                log_event("do_list_success", {"count": len(droplets)}, trace_id)
                
                return {
                    "provider": "digitalocean",
                    "count": len(droplets),
                    "droplets": [
                        {
                            "id": str(d["id"]),
                            "name": d["name"],
                            "status": d["status"],
                            "ip": d["networks"]["v4"][0]["ip_address"] if d["networks"]["v4"] else None,
                            "region": d["region"]["slug"],
                            "size": d["size"]["slug"],
                            "created_at": d["created_at"]
                        }
                        for d in droplets
                    ]
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("do_list_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def create_do_droplet(
    req: DOCreateRequest,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Create DigitalOcean droplet and auto-register with Registry"""
    trace_id = get_trace_id(request)
    
    if not settings.do_token:
        raise HTTPException(status_code=503, detail="DigitalOcean not configured")
    
    try:
        payload = {
            "name": req.name,
            "region": req.region,
            "size": req.size,
            "image": req.image
        }
        
        if req.ssh_keys:
            payload["ssh_keys"] = req.ssh_keys
        if req.user_data:
            payload["user_data"] = req.user_data
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.digitalocean.com/v2/droplets",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.do_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code in [200, 201, 202]:
                result = response.json()
                droplet = result.get("droplet", {})
                
                droplet_id = str(droplet.get("id"))
                ip = None
                if droplet.get("networks", {}).get("v4"):
                    ip = droplet["networks"]["v4"][0].get("ip_address")
                
                log_event("do_create_success", {
                    "name": req.name,
                    "id": droplet_id,
                    "region": req.region,
                    "size": req.size
                }, trace_id)
                record_action(f"create_do_droplet_{req.name}", trace_id)
                
                # Auto-register with Registry
                registry_success = await register_instance_with_registry(
                    name=req.name,
                    provider="digitalocean",
                    instance_id=droplet_id,
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
        log.error("do_create_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/action/{droplet_id}")
async def do_droplet_action(
    droplet_id: str,
    req: PowerActionRequest,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Perform power action on DigitalOcean droplet"""
    trace_id = get_trace_id(request)
    
    if not settings.do_token:
        raise HTTPException(status_code=503, detail="DigitalOcean not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.digitalocean.com/v2/droplets/{droplet_id}/actions",
                json={"type": req.action},
                headers={
                    "Authorization": f"Bearer {settings.do_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                log_event("do_action_success", {
                    "droplet_id": droplet_id,
                    "action": req.action
                }, trace_id)
                record_action(f"do_{req.action}_{droplet_id}", trace_id)
                return result
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("do_action_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{droplet_id}")
async def delete_do_droplet(
    droplet_id: str,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Delete DigitalOcean droplet and deregister from Registry"""
    trace_id = get_trace_id(request)
    
    if not settings.do_token:
        raise HTTPException(status_code=503, detail="DigitalOcean not configured")
    
    droplet_name = None
    
    try:
        # First, get the droplet info to extract the name
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get droplet details
            get_response = await client.get(
                f"https://api.digitalocean.com/v2/droplets/{droplet_id}",
                headers={"Authorization": f"Bearer {settings.do_token}"}
            )
            
            if get_response.status_code == 200:
                droplet_data = get_response.json().get("droplet", {})
                droplet_name = droplet_data.get("name")
            
            # Delete the droplet
            response = await client.delete(
                f"https://api.digitalocean.com/v2/droplets/{droplet_id}",
                headers={"Authorization": f"Bearer {settings.do_token}"}
            )
            
            if response.status_code == 204:
                log_event("do_delete_success", {"droplet_id": droplet_id, "name": droplet_name}, trace_id)
                record_action(f"delete_do_droplet_{droplet_id}", trace_id)
                
                # Auto-deregister from Registry (if we got the name)
                registry_deregistered = False
                if droplet_name:
                    registry_deregistered = await deregister_instance_from_registry(
                        name=droplet_name,
                        provider="digitalocean",
                        trace_id=trace_id
                    )
                
                return {
                    "status": "deleted",
                    "droplet_id": droplet_id,
                    "name": droplet_name,
                    "registry_deregistered": registry_deregistered
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("do_delete_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))
