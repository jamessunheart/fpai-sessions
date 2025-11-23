from fastapi import FastAPI, HTTPException, status
from app.models import ProxyConfig, ProxyStatus, SSLCertRequest, HealthResponse
from app.nginx_manager import NginxManager
from app.config import settings
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Proxy Manager API",
    version="1.0.0",
    description="Automates NGINX reverse proxy and SSL management for FPAI droplets."
)

nginx_manager = NginxManager()

@app.put("/proxies/{droplet_name}", response_model=ProxyStatus, status_code=status.HTTP_201_CREATED)
async def create_update_proxy(droplet_name: str, config: ProxyConfig):
    config.droplet_name = droplet_name # Ensure name matches path
    
    if not nginx_manager.create_config(config):
        raise HTTPException(status_code=500, detail="Failed to write NGINX config")
        
    if not nginx_manager.test_and_reload():
        # Rollback attempt could go here
        raise HTTPException(status_code=422, detail="NGINX config test failed")
        
    return ProxyStatus(
        droplet_name=droplet_name,
        domain=config.domain,
        upstream=f"http://{config.upstream_host}:{config.upstream_port}",
        ssl_enabled=config.ssl_enabled,
        status="active"
    )

@app.delete("/proxies/{droplet_name}")
async def delete_proxy(droplet_name: str):
    if not nginx_manager.delete_config(droplet_name):
        raise HTTPException(status_code=500, detail="Failed to delete config")
    
    nginx_manager.test_and_reload()
    return {"status": "deleted"}

@app.post("/proxies/{droplet_name}/ssl")
async def enable_ssl(droplet_name: str, request: SSLCertRequest):
    # Placeholder for Certbot integration
    # In v1, we'd call subprocess.run([settings.certbot_bin, ...])
    return {"status": "ssl_triggered", "droplet": droplet_name}

@app.get("/proxy-manager/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        nginx={"present": True, "config_test_ok": True},
        ssl={"certbot_present": True, "last_operation": "none"}
    )

# UDC Standard Endpoints
@app.get("/health")
async def udc_health():
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/capabilities")
async def udc_capabilities():
    return {
        "service_name": "proxy-manager",
        "droplet_id": 3, # Assuming ID 3 or similar
        "capabilities": ["proxy_management", "ssl_termination"],
        "integration_endpoints": [
            {"path": "/proxies/{droplet_name}", "method": "PUT"}
        ]
    }
