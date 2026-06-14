"""
Registry v2 communication service
Handles registration, heartbeat, and instance tracking
"""

import asyncio
import httpx
import json
import psutil
import socket
from datetime import datetime
from typing import Optional

from app.config import settings
from app.utils.logging import log, log_event
from app.services.jwt_service import fetch_registry_jwt_token, clear_token_cache
from app.utils.state import request_count, error_count, start_time


def get_server_ip() -> str:
    """
    Get server's public IP address automatically
    Returns '0.0.0.0' if detection fails
    """
    try:
        # Method 1: Try external IP detection services
        import httpx
        services = [
            "https://api.ipify.org?format=text",
            "https://icanhazip.com",
            "https://ifconfig.me/ip"
        ]
        
        for service in services:
            try:
                with httpx.Client(timeout=3.0) as client:
                    response = client.get(service)
                    if response.status_code == 200:
                        ip = response.text.strip()
                        # Validate it's not a private IP
                        if not ip.startswith(('172.', '192.168.', '10.')):
                            log.info("public_ip_detected", ip=ip, service=service)
                            return ip
            except Exception:
                continue
        
        # Method 2: Fallback to socket method (may return private IP)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        
        log.warning("ip_detection_fallback", ip=ip, message="Using fallback IP detection")
        return ip
        
    except Exception as e:
        log.warning("ip_detection_failed", error=str(e))
        return "0.0.0.0"


async def register_with_registry():
    """Register with Registry v2 on startup"""
    try:
        # Clear token cache to force fresh token fetch
        clear_token_cache()
        
        # Get fresh JWT token
        token = await fetch_registry_jwt_token()
        if not token:
            log.error("registry_registration_failed", message="Could not fetch JWT token for registration")
            return False

        # Get server IP automatically
        server_ip = get_server_ip()

        # Align with registry's expected structure
        registration_data = {
            "droplet_id": settings.droplet_domain,  # REQUIRED: Primary identifier
            "id": settings.droplet_domain,  # Also include id for backward compatibility
            "host": settings.droplet_domain,
            "ip": server_ip,
            "status": "active",
            "metadata": {
                "name": settings.droplet_name,
                "steward": settings.steward,
                "version": "1.0.0",
                "udc_version": "1.0",
                "endpoint": f"https://{settings.droplet_domain}",
                "capabilities": [
                    "multi-cloud-management",
                    "digitalocean",
                    "hetzner",
                    "vultr",
                    "udc-v1.0",
                    "jwt-jwks"
                ]
            }
        }

        log.info(
            "registry_registration_attempt",
            payload=registration_data
        )

        # CRITICAL: Registry requires BOTH headers
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.registry_url}/registry/register",
                json=registration_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Registry-Key": settings.registry_key  # REQUIRED!
                }
            )

            if response.status_code in [200, 201]:
                result = response.json()
                log.info(
                    "registry_registration_success",
                    droplet_name=settings.droplet_name,
                    ip=server_ip,
                    response=result
                )
                log_event("registry_v2_registration_success", {
                    "registry": settings.registry_url,
                    "ip": server_ip,
                    "response": result
                })
                return True
            elif response.status_code == 401:
                log.error(
                    "registry_registration_token_expired",
                    message="Token expired during registration - will retry"
                )
                return False
            else:
                log.error(
                    "registry_registration_error",
                    status_code=response.status_code,
                    response=response.text
                )
                log_event("registry_v2_registration_failed", {
                    "status": response.status_code,
                    "error": response.text
                })
                return False

    except Exception as e:
        log.error("registry_registration_exception", error=str(e))
        return False


