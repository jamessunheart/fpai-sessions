"""
INFRASTRUCTURE SENSOR
=====================

Monitors server infrastructure for health, costs, and optimization opportunities.

Watches:
- Service health (systemd status)
- Memory/CPU usage
- GPU fleet status (Vast.ai)
- Cost tracking
- Disk usage
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import httpx

from ..proactive import Signal, Priority, ActionType

logger = logging.getLogger("aria.sensors.infrastructure")

# Endpoints
GPU_SCALER_URL = os.getenv("GPU_SCALER_URL", "http://162.0.208.88:8450")
PRIMARY_SERVER = os.getenv("PRIMARY_SERVER", "198.54.123.234")
SECONDARY_SERVER = os.getenv("SECONDARY_SERVER", "162.0.208.88")

# Thresholds
MEMORY_WARNING_THRESHOLD = 80  # % usage
MEMORY_CRITICAL_THRESHOLD = 90
GPU_IDLE_MINUTES = 10  # Minutes before suggesting scale down
COST_ALERT_THRESHOLD = 1.0  # $ per hour


class InfrastructureSensor:
    """
    Sensor for infrastructure health and costs.
    
    Monitors:
    - GPU fleet via Smart Scaler
    - Service health via API
    - Memory and CPU usage
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=15.0)
        self.last_gpu_count = None
        self.last_memory_alert = None
        logger.info("InfrastructureSensor initialized")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def sense(self) -> List[Signal]:
        """
        Sense infrastructure state and generate signals.
        
        Returns list of signals detected.
        """
        signals = []
        
        # 1. Check GPU fleet status
        gpu_signals = await self._check_gpu_fleet()
        signals.extend(gpu_signals)
        
        # 2. Check service health
        service_signals = await self._check_services()
        signals.extend(service_signals)
        
        # 3. Check memory usage (if we can reach the servers)
        memory_signals = await self._check_memory()
        signals.extend(memory_signals)
        
        return signals
    
    async def _check_gpu_fleet(self) -> List[Signal]:
        """Check GPU fleet status and costs."""
        signals = []
        
        try:
            r = await self.http.get(f"{GPU_SCALER_URL}/status")
            if r.status_code != 200:
                return signals
            
            data = r.json()
            gpu_count = data.get("gpus", 0)
            hourly_cost = data.get("hourly_cost", 0)
            queue_depth = data.get("queue_depth", 0)
            pending_requests = data.get("pending_requests", [])
            
            # Track GPU count changes
            if self.last_gpu_count is not None and gpu_count != self.last_gpu_count:
                change = gpu_count - self.last_gpu_count
                if change > 0:
                    signals.append(Signal(
                        source="infrastructure",
                        signal_type="gpu_scaled_up",
                        priority=Priority.LOW,
                        title=f"📈 GPU Fleet Expanded to {gpu_count}",
                        description=f"Added {change} GPU(s). Current cost: ${hourly_cost:.2f}/hr",
                        data={"gpu_count": gpu_count, "hourly_cost": hourly_cost},
                        action_type=ActionType.NOTIFY
                    ))
                else:
                    signals.append(Signal(
                        source="infrastructure",
                        signal_type="gpu_scaled_down",
                        priority=Priority.LOW,
                        title=f"📉 GPU Fleet Reduced to {gpu_count}",
                        description=f"Removed {-change} GPU(s). Saving ${-change * 0.05:.2f}/hr",
                        data={
                            "gpu_count": gpu_count, 
                            "hourly_cost": hourly_cost,
                            "savings": -change * 0.05
                        },
                        action_type=ActionType.NOTIFY
                    ))
            
            self.last_gpu_count = gpu_count
            
            # Check if GPUs are idle and can be scaled down
            if gpu_count > 1 and queue_depth == 0:
                signals.append(Signal(
                    source="infrastructure",
                    signal_type="gpu_idle_scale_down",
                    priority=Priority.LOW,
                    title="💤 GPU Fleet Idle - Scaling Down",
                    description=f"{gpu_count} GPUs running with empty queue. Auto-scaling to save costs.",
                    data={
                        "current_gpus": gpu_count,
                        "target_gpus": 1,
                        "savings": (gpu_count - 1) * 0.05
                    },
                    action_type=ActionType.AUTO_EXECUTE,
                    suggested_action="Scale GPU fleet down to 1"
                ))
            
            # Alert on high costs
            if hourly_cost > COST_ALERT_THRESHOLD:
                signals.append(Signal(
                    source="infrastructure",
                    signal_type="high_gpu_cost",
                    priority=Priority.MEDIUM,
                    title=f"💰 GPU Cost Alert: ${hourly_cost:.2f}/hr",
                    description=f"Running {gpu_count} GPUs at ${hourly_cost:.2f}/hr. "
                               f"Daily cost: ${hourly_cost * 24:.2f}",
                    data={"gpu_count": gpu_count, "hourly_cost": hourly_cost},
                    action_type=ActionType.NOTIFY
                ))
            
            # Note pending approval requests
            for req in pending_requests:
                signals.append(Signal(
                    source="infrastructure",
                    signal_type="pending_gpu_request",
                    priority=Priority.MEDIUM,
                    title=f"📋 GPU Request Pending: {req.get('id', 'unknown')}",
                    description=req.get("reason", "Unknown reason"),
                    data=req,
                    action_type=ActionType.NOTIFY
                ))
        
        except Exception as e:
            logger.warning(f"GPU fleet check error: {e}")
        
        return signals
    
    async def _check_services(self) -> List[Signal]:
        """Check critical service health."""
        signals = []
        
        # Critical services to check
        services = [
            {"name": "aria-core", "url": f"http://{SECONDARY_SERVER}:8180/health"},
            {"name": "aria-telegram", "url": f"http://{SECONDARY_SERVER}:8710/health"},
            {"name": "whaletrack-magnet", "url": f"http://{PRIMARY_SERVER}:8601/health"},
            {"name": "gpu-bridge", "url": f"http://{SECONDARY_SERVER}:8400/health"},
            {"name": "ollama", "url": f"http://{SECONDARY_SERVER}:11434/api/tags"},
        ]
        
        for service in services:
            try:
                r = await self.http.get(service["url"], timeout=5.0)
                if r.status_code != 200:
                    signals.append(Signal(
                        source="infrastructure",
                        signal_type="service_unhealthy",
                        priority=Priority.HIGH,
                        title=f"🔴 {service['name']} Unhealthy",
                        description=f"Service returned HTTP {r.status_code}",
                        data={"service": service["name"], "status_code": r.status_code},
                        action_type=ActionType.NOTIFY
                    ))
            except httpx.TimeoutException:
                signals.append(Signal(
                    source="infrastructure",
                    signal_type="service_timeout",
                    priority=Priority.HIGH,
                    title=f"⏰ {service['name']} Timeout",
                    description=f"Service did not respond within 5 seconds",
                    data={"service": service["name"]},
                    action_type=ActionType.NOTIFY
                ))
            except Exception as e:
                signals.append(Signal(
                    source="infrastructure",
                    signal_type="service_unreachable",
                    priority=Priority.URGENT,
                    title=f"❌ {service['name']} Unreachable",
                    description=f"Could not connect: {str(e)[:100]}",
                    data={"service": service["name"], "error": str(e)},
                    action_type=ActionType.NOTIFY
                ))
        
        return signals
    
    async def _check_memory(self) -> List[Signal]:
        """Check server memory usage."""
        signals = []
        
        # This would ideally connect to a monitoring endpoint
        # For now, we check via God Mode dashboard if available
        try:
            r = await self.http.get(f"http://{PRIMARY_SERVER}:8120/api/system/stats", timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                memory_pct = data.get("memory_percent", 0)
                
                # Avoid duplicate alerts
                now = datetime.utcnow()
                if self.last_memory_alert and now - self.last_memory_alert < timedelta(minutes=30):
                    return signals
                
                if memory_pct >= MEMORY_CRITICAL_THRESHOLD:
                    self.last_memory_alert = now
                    signals.append(Signal(
                        source="infrastructure",
                        signal_type="memory_critical",
                        priority=Priority.URGENT,
                        title=f"🔴 CRITICAL: Primary Server Memory at {memory_pct:.0f}%",
                        description="Server may become unresponsive. Consider stopping non-essential services.",
                        data={
                            "server": "primary",
                            "memory_percent": memory_pct
                        },
                        action_type=ActionType.PROPOSE,
                        suggested_action="Stop non-essential services on primary server"
                    ))
                elif memory_pct >= MEMORY_WARNING_THRESHOLD:
                    self.last_memory_alert = now
                    signals.append(Signal(
                        source="infrastructure",
                        signal_type="memory_warning",
                        priority=Priority.MEDIUM,
                        title=f"⚠️ Primary Server Memory at {memory_pct:.0f}%",
                        description="Memory usage is elevated. Monitoring situation.",
                        data={
                            "server": "primary",
                            "memory_percent": memory_pct
                        },
                        action_type=ActionType.NOTIFY
                    ))
        
        except Exception as e:
            logger.debug(f"Memory check error: {e}")
        
        return signals
    
    async def get_status(self) -> Dict:
        """Get sensor status."""
        return {
            "name": "infrastructure",
            "last_gpu_count": self.last_gpu_count,
            "gpu_scaler_url": GPU_SCALER_URL,
            "primary_server": PRIMARY_SERVER,
            "secondary_server": SECONDARY_SERVER
        }


