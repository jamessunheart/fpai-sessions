"""
Configuration for Chief of Staff Service
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""

    # Service Info
    SERVICE_NAME: str = "chief-of-staff"
    DROPLET_ID: int = 107
    APP_VERSION: str = "1.0.0"
    PORT: int = 8107
    DEBUG: bool = False

    # Alerts Integration
    ALERTS_SERVICE_URL: str = "http://localhost:8765"

    # Decision Filter
    DECISION_WINDOW_DAYS: int = 30
    DECISION_FILTER_KEYWORDS: str = "revenue,booking,conversion,user,payment,zen village,retreat,proof,clarity"

    @property
    def decision_keywords(self) -> List[str]:
        """Parse keywords from comma-separated string"""
        return [k.strip() for k in self.DECISION_FILTER_KEYWORDS.split(",")]

    # Urgency Thresholds
    URGENT_THRESHOLD_REVENUE_DROP: float = 0.20  # 20% drop
    URGENT_THRESHOLD_ERROR_RATE: float = 0.05  # 5% error rate
    URGENT_THRESHOLD_UPTIME: float = 95.0  # 95% uptime

    # Notification Schedule
    DIGEST_TIME: str = "09:00"  # Daily digest time (HH:MM)
    SUMMARY_DAY: str = "monday"  # Weekly summary day
    SUMMARY_TIME: str = "09:00"  # Weekly summary time

    # Learning
    TRACK_USER_ACTIONS: bool = True
    AUTO_SUGGEST_THRESHOLD: int = 3  # Suggest automation after N occurrences

    # Signal Storage
    MAX_SIGNALS_HISTORY: int = 10000
    SIGNAL_RETENTION_DAYS: int = 90

    # Cockpit integration (Priority + Money views)
    COCKPIT_ROOT: str = "/Users/jamessunheart/FPAI_Cockpit"
    SERVICES_SUBDIR: str = "SERVICES"
    STATE_SUBDIR: str = "core/STATE"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
