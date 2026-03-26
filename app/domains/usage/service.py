from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select, text
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.domains.memberships.models import Membership
from app.domains.notifications.service import create_notification_if_missing
from app.domains.subscriptions.models import Plan, Subscription
from app.domains.subscriptions.service import ensure_subscription
from app.domains.usage.models import UsageCounter, UsageEvent
from worker.dispatch import enqueue_task_after_commit

API_REQUESTS = "api_requests"
MEMBER_SEATS = "member_seats"
TRACKED_METRICS = (API_REQUESTS, MEMBER_SEATS)
USAGE_PERIOD_START = datetime(1970, 1, 1)


def build_usage_counter_query(tenant_id: int, metric_code: str) -> Select[tuple[UsageCounter]]:
    return select(UsageCounter).where(
        UsageCounter.tenant_id == tenant_id,
        UsageCounter.metric_code == metric_code,
        UsageCounter.period_start == USAGE_PERIOD_START,
    )


def build_usage_counters_query(tenant_id: int) -> Select[tuple[UsageCounter]]:
    return select(UsageCounter).where(
        UsageCounter.tenant_id == tenant_id,
        UsageCounter.period_start == USAGE_PERIOD_START,
    )


def get_usage_counter(session: Session, tenant_id: int, metric_code: str) -> UsageCounter | None:
    return session.execute(build_usage_counter_query(tenant_id, metric_code)).scalar_one_or_none()


def ensure_usage_counter(session: Session, tenant_id: int, metric_code: str) -> UsageCounter:
    counter = get_usage_counter(session, tenant_id, metric_code)
    if counter is not None:
        return counter

    counter = UsageCounter(
        tenant_id=tenant_id,
        metric_code=metric_code,
        period_start=USAGE_PERIOD_START,
        current_value=0,
    )
    session.add(counter)
    session.flush()
    return counter


def record_event(session: Session, tenant_id: int, metric_code: str, value: int = 1) -> UsageEvent:
    event = UsageEvent(tenant_id=tenant_id, metric_code=metric_code, value=value)
    session.add(event)
    session.flush()
    return event


def increment_counter(session: Session, tenant_id: int, metric_code: str, value: int = 1, enqueue_warning: bool = True) -> UsageCounter:
    return increment_usage_counter_atomic(
        session=session,
        tenant_id=tenant_id,
        metric_code=metric_code,
        limit_count=None,
        value=value,
        enqueue_warning=enqueue_warning,
    )


def set_counter(session: Session, tenant_id: int, metric_code: str, value: int, enqueue_warning: bool = True) -> UsageCounter:
    initialize_usage_counter_row(session, tenant_id, metric_code)
    session.execute(
        text(
            """
            UPDATE usage_counters
            SET current_value = :value,
                updated_at = UTC_TIMESTAMP()
            WHERE tenant_id = :tenant_id
              AND metric_code = :metric_code
              AND period_start = :period_start
            """
        ),
        {
            "tenant_id": tenant_id,
            "metric_code": metric_code,
            "period_start": USAGE_PERIOD_START,
            "value": value,
        },
    )
    counter = get_usage_counter(session, tenant_id, metric_code)
    if counter is None:
        raise RuntimeError("Usage counter not found after counter set")
    if enqueue_warning:
        enqueue_usage_warning_check(session, tenant_id, metric_code)
    return counter


def build_membership_count_query(tenant_id: int) -> Select[tuple[int]]:
    return select(func.count(Membership.id)).where(Membership.tenant_id == tenant_id)


def get_membership_count(session: Session, tenant_id: int) -> int:
    return int(session.execute(build_membership_count_query(tenant_id)).scalar_one())


def sync_member_seats(session: Session, tenant_id: int, enqueue_warning: bool = False) -> UsageCounter:
    return set_counter(session, tenant_id, MEMBER_SEATS, get_membership_count(session, tenant_id), enqueue_warning=enqueue_warning)


def get_current_usage(session: Session, tenant_id: int) -> dict[str, int]:
    sync_member_seats(session, tenant_id, enqueue_warning=False)
    counters = session.execute(build_usage_counters_query(tenant_id)).scalars().all()
    usage = {metric_code: 0 for metric_code in TRACKED_METRICS}
    for counter in counters:
        usage[counter.metric_code] = counter.current_value
    return usage


def get_active_subscription(session: Session, tenant_id: int) -> Subscription:
    subscription = ensure_subscription(session, tenant_id)
    session.flush()
    session.refresh(subscription, attribute_names=["plan"])
    return subscription


def get_active_plan(session: Session, tenant_id: int) -> Plan:
    return get_active_subscription(session, tenant_id).plan


