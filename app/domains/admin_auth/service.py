from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from app.domains.admin_audit.service import record_admin_audit_log
from app.domains.admin_auth.models import AdminAccount
from app.domains.admin_auth.models import AdminRole
from app.domains.admin_auth.session_service import issue_admin_login_tokens
from app.domains.admin_auth.session_service import revoke_admin_refresh_token
from app.domains.admin_auth.session_service import rotate_admin_refresh_token
from app.domains.auth.magic_links import MagicLinkFlow
from app.domains.auth.magic_links import consume_magic_link
from app.domains.auth.magic_links import create_magic_link
from app.domains.auth.passwords import make_unusable_password_hash
from app.domains.auth.passwords import normalize_email
from app.domains.auth.passwords import verify_password
from app.domains.mail.service import send_email
from app.domains.users.service import create_user
from app.domains.users.service import get_user_by_email


def build_admin_account_by_id_query(admin_account_id: int) -> Select[tuple[AdminAccount]]:
    return (
        select(AdminAccount)
        .where(AdminAccount.id == admin_account_id)
        .options(joinedload(AdminAccount.user))
    )


def build_admin_account_by_user_id_query(user_id: int) -> Select[tuple[AdminAccount]]:
    return (
        select(AdminAccount)
        .where(AdminAccount.user_id == user_id)
        .options(joinedload(AdminAccount.user))
    )


def get_admin_account_by_id(session: Session, admin_account_id: int) -> AdminAccount | None:
    return session.execute(build_admin_account_by_id_query(admin_account_id)).scalar_one_or_none()


def get_admin_account_by_user_id(session: Session, user_id: int) -> AdminAccount | None:
    return session.execute(build_admin_account_by_user_id_query(user_id)).scalar_one_or_none()


def ensure_admin_account(session: Session, user_id: int, role: AdminRole = AdminRole.admin) -> AdminAccount:
    admin_account = get_admin_account_by_user_id(session, user_id)
    if admin_account is not None:
        return admin_account
    admin_account = AdminAccount(user_id=user_id, role=role, bootstrap_source="self-service")
    session.add(admin_account)
    session.flush()
    return admin_account


def authenticate_admin_user(
    session: Session,
    email: str,
    password: str,
    otp_code: str | None = None,
) -> AdminAccount:
    normalized_email = normalize_email(email)
    user = get_user_by_email(session, normalized_email)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    admin_account = get_admin_account_by_user_id(session, user.id)
    if admin_account is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access is not allowed")
    if not admin_account.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is inactive")
    if admin_account.mfa_enabled:
        if not otp_code:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MFA code required")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MFA verification is not configured")
    user.last_login_at = datetime.now(timezone.utc)
    admin_account.last_admin_login_at = datetime.now(timezone.utc)
    session.add(user)
    session.add(admin_account)
    return admin_account


def login_admin(session: Session, email: str, password: str, otp_code: str | None, request: Request | None) -> dict[str, object]:
    try:
        admin_account = authenticate_admin_user(session, email, password, otp_code)
    except HTTPException as exc:
        record_admin_audit_log(
            session,
            action="admin_login_failed",
            status="failed",
            request=request,
            target_type="email",
            target_id=normalize_email(email),
            detail={"reason": exc.detail},
        )
        session.commit()
        raise

    response, auth_session = issue_admin_login_tokens(session, admin_account)
    record_admin_audit_log(
        session,
        action="admin_login_succeeded",
        status="succeeded",
        request=request,
        admin_account_id=admin_account.id,
        auth_session_id=auth_session.id,
        target_type="admin_account",
        target_id=str(admin_account.id),
    )
    session.commit()
    session.refresh(admin_account)
    return response


def refresh_admin_access_token(session: Session, refresh_token: str, request: Request | None) -> dict[str, str]:
    try:
        with session.begin():
            response, auth_session = rotate_admin_refresh_token(session, refresh_token)
            record_admin_audit_log(
                session,
                action="admin_refresh_succeeded",
                status="succeeded",
                request=request,
                admin_account_id=auth_session.admin_account_id,
                auth_session_id=auth_session.id,
                target_type="admin_account",
                target_id=str(auth_session.admin_account_id),
            )
        return response
    except HTTPException as exc:
        record_admin_audit_log(
            session,
            action="admin_refresh_failed",
            status="failed",
            request=request,
            detail={"reason": exc.detail},
        )
        session.commit()
        raise


def logout_admin(session: Session, refresh_token: str, request: Request | None) -> None:
    with session.begin():
        auth_session = revoke_admin_refresh_token(session, refresh_token)
        record_admin_audit_log(
            session,
            action="admin_logout",
            status="succeeded",
            request=request,
            admin_account_id=auth_session.admin_account_id if auth_session is not None else None,
            auth_session_id=auth_session.id if auth_session is not None else None,
            target_type="admin_account" if auth_session is not None else None,
            target_id=str(auth_session.admin_account_id) if auth_session is not None else None,
        )


def send_admin_magic_link(session: Session, email: str, request: Request) -> None:
    normalized_email = normalize_email(email)
    user = get_user_by_email(session, normalized_email)
    if user is None:
        user = create_user(
            session=session,
            email=normalized_email,
            full_name="Admin Viewer",
            password_hash=make_unusable_password_hash(),
            is_active=True,
        )
    admin_account = ensure_admin_account(session, user.id)
    if admin_account.is_active and admin_account.user.is_active:
        _, raw_token = create_magic_link(session, email=normalized_email, flow=MagicLinkFlow.admin)
        link_url = f"{request.base_url}magic-link/complete?flow=admin&token={raw_token}"
        role_label = "superadmin" if admin_account.role == AdminRole.superadmin else "admin"
        send_email(
            to_address=normalized_email,
            subject="Admin sign-in link",
            body=f"Use this {role_label} sign-in link:\n\n{link_url}",
        )
    session.commit()


def consume_admin_magic_link(session: Session, token: str, request: Request | None) -> dict[str, object]:
    with session.begin():
        magic_link = consume_magic_link(session, token, MagicLinkFlow.admin)
        user = get_user_by_email(session, magic_link.email)
        if user is None:
            user = create_user(
                session=session,
                email=magic_link.email,
                full_name="Admin Viewer",
                password_hash=make_unusable_password_hash(),
                is_active=True,
            )
        admin_account = ensure_admin_account(session, user.id)
        if not user.is_active or not admin_account.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is inactive")
        user.last_login_at = datetime.now(timezone.utc)
        admin_account.last_admin_login_at = datetime.now(timezone.utc)
        session.add(user)
        session.add(admin_account)
        response, auth_session = issue_admin_login_tokens(session, admin_account)
        record_admin_audit_log(
            session,
            action="admin_magic_link_login_succeeded",
            status="succeeded",
            request=request,
            admin_account_id=admin_account.id,
            auth_session_id=auth_session.id,
            target_type="admin_account",
            target_id=str(admin_account.id),
        )
    session.refresh(admin_account)
    return response
