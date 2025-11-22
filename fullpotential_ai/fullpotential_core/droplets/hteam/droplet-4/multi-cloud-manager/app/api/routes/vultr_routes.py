"""
Vultr API routes
Manages Vultr instances with auto-registry integration
"""

import base64
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.models.domain import VultrCreateRequest, PowerActionRequest
from app.utils.auth import verify_jwt_token
from app.utils.logging import log, log_event, record_action
from app.utils.helpers import get_trace_id
from app.services.registry import register_instance_with_registry, deregister_instance_from_registry

router = APIRouter()


@router.get("/list")
async def list_vultr_instances(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """List all Vultr instances"""
    trace_id = get_trace_id(request)
    
    if not settings.vultr_token:
        raise HTTPException(status_code=503, detail="Vultr not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.vultr.com/v2/instances",
                headers={"Authorization": f"Bearer {settings.vultr_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                instances = data.get("instances", [])
                
                log_event("vultr_list_success", {"count": len(instances)}, trace_id)
                
                return {
                    "provider": "vultr",
                    "count": len(instances),
                    "instances": [
                        {
                            "id": i["id"],
                            "name": i.get("label", i["id"]),
                            "status": i["status"],
                            "ip": i.get("main_ip"),
                            "region": i["region"],
                            "size": i["plan"],
                            "created_at": i["date_created"]
                        }
                        for i in instances
                    ]
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("vultr_list_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def create_vultr_instance(
    req: VultrCreateRequest,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Create Vultr instance and auto-register with Registry"""
    trace_id = get_trace_id(request)
    
    if not settings.vultr_token:
        raise HTTPException(status_code=503, detail="Vultr not configured")
    
    try:
        payload = {
            "label": req.name,
            "region": req.region,
            "plan": req.size,
            "os_id": int(req.image)
        }
        
        # Vultr requires base64-encoded user_data
        if req.user_data:
            user_data_b64 = base64.b64encode(req.user_data.encode('utf-8')).decode('utf-8')
            payload["user_data"] = user_data_b64
            log.info("vultr_userdata_encoded", trace_id=trace_id, message="Encoded user_data to base64")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.vultr.com/v2/instances",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.vultr_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code in [200, 201, 202]:
                result = response.json()
                instance = result.get("instance", {})
                
                # Extract details
                instance_id = instance.get("id")
                ip = instance.get("main_ip")
                
                log_event("vultr_create_success", {
                    "name": req.name,
                    "id": instance_id,
                    "region": req.region,
                    "size": req.size
                }, trace_id)
                record_action(f"create_vultr_instance_{req.name}", trace_id)
                
                # Auto-register with Registry
                registry_success = await register_instance_with_registry(
                    name=req.name,
                    provider="vultr",
                    instance_id=instance_id,
                    ip=ip,
                    region=req.region,
                    size=req.size,
                    trace_id=trace_id
                )
                
                # Add registry status to response
                result["registry_registered"] = registry_success
                
                return result
            else:
                log.error(
                    "vultr_create_failed",
                    status_code=response.status_code,
                    response=response.text,
                    trace_id=trace_id
                )
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("vultr_create_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/action/{instance_id}")
async def vultr_instance_action(
    instance_id: str,
    req: PowerActionRequest,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Perform power action on Vultr instance"""
    trace_id = get_trace_id(request)
    
    if not settings.vultr_token:
        raise HTTPException(status_code=503, detail="Vultr not configured")
    
    # Map our standard actions to Vultr API actions
    action_map = {
        "reboot": "reboot",
        "power_off": "halt",
        "power_on": "start"
    }
    
    vultr_action = action_map.get(req.action)
    if not vultr_action:
        raise HTTPException(status_code=400, detail=f"Invalid action: {req.action}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.vultr.com/v2/instances/{instance_id}/{vultr_action}",
                headers={
                    "Authorization": f"Bearer {settings.vultr_token}",
                    "Content-Type": "application/json"
                }
            )
            
            # Vultr returns 204 for successful actions
            if response.status_code in [200, 202, 204]:
                log_event("vultr_action_success", {
                    "instance_id": instance_id,
                    "action": req.action
                }, trace_id)
                record_action(f"vultr_{req.action}_{instance_id}", trace_id)
                return {"status": "success", "action": req.action, "instance_id": instance_id}
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("vultr_action_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{instance_id}")
async def delete_vultr_instance(
    instance_id: str,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Delete Vultr instance and deregister from Registry"""
    trace_id = get_trace_id(request)
    
    if not settings.vultr_token:
        raise HTTPException(status_code=503, detail="Vultr not configured")
    
    instance_name = None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, get the instance info to extract the name
            get_response = await client.get(
                f"https://api.vultr.com/v2/instances/{instance_id}",
                headers={"Authorization": f"Bearer {settings.vultr_token}"}
            )
            
            if get_response.status_code == 200:
                instance_data = get_response.json().get("instance", {})
                instance_name = instance_data.get("label", instance_id)
            
            # Delete the instance
            response = await client.delete(
                f"https://api.vultr.com/v2/instances/{instance_id}",
                headers={"Authorization": f"Bearer {settings.vultr_token}"}
            )
            
            # Vultr returns 204 for successful deletion
            if response.status_code == 204:
                log_event("vultr_delete_success", {
                    "instance_id": instance_id,
                    "name": instance_name
                }, trace_id)
                record_action(f"delete_vultr_instance_{instance_id}", trace_id)
                
                # Auto-deregister from Registry (if we got the name)
                registry_deregistered = False
                if instance_name:
                    registry_deregistered = await deregister_instance_from_registry(
                        name=instance_name,
                        provider="vultr",
                        trace_id=trace_id
                    )
                
                return {
                    "status": "deleted",
                    "instance_id": instance_id,
                    "name": instance_name,
                    "registry_deregistered": registry_deregistered
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("vultr_delete_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans")
async def list_vultr_plans(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """List available Vultr plans/sizes"""
    trace_id = get_trace_id(request)
    
    if not settings.vultr_token:
        raise HTTPException(status_code=503, detail="Vultr not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.vultr.com/v2/plans",
                headers={"Authorization": f"Bearer {settings.vultr_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                plans = data.get("plans", [])
                
                return {
                    "provider": "vultr",
                    "plans": [
                        {
                            "id": plan["id"],
                            "vcpu_count": plan["vcpu_count"],
                            "ram": plan["ram"],
                            "disk": plan["disk"],
                            "bandwidth": plan["bandwidth"],
                            "monthly_cost": plan["monthly_cost"],
                            "type": plan["type"],
                            "locations": plan.get("locations", [])
                        }
                        for plan in plans
                    ]
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("vultr_plans_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/os")
async def list_vultr_os_images(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """List available Vultr OS images"""
    trace_id = get_trace_id(request)
    
    if not settings.vultr_token:
        raise HTTPException(status_code=503, detail="Vultr not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.vultr.com/v2/os",
                headers={"Authorization": f"Bearer {settings.vultr_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                os_images = data.get("os", [])
                
                return {
                    "provider": "vultr",
                    "os_images": [
                        {
                            "id": os["id"],
                            "name": os["name"],
                            "family": os["family"],
                            "arch": os["arch"]
                        }
                        for os in os_images
                    ]
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("vultr_os_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regions")
async def list_vultr_regions(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """List available Vultr regions"""
    trace_id = get_trace_id(request)
    
    if not settings.vultr_token:
        raise HTTPException(status_code=503, detail="Vultr not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.vultr.com/v2/regions",
                headers={"Authorization": f"Bearer {settings.vultr_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                regions = data.get("regions", [])
                
                return {
                    "provider": "vultr",
                    "regions": [
                        {
                            "id": region["id"],
                            "city": region["city"],
                            "country": region["country"],
                            "continent": region["continent"],
                            "options": region.get("options", [])
                        }
                        for region in regions
                    ]
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("vultr_regions_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instance/{instance_id}")
async def get_vultr_instance(
    instance_id: str,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """Get detailed information about a Vultr instance"""
    trace_id = get_trace_id(request)
    
    if not settings.vultr_token:
        raise HTTPException(status_code=503, detail="Vultr not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://api.vultr.com/v2/instances/{instance_id}",
                headers={"Authorization": f"Bearer {settings.vultr_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                instance = data.get("instance", {})
                
                log_event("vultr_instance_retrieved", {"instance_id": instance_id}, trace_id)
                
                return {
                    "provider": "vultr",
                    "instance": {
                        "id": instance["id"],
                        "name": instance.get("label", instance["id"]),
                        "status": instance["status"],
                        "power_status": instance.get("power_status"),
                        "server_status": instance.get("server_status"),
                        "main_ip": instance.get("main_ip"),
                        "v6_main_ip": instance.get("v6_main_ip"),
                        "region": instance["region"],
                        "plan": instance["plan"],
                        "os": instance.get("os"),
                        "ram": instance.get("ram"),
                        "disk": instance.get("disk"),
                        "vcpu_count": instance.get("vcpu_count"),
                        "bandwidth": instance.get("bandwidth"),
                        "created_at": instance.get("date_created")
                    }
                }
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
    except HTTPException:
        raise
    except Exception as e:
        log.error("vultr_instance_get_error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail=str(e))
