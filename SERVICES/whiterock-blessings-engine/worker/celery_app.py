"""
WhiteRock Blessings Engine - Celery Configuration
Background task worker for CORA decay and scheduled jobs.
"""

from celery import Celery
from celery.schedules import crontab
import os

# Load settings
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "whiterock_blessings",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["worker.tasks"]
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Run CORA decay check monthly on the 1st at 3am UTC
    "monthly-cora-decay": {
        "task": "worker.tasks.run_cora_decay",
        "schedule": crontab(day_of_month="1", hour=3, minute=0),
    },
    
    # Check for decay warnings daily at 9am UTC
    "daily-decay-warnings": {
        "task": "worker.tasks.send_decay_warnings",
        "schedule": crontab(hour=9, minute=0),
    },
    
    # Daily health check at midnight
    "daily-health-check": {
        "task": "worker.tasks.health_check",
        "schedule": crontab(hour=0, minute=0),
    },
    
    # Weekly audit log cleanup on Sundays at 4am UTC
    "weekly-audit-cleanup": {
        "task": "worker.tasks.cleanup_old_audit_logs",
        "schedule": crontab(day_of_week="sunday", hour=4, minute=0),
        "kwargs": {"days_to_keep": 365},
    },
}

# Task routing
celery_app.conf.task_routes = {
    "worker.tasks.run_cora_decay": {"queue": "critical"},
    "worker.tasks.send_decay_warnings": {"queue": "notifications"},
    "worker.tasks.process_tithe_receipts": {"queue": "notifications"},
    "worker.tasks.health_check": {"queue": "maintenance"},
    "worker.tasks.cleanup_old_audit_logs": {"queue": "maintenance"},
}