def get_plan_limit(plan: Plan, metric_code: str) -> int | None:
    value = plan.limits_json.get(metric_code)
    if value is None:
        return None
    return int(value)


def assert_within_limit(session: Session, tenant_id: int, metric_code: str, value: int | None = None) -> None:
    plan = get_active_plan(session, tenant_id)
    current_usage = get_current_usage(session, tenant_id)
    next_value = current_usage.get(metric_code, 0) if value is None else value
    limit = get_plan_limit(plan, metric_code)
    if limit is not None and next_value > limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Plan limit exceeded for {metric_code}",
        )


def initialize_usage_counter_row(session: Session, tenant_id: int, metric_code: str) -> None:
    session.execute(
        text(
            """
            INSERT INTO usage_counters (tenant_id, metric_code, period_start, current_value, updated_at)
            VALUES (:tenant_id, :metric_code, :period_start, 0, UTC_TIMESTAMP())
            ON DUPLICATE KEY UPDATE updated_at = updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "metric_code": metric_code,
            "period_start": USAGE_PERIOD_START,
        },
    )


def increment_usage_counter_atomic(
    session: Session,
    tenant_id: int,
    metric_code: str,
    limit_count: int | None,
    value: int = 1,
    enqueue_warning: bool = True,
) -> UsageCounter:
    initialize_usage_counter_row(session, tenant_id, metric_code)
    if limit_count is None:
        result = session.execute(
            text(
                """
                UPDATE usage_counters
                SET current_value = current_value + :value,
                    updated_at = UTC_TIMESTAMP()
                WHERE tenant_id = :tenant_id
                  AND metric_code = :metric_code
                  AND period_start = :period_start
                """
            ),
            {
                "tenant_id": tenant_id,
                "metric_code": metric_code,
                "period_start": USAGE_PERIOD_START,
                "value": value,
            },
        )
    else:
        result = session.execute(
            text(
                """
                UPDATE usage_counters
                SET current_value = current_value + :value,
                    updated_at = UTC_TIMESTAMP()
                WHERE tenant_id = :tenant_id
                  AND metric_code = :metric_code
                  AND period_start = :period_start
                  AND current_value + :value <= :limit_count
                """
            ),
            {
                "tenant_id": tenant_id,
                "metric_code": metric_code,
                "period_start": USAGE_PERIOD_START,
                "value": value,
                "limit_count": limit_count,
            },
        )

    if result.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Plan limit exceeded for {metric_code}",
        )

    counter = get_usage_counter(session, tenant_id, metric_code)
    if counter is None:
        raise RuntimeError("Usage counter not found after atomic increment")
    if enqueue_warning:
        enqueue_usage_warning_check(session, tenant_id, metric_code)
    return counter


def track_metric(session: Session, tenant_id: int, metric_code: str, value: int = 1) -> None:
    plan = get_active_plan(session, tenant_id)
    limit_count = get_plan_limit(plan, metric_code)
    increment_usage_counter_atomic(session, tenant_id, metric_code, limit_count, value)
    record_event(session, tenant_id, metric_code, value)


def get_usage_snapshot(session: Session, tenant_id: int) -> tuple[Plan, dict[str, int], dict[str, int | None], dict[str, int | None]]:
    plan = get_active_plan(session, tenant_id)
    counters = get_current_usage(session, tenant_id)
    limits = {metric_code: get_plan_limit(plan, metric_code) for metric_code in TRACKED_METRICS}
    remaining = {
        metric_code: None if limits[metric_code] is None else max(limits[metric_code] - counters.get(metric_code, 0), 0)
        for metric_code in TRACKED_METRICS
    }
    return plan, counters, limits, remaining


def enqueue_usage_warning_check(session: Session, tenant_id: int, metric_code: str) -> None:
    enqueue_task_after_commit(session, "worker.check_usage_limit_warning", tenant_id, metric_code)


def create_usage_limit_warning(session: Session, tenant_id: int, metric_code: str) -> int | None:
    settings = get_settings()
    threshold_percent = settings.usage_warning_threshold_percent
    plan = get_active_plan(session, tenant_id)
    limit = get_plan_limit(plan, metric_code)
    if limit is None or limit <= 0:
        return None

    current_usage = get_current_usage(session, tenant_id).get(metric_code, 0)
    threshold_value = max(int(limit * threshold_percent / 100), 1)
    if current_usage < threshold_value:
        return None

    notification = create_notification_if_missing(
        session=session,
        tenant_id=tenant_id,
        type="usage_limit_warning",
        title=f"{metric_code} usage is near the plan limit",
        body=f"Current usage for {metric_code} is {current_usage} of {limit}.",
        dedupe_key=f"usage_limit_warning:{tenant_id}:{metric_code}:{threshold_percent}:{limit}",
    )
    return notification.id
