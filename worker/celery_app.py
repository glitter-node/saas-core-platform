from celery import Celery

from app.config.settings import get_settings

settings = get_settings()

celery_app = Celery("saas_worker", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="operations",
    beat_schedule={
        "scan-subscription-expiry-warnings": {
            "task": "worker.scan_subscription_expiry_warnings",
            "schedule": max(settings.scheduler_subscription_expiry_scan_minutes, 1) * 60,
        }
    },
)
