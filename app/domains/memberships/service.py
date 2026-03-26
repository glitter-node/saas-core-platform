from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.domains.memberships.models import Membership, MembershipRole
from app.domains.usage.service import sync_member_seats
from app.domains.users.models import User


def build_memberships_query(tenant_id: int) -> Select[tuple[Membership]]:
    return (
        select(Membership)
        .where(Membership.tenant_id == tenant_id)
        .options(selectinload(Membership.user))
        .order_by(Membership.id)
    )


def list_memberships(session: Session, tenant_id: int) -> list[Membership]:
    return list(session.execute(build_memberships_query(tenant_id)).scalars().all())


def build_membership_by_tenant_and_user_query(tenant_id: int, user_id: int) -> Select[tuple[Membership]]:
    return (
        select(Membership)
        .where(Membership.tenant_id == tenant_id, Membership.user_id == user_id)
        .options(selectinload(Membership.user))
    )


def get_membership_by_tenant_and_user(session: Session, tenant_id: int, user_id: int) -> Membership | None:
    return session.execute(build_membership_by_tenant_and_user_query(tenant_id, user_id)).scalar_one_or_none()


def create_membership(session: Session, tenant_id: int, user: User, role: MembershipRole) -> Membership:
    membership = Membership(tenant_id=tenant_id, user=user, role=role)
    session.add(membership)
    session.flush()
    sync_member_seats(session, tenant_id, enqueue_warning=True)
    return membership
