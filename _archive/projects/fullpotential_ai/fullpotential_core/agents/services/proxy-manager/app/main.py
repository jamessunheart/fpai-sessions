"""Proxy Manager API - Main FastAPI application."""
import logging
import time
from datetime import datetime
from typing import List
import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import (
    ProxyConfigRequest,
    ProxyConfig,
    ProxyConfigResponse,
    SSLRequest,
    SSLResponse,
    HealthResponse,
    ErrorResponse,
    ErrorDetail,
    CapabilitiesResponse,
    StateResponse,
    DependenciesResponse,
    DependencyStatus,
    MessageRequest,
    MessageResponse,
)
from app.nginx_manager import NGINXManager
from app.ssl_manager import SSLManager
from app.registry_client import RegistryClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Proxy Manager API",
    description="Automates NGINX reverse proxy and SSL management for FPAI droplet mesh",
    version="1.0.0",
)

# Initialize managers
nginx_manager = NGINXManager()
ssl_manager = SSLManager()
registry_client = RegistryClient()

# Track startup time for uptime calculation
startup_time = time.time()

# In-memory store for proxy configs (v1 - filesystem-based)
# Configs are reconstructed from NGINX files on startup
proxy_configs: dict[str, ProxyConfig] = {}


def load_existing_configs():
    """Load existing proxy configs from NGINX files on startup."""
    try:
        droplet_names = nginx_manager.list_configs()
        logger.info(f"Found {len(droplet_names)} existing proxy configs")

        # Note: In v1, we don't persist full config details
        # This is just for listing. Full details would require parsing NGINX files
        # or adding a JSON index file (future enhancement)

    except Exception as e:
        logger.error(f"Failed to load existing configs: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting Proxy Manager API")
    load_existing_configs()


