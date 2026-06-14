#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - 24/7 MONITORING
======================================

Continuous monitoring for:
- Error spikes
- Memory usage
- Service health
- Deploy status
- Cost tracking
"""

import os
import asyncio
import logging
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import httpx

logger = logging.getLogger("aria.monitors")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Server endpoints
SERVERS = {
    "primary": "198.54.123.234",
    "secondary": "162.0.208.88"
}

# Service health endpoints
SERVICES = {
    "aria": ("secondary", 8710, "/health"),
    "aria-builder": ("secondary", 8720, "/health"),
    "whaletrack-live": ("primary", 8601, "/health"),
    "whaletrack-magnet": ("primary", 8600, "/health"),
    "godmode": ("primary", 3000, "/health"),  # Fixed: was 8300, actually on 3000
    "ai-brain": ("secondary", 8101, "/health"),
}

# Alert thresholds
THRESHOLDS = {
    "memory_warning": 80,       # % RAM usage
    "memory_critical": 90,
    "disk_warning": 80,         # % disk usage
    "disk_critical": 90,
    "error_rate": 10,           # errors per minute
    "response_time": 5000,      # ms
    "cost_hourly": 5.0,         # $ per hour
}


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """An alert from monitoring."""
    id: str
    level: AlertLevel
    category: str
    message: str
    server: Optional[str] = None
    service: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    
    def format_telegram(self) -> str:
        """Format alert for Telegram."""
        emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}[self.level.value]
        
        msg = f"{emoji} **{self.level.value.upper()}**\n\n"
        msg += f"{self.message}\n"
        
        if self.server:
            msg += f"\nServer: {self.server}"
        if self.service:
            msg += f"\nService: {self.service}"
        if self.value is not None and self.threshold is not None:
            msg += f"\nValue: {self.value} (threshold: {self.threshold})"
        
        msg += f"\n\n_ID: {self.id}_"
        return msg


@dataclass
class MonitorResult:
    """Result of a monitoring check."""
    healthy: bool
    alerts: List[Alert] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)


class SystemMonitor:
    """
    24/7 system monitoring.
    
    Monitors:
    - Service health
    - Server resources (CPU, memory, disk)
    - Error rates
    - Costs
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=10.0)
        self.alert_callback: Optional[Callable] = None
        self.recent_alerts: List[Alert] = []
        self.alert_cooldowns: Dict[str, datetime] = {}
        
        # Cooldown between repeated alerts (5 minutes)
        self.cooldown_duration = timedelta(minutes=5)
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    def set_alert_callback(self, callback: Callable):
        """Set callback for alerts."""
        self.alert_callback = callback
    
    def _generate_alert_id(self, category: str, target: str) -> str:
        """Generate unique alert ID."""
        import hashlib
        return hashlib.md5(f"{category}{target}{datetime.now().minute}".encode()).hexdigest()[:8]
    
    def _check_cooldown(self, alert_key: str) -> bool:
        """Check if alert is in cooldown."""
        if alert_key in self.alert_cooldowns:
            if datetime.now() - self.alert_cooldowns[alert_key] < self.cooldown_duration:
                return True
        return False
    
    async def _send_alert(self, alert: Alert):
        """Send alert via callback."""
        alert_key = f"{alert.category}_{alert.server}_{alert.service}"
        
        # Check cooldown
        if self._check_cooldown(alert_key):
            return
        
        self.alert_cooldowns[alert_key] = datetime.now()
        self.recent_alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.recent_alerts) > 100:
            self.recent_alerts = self.recent_alerts[-100:]
        
        if self.alert_callback:
            await self.alert_callback(alert)
    
    async def check_all(self) -> MonitorResult:
        """Run all monitoring checks."""
        alerts = []
        metrics = {}
        
        # Check services
        service_results = await self.check_services()
        alerts.extend(service_results.alerts)
        metrics["services"] = service_results.metrics
        
        # Check server resources
        for server_name in SERVERS.keys():
            resource_results = await self.check_server_resources(server_name)
            alerts.extend(resource_results.alerts)
            metrics[f"{server_name}_resources"] = resource_results.metrics
        
        # Send any alerts
        for alert in alerts:
            await self._send_alert(alert)
        
        return MonitorResult(
            healthy=len([a for a in alerts if a.level == AlertLevel.CRITICAL]) == 0,
            alerts=alerts,
            metrics=metrics
        )
    
    async def check_services(self) -> MonitorResult:
        """Check health of all services."""
        alerts = []
        metrics = {}
        
        for service_name, (server, port, path) in SERVICES.items():
            try:
                url = f"http://{SERVERS[server]}:{port}{path}"
                response = await self.http.get(url)
                
                healthy = response.status_code == 200
                metrics[service_name] = {
                    "healthy": healthy,
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
                
                if not healthy:
                    alerts.append(Alert(
                        id=self._generate_alert_id("service_down", service_name),
                        level=AlertLevel.CRITICAL,
                        category="service_health",
                        message=f"Service {service_name} is down",
                        server=server,
                        service=service_name,
                        value=response.status_code,
                        threshold=200
                    ))
                    
            except Exception as e:
                metrics[service_name] = {"healthy": False, "error": str(e)}
                alerts.append(Alert(
                    id=self._generate_alert_id("service_unreachable", service_name),
                    level=AlertLevel.CRITICAL,
                    category="service_health",
                    message=f"Cannot reach {service_name}: {str(e)[:50]}",
                    server=server,
                    service=service_name
                ))
        
        return MonitorResult(
            healthy=len(alerts) == 0,
            alerts=alerts,
            metrics=metrics
        )
    
    async def check_server_resources(self, server_name: str) -> MonitorResult:
        """Check server resource usage."""
        alerts = []
        metrics = {}
        
        try:
            # For secondary server (where we run), use local commands
            if server_name == "secondary":
                return await self._check_local_resources(server_name)
            
            # For other servers, use SSH
            import asyncssh
            
            server_ip = SERVERS[server_name]
            
            async with asyncssh.connect(server_ip, username="root", known_hosts=None) as conn:
                # Check memory
                mem_result = await conn.run("free -m | grep Mem")
                mem_parts = mem_result.stdout.split()
                if len(mem_parts) >= 3:
                    total_mem = int(mem_parts[1])
                    used_mem = int(mem_parts[2])
                    mem_percent = (used_mem / total_mem) * 100
                    
                    metrics["memory"] = {
                        "total_mb": total_mem,
                        "used_mb": used_mem,
                        "percent": mem_percent
                    }
                    
                    if mem_percent >= THRESHOLDS["memory_critical"]:
                        alerts.append(Alert(
                            id=self._generate_alert_id("memory_critical", server_name),
                            level=AlertLevel.CRITICAL,
                            category="resources",
                            message=f"Critical memory usage on {server_name}",
                            server=server_name,
                            value=mem_percent,
                            threshold=THRESHOLDS["memory_critical"]
                        ))
                    elif mem_percent >= THRESHOLDS["memory_warning"]:
                        alerts.append(Alert(
                            id=self._generate_alert_id("memory_warning", server_name),
                            level=AlertLevel.WARNING,
                            category="resources",
                            message=f"High memory usage on {server_name}",
                            server=server_name,
                            value=mem_percent,
                            threshold=THRESHOLDS["memory_warning"]
                        ))
                
                # Check disk
                disk_result = await conn.run("df -h / | tail -1")
                disk_parts = disk_result.stdout.split()
                if len(disk_parts) >= 5:
                    disk_percent = int(disk_parts[4].replace('%', ''))
                    
                    metrics["disk"] = {
                        "percent": disk_percent,
                        "used": disk_parts[2],
                        "available": disk_parts[3]
                    }
                    
                    if disk_percent >= THRESHOLDS["disk_critical"]:
                        alerts.append(Alert(
                            id=self._generate_alert_id("disk_critical", server_name),
                            level=AlertLevel.CRITICAL,
                            category="resources",
                            message=f"Critical disk usage on {server_name}",
                            server=server_name,
                            value=disk_percent,
                            threshold=THRESHOLDS["disk_critical"]
                        ))
                
                # Check load
                load_result = await conn.run("cat /proc/loadavg")
                load_parts = load_result.stdout.split()
                if len(load_parts) >= 3:
                    metrics["load"] = {
                        "1min": float(load_parts[0]),
                        "5min": float(load_parts[1]),
                        "15min": float(load_parts[2])
                    }
                    
        except Exception as e:
            logger.error(f"Resource check failed for {server_name}: {e}")
            metrics["error"] = str(e)
        
        return MonitorResult(
            healthy=len([a for a in alerts if a.level == AlertLevel.CRITICAL]) == 0,
            alerts=alerts,
            metrics=metrics
        )
    
    async def _check_local_resources(self, server_name: str) -> MonitorResult:
        """Check local server resources (no SSH needed)."""
        alerts = []
        metrics = {}
        
        try:
            import psutil
            
            # Memory
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            metrics["memory"] = {
                "total_mb": mem.total // (1024 * 1024),
                "used_mb": mem.used // (1024 * 1024),
                "percent": mem_percent
            }
            
            if mem_percent >= THRESHOLDS["memory_critical"]:
                alerts.append(Alert(
                    id=self._generate_alert_id("memory_critical", server_name),
                    level=AlertLevel.CRITICAL,
                    category="resources",
                    message=f"Critical memory usage on {server_name}",
                    server=server_name,
                    value=mem_percent,
                    threshold=THRESHOLDS["memory_critical"]
                ))
            elif mem_percent >= THRESHOLDS["memory_warning"]:
                alerts.append(Alert(
                    id=self._generate_alert_id("memory_warning", server_name),
                    level=AlertLevel.WARNING,
                    category="resources",
                    message=f"High memory usage on {server_name}",
                    server=server_name,
                    value=mem_percent,
                    threshold=THRESHOLDS["memory_warning"]
                ))
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            metrics["disk"] = {
                "percent": disk_percent,
                "used": f"{disk.used // (1024**3)}G",
                "available": f"{disk.free // (1024**3)}G"
            }
            
            if disk_percent >= THRESHOLDS["disk_critical"]:
                alerts.append(Alert(
                    id=self._generate_alert_id("disk_critical", server_name),
                    level=AlertLevel.CRITICAL,
                    category="resources",
                    message=f"Critical disk usage on {server_name}",
                    server=server_name,
                    value=disk_percent,
                    threshold=THRESHOLDS["disk_critical"]
                ))
            
            # Load
            load = psutil.getloadavg()
            metrics["load"] = {
                "1min": load[0],
                "5min": load[1],
                "15min": load[2]
            }
            
        except Exception as e:
            logger.error(f"Local resource check failed: {e}")
            metrics["error"] = str(e)
        
        return MonitorResult(
            healthy=len([a for a in alerts if a.level == AlertLevel.CRITICAL]) == 0,
            alerts=alerts,
            metrics=metrics
        )
    
    async def check_error_logs(self, server_name: str, minutes: int = 5) -> MonitorResult:
        """Check for error spikes in logs."""
        alerts = []
        metrics = {}
        
        try:
            import asyncssh
            
            server_ip = SERVERS[server_name]
            
            async with asyncssh.connect(server_ip, username="root", known_hosts=None) as conn:
                # Count recent errors in journalctl
                result = await conn.run(
                    f"journalctl --since '{minutes} minutes ago' -p err --no-pager | wc -l"
                )
                error_count = int(result.stdout.strip())
                error_rate = error_count / minutes
                
                metrics["error_count"] = error_count
                metrics["error_rate_per_min"] = error_rate
                
                if error_rate >= THRESHOLDS["error_rate"]:
                    # Get sample of errors
                    sample_result = await conn.run(
                        f"journalctl --since '{minutes} minutes ago' -p err --no-pager | tail -5"
                    )
                    
                    alerts.append(Alert(
                        id=self._generate_alert_id("error_spike", server_name),
                        level=AlertLevel.WARNING,
                        category="errors",
                        message=f"Error spike on {server_name}: {error_rate:.1f}/min\n\n{sample_result.stdout[:500]}",
                        server=server_name,
                        value=error_rate,
                        threshold=THRESHOLDS["error_rate"]
                    ))
                    
        except Exception as e:
            logger.error(f"Error log check failed: {e}")
        
        return MonitorResult(
            healthy=len(alerts) == 0,
            alerts=alerts,
            metrics=metrics
        )
    
    def get_recent_alerts(self, minutes: int = 60) -> List[Alert]:
        """Get alerts from the last N minutes."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [a for a in self.recent_alerts if a.created_at > cutoff]


# ============================================================================
# MONITORING LOOP
# ============================================================================

class MonitoringDaemon:
    """
    Background monitoring daemon.
    
    Runs checks at regular intervals.
    """
    
    def __init__(self, check_interval: int = 60):
        self.monitor = SystemMonitor()
        self.check_interval = check_interval
        self.running = False
    
    async def start(self, alert_callback: Optional[Callable] = None):
        """Start the monitoring loop."""
        self.running = True
        
        if alert_callback:
            self.monitor.set_alert_callback(alert_callback)
        
        logger.info("Monitoring daemon started")
        
        while self.running:
            try:
                result = await self.monitor.check_all()
                
                if not result.healthy:
                    logger.warning(f"System unhealthy: {len(result.alerts)} alerts")
                else:
                    logger.debug("All checks passed")
                    
            except Exception as e:
                logger.error(f"Monitoring cycle failed: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the monitoring loop."""
        self.running = False


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_monitor: Optional[SystemMonitor] = None


def get_monitor() -> SystemMonitor:
    """Get or create global monitor."""
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor


async def quick_health_check() -> Dict:
    """Quick health check of all services."""
    monitor = get_monitor()
    result = await monitor.check_services()
    return result.metrics


async def get_server_status(server: str) -> Dict:
    """Get status of a specific server."""
    monitor = get_monitor()
    result = await monitor.check_server_resources(server)
    return result.metrics

