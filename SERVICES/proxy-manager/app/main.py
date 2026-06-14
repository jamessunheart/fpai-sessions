from fastapi import FastAPI, HTTPException, status
from datetime import datetime
from typing import List, Dict, Any

from app.config import settings
from app.models import (
    ProxyConfigRequest, ProxyConfigResponse, ProxyConfig,
    ErrorResponse, MessageRequest, MessageResponse
)
from app.nginx_manager import NGINXManager

app = FastAPI(title="FPAI Proxy Manager", version="1.0.0")

nginx_manager = NGINXManager()

# In-memory store for now (should be persisted)
PROXIES: Dict[str, ProxyConfig] = {}

@app.get("/health")
async def health():
    """UDC Health Check."""
    return {
        "status": "active",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "proxies_managed": len(PROXIES)
    }

@app.get("/capabilities")
async def capabilities():
    """UDC Capabilities."""
    return {
        "name": "proxy-manager",
        "version": "1.0.0",
        "capabilities": ["nginx-config", "ssl-management", "routing"],
        "endpoints": ["/proxies", "/proxies/{droplet_name}"]
    }

@app.put("/proxies/{droplet_name}", response_model=ProxyConfigResponse)
async def create_update_proxy(droplet_name: str, request: ProxyConfigRequest):
    """Create or update a proxy configuration."""
    
    # Create internal config object
    config = ProxyConfig(
        droplet_name=droplet_name,
        **request.dict()
    )
    
    # Write Nginx Config
    success, error = nginx_manager.write_config(config)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write config: {error}"
        )
        
    # Test and Reload
    success, output = nginx_manager.test_config()
    if not success:
        # Rollback? For now just fail
        nginx_manager.delete_config(droplet_name)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Nginx config generated: {output}"
        )
        
    success, output = nginx_manager.reload()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload Nginx: {output}"
        )
        
    config.status = "active"
    PROXIES[droplet_name] = config
    
    return config

@app.delete("/proxies/{droplet_name}")
async def delete_proxy(droplet_name: str):
    """Delete a proxy configuration."""
    if droplet_name not in PROXIES:
        # Check if config file exists anyway
        pass
        
    success, error = nginx_manager.delete_config(droplet_name)
    if not success:
        raise HTTPException(status_code=500, detail=str(error))
        
    nginx_manager.reload()
    
    if droplet_name in PROXIES:
        del PROXIES[droplet_name]
        
    return {"status": "deleted", "droplet_name": droplet_name}

@app.get("/proxies", response_model=List[ProxyConfigResponse])
async def list_proxies():
    """List all managed proxies."""
    return list(PROXIES.values())
