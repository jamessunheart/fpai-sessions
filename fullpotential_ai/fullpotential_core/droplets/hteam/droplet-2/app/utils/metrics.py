import time
import psutil
from datetime import datetime
from typing import Dict, Any


class MetricsCollector:
    """Collect and track droplet metrics"""
    
    def __init__(self):
        self.startup_time = time.time()
        self.request_count = 0
        self.error_count = 0
    
    def increment_requests(self):
        """Increment request counter"""
        self.request_count += 1
    
    def increment_errors(self):
        """Increment error counter"""
        self.error_count += 1
    
    def get_uptime_seconds(self) -> int:
        """Get uptime in seconds"""
        return int(time.time() - self.startup_time)
    
    def get_cpu_percent(self) -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=0.1)
    
    def get_memory_mb(self) -> int:
        """Get current memory usage in MB"""
        return int(psutil.virtual_memory().used / 1024 / 1024)
    
    def get_requests_per_minute(self) -> int:
        """Calculate requests per minute"""
        uptime_minutes = max(self.get_uptime_seconds() / 60, 1)
        return int(self.request_count / uptime_minutes)
    
    def get_startup_timestamp(self) -> str:
        """Get startup timestamp in ISO format"""
        return datetime.fromtimestamp(self.startup_time).isoformat() + "Z"
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + "Z"
    
    def get_state_metrics(self) -> Dict[str, Any]:
        """Get all state metrics"""
        return {
            "cpu_percent": self.get_cpu_percent(),
            "memory_mb": self.get_memory_mb(),
            "uptime_seconds": self.get_uptime_seconds(),
            "requests_total": self.request_count,
            "requests_per_minute": self.get_requests_per_minute(),
            "errors_last_hour": self.error_count,
            "last_restart": self.get_startup_timestamp()
        }


# Global metrics instance
metrics = MetricsCollector()