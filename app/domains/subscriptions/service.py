from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.config.settings import get_settings
from app.domains.notifications.service import create_notification_if_missing
from app.domains.subscriptions.models import BillingEventLedger, Plan, Subscription
from app.domains.subscriptions.stripe_client import get_object_value

TERMINAL_SUBSCRIPTION_STATUSES = {"canceled", "unpaid", "incomplete_expired"}


def build_plan_by_code_query(code: str) -> Select[tuple[Plan]]:
    return select(Plan).where(Plan.code == code)


def get_plan_by_code(session: Session, code: str) -> Plan | None:
    return session.execute(build_plan_by_code_query(code)).scalar_one_or_none()


def build_subscription_by_tenant_query(tenant_id: int) -> Select[tuple[Subscription]]:
    return select(Subscription).where(Subscription.tenant_id == tenant_id).options(selectinload(Subscription.plan))


def build_subscription_by_customer_query(customer_id: str) -> Select[tuple[Subscription]]:
    return (
        select(Subscription)
        .where(Subscription.stripe_customer_id == customer_id)
        .options(selectinload(Subscription.plan))
    )


def build_subscription_by_stripe_subscription_query(subscription_id: str) -> Select[tuple[Subscription]]:
    return (
        select(Subscription)
        .where(Subscription.stripe_subscription_id == subscription_id)
        .options(selectinload(Subscription.plan))
    )


def build_locked_subscription_by_tenant_query(tenant_id: int) -> Select[tuple[Subscription]]:
    return build_subscription_by_tenant_query(tenant_id).with_for_update()


def build_locked_subscription_by_customer_query(customer_id: str) -> Select[tuple[Subscription]]:
    return build_subscription_by_customer_query(customer_id).with_for_update()


def build_locked_subscription_by_stripe_subscription_query(subscription_id: str) -> Select[tuple[Subscription]]:
    return build_subscription_by_stripe_subscription_query(subscription_id).with_for_update()


def build_billing_event_ledger_query(stripe_event_id: str) -> Select[tuple[BillingEventLedger]]:
    return select(BillingEventLedger).where(BillingEventLedger.stripe_event_id == stripe_event_id)


def build_expiring_subscriptions_query(deadline: datetime, now: datetime) -> Select[tuple[Subscription]]:
    return (
        select(Subscription)
        .where(
            Subscription.current_period_end.is_not(None),
            Subscription.current_period_end >= now,
            Subscription.current_period_end <= deadline,
            Subscription.status.in_(("active", "trialing", "past_due")),
        )
        .options(selectinload(Subscription.plan))
        .order_by(Subscription.current_period_end.asc(), Subscription.id.asc())
    )


def get_subscription_by_tenant(session: Session, tenant_id: int) -> Subscription | None:
    return session.execute(build_subscription_by_tenant_query(tenant_id)).scalar_one_or_none()


def get_subscription_by_customer_id(session: Session, customer_id: str) -> Subscription | None:
    return session.execute(build_subscription_by_customer_query(customer_id)).scalar_one_or_none()


def get_subscription_by_stripe_subscription_id(session: Session, subscription_id: str) -> Subscription | None:
    return session.execute(build_subscription_by_stripe_subscription_query(subscription_id)).scalar_one_or_none()


def get_locked_subscription_by_tenant(session: Session, tenant_id: int) -> Subscription | None:
    return session.execute(build_locked_subscription_by_tenant_query(tenant_id)).scalar_one_or_none()


def get_locked_subscription_by_customer_id(session: Session, customer_id: str) -> Subscription | None:
    return session.execute(build_locked_subscription_by_customer_query(customer_id)).scalar_one_or_none()


def get_locked_subscription_by_stripe_subscription_id(session: Session, subscription_id: str) -> Subscription | None:
    return session.execute(build_locked_subscription_by_stripe_subscription_query(subscription_id)).scalar_one_or_none()


def get_billing_event_ledger(session: Session, stripe_event_id: str) -> BillingEventLedger | None:
    return session.execute(build_billing_event_ledger_query(stripe_event_id)).scalar_one_or_none()


def list_expiring_subscriptions(session: Session, warning_days: int) -> list[Subscription]:
    now = datetime.now(UTC)
    deadline = now + timedelta(days=warning_days)
    return list(session.execute(build_expiring_subscriptions_query(deadline, now)).scalars().all())


def get_default_plan(session: Session) -> Plan:
    plan = get_plan_by_code(session, "free")
    if plan is None:
        raise RuntimeError("Default plan not found")
    return plan


def get_billable_price_id(plan_code: str) -> str | None:
    settings = get_settings()
    prices = {
        "pro": settings.stripe_price_id_pro,
        "enterprise": settings.stripe_price_id_enterprise,
    }
    return prices.get(plan_code)


def get_plan_code_by_price_id(price_id: str | None) -> str | None:
    if price_id is None:
        return None

    settings = get_settings()
    prices = {
        settings.stripe_price_id_pro: "pro",
        settings.stripe_price_id_enterprise: "enterprise",
    }
    return prices.get(price_id)


def ensure_subscription(session: Session, tenant_id: int) -> Subscription:
    subscription = get_subscription_by_tenant(session, tenant_id)
    if subscription is not None:
        return subscription

    subscription = Subscription(tenant_id=tenant_id, plan=get_default_plan(session), status="active")
    session.add(subscription)
    session.flush()
    session.refresh(subscription, attribute_names=["plan"])
    return subscription


def ensure_locked_subscription(session: Session, tenant_id: int) -> Subscription:
    subscription = get_locked_subscription_by_tenant(session, tenant_id)
    if subscription is not None:
        return subscription

    subscription = Subscription(tenant_id=tenant_id, plan=get_default_plan(session), status="active")
    session.add(subscription)
    session.flush()
    session.refresh(subscription, attribute_names=["plan"])
    return subscription


