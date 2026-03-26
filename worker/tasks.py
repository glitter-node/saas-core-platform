from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.db import models
from app.db.session import SessionLocal
from app.domains.subscriptions.service import create_subscription_expiry_notifications
from app.domains.usage.service import create_usage_limit_warning
from worker.celery_app import celery_app


@celery_app.task(name="worker.check_usage_limit_warning")
def check_usage_limit_warning(tenant_id: int, metric_code: str) -> int | None:
    with SessionLocal() as session:
        notification_id = _create_usage_limit_warning(session, tenant_id, metric_code)
        session.commit()
        return notification_id


@celery_app.task(name="worker.scan_subscription_expiry_warnings")
def scan_subscription_expiry_warnings() -> list[int]:
    settings = get_settings()
    with SessionLocal() as session:
        tenant_ids = create_subscription_expiry_notifications(session, settings.subscription_expiry_warning_days)
        session.commit()
        return tenant_ids


def _create_usage_limit_warning(session: Session, tenant_id: int, metric_code: str) -> int | None:
    return create_usage_limit_warning(session, tenant_id, metric_code)