async def check_upstream_health(host: str, port: int) -> tuple[bool, str]:
    """
    Check if upstream service is healthy.

    Args:
        host: Upstream host
        port: Upstream port

    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        health_url = f"http://{host}:{port}{settings.health_check_path}"
        timeout = settings.health_check_timeout_ms / 1000

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(health_url)

            if response.status_code == 200:
                return True, "healthy"
            else:
                return False, f"unhealthy (status {response.status_code})"

    except httpx.TimeoutException:
        return False, "timeout"
    except Exception as e:
        return False, f"error: {str(e)}"


def create_error_response(code: str, message: str, details: dict = None) -> JSONResponse:
    """Create a UDC-compliant error response."""
    error = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details or {})
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content=error.model_dump()
    )


@app.put("/proxies/{droplet_name}", response_model=ProxyConfigResponse)
async def create_or_update_proxy(
    droplet_name: str, request: ProxyConfigRequest
) -> ProxyConfigResponse:
    """
    Create or update a proxy configuration for a droplet.

    This endpoint:
    1. Validates upstream health (if required)
    2. Generates NGINX configuration
    3. Tests NGINX config
    4. Reloads NGINX
    5. Returns proxy details
    """
    correlation_id = f"{droplet_name}-{int(datetime.utcnow().timestamp())}"

    logger.info(
        f"[{correlation_id}] Creating/updating proxy for {droplet_name} -> {request.domain}"
    )

    # Health check if required
    if request.require_healthy:
        is_healthy, health_status = await check_upstream_health(
            request.upstream_host, request.upstream_port
        )

        if not is_healthy:
            logger.warning(
                f"[{correlation_id}] Upstream health check failed: {health_status}"
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "UPSTREAM_UNHEALTHY",
                    "message": f"Upstream service is not healthy: {health_status}",
                    "details": {
                        "upstream": f"{request.upstream_host}:{request.upstream_port}",
                        "health_status": health_status,
                    },
                },
            )

    # Check if SSL is enabled but certificate doesn't exist
    ssl_enabled = request.enable_ssl
    if request.enable_ssl and not ssl_manager.check_certificate_exists(request.domain):
        logger.info(
            f"[{correlation_id}] SSL requested but no certificate exists for {request.domain}"
        )
        ssl_enabled = False  # Will be enabled after SSL issuance

    # Create proxy config
    proxy_config = ProxyConfig(
        droplet_name=droplet_name,
        domain=request.domain,
        upstream_host=request.upstream_host,
        upstream_port=request.upstream_port,
        ssl_enabled=ssl_enabled,
        status="active",
        last_health_checked_at=datetime.utcnow(),
    )

    # Write NGINX config
    success, error_msg = nginx_manager.write_config(proxy_config)
    if not success:
        logger.error(f"[{correlation_id}] Failed to write config: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "CONFIG_WRITE_FAILED",
                "message": "Failed to write NGINX configuration",
                "details": {"error": error_msg},
            },
        )

    # Test NGINX config
    test_success, test_output = nginx_manager.test_config()
    if not test_success:
        logger.error(f"[{correlation_id}] NGINX config test failed: {test_output}")

        # Rollback - delete the config we just wrote
        nginx_manager.delete_config(droplet_name)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "NGINX_TEST_FAILED",
                "message": "NGINX configuration test failed",
                "details": {"nginx_output": test_output},
            },
        )

    # Reload NGINX
    reload_success, reload_output = nginx_manager.reload()
    if not reload_success:
        logger.error(f"[{correlation_id}] NGINX reload failed: {reload_output}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "NGINX_RELOAD_FAILED",
                "message": "NGINX reload failed",
                "details": {"nginx_output": reload_output},
            },
        )

    # Store config
    proxy_configs[droplet_name] = proxy_config

    logger.info(f"[{correlation_id}] Proxy created successfully for {droplet_name}")

    return ProxyConfigResponse(
        droplet_name=droplet_name,
        domain=request.domain,
        upstream=proxy_config.upstream,
        ssl_enabled=ssl_enabled,
        status="active",
    )


@app.delete("/proxies/{droplet_name}")
async def delete_proxy(droplet_name: str):
    """
    Delete a proxy configuration.

    This endpoint:
    1. Removes NGINX config file and symlink
    2. Tests NGINX config
    3. Reloads NGINX
    """
    correlation_id = f"{droplet_name}-delete-{int(datetime.utcnow().timestamp())}"

    logger.info(f"[{correlation_id}] Deleting proxy for {droplet_name}")

    if droplet_name not in proxy_configs and droplet_name not in nginx_manager.list_configs():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROXY_NOT_FOUND",
                "message": f"Proxy configuration not found for {droplet_name}",
            },
        )

    # Delete config
    success, error_msg = nginx_manager.delete_config(droplet_name)
    if not success:
        logger.error(f"[{correlation_id}] Failed to delete config: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "CONFIG_DELETE_FAILED",
                "message": "Failed to delete NGINX configuration",
                "details": {"error": error_msg},
            },
        )

    # Test and reload NGINX
    test_success, test_output = nginx_manager.test_config()
    if test_success:
        nginx_manager.reload()

    # Remove from memory
    if droplet_name in proxy_configs:
        del proxy_configs[droplet_name]

    logger.info(f"[{correlation_id}] Proxy deleted successfully")

    return {"status": "deleted", "droplet_name": droplet_name}


@app.get("/proxies", response_model=List[ProxyConfigResponse])
async def list_proxies() -> List[ProxyConfigResponse]:
    """List all proxy configurations."""
    # Get all configs from NGINX files
    droplet_names = nginx_manager.list_configs()

    results = []
    for droplet_name in droplet_names:
        # If we have it in memory, use that
        if droplet_name in proxy_configs:
            config = proxy_configs[droplet_name]
            results.append(
                ProxyConfigResponse(
                    droplet_name=config.droplet_name,
                    domain=config.domain,
                    upstream=config.upstream,
                    ssl_enabled=config.ssl_enabled,
                    status=config.status,
                )
            )
        else:
            # Otherwise just return the name (v1 limitation)
            results.append(
                ProxyConfigResponse(
                    droplet_name=droplet_name,
                    domain="unknown",
                    upstream="unknown",
                    ssl_enabled=False,
                    status="active",
                )
            )

    return results


@app.get("/proxies/{droplet_name}", response_model=ProxyConfigResponse)
async def get_proxy(droplet_name: str) -> ProxyConfigResponse:
    """Get details for a specific proxy configuration."""
    if droplet_name in proxy_configs:
        config = proxy_configs[droplet_name]
        return ProxyConfigResponse(
            droplet_name=config.droplet_name,
            domain=config.domain,
            upstream=config.upstream,
            ssl_enabled=config.ssl_enabled,
            status=config.status,
        )

    # Check if it exists in NGINX files
    if droplet_name in nginx_manager.list_configs():
        return ProxyConfigResponse(
            droplet_name=droplet_name,
            domain="unknown",
            upstream="unknown",
            ssl_enabled=False,
            status="active",
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "PROXY_NOT_FOUND",
            "message": f"Proxy configuration not found for {droplet_name}",
        },
    )


@app.post("/proxies/{droplet_name}/ssl", response_model=SSLResponse)
async def issue_ssl_certificate(
    droplet_name: str, request: SSLRequest = SSLRequest()
) -> SSLResponse:
    """
    Issue or renew SSL certificate for a proxy.

    This endpoint:
    1. Calls certbot to obtain/renew certificate
    2. Updates NGINX config to use SSL
    3. Reloads NGINX
    """
    correlation_id = f"{droplet_name}-ssl-{int(datetime.utcnow().timestamp())}"

    logger.info(f"[{correlation_id}] Issuing SSL certificate for {droplet_name}")

    # Get proxy config
    if droplet_name not in proxy_configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROXY_NOT_FOUND",
                "message": f"Proxy configuration not found for {droplet_name}",
            },
        )

    config = proxy_configs[droplet_name]

    # Issue certificate
    success, message, cert_info = ssl_manager.issue_certificate(
        domain=config.domain, email=request.email, force_renew=request.force_renew
    )

    if not success:
        logger.error(f"[{correlation_id}] SSL issuance failed: {message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SSL_ISSUANCE_FAILED",
                "message": message,
            },
        )

    # Update config to enable SSL
    config.ssl_enabled = True

    # Rewrite NGINX config with SSL enabled
    nginx_manager.write_config(config)
    test_success, _ = nginx_manager.test_config()

    if test_success:
        nginx_manager.reload()
        logger.info(f"[{correlation_id}] SSL certificate issued and NGINX updated")
    else:
        logger.error(f"[{correlation_id}] NGINX config test failed after SSL update")

    return SSLResponse(
        domain=config.domain,
        status="active",
        expiry=cert_info.get("expiry") if cert_info else None,
        issuer=cert_info.get("issuer") if cert_info else None,
    )


@app.get("/proxy-manager/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check endpoint for Proxy Manager.

    Returns health status based on:
    - NGINX availability
    - Config directory writability
    - Last reload status
    """
    nginx_available = nginx_manager.is_nginx_available()
    config_writable = nginx_manager.is_config_dir_writable()
    certbot_available = ssl_manager.is_certbot_available()

    # Determine overall status (UDC compliant: active|inactive|error)
    if nginx_available and config_writable and nginx_manager.last_reload_status:
        overall_status = "active"
    elif nginx_available:
        overall_status = "inactive"
    else:
        overall_status = "error"

    return HealthResponse(
        status=overall_status,
        nginx={
            "present": nginx_available,
            "config_test_ok": nginx_manager.last_reload_status,
            "last_reload_timestamp": (
                nginx_manager.last_reload_timestamp.isoformat()
                if nginx_manager.last_reload_timestamp
                else None
            ),
        },
        ssl={
            "certbot_present": certbot_available,
            "last_operation": ssl_manager.last_operation_status,
        },
    )


