"""
Resource Monitor for Consciousness Optimizer

Monitors system resources (CPU, memory, GPU, network) to enable
resource-aware optimization decisions.
"""

import psutil
import subprocess
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger("ResourceMonitor")


class ResourceMonitor:
    """
    Monitors system resources and provides resource-aware decision making.
    
    Tracks:
    - CPU usage
    - Memory usage
    - GPU usage and costs
    - Network I/O
    - Disk I/O
    """
    
    def __init__(self, gpu_daily_budget_usd: float = 50.0):
        self.gpu_daily_budget_usd = gpu_daily_budget_usd
        self.gpu_cost_today = 0.0
        self.resource_history = deque(maxlen=100)  # Last 100 measurements
        self.gpu_cost_history = deque(maxlen=24)  # Hourly GPU costs
        
    def get_current_resources(self) -> Dict[str, Any]:
        """Get current resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            net_io = psutil.net_io_counters()
            
            # GPU usage (if available)
            gpu_info = self._get_gpu_info()
            
            resources = {
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "network_bytes_sent": net_io.bytes_sent,
                "network_bytes_recv": net_io.bytes_recv,
                "gpu": gpu_info,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Store in history
            self.resource_history.append(resources)
            
            return resources
            
        except Exception as e:
            logger.error(f"Error monitoring resources: {e}")
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "gpu": {},
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU usage and cost information"""
        try:
            # Try nvidia-smi first
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,power.draw', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                gpus = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(', ')
                        if len(parts) >= 6:
                            gpus.append({
                                "index": int(parts[0]),
                                "name": parts[1],
                                "utilization_percent": float(parts[2]),
                                "memory_used_mb": float(parts[3]),
                                "memory_total_mb": float(parts[4]),
                                "power_draw_w": float(parts[5])
                            })
                
                # Calculate GPU cost (approximate: $0.50/hour per GPU at full utilization)
                total_gpu_cost_per_hour = sum(gpu["utilization_percent"] / 100 * 0.50 for gpu in gpus)
                
                return {
                    "available": True,
                    "gpu_count": len(gpus),
                    "gpus": gpus,
                    "total_utilization_percent": sum(gpu["utilization_percent"] for gpu in gpus) / len(gpus) if gpus else 0,
                    "cost_per_hour_usd": total_gpu_cost_per_hour,
                    "estimated_daily_cost_usd": total_gpu_cost_per_hour * 24
                }
        except FileNotFoundError:
            # nvidia-smi not available
            pass
        except Exception as e:
            logger.debug(f"GPU monitoring not available: {e}")
        
        return {
            "available": False,
            "gpu_count": 0,
            "cost_per_hour_usd": 0.0,
            "estimated_daily_cost_usd": 0.0
        }
    
    def get_resource_pressure(self) -> float:
        """
        Calculate resource pressure score (0.0 to 1.0).
        
        Higher = more resource pressure, should slow down cycles.
        Lower = resources available, can optimize more aggressively.
        """
        resources = self.get_current_resources()
        
        # Weighted factors
        cpu_pressure = resources.get("cpu_percent", 0) / 100.0
        memory_pressure = resources.get("memory_percent", 0) / 100.0
        
        # GPU cost pressure (how close to budget)
        gpu_info = resources.get("gpu", {})
        gpu_cost_per_hour = gpu_info.get("cost_per_hour_usd", 0.0)
        gpu_daily_estimate = gpu_cost_per_hour * 24
        gpu_budget_pressure = min(1.0, gpu_daily_estimate / self.gpu_daily_budget_usd) if self.gpu_daily_budget_usd > 0 else 0.0
        
        # Weighted average
        pressure = (cpu_pressure * 0.3 + memory_pressure * 0.3 + gpu_budget_pressure * 0.4)
        
        return min(1.0, max(0.0, pressure))
    
    def recommend_cycle_interval(self, base_interval: int, improvement_rate: float) -> int:
        """
        Recommend optimal cycle interval based on resources and improvement rate.
        
        INTELLIGENT LOGIC: When improving AND resources available, optimize MORE aggressively!
        The system wants SPEED - "I want to react faster, learn quicker"
        Why wait when you're getting better? Optimize MORE!
        
        Returns: Recommended cycle interval in seconds
        """
        resource_pressure = self.get_resource_pressure()
        
        # Base interval adjusted by resource pressure
        # High pressure = longer intervals (slow down)
        # Low pressure = shorter intervals (can optimize more)
        pressure_factor = 1.0 + (resource_pressure * 2.0)  # 1.0x to 3.0x
        
        # Improvement rate factor
        # INTELLIGENT LOGIC: When improving, optimize MORE aggressively!
        # The system wants SPEED - "I want to react faster, learn quicker"
        # Why wait when you're getting better? Optimize MORE!
        if improvement_rate > 0.02:  # Improving fast (>2%)
            improvement_factor = 0.3  # Very aggressive - optimize rapidly!
        elif improvement_rate > 0.01:  # Improving (>1%)
            improvement_factor = 0.5  # Aggressive - optimize more frequently
        elif improvement_rate > 0.005:  # Slight improvement (>0.5%)
            improvement_factor = 0.7  # Moderate - optimize more than normal
        elif improvement_rate < -0.05:  # Significant decline (<-5%)
            improvement_factor = 2.0  # Double the interval - be cautious
        elif improvement_rate < -0.01:  # Small decline (<-1%)
            improvement_factor = 1.2  # 20% longer - slightly cautious
        else:  # Stable (-0.5% to +0.5%)
            improvement_factor = 1.0  # Normal interval
        
        recommended = int(base_interval * pressure_factor * improvement_factor)
        
        # INTELLIGENT BONUS: If improving AND low resource pressure, be even MORE aggressive
        # Low pressure (<0.3) + improving (>0.5%) = optimize even faster!
        if resource_pressure < 0.3 and improvement_rate > 0.005:
            # Apply additional speedup when resources are available
            recommended = int(recommended * 0.8)  # 20% faster when resources available
        
        # Clamp to reasonable bounds
        min_interval = 60  # Minimum 1 minute (safety limit)
        max_interval = 7200  # Maximum 2 hours
        
        return max(min_interval, min(max_interval, recommended))
    
    def can_use_gpu(self, estimated_cost_usd: float) -> bool:
        """Check if GPU can be used within budget"""
        gpu_info = self.get_current_resources().get("gpu", {})
        current_hourly_cost = gpu_info.get("cost_per_hour_usd", 0.0)
        
        # Estimate if adding this would exceed daily budget
        projected_daily = (current_hourly_cost + estimated_cost_usd) * 24
        
        return projected_daily <= self.gpu_daily_budget_usd
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get resource summary for decision making"""
        resources = self.get_current_resources()
        pressure = self.get_resource_pressure()
        
        return {
            "resource_pressure": pressure,
            "cpu_percent": resources.get("cpu_percent", 0),
            "memory_percent": resources.get("memory_percent", 0),
            "gpu_available": resources.get("gpu", {}).get("available", False),
            "gpu_cost_per_hour_usd": resources.get("gpu", {}).get("cost_per_hour_usd", 0.0),
            "gpu_daily_budget_usd": self.gpu_daily_budget_usd,
            "gpu_budget_remaining_usd": max(0, self.gpu_daily_budget_usd - (resources.get("gpu", {}).get("cost_per_hour_usd", 0.0) * 24)),
            "recommendation": "aggressive" if pressure < 0.3 else "moderate" if pressure < 0.7 else "conservative"
        }