async def heartbeat_task():
    """Send periodic heartbeat to Registry v2"""
    # Wait for initial registration
    await asyncio.sleep(5)

    # Track last registration time
    last_registration = datetime.utcnow()
    registration_interval = 86400  # 24 hours in seconds
    consecutive_401_errors = 0  # Track 401 errors

    while True:
        try:
            # Check if 24 hours have passed since last registration
            time_since_registration = (datetime.utcnow() - last_registration).total_seconds()
            if time_since_registration >= registration_interval:
                log.info("auto_reregistration", message="24 hours elapsed, re-registering with registry")
                if await register_with_registry():
                    last_registration = datetime.utcnow()
                    consecutive_401_errors = 0

            # Get JWT token (will use cache if valid)
            token = await fetch_registry_jwt_token()
            if not token:
                log.warning("heartbeat_no_token", message="Could not fetch JWT token for heartbeat")
                await asyncio.sleep(settings.heartbeat_interval)
                continue

            heartbeat_data = {
                "droplet_id": settings.droplet_domain,  # Use FQDN, not numeric ID
                "status": "active",
                "metrics": {
                    "cpu_percent": round(psutil.cpu_percent(interval=1), 2),
                    "memory_mb": round(psutil.virtual_memory().used / (1024 * 1024), 2),
                    "requests_per_minute": request_count,
                    "errors_last_hour": error_count,
                    "uptime_seconds": int((datetime.utcnow() - start_time).total_seconds())
                }
            }

            # CRITICAL: Registry requires BOTH headers
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{settings.registry_url}/registry/heartbeat",
                    json=heartbeat_data,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "X-Registry-Key": settings.registry_key  # REQUIRED!
                    }
                )

                if response.status_code == 200:
                    log.info("heartbeat_success", message="Heartbeat sent to Registry v2")
                    consecutive_401_errors = 0  # Reset error counter on success
                elif response.status_code == 401:
                    # Token expired, trigger immediate re-registration
                    consecutive_401_errors += 1
                    log.warning(
                        "heartbeat_token_expired", 
                        message=f"Token expired (attempt {consecutive_401_errors}), triggering immediate re-registration"
                    )
                    
                    # Clear token cache and re-register
                    clear_token_cache()
                    if await register_with_registry():
                        last_registration = datetime.utcnow()
                        consecutive_401_errors = 0
                        log.info("reregistration_after_token_expiry_success")
                    else:
                        log.error("reregistration_after_token_expiry_failed", attempts=consecutive_401_errors)
                    
                    # If multiple failures, wait longer before next attempt
                    if consecutive_401_errors >= 3:
                        log.error("multiple_registration_failures", count=consecutive_401_errors)
                        await asyncio.sleep(300)  # Wait 5 minutes after multiple failures
                        
                else:
                    log.warning(
                        "heartbeat_failed",
                        status_code=response.status_code,
                        response=response.text
                    )

        except Exception as e:
            log.error("heartbeat_error", error=str(e))

        await asyncio.sleep(settings.heartbeat_interval)


