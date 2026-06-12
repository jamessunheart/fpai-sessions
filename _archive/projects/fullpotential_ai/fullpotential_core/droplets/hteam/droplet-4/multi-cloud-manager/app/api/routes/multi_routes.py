"""
Multi-cloud unified API routes
Aggregates instances across all cloud providers
"""

from typing import Optional
from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.utils.auth import verify_jwt_token
from app.utils.logging import log, log_event
from app.utils.helpers import get_trace_id

router = APIRouter()


@router.get("/list")
async def list_all_providers(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Unified multi-cloud listing
    Returns instances from all configured providers
    Gracefully handles errors from individual providers
    """
    trace_id = get_trace_id(request)
    result = {
        "providers": [],
        "total_instances": 0,
        "do": [],
        "hetzner": [],
        "vultr": [],
        "errors": {}
    }
    
    # Import route handlers
    from app.api.routes import do_routes, hetzner_routes, vultr_routes
    
    # DigitalOcean
    if settings.do_token:
        result["providers"].append("digitalocean")
        try:
            do_data = await do_routes.list_do_droplets(request, token_data)
            result["do"] = do_data.get("droplets", [])
            log.info("multi_list_do_success", count=len(result["do"]), trace_id=trace_id)
        except Exception as e:
            log.error("multi_list_do_error", error=str(e), trace_id=trace_id)
            result["errors"]["digitalocean"] = str(e)
            result["do"] = []
    
    # Hetzner
    if settings.hetzner_token:
        result["providers"].append("hetzner")
        try:
            hetzner_data = await hetzner_routes.list_hetzner_servers(request, token_data)
            result["hetzner"] = hetzner_data.get("servers", [])
            log.info("multi_list_hetzner_success", count=len(result["hetzner"]), trace_id=trace_id)
        except Exception as e:
            log.error("multi_list_hetzner_error", error=str(e), trace_id=trace_id)
            result["errors"]["hetzner"] = str(e)
            result["hetzner"] = []
    
    # Vultr
    if settings.vultr_token:
        result["providers"].append("vultr")
        try:
            vultr_data = await vultr_routes.list_vultr_instances(request, token_data)
            result["vultr"] = vultr_data.get("instances", [])
            log.info("multi_list_vultr_success", count=len(result["vultr"]), trace_id=trace_id)
        except Exception as e:
            log.error("multi_list_vultr_error", error=str(e), trace_id=trace_id)
            result["errors"]["vultr"] = str(e)
            result["vultr"] = []
    
    # Calculate totals
    result["total_instances"] = (
        len(result["do"]) +
        len(result["hetzner"]) +
        len(result["vultr"])
    )
    
    # Log summary event
    log_event("multi_list_success", {
        "do_count": len(result["do"]),
        "hetzner_count": len(result["hetzner"]),
        "vultr_count": len(result["vultr"]),
        "total": result["total_instances"],
        "providers": result["providers"],
        "errors": list(result["errors"].keys())
    }, trace_id)
    
    return result


@router.get("/summary")
async def get_multi_cloud_summary(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Get summary statistics across all cloud providers
    Returns counts, costs, and status overview
    """
    trace_id = get_trace_id(request)
    
    # Get full listing
    full_list = await list_all_providers(request, token_data)
    
    summary = {
        "total_instances": full_list["total_instances"],
        "by_provider": {
            "digitalocean": {
                "count": len(full_list["do"]),
                "configured": bool(settings.do_token),
                "status": "error" if "digitalocean" in full_list["errors"] else "ok"
            },
            "hetzner": {
                "count": len(full_list["hetzner"]),
                "configured": bool(settings.hetzner_token),
                "status": "error" if "hetzner" in full_list["errors"] else "ok"
            },
            "vultr": {
                "count": len(full_list["vultr"]),
                "configured": bool(settings.vultr_token),
                "status": "error" if "vultr" in full_list["errors"] else "ok"
            }
        },
        "by_status": {
            "running": 0,
            "stopped": 0,
            "other": 0
        },
        "errors": full_list["errors"]
    }
    
    # Count by status
    for instance in full_list["do"]:
        status = instance.get("status", "").lower()
        if status in ["active", "running"]:
            summary["by_status"]["running"] += 1
        elif status in ["off", "stopped", "powered off"]:
            summary["by_status"]["stopped"] += 1
        else:
            summary["by_status"]["other"] += 1
    
    for server in full_list["hetzner"]:
        status = server.get("status", "").lower()
        if status == "running":
            summary["by_status"]["running"] += 1
        elif status == "off":
            summary["by_status"]["stopped"] += 1
        else:
            summary["by_status"]["other"] += 1
    
    for instance in full_list["vultr"]:
        status = instance.get("status", "").lower()
        if status == "active":
            summary["by_status"]["running"] += 1
        elif status in ["stopped", "suspended"]:
            summary["by_status"]["stopped"] += 1
        else:
            summary["by_status"]["other"] += 1
    
    log_event("multi_summary_generated", {
        "total": summary["total_instances"],
        "running": summary["by_status"]["running"],
        "stopped": summary["by_status"]["stopped"]
    }, trace_id)
    
    return summary


@router.get("/search")
async def search_instances(
    request: Request,
    name: Optional[str] = None,
    ip: Optional[str] = None,
    provider: Optional[str] = None,
    status: Optional[str] = None,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Search instances across all providers
    Supports filtering by name, ip, provider, and status
    """
    trace_id = get_trace_id(request)
    
    # Get full listing
    full_list = await list_all_providers(request, token_data)
    
    results = []
    
    # Search DigitalOcean
    if not provider or provider == "digitalocean":
        for droplet in full_list["do"]:
            if name and name.lower() not in droplet.get("name", "").lower():
                continue
            if ip and ip not in droplet.get("ip", ""):
                continue
            if status and status.lower() != droplet.get("status", "").lower():
                continue
            
            results.append({
                "provider": "digitalocean",
                "instance": droplet
            })
    
    # Search Hetzner
    if not provider or provider == "hetzner":
        for server in full_list["hetzner"]:
            if name and name.lower() not in server.get("name", "").lower():
                continue
            if ip and ip not in server.get("ip", ""):
                continue
            if status and status.lower() != server.get("status", "").lower():
                continue
            
            results.append({
                "provider": "hetzner",
                "instance": server
            })
    
    # Search Vultr
    if not provider or provider == "vultr":
        for instance in full_list["vultr"]:
            if name and name.lower() not in instance.get("name", "").lower():
                continue
            if ip and ip not in instance.get("ip", ""):
                continue
            if status and status.lower() != instance.get("status", "").lower():
                continue
            
            results.append({
                "provider": "vultr",
                "instance": instance
            })
    
    log_event("multi_search_completed", {
        "filters": {
            "name": name,
            "ip": ip,
            "provider": provider,
            "status": status
        },
        "results_count": len(results)
    }, trace_id)
    
    return {
        "results": results,
        "count": len(results),
        "filters": {
            "name": name,
            "ip": ip,
            "provider": provider,
            "status": status
        }
    }


@router.get("/health-check")
async def multi_cloud_health_check(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Health check for all configured cloud providers
    Tests API connectivity without fetching full instance lists
    """
    trace_id = get_trace_id(request)
    
    health = {
        "digitalocean": {
            "configured": bool(settings.do_token),
            "status": "not_configured",
            "error": None
        },
        "hetzner": {
            "configured": bool(settings.hetzner_token),
            "status": "not_configured",
            "error": None
        },
        "vultr": {
            "configured": bool(settings.vultr_token),
            "status": "not_configured",
            "error": None
        }
    }
    
    # Test DigitalOcean
    if settings.do_token:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.digitalocean.com/v2/account",
                    headers={"Authorization": f"Bearer {settings.do_token}"}
                )
                health["digitalocean"]["status"] = "healthy" if response.status_code == 200 else "error"
                if response.status_code != 200:
                    health["digitalocean"]["error"] = f"HTTP {response.status_code}"
        except Exception as e:
            health["digitalocean"]["status"] = "error"
            health["digitalocean"]["error"] = str(e)
    
    # Test Hetzner
    if settings.hetzner_token:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.hetzner.cloud/v1/servers?per_page=1",
                    headers={"Authorization": f"Bearer {settings.hetzner_token}"}
                )
                health["hetzner"]["status"] = "healthy" if response.status_code == 200 else "error"
                if response.status_code != 200:
                    health["hetzner"]["error"] = f"HTTP {response.status_code}"
        except Exception as e:
            health["hetzner"]["status"] = "error"
            health["hetzner"]["error"] = str(e)
    
    # Test Vultr
    if settings.vultr_token:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.vultr.com/v2/account",
                    headers={"Authorization": f"Bearer {settings.vultr_token}"}
                )
                health["vultr"]["status"] = "healthy" if response.status_code == 200 else "error"
                if response.status_code != 200:
                    health["vultr"]["error"] = f"HTTP {response.status_code}"
        except Exception as e:
            health["vultr"]["status"] = "error"
            health["vultr"]["error"] = str(e)
    
    # Calculate overall status
    configured_count = sum(1 for p in health.values() if p["configured"])
    healthy_count = sum(1 for p in health.values() if p["status"] == "healthy")
    
    overall_status = "healthy" if healthy_count == configured_count and configured_count > 0 else "degraded"
    if configured_count == 0:
        overall_status = "not_configured"
    elif healthy_count == 0:
        overall_status = "unhealthy"
    
    log_event("multi_health_check", {
        "overall": overall_status,
        "configured": configured_count,
        "healthy": healthy_count
    }, trace_id)
    
    return {
        "overall_status": overall_status,
        "configured_providers": configured_count,
        "healthy_providers": healthy_count,
        "providers": health
    }
