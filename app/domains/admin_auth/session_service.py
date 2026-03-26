import hashlib
import secrets
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session, joinedload

from app.domains.admin_auth.models import AdminAccount
from app.domains.admin_auth.models import AdminAuthSession
from app.domains.admin_auth.tokens import create_admin_access_token
from app.domains.admin_auth.tokens import create_admin_refresh_token


def hash_admin_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def build_admin_auth_session_by_token_hash_query(token_hash: str) -> Select[tuple[AdminAuthSession]]:
    return (
        select(AdminAuthSession)
        .where(AdminAuthSession.token_hash == token_hash)
        .options(joinedload(AdminAuthSession.admin_account).joinedload(AdminAccount.user))
    )


def build_locked_admin_auth_session_by_token_hash_query(token_hash: str) -> Select[tuple[AdminAuthSession]]:
    return build_admin_auth_session_by_token_hash_query(token_hash).with_for_update()


def get_locked_admin_auth_session_by_token_hash(session: Session, token_hash: str) -> AdminAuthSession | None:
    return session.execute(build_locked_admin_auth_session_by_token_hash_query(token_hash)).scalar_one_or_none()


def create_admin_auth_session(
    session: Session,
    *,
    admin_account: AdminAccount,
    refresh_token: str,
    expires_at: datetime,
    token_family_id: str,
    rotated_from_session_id: int | None = None,
) -> AdminAuthSession:
    auth_session = AdminAuthSession(
        admin_account_id=admin_account.id,
        token_hash=hash_admin_refresh_token(refresh_token),
        token_family_id=token_family_id,
        rotated_from_session_id=rotated_from_session_id,
        expires_at=expires_at,
    )
    session.add(auth_session)
    session.flush()
    return auth_session


def revoke_admin_auth_session(auth_session: AdminAuthSession) -> AdminAuthSession:
    now = datetime.utcnow()
    auth_session.revoked_at = now
    auth_session.last_used_at = now
    return auth_session


def issue_admin_login_tokens(session: Session, admin_account: AdminAccount) -> tuple[dict[str, object], AdminAuthSession]:
    access_token = create_admin_access_token(admin_account)
    refresh_token, expires_at = create_admin_refresh_token(admin_account, session_nonce=secrets.token_urlsafe(24))
    auth_session = create_admin_auth_session(
        session,
        admin_account=admin_account,
        refresh_token=refresh_token,
        expires_at=expires_at,
        token_family_id=uuid4().hex,
    )
    return (
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "admin": admin_account,
        },
        auth_session,
    )


def rotate_admin_refresh_token(session: Session, refresh_token: str) -> tuple[dict[str, str], AdminAuthSession]:
    auth_session = get_locked_admin_auth_session_by_token_hash(session, hash_admin_refresh_token(refresh_token))
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if auth_session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")
    if auth_session.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")

    admin_account = auth_session.admin_account
    if not admin_account.is_active or not admin_account.user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account is inactive")

    revoke_admin_auth_session(auth_session)
    new_refresh_token, expires_at = create_admin_refresh_token(admin_account, session_nonce=secrets.token_urlsafe(24))
    new_auth_session = create_admin_auth_session(
        session,
        admin_account=admin_account,
        refresh_token=new_refresh_token,
        expires_at=expires_at,
        token_family_id=auth_session.token_family_id,
        rotated_from_session_id=auth_session.id,
    )
    return (
        {
            "access_token": create_admin_access_token(admin_account),
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        },
        new_auth_session,
    )


def revoke_admin_refresh_token(session: Session, refresh_token: str) -> AdminAuthSession | None:
    auth_session = get_locked_admin_auth_session_by_token_hash(session, hash_admin_refresh_token(refresh_token))
    if auth_session is None:
        return None
    revoke_admin_auth_session(auth_session)
    return auth_session


def revoke_all_admin_sessions_for_account(session: Session, admin_account_id: int) -> None:
    now = datetime.utcnow()
    session.execute(
        update(AdminAuthSession)
        .where(AdminAuthSession.admin_account_id == admin_account_id, AdminAuthSession.revoked_at.is_(None))
        .values(revoked_at=now, last_used_at=now)
    )