async def register_instance_with_registry(
    name: str,
    provider: str,
    instance_id: str,
    ip: Optional[str],
    region: str,
    size: str,
    trace_id: str
) -> bool:
    """
    Register newly created cloud instance with Registry

    Args:
        name: Instance name
        provider: Cloud provider (digitalocean, hetzner, vultr)
        instance_id: Provider's instance ID
        ip: Instance IP address
        region: Cloud region
        size: Instance size/plan
        trace_id: Request trace ID

    Returns:
        True if registration successful, False otherwise
    """
    try:
        token = await fetch_registry_jwt_token()
        if not token:
            log.error("instance_registration_no_token", trace_id=trace_id)
            return False

        # Build FQDN for the instance
        instance_fqdn = f"{name}.{provider}.fullpotential.ai"
        
        # Align with registry structure - REQUIRED fields
        registration_data = {
            "droplet_id": instance_fqdn,  # REQUIRED: Primary identifier
            "id": instance_fqdn,           # Backward compatibility
            "host": instance_fqdn,
            "ip": ip or "pending",
            "status": "active",
            "metadata": {
                "name": name,
                "provider": provider,
                "instance_id": instance_id,
                "region": region,
                "size": size,
                "role": "compute",
                "env": "production",
                "version": "1.0.0",
                "udc_version": "1.0",
                "created_by": f"{settings.droplet_name} ({settings.droplet_domain})",
                "created_at": datetime.utcnow().isoformat(),
                "managed_by": "multi-cloud-manager"
            }
        }

        log.info(
            "instance_registration_attempt",
            name=name,
            provider=provider,
            fqdn=instance_fqdn,
            trace_id=trace_id
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.registry_url}/registry/register",
                json=registration_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Registry-Key": settings.registry_key
                }
            )

            if response.status_code in [200, 201]:
                result = response.json()
                log.info(
                    "instance_registered_success",
                    name=name,
                    provider=provider,
                    fqdn=instance_fqdn,
                    instance_id=instance_id,
                    ip=ip,
                    trace_id=trace_id,
                    response=result
                )
                log_event("instance_registered", {
                    "name": name,
                    "provider": provider,
                    "fqdn": instance_fqdn,
                    "instance_id": instance_id,
                    "ip": ip,
                    "region": region,
                    "size": size
                }, trace_id)
                return True
            elif response.status_code == 401:
                # Token expired, clear cache and retry once
                log.warning(
                    "instance_registration_token_expired",
                    trace_id=trace_id,
                    message="Token expired, retrying with fresh token"
                )
                clear_token_cache()
                
                # Retry with fresh token
                new_token = await fetch_registry_jwt_token()
                if new_token:
                    retry_response = await client.post(
                        f"{settings.registry_url}/registry/register",
                        json=registration_data,
                        headers={
                            "Authorization": f"Bearer {new_token}",
                            "Content-Type": "application/json",
                            "X-Registry-Key": settings.registry_key
                        }
                    )
                    if retry_response.status_code in [200, 201]:
                        log.info("instance_registration_retry_success", trace_id=trace_id)
                        return True
                
                log.error("instance_registration_retry_failed", trace_id=trace_id)
                return False
            else:
                log.warning(
                    "instance_registration_failed",
                    status_code=response.status_code,
                    response=response.text,
                    trace_id=trace_id
                )
                return False

    except Exception as e:
        log.error(
            "instance_registration_error",
            error=str(e),
            name=name,
            provider=provider,
            trace_id=trace_id
        )
        return False


async def deregister_instance_from_registry(
    name: str,
    provider: str,
    trace_id: str
) -> bool:
    """
    Deregister instance from Registry when it's deleted

    Args:
        name: Instance name
        provider: Cloud provider (digitalocean, hetzner, vultr)
        trace_id: Request trace ID

    Returns:
        True if deregistration successful, False otherwise
    """
    try:
        token = await fetch_registry_jwt_token()
        if not token:
            log.error("instance_deregistration_no_token", trace_id=trace_id)
            return False

        # Build FQDN for the instance
        instance_fqdn = f"{name}.{provider}.fullpotential.ai"
        
        log.info(
            "instance_deregistration_attempt",
            name=name,
            provider=provider,
            fqdn=instance_fqdn,
            trace_id=trace_id
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(
                f"{settings.registry_url}/registry/droplets/{instance_fqdn}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Registry-Key": settings.registry_key
                }
            )

            if response.status_code in [200, 204]:
                log.info(
                    "instance_deregistered_success",
                    name=name,
                    provider=provider,
                    fqdn=instance_fqdn,
                    trace_id=trace_id
                )
                log_event("instance_deregistered", {
                    "name": name,
                    "provider": provider,
                    "fqdn": instance_fqdn
                }, trace_id)
                return True
            elif response.status_code == 404:
                # Instance not found in registry - not a critical error
                log.warning(
                    "instance_not_found_in_registry",
                    fqdn=instance_fqdn,
                    trace_id=trace_id
                )
                return True
            elif response.status_code == 401:
                # Token expired, retry with fresh token
                clear_token_cache()
                new_token = await fetch_registry_jwt_token()
                if new_token:
                    retry_response = await client.delete(
                        f"{settings.registry_url}/registry/droplets/{instance_fqdn}",
                        headers={
                            "Authorization": f"Bearer {new_token}",
                            "X-Registry-Key": settings.registry_key
                        }
                    )
                    if retry_response.status_code in [200, 204, 404]:
                        return True
                return False
            else:
                log.warning(
                    "instance_deregistration_failed",
                    status_code=response.status_code,
                    response=response.text,
                    trace_id=trace_id
                )
                return False

    except Exception as e:
        log.error(
            "instance_deregistration_error",
            error=str(e),
            name=name,
            provider=provider,
            trace_id=trace_id
        )
        return False
