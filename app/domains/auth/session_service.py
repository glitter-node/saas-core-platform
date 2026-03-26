import hashlib
import secrets
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.domains.auth.models import AuthSession
from app.domains.auth.tokens import create_access_token
from app.domains.auth.tokens import create_refresh_token
from app.domains.users.models import User


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def build_auth_session_by_token_hash_query(token_hash: str) -> Select[tuple[AuthSession]]:
    return select(AuthSession).where(AuthSession.token_hash == token_hash).options(selectinload(AuthSession.user))


def build_locked_auth_session_by_token_hash_query(token_hash: str) -> Select[tuple[AuthSession]]:
    return build_auth_session_by_token_hash_query(token_hash).with_for_update()


def get_locked_auth_session_by_token_hash(session: Session, token_hash: str) -> AuthSession | None:
    return session.execute(build_locked_auth_session_by_token_hash_query(token_hash)).scalar_one_or_none()


def create_auth_session(
    session: Session,
    *,
    user: User,
    refresh_token: str,
    expires_at: datetime,
    token_family_id: str,
    rotated_from_session_id: int | None = None,
) -> AuthSession:
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        token_family_id=token_family_id,
        rotated_from_session_id=rotated_from_session_id,
        expires_at=expires_at,
    )
    session.add(auth_session)
    session.flush()
    return auth_session


def revoke_auth_session(auth_session: AuthSession) -> AuthSession:
    now = datetime.utcnow()
    auth_session.revoked_at = now
    auth_session.last_used_at = now
    return auth_session


def issue_login_tokens(session: Session, user: User) -> dict[str, object]:
    access_token = create_access_token(user)
    refresh_token, expires_at = create_refresh_token(user, session_nonce=secrets.token_urlsafe(24))
    create_auth_session(
        session,
        user=user,
        refresh_token=refresh_token,
        expires_at=expires_at,
        token_family_id=uuid4().hex,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


def rotate_refresh_token(session: Session, refresh_token: str) -> dict[str, str]:
    auth_session = get_locked_auth_session_by_token_hash(session, hash_refresh_token(refresh_token))
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if auth_session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")
    if auth_session.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")

    user = auth_session.user
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    revoke_auth_session(auth_session)
    new_refresh_token, expires_at = create_refresh_token(user, session_nonce=secrets.token_urlsafe(24))
    create_auth_session(
        session,
        user=user,
        refresh_token=new_refresh_token,
        expires_at=expires_at,
        token_family_id=auth_session.token_family_id,
        rotated_from_session_id=auth_session.id,
    )
    return {
        "access_token": create_access_token(user),
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


def revoke_refresh_token(session: Session, refresh_token: str) -> None:
    auth_session = get_locked_auth_session_by_token_hash(session, hash_refresh_token(refresh_token))
    if auth_session is None:
        return
    revoke_auth_session(auth_session)
