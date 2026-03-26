from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_tenant
from app.config.settings import get_settings
from app.db.session import get_db_session
from app.domains.auth.tokens import TokenType
from app.domains.auth.tokens import decode_token
from app.domains.memberships.models import Membership, MembershipRole
from app.domains.memberships.service import get_membership_by_tenant_and_user
from app.domains.tenants.models import Tenant
from app.domains.users.models import User
from app.domains.users.service import get_user_by_id
from app.domains.users.service import get_user_by_email


def require_development_auth_enabled() -> None:
    settings = get_settings()
    if not settings.is_local_env or not settings.dev_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Development authentication is disabled in this environment",
        )


def get_current_user_from_development_header(
    _: None = Depends(require_development_auth_enabled),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
    session: Session = Depends(get_db_session),
) -> User:
    require_development_auth_enabled()
    if x_user_email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-User-Email header")

    user = get_user_by_email(session, x_user_email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")
    return user


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
    session: Session = Depends(get_db_session),
) -> User:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
        payload = decode_token(token, expected_token_type=TokenType.access)
        try:
            user_id = int(str(payload["sub"]))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from None
        user = get_user_by_id(session, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        if user.email != payload["email"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")
        return user

    if x_user_email is not None:
        return get_current_user_from_development_header(x_user_email=x_user_email, session=session)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")


def get_current_membership(
    tenant: Tenant = Depends(require_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> Membership:
    membership = get_membership_by_tenant_and_user(session, tenant.id, user.id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership required")
    return membership


def require_member(membership: Membership = Depends(get_current_membership)) -> Membership:
    return membership


def require_admin_or_owner(membership: Membership = Depends(get_current_membership)) -> Membership:
    if membership.role not in {MembershipRole.owner, MembershipRole.admin}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or owner role required")
    return membership


def require_owner(membership: Membership = Depends(get_current_membership)) -> Membership:
    if membership.role != MembershipRole.owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required")
    return membership
