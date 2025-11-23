import os
from fastapi import FastAPI, HTTPException, status
from datetime import datetime
from typing import List

from app.core.config import settings
from app.models.schemas import ProxyConfig, ProxyStatus, SSLRequest, HealthStatus
from app.services.nginx import NginxManager
from app.services.ssl import SSLManager

app = FastAPI(
    title="Proxy Manager API",
    version=settings.VERSION,
    description="Automated NGINX reverse proxy and SSL management for FPAI"
)

nginx_mgr = NginxManager()
ssl_mgr = SSLManager()

# In-memory store for v1 (filesystem is source of truth, this is cache)
known_proxies = {}

@app.get("/health", response_model=HealthStatus)
async def health_check():
    nginx_ok = nginx_mgr.test_config()
    return {
        "status": "healthy" if nginx_ok else "degraded",
        "nginx": {
            "present": os.path.exists(settings.NGINX_BIN),
            "config_test_ok": nginx_ok,
            "last_reload_timestamp": datetime.utcnow().isoformat()
        },
        "ssl": {
            "certbot_present": os.path.exists(settings.CERTBOT_BIN),
            "last_operation": "unknown"
        },
        "timestamp": datetime.utcnow()
    }

@app.get("/proxies", response_model=List[ProxyStatus])
async def list_proxies():
    return list(known_proxies.values())

@app.put("/proxies/{droplet_name}", status_code=status.HTTP_201_CREATED)
async def create_proxy(droplet_name: str, config: ProxyConfig):
    if droplet_name != config.droplet_name:
        raise HTTPException(status_code=400, detail="Droplet name mismatch")
        
    try:
        nginx_mgr.create_config(config)
        nginx_mgr.enable_site(droplet_name)
        
        if not nginx_mgr.reload():
            # Rollback
            nginx_mgr.delete_site(droplet_name)
            nginx_mgr.reload()
            raise HTTPException(status_code=422, detail="NGINX config test failed")
            
        status_obj = ProxyStatus(
            droplet_name=config.droplet_name,
            domain=config.domain,
            upstream=f"http://{config.upstream_host}:{config.upstream_port}",
            ssl_enabled=config.enable_ssl,
            status="active"
        )
        known_proxies[droplet_name] = status_obj
        return status_obj
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/proxies/{droplet_name}/ssl")
async def enable_ssl(droplet_name: str, ssl_req: SSLRequest):
    if droplet_name not in known_proxies:
        raise HTTPException(status_code=404, detail="Proxy not found")
        
    proxy = known_proxies[droplet_name]
    
    if ssl_mgr.obtain_cert(proxy.domain, ssl_req.email, ssl_req.force_renew):
        # Update config to enable SSL
        config = ProxyConfig(
            droplet_name=proxy.droplet_name,
            domain=proxy.domain,
            upstream_host=proxy.upstream.split(":")[1].strip("//"),
            upstream_port=int(proxy.upstream.split(":")[2]),
            enable_ssl=True
        )
        nginx_mgr.create_config(config)
        nginx_mgr.reload()
        
        proxy.ssl_enabled = True
        proxy.last_updated = datetime.utcnow()
        return {"status": "ssl_enabled", "domain": proxy.domain}
    else:
        raise HTTPException(status_code=500, detail="SSL issuance failed")

@app.delete("/proxies/{droplet_name}")
async def delete_proxy(droplet_name: str):
    nginx_mgr.delete_site(droplet_name)
    nginx_mgr.reload()
    if droplet_name in known_proxies:
        del known_proxies[droplet_name]
    return {"status": "deleted"}

# UDC Endpoints
@app.get("/capabilities")
def capabilities():
    return {
        "service_name": settings.SERVICE_NAME,
        "droplet_id": settings.DROPLET_ID,
        "capabilities": ["reverse_proxy", "ssl_management", "load_balancing"],
        "version": settings.VERSION
    }

@app.get("/state")
def state():
    return {
        "status": "active",
        "active_proxies": len(known_proxies),
        "mode": "production"
    }

@app.get("/dependencies")
def dependencies():
    return {
        "required_services": [{"name": "registry", "url": settings.REGISTRY_URL}],
        "external_apis": ["letsencrypt"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
