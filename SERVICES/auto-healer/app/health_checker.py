"""
Health Checker - Detection layer for service health
"""
import asyncio
import subprocess
import httpx
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

from .config import HTTP_TIMEOUT, HEALTH_CHECK_INTERVAL
from .registry import ServiceDefinition, registry

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"
    STOPPED = "stopped"
    RESTARTING = "restarting"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check for a single service."""
    service_name: str
    status: ServiceStatus
    timestamp: datetime
    response_time_ms: Optional[int] = None
    http_status_code: Optional[int] = None
    systemd_status: Optional[str] = None
    error: Optional[str] = None
    consecutive_failures: int = 0
    
    def is_healthy(self) -> bool:
        return self.status == ServiceStatus.HEALTHY
    
    def to_dict(self) -> dict:
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "http_status_code": self.http_status_code,
            "systemd_status": self.systemd_status,
            "error": self.error,
            "consecutive_failures": self.consecutive_failures,
        }


class HealthChecker:
    """
    Monitors service health via HTTP health endpoints and systemd status.
    """
    
    def __init__(self):
        self.results: Dict[str, HealthCheckResult] = {}
        self.consecutive_failures: Dict[str, int] = {}
        self._running = False
    
    async def check_http_health(self, service: ServiceDefinition) -> tuple[bool, int, Optional[str]]:
        """
        Check service health via HTTP endpoint.
        Returns: (is_healthy, response_time_ms, error_message)
        """
        url = f"http://localhost:{service.port}{service.health_endpoint}"
        start_time = datetime.now()
        
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                response = await client.get(url)
                response_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                if response.status_code == 200:
                    return True, response_time, None
                else:
                    return False, response_time, f"HTTP {response.status_code}"
                    
        except httpx.TimeoutException:
            return False, HTTP_TIMEOUT * 1000, "Timeout"
        except httpx.ConnectError:
            return False, 0, "Connection refused"
        except Exception as e:
            return False, 0, str(e)
    
    def check_systemd_status(self, service: ServiceDefinition) -> tuple[str, Optional[str]]:
        """
        Check systemd service status.
        Returns: (status, error_message)
        """
        try:
            # Check if service is active
            result = subprocess.run(
                ["systemctl", "is-active", service.systemd_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            status = result.stdout.strip()
            
            if status == "active":
                return "active", None
            elif status == "activating":
                return "activating", "Service is starting"
            elif status == "inactive":
                return "inactive", "Service is stopped"
            elif status == "failed":
                # Get failure reason
                reason_result = subprocess.run(
                    ["systemctl", "status", service.systemd_name, "--no-pager"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return "failed", reason_result.stdout[:500]
            else:
                return status, f"Unknown status: {status}"
                
        except subprocess.TimeoutExpired:
            return "unknown", "Systemctl timeout"
        except FileNotFoundError:
            return "unknown", "Systemctl not found (not on Linux?)"
        except Exception as e:
            return "unknown", str(e)
    
    async def check_service(self, service: ServiceDefinition) -> HealthCheckResult:
        """
        Perform comprehensive health check on a service.
        """
        timestamp = datetime.now()
        
        # Check systemd status first
        systemd_status, systemd_error = self.check_systemd_status(service)
        
        # If systemd says it's not running, don't bother with HTTP
        if systemd_status in ["inactive", "failed"]:
            self.consecutive_failures[service.name] = self.consecutive_failures.get(service.name, 0) + 1
            return HealthCheckResult(
                service_name=service.name,
                status=ServiceStatus.STOPPED if systemd_status == "inactive" else ServiceStatus.UNHEALTHY,
                timestamp=timestamp,
                systemd_status=systemd_status,
                error=systemd_error,
                consecutive_failures=self.consecutive_failures[service.name],
            )
        
        # If systemd is activating, mark as restarting
        if systemd_status == "activating":
            return HealthCheckResult(
                service_name=service.name,
                status=ServiceStatus.RESTARTING,
                timestamp=timestamp,
                systemd_status=systemd_status,
                error=systemd_error,
                consecutive_failures=self.consecutive_failures.get(service.name, 0),
            )
        
        # Systemd says active, check HTTP endpoint
        is_healthy, response_time, http_error = await self.check_http_health(service)
        
        if is_healthy:
            # Reset consecutive failures on success
            self.consecutive_failures[service.name] = 0
            return HealthCheckResult(
                service_name=service.name,
                status=ServiceStatus.HEALTHY,
                timestamp=timestamp,
                response_time_ms=response_time,
                http_status_code=200,
                systemd_status=systemd_status,
                consecutive_failures=0,
            )
        else:
            self.consecutive_failures[service.name] = self.consecutive_failures.get(service.name, 0) + 1
            return HealthCheckResult(
                service_name=service.name,
                status=ServiceStatus.UNREACHABLE if "Connection refused" in (http_error or "") else ServiceStatus.UNHEALTHY,
                timestamp=timestamp,
                response_time_ms=response_time,
                systemd_status=systemd_status,
                error=http_error,
                consecutive_failures=self.consecutive_failures[service.name],
            )
    
    async def check_all_services(self) -> Dict[str, HealthCheckResult]:
        """
        Check health of all registered services.
        """
        services = registry.get_all()
        tasks = [self.check_service(svc) for svc in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service = services[i]
                result = HealthCheckResult(
                    service_name=service.name,
                    status=ServiceStatus.UNKNOWN,
                    timestamp=datetime.now(),
                    error=str(result),
                    consecutive_failures=self.consecutive_failures.get(service.name, 0) + 1,
                )
                self.consecutive_failures[service.name] = result.consecutive_failures
            
            self.results[result.service_name] = result
        
        return self.results
    
    def get_unhealthy_services(self) -> List[HealthCheckResult]:
        """Get all services that are not healthy."""
        return [r for r in self.results.values() if not r.is_healthy()]
    
    def get_critical_down(self) -> List[HealthCheckResult]:
        """Get critical services that are down."""
        critical_names = {s.name for s in registry.get_critical()}
        return [
            r for r in self.results.values() 
            if r.service_name in critical_names and not r.is_healthy()
        ]
    
    def get_summary(self) -> dict:
        """Get health summary."""
        total = len(self.results)
        healthy = sum(1 for r in self.results.values() if r.is_healthy())
        critical_down = len(self.get_critical_down())
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_services": total,
            "healthy": healthy,
            "unhealthy": total - healthy,
            "critical_down": critical_down,
            "health_score": round(healthy / total * 100, 1) if total > 0 else 0,
            "services": {name: r.to_dict() for name, r in self.results.items()},
        }
    
    async def run_continuous(self, callback=None):
        """
        Run continuous health checking loop.
        Optionally calls callback(results) after each cycle.
        """
        self._running = True
        logger.info(f"Starting continuous health checks every {HEALTH_CHECK_INTERVAL}s")
        
        while self._running:
            try:
                results = await self.check_all_services()
                
                # Log summary
                summary = self.get_summary()
                logger.info(
                    f"Health check: {summary['healthy']}/{summary['total_services']} healthy, "
                    f"{summary['critical_down']} critical down"
                )
                
                # Call callback if provided
                if callback:
                    await callback(results)
                    
            except Exception as e:
                logger.error(f"Health check cycle failed: {e}")
            
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
    
    def stop(self):
        """Stop the continuous health check loop."""
        self._running = False


# Global health checker instance
health_checker = HealthChecker()











