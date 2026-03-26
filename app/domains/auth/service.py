import re
from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.domains.auth.magic_links import MagicLinkFlow
from app.domains.auth.magic_links import consume_magic_link
from app.domains.auth.magic_links import create_magic_link
from app.domains.auth.passwords import hash_password
from app.domains.auth.passwords import make_unusable_password_hash
from app.domains.auth.passwords import normalize_email
from app.domains.auth.passwords import verify_password
from app.domains.auth.session_service import issue_login_tokens
from app.domains.auth.session_service import revoke_refresh_token
from app.domains.auth.session_service import rotate_refresh_token
from sqlalchemy import Select, select

from app.domains.mail.service import send_email
from app.domains.memberships.models import Membership
from app.domains.memberships.models import MembershipRole
from app.domains.memberships.service import create_membership
from app.domains.memberships.service import get_membership_by_tenant_and_user
from app.domains.tenants.service import get_active_tenant_by_subdomain
from app.domains.tenants.service import list_active_tenants
from app.domains.tenants.models import Tenant
from app.domains.usage.service import MEMBER_SEATS
from app.domains.usage.service import assert_within_limit
from app.domains.usage.service import get_membership_count
from app.domains.users.models import User
from app.domains.users.service import create_user
from app.domains.users.service import get_user_by_email


def register_user(session: Session, email: str, full_name: str, password: str) -> User:
    normalized_email = normalize_email(email)
    existing_user = get_user_by_email(session, normalized_email)
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    user = create_user(
        session=session,
        email=normalized_email,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        is_active=True,
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists") from None
    session.refresh(user)
    return user


def authenticate_user(session: Session, email: str, password: str) -> User:
    normalized_email = normalize_email(email)
    user = get_user_by_email(session, normalized_email)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    return user


def login_user(session: Session, email: str, password: str) -> dict[str, object]:
    user = authenticate_user(session, email, password)
    response = issue_login_tokens(session, user)
    session.commit()
    session.refresh(user)
    return response


def refresh_access_token(session: Session, refresh_token: str) -> dict[str, str]:
    with session.begin():
        response = rotate_refresh_token(session, refresh_token)
    return response


def logout_user(session: Session, refresh_token: str) -> None:
    with session.begin():
        revoke_refresh_token(session, refresh_token)


def build_magic_link_url(request: Request, flow: MagicLinkFlow, token: str, tenant: Tenant | None = None) -> str:
    if flow == MagicLinkFlow.user and tenant is not None:
        settings = get_settings()
        return (
            f"{request.url.scheme}://{tenant.subdomain}.{settings.app_domain}/magic-link/complete"
            f"?flow={flow.value}&token={token}"
        )
    return f"{request.base_url}magic-link/complete?flow={flow.value}&token={token}"


def build_user_tenants_by_email_query(email: str) -> Select[tuple[Tenant]]:
    normalized_email = normalize_email(email)
    return (
        select(Tenant)
        .join(Tenant.memberships)
        .join(Membership.user)
        .where(User.email == normalized_email, Tenant.status == "active")
        .order_by(Tenant.name.asc(), Tenant.id.asc())
    )


def list_user_tenants_by_email(session: Session, email: str) -> list[Tenant]:
    return list(session.execute(build_user_tenants_by_email_query(email)).scalars().all())


def resolve_magic_link_tenant(session: Session, request: Request, tenant_subdomain: str | None = None) -> Tenant:
    request_tenant = getattr(request.state, "tenant", None)
    if request_tenant is not None and isinstance(request_tenant, Tenant):
        return request_tenant
    if tenant_subdomain:
        tenant = get_active_tenant_by_subdomain(session, tenant_subdomain)
        if tenant is not None:
            return tenant
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant context not found")


def derive_full_name_from_email(email: str) -> str:
    local_part = email.split("@", maxsplit=1)[0]
    name = re.sub(r"[^a-zA-Z0-9]+", " ", local_part).strip()
    if not name:
        return "New User"
    return " ".join(part.capitalize() for part in name.split())


def send_user_magic_link(session: Session, tenant: Tenant, email: str, request: Request) -> None:
    normalized_email = normalize_email(email)
    _, raw_token = create_magic_link(session, email=normalized_email, flow=MagicLinkFlow.user, tenant_id=tenant.id)
    settings = get_settings()
    link_url = build_magic_link_url(request, MagicLinkFlow.user, raw_token, tenant)
    send_email(
        to_address=normalized_email,
        subject=f"{settings.app_name} sign-in link",
        body=(
            f"Use this sign-in link for tenant {tenant.subdomain}.{settings.app_domain}:\n\n"
            f"{link_url}\n\n"
            "If the email is new, the account will be created automatically on verification."
        ),
    )
    session.commit()


def discover_user_entry(session: Session, email: str, request: Request) -> dict[str, object]:
    normalized_email = normalize_email(email)
    tenants = list_user_tenants_by_email(session, normalized_email)
    example_tenants = list_active_tenants(session, limit=6)
    if len(tenants) == 1:
        send_user_magic_link(session, tenants[0], normalized_email, request)
        return {
            "mode": "single_tenant",
            "detail": f"A sign-in link was sent for {tenants[0].subdomain}.{get_settings().app_domain}",
            "tenants": tenants,
            "example_tenants": example_tenants,
        }
    if len(tenants) > 1:
        return {
            "mode": "multiple_tenants",
            "detail": "Select the tenant you want to enter.",
            "tenants": tenants,
            "example_tenants": example_tenants,
        }
    return {
        "mode": "no_tenants",
        "detail": "Select a tenant example to request your first access. After you choose one, check your mailbox and click the sign-in link.",
        "tenants": [],
        "example_tenants": example_tenants,
    }


def get_tenant_examples(session: Session) -> list[Tenant]:
    return list_active_tenants(session, limit=6)


def consume_user_magic_link(session: Session, token: str) -> dict[str, object]:
    with session.begin():
        magic_link = consume_magic_link(session, token, MagicLinkFlow.user)
        if magic_link.tenant_id is None or magic_link.tenant is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant context is required")
        user = get_user_by_email(session, magic_link.email)
        if user is None:
            user = create_user(
                session=session,
                email=magic_link.email,
                full_name=derive_full_name_from_email(magic_link.email),
                password_hash=make_unusable_password_hash(),
                is_active=True,
            )
        membership = get_membership_by_tenant_and_user(session, magic_link.tenant_id, user.id)
        if membership is None:
            next_count = get_membership_count(session, magic_link.tenant_id) + 1
            assert_within_limit(session, magic_link.tenant_id, MEMBER_SEATS, next_count)
            create_membership(session, magic_link.tenant_id, user, MembershipRole.member)
        user.last_login_at = datetime.now(timezone.utc)
        session.add(user)
        response = issue_login_tokens(session, user)
    session.refresh(user)
    return response