def get_checkout_urls(host: str, scheme: str) -> tuple[str, str]:
    return (
        f"{scheme}://{host}/billing/success",
        f"{scheme}://{host}/billing/cancel",
    )


def get_subscription_payload_plan_code(stripe_subscription: object) -> str | None:
    metadata = get_object_value(stripe_subscription, "metadata")
    if metadata is not None:
        plan_code = get_object_value(metadata, "plan_code")
        if isinstance(plan_code, str) and plan_code:
            return plan_code

    items = get_object_value(stripe_subscription, "items")
    items_data = get_object_value(items, "data") if items is not None else None
    if isinstance(items_data, list) and items_data:
        price = get_object_value(items_data[0], "price")
        price_id = get_object_value(price, "id") if price is not None else None
        if isinstance(price_id, str):
            return get_plan_code_by_price_id(price_id)
    return None


def get_subscription_tenant_id(stripe_subscription: object) -> int | None:
    metadata = get_object_value(stripe_subscription, "metadata")
    tenant_id = get_object_value(metadata, "tenant_id") if metadata is not None else None
    if tenant_id is None:
        return None
    try:
        return int(str(tenant_id))
    except ValueError:
        return None


def get_current_period_end(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    return None


def should_apply_subscription_update(
    subscription: Subscription,
    status: str | None,
    current_period_end: datetime | None,
) -> bool:
    if current_period_end is not None and subscription.current_period_end is not None:
        if current_period_end < subscription.current_period_end and status not in TERMINAL_SUBSCRIPTION_STATUSES:
            return False

    if (
        subscription.status in TERMINAL_SUBSCRIPTION_STATUSES
        and status not in TERMINAL_SUBSCRIPTION_STATUSES
        and current_period_end is not None
        and subscription.current_period_end is not None
        and current_period_end <= subscription.current_period_end
    ):
        return False

    return True


def apply_checkout_session_completed(session: Session, checkout_session: object) -> Subscription | None:
    tenant_id = get_object_value(checkout_session, "metadata")
    tenant_value = get_object_value(tenant_id, "tenant_id") if tenant_id is not None else None
    if tenant_value is None:
        return None

    subscription = ensure_locked_subscription(session, int(str(tenant_value)))
    customer_id = get_object_value(checkout_session, "customer")
    subscription_id = get_object_value(checkout_session, "subscription")
    if isinstance(customer_id, str):
        subscription.stripe_customer_id = customer_id
    if isinstance(subscription_id, str):
        subscription.stripe_subscription_id = subscription_id
    session.flush()
    return subscription


def apply_stripe_subscription_event(session: Session, stripe_subscription: object) -> Subscription | None:
    stripe_subscription_id = get_object_value(stripe_subscription, "id")
    customer_id = get_object_value(stripe_subscription, "customer")

    subscription = None
    if isinstance(stripe_subscription_id, str):
        subscription = get_locked_subscription_by_stripe_subscription_id(session, stripe_subscription_id)
    if subscription is None and isinstance(customer_id, str):
        subscription = get_locked_subscription_by_customer_id(session, customer_id)
    if subscription is None:
        tenant_id = get_subscription_tenant_id(stripe_subscription)
        if tenant_id is None:
            return None
        subscription = ensure_locked_subscription(session, tenant_id)

    plan_code = get_subscription_payload_plan_code(stripe_subscription) or "free"
    plan = get_plan_by_code(session, plan_code)
    if plan is None:
        raise RuntimeError("Plan not found")

    status = get_object_value(stripe_subscription, "status")
    current_period_end = get_current_period_end(get_object_value(stripe_subscription, "current_period_end"))
    next_status = str(status) if status is not None else subscription.status

    if not should_apply_subscription_update(subscription, next_status, current_period_end):
        session.refresh(subscription, attribute_names=["plan"])
        return subscription

    subscription.plan = plan
    subscription.status = next_status
    subscription.current_period_end = current_period_end
    if isinstance(customer_id, str):
        subscription.stripe_customer_id = customer_id
    if isinstance(stripe_subscription_id, str):
        subscription.stripe_subscription_id = stripe_subscription_id
    session.flush()
    session.refresh(subscription, attribute_names=["plan"])
    return subscription


def create_billing_event_ledger_entry(session: Session, stripe_event_id: str, event_type: str) -> BillingEventLedger:
    ledger_entry = BillingEventLedger(stripe_event_id=stripe_event_id, event_type=event_type)
    session.add(ledger_entry)
    session.flush()
    return ledger_entry


def mark_billing_event_processed(ledger_entry: BillingEventLedger) -> BillingEventLedger:
    ledger_entry.processed_at = datetime.now(UTC)
    return ledger_entry


def create_subscription_expiry_notifications(session: Session, warning_days: int) -> list[int]:
    subscriptions = list_expiring_subscriptions(session, warning_days)
    created_tenant_ids: list[int] = []
    for subscription in subscriptions:
        period_key = subscription.current_period_end.date().isoformat() if subscription.current_period_end else "none"
        notification = create_notification_if_missing(
            session=session,
            tenant_id=subscription.tenant_id,
            type="subscription_expiry_warning",
            title="Subscription expires soon",
            body=f"Your subscription is scheduled to expire on {period_key}.",
            dedupe_key=f"subscription_expiry_warning:{subscription.tenant_id}:{subscription.id}:{period_key}",
        )
        if notification.tenant_id not in created_tenant_ids:
            created_tenant_ids.append(notification.tenant_id)
    return created_tenant_ids
