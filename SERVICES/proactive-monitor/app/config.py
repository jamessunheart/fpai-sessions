"""Configuration for Proactive Monitor"""
from pydantic_settings import BaseSettings
from typing import List, Dict


class Settings(BaseSettings):
    """Monitor settings"""

    # Service Info
    SERVICE_NAME: str = "proactive-monitor"
    DROPLET_ID: int = 108
    APP_VERSION: str = "1.0.0"
    PORT: int = 8108
    DEBUG: bool = False

    # Chief of Staff Integration
    CHIEF_OF_STAFF_URL: str = "http://localhost:8107"

    # Monitoring Configuration
    CHECK_INTERVAL_SECONDS: int = 300  # 5 minutes
    HEALTH_CHECK_TIMEOUT: int = 10  # seconds

    # Services to Monitor
    MONITORED_SERVICES: str = """
    fp-index:8550:critical
    alerts:8766:critical
    chief-of-staff:8107:critical
    credits-gateway:8765:high
    whaletrack-magnet:8600:high
    """

    @property
    def services(self) -> List[Dict[str, str]]:
        """Parse monitored services"""
        services = []
        for line in self.MONITORED_SERVICES.strip().split('\n'):
            line = line.strip()
            if line:
                parts = line.split(':')
                if len(parts) == 3:
                    services.append({
                        'name': parts[0],
                        'port': int(parts[1]),
                        'priority': parts[2]
                    })
        return services

    # Thresholds
    RESPONSE_TIME_SLOW_THRESHOLD: float = 2.0  # seconds
    RESPONSE_TIME_VERY_SLOW_THRESHOLD: float = 5.0  # seconds

    # System Monitoring
    MONITOR_SYSTEM_RESOURCES: bool = True
    DISK_USAGE_THRESHOLD: float = 90.0  # percent
    MEMORY_USAGE_THRESHOLD: float = 90.0  # percent
    CPU_LOAD_THRESHOLD: float = 80.0  # percent

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
