from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domains.notifications.models import Notification


def build_notification_by_dedupe_key_query(dedupe_key: str) -> Select[tuple[Notification]]:
    return select(Notification).where(Notification.dedupe_key == dedupe_key)


def get_notification_by_dedupe_key(session: Session, dedupe_key: str) -> Notification | None:
    return session.execute(build_notification_by_dedupe_key_query(dedupe_key)).scalar_one_or_none()


def create_notification(
    session: Session,
    tenant_id: int,
    type: str,
    title: str,
    body: str,
    dedupe_key: str,
) -> Notification:
    notification = Notification(
        tenant_id=tenant_id,
        type=type,
        title=title,
        body=body,
        dedupe_key=dedupe_key,
    )
    session.add(notification)
    session.flush()
    return notification


def create_notification_if_missing(
    session: Session,
    tenant_id: int,
    type: str,
    title: str,
    body: str,
    dedupe_key: str,
) -> Notification:
    notification = get_notification_by_dedupe_key(session, dedupe_key)
    if notification is not None:
        return notification
    return create_notification(session, tenant_id, type, title, body, dedupe_key)