@app.get("/proxy-manager/capabilities", response_model=CapabilitiesResponse)
async def capabilities() -> CapabilitiesResponse:
    """
    UDC /capabilities endpoint.

    Returns what this droplet provides and its dependencies.
    """
    return CapabilitiesResponse(
        version="1.0.0",
        features=[
            "nginx_proxy_management",
            "ssl_certificate_automation",
            "health_checks",
            "registry_sync",
        ],
        dependencies=["nginx", "certbot"],
        udc_version="1.0",
        metadata={
            "proxy_count": len(proxy_configs),
            "ssl_enabled_count": len([c for c in proxy_configs.values() if c.ssl_enabled]),
        },
    )


@app.get("/proxy-manager/state", response_model=StateResponse)
async def state() -> StateResponse:
    """
    UDC /state endpoint.

    Returns current resource usage and performance metrics.
    """
    uptime = int(time.time() - startup_time)

    return StateResponse(
        uptime_seconds=uptime,
        requests_total=0,  # TODO: Track requests
        errors_last_hour=0,  # TODO: Track errors
        last_restart=datetime.fromtimestamp(startup_time).isoformat() + "Z",
    )


@app.get("/proxy-manager/dependencies", response_model=DependenciesResponse)
async def dependencies() -> DependenciesResponse:
    """
    UDC /dependencies endpoint.

    Returns required and optional service dependencies with their status.
    """
    # Check NGINX status
    nginx_available = nginx_manager.is_nginx_available()
    nginx_status = DependencyStatus(
        name="nginx",
        status="connected" if nginx_available else "unavailable"
    )

    # Check certbot status
    certbot_available = ssl_manager.is_certbot_available()
    certbot_status = DependencyStatus(
        name="certbot",
        status="connected" if certbot_available else "unavailable"
    )

    # Check Registry status (optional)
    registry_status = DependencyStatus(
        name="registry",
        status="available"  # TODO: Actually check registry connectivity
    )

    return DependenciesResponse(
        required=[nginx_status, certbot_status],
        optional=[registry_status],
        missing=[]
    )


