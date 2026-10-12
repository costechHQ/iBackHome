"""Celery app for the `worker` and `beat` containers. Owner: Christopher.

Every `tasks.py` under app/base/ and app/features/ is registered automatically, so nobody edits
this file to add a job. In your own tasks.py:

    from app.workers.celery_app import celery_app

    @celery_app.task
    def send_reminders() -> None: ...

    # Periodic jobs (Celery Beat). Times are UTC: Friday 16:00 WAT is 15:00 UTC.
    from celery.schedules import crontab

    celery_app.conf.beat_schedule["milestones.remind"] = {
        "task": "app.features.milestones.tasks.send_reminders",
        "schedule": crontab(hour=8, minute=0),
    }
"""

from celery import Celery

from app.core.config import get_settings
from app.core.discovery import module_names
from app.core.models_registry import load_all_models

settings = get_settings()

celery_app = Celery(
    "ibackhome",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=list(module_names("tasks")),
)
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    beat_schedule={},
)

# Tasks query the database, so every table must be known before the first task runs.
load_all_models()
