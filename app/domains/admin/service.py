from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domains.memberships.models import Membership
from app.domains.notifications.models import Notification
from app.domains.subscriptions.models import Plan, Subscription
from app.domains.tenants.models import Tenant
from app.domains.users.models import User

ACTIVE_SUBSCRIPTION_STATUSES = ("active", "trialing", "past_due")
PLAN_PRICING = {
    "free": 0,
    "pro": 2900,
    "enterprise": 9900,
}


def build_total_tenants_query() -> Select[tuple[int]]:
    return select(func.count(Tenant.id)).where(Tenant.deleted_at.is_(None))


def build_active_tenants_query() -> Select[tuple[int]]:
    return select(func.count(Tenant.id)).where(Tenant.status == "active", Tenant.deleted_at.is_(None))


def build_total_users_query() -> Select[tuple[int]]:
    return select(func.count(User.id))


def build_total_memberships_query() -> Select[tuple[int]]:
    return select(func.count(Membership.id))


def build_active_subscriptions_query() -> Select[tuple[int]]:
    return select(func.count(Subscription.id)).where(Subscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES))


def build_plan_distribution_query() -> Select[tuple[str, int]]:
    return (
        select(Plan.code, func.count(Subscription.id))
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES))
        .group_by(Plan.code)
        .order_by(Plan.code.asc())
    )


def build_notifications_count_query() -> Select[tuple[int]]:
    return select(func.count(Notification.id))


def build_recent_tenants_query(limit: int) -> Select[tuple[Tenant]]:
    return select(Tenant).where(Tenant.deleted_at.is_(None)).order_by(Tenant.created_at.desc(), Tenant.id.desc()).limit(limit)


def build_active_paid_subscriptions_query() -> Select[tuple[str, int]]:
    return (
        select(Plan.code, func.count(Subscription.id))
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES), Plan.code != "free")
        .group_by(Plan.code)
    )


def get_admin_overview(session: Session) -> dict[str, object]:
    total_tenants = int(session.execute(build_total_tenants_query()).scalar_one())
    active_tenants = int(session.execute(build_active_tenants_query()).scalar_one())
    total_users = int(session.execute(build_total_users_query()).scalar_one())
    total_memberships = int(session.execute(build_total_memberships_query()).scalar_one())
    active_subscriptions = int(session.execute(build_active_subscriptions_query()).scalar_one())
    notifications_count = int(session.execute(build_notifications_count_query()).scalar_one())
    plan_distribution = {
        code: int(count) for code, count in session.execute(build_plan_distribution_query()).all()
    }
    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "total_users": total_users,
        "total_memberships": total_memberships,
        "active_subscriptions": active_subscriptions,
        "plan_distribution": plan_distribution,
        "notifications_count": notifications_count,
    }


def get_admin_revenue(session: Session) -> dict[str, object]:
    rows = session.execute(build_active_paid_subscriptions_query()).all()
    active_paid_subscriptions = sum(int(count) for _, count in rows)
    estimated_mrr = sum(PLAN_PRICING.get(code, 0) * int(count) for code, count in rows)
    return {
        "active_paid_subscriptions": active_paid_subscriptions,
        "estimated_mrr": estimated_mrr,
        "currency": "usd_cents",
        "pricing": PLAN_PRICING,
    }


def list_recent_tenants(session: Session, limit: int = 10) -> list[Tenant]:
    return list(session.execute(build_recent_tenants_query(limit)).scalars().all())