@app.post("/proxy-manager/message", response_model=MessageResponse)
async def message(msg: MessageRequest) -> MessageResponse:
    """
    UDC /message endpoint.

    Receives inter-droplet messages for proxy configuration
    updates, health queries, and sync commands.
    """
    from datetime import datetime

    logger.info(f"Received message from {msg.source}: {msg.message_type}")

    # Handle different message types
    if msg.message_type == "query":
        # Respond to queries about proxy status
        logger.info(f"Processing query: {msg.payload}")
    elif msg.message_type == "command":
        # Handle commands like sync, reload, etc.
        logger.info(f"Processing command: {msg.payload}")
    elif msg.message_type == "event":
        # Handle events from other droplets
        logger.info(f"Processing event: {msg.payload}")

    return MessageResponse(
        received=True,
        trace_id=msg.trace_id,
        processed_at=datetime.utcnow().isoformat() + "Z",
        result="success"
    )


@app.get("/proxy-manager/sync-from-registry")
async def sync_from_registry():
    """
    Sync proxy configurations from Registry.

    Fetches all droplets from Registry and creates proxy configs
    for those that have domain information.
    """
    if not registry_client.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "REGISTRY_NOT_CONFIGURED",
                "message": "Registry URL is not configured",
            },
        )

    droplets = await registry_client.get_droplets()

    if droplets is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "REGISTRY_UNAVAILABLE",
                "message": "Failed to fetch droplets from Registry",
            },
        )

    synced = []
    skipped = []

    for droplet in droplets:
        # Check if droplet has required fields
        if "domain" in droplet and "port" in droplet and "name" in droplet:
            droplet_name = droplet["name"]
            domain = droplet["domain"]
            port = droplet["port"]
            host = droplet.get("host", "localhost")

            # Create proxy config request
            proxy_request = ProxyConfigRequest(
                domain=domain,
                upstream_host=host,
                upstream_port=port,
                require_healthy=False,  # Don't require health for bulk sync
                enable_ssl=False,  # SSL can be enabled separately
            )

            try:
                await create_or_update_proxy(droplet_name, proxy_request)
                synced.append(droplet_name)
            except Exception as e:
                logger.error(f"Failed to sync {droplet_name}: {str(e)}")
                skipped.append({"name": droplet_name, "reason": str(e)})
        else:
            skipped.append(
                {"name": droplet.get("name", "unknown"), "reason": "missing fields"}
            )

    return {
        "synced": synced,
        "synced_count": len(synced),
        "skipped": skipped,
        "skipped_count": len(skipped),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.proxy_manager_port)
