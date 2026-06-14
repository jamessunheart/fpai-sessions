"""
Auto-Healer Configuration
"""
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
import os

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Service Configuration
SERVICE_NAME = "auto-healer"
SERVICE_PORT = int(os.getenv("PORT", "8180"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Health Check Settings
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # seconds
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "5"))  # seconds

# Healing Settings
MAX_AUTO_RESTARTS = int(os.getenv("MAX_AUTO_RESTARTS", "3"))
RESTART_COOLDOWN = int(os.getenv("RESTART_COOLDOWN", "60"))  # seconds
HEALING_TIMEOUT = int(os.getenv("HEALING_TIMEOUT", "120"))  # seconds

# Escalation Settings
CRITICAL_DOWN_THRESHOLD = int(os.getenv("CRITICAL_DOWN_THRESHOLD", "300"))  # 5 minutes
RECURRING_FAILURE_THRESHOLD = int(os.getenv("RECURRING_FAILURE_THRESHOLD", "5"))  # times in 24h

# Alert Settings
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "james@fullpotential.ai")
COMMUNICATION_HUB_URL = os.getenv("COMMUNICATION_HUB_URL", "http://localhost:8800")
GOD_MODE_URL = os.getenv("GOD_MODE_URL", "http://localhost:8355")

# Database
DB_PATH = DATA_DIR / "outcomes.db"
REGISTRY_PATH = DATA_DIR / "registry.json"











