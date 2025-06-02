"""
Celery configuration
"""

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Create Celery instance
celery_app = Celery(
    "emberframe",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.file_tasks",
        "app.tasks.maintenance_tasks"
    ]
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_disable_rate_limits=True,
    worker_prefetch_multiplier=1
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-temp-files": {
        "task": "app.tasks.file_tasks.cleanup_temp_files",
        "schedule": 3600.0,  # Every hour
    },
    "cleanup-audit-logs": {
        "task": "app.tasks.maintenance_tasks.cleanup_old_audit_logs",
        "schedule": 86400.0,  # Daily
    },
    "update-storage-stats": {
        "task": "app.tasks.maintenance_tasks.update_storage_statistics",
        "schedule": 1800.0,  # Every 30 minutes
    },
    "system-health-check": {
        "task": "app.tasks.maintenance_tasks.system_health_check",
        "schedule": 300.0,  # Every 5 minutes
    }
}
