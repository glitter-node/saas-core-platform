from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import TenantAPIRouter, require_tenant
from app.db.session import get_db_session
from app.domains.auth.dependencies import require_admin_or_owner, require_member
from app.domains.memberships.models import Membership
from app.domains.memberships.schemas import MembershipInviteCreate, MembershipRead
from app.domains.memberships.service import create_membership, get_membership_by_tenant_and_user, list_memberships
from app.domains.tenants.models import Tenant
from app.domains.usage.dependencies import track_api_request_usage
from app.domains.usage.service import MEMBER_SEATS, assert_within_limit, get_membership_count
from app.domains.users.service import create_user, get_user_by_email

router = TenantAPIRouter(prefix="/memberships", tags=["memberships"])


@router.get("", response_model=list[MembershipRead], dependencies=[Depends(require_member), Depends(track_api_request_usage)])
def get_memberships(
    tenant: Tenant = Depends(require_tenant),
    session: Session = Depends(get_db_session),
) -> list[MembershipRead]:
    return [MembershipRead.model_validate(membership) for membership in list_memberships(session, tenant.id)]


@router.post("/invite", response_model=MembershipRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_or_owner)])
def invite_membership(
    payload: MembershipInviteCreate,
    tenant: Tenant = Depends(require_tenant),
    session: Session = Depends(get_db_session),
) -> MembershipRead:
    if session.in_transaction():
        session.rollback()

    with session.begin():
        session.execute(select(Tenant).where(Tenant.id == tenant.id).with_for_update()).scalar_one()

        user = get_user_by_email(session, payload.email)
        if user is None:
            user = create_user(session, payload.email, payload.full_name)

        membership = get_membership_by_tenant_and_user(session, tenant.id, user.id)
        if membership is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Membership already exists")

        assert_within_limit(session, tenant.id, MEMBER_SEATS, get_membership_count(session, tenant.id) + 1)
        membership = create_membership(session, tenant.id, user, payload.role)

    session.refresh(membership)
    return MembershipRead.model_validate(membership)
