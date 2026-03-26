import hashlib
import secrets
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import StrEnum

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from app.config.settings import get_settings
from app.domains.auth.models import AuthMagicLink


class MagicLinkFlow(StrEnum):
    user = "user"
    admin = "admin"


def hash_magic_link_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_magic_link_by_token_hash_query(token_hash: str) -> Select[tuple[AuthMagicLink]]:
    return select(AuthMagicLink).where(AuthMagicLink.token_hash == token_hash).options(joinedload(AuthMagicLink.tenant))


def build_locked_magic_link_by_token_hash_query(token_hash: str) -> Select[tuple[AuthMagicLink]]:
    return build_magic_link_by_token_hash_query(token_hash).with_for_update()


def get_locked_magic_link_by_token_hash(session: Session, token_hash: str) -> AuthMagicLink | None:
    return session.execute(build_locked_magic_link_by_token_hash_query(token_hash)).scalar_one_or_none()


def create_magic_link(session: Session, *, email: str, flow: MagicLinkFlow, tenant_id: int | None = None) -> tuple[AuthMagicLink, str]:
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.magic_link_expire_minutes)
    magic_link = AuthMagicLink(
        email=email,
        token_hash=hash_magic_link_token(raw_token),
        flow=flow.value,
        tenant_id=tenant_id,
        expires_at=expires_at,
    )
    session.add(magic_link)
    session.flush()
    return magic_link, raw_token


def consume_magic_link(session: Session, token: str, expected_flow: MagicLinkFlow) -> AuthMagicLink:
    magic_link = get_locked_magic_link_by_token_hash(session, hash_magic_link_token(token))
    if magic_link is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid magic link")
    if magic_link.flow != expected_flow.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid magic link")
    if magic_link.consumed_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Magic link has already been used")
    if magic_link.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Magic link has expired")
    magic_link.consumed_at = datetime.utcnow()
    return magic_link
