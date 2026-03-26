from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    token_family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rotated_from_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="auth_sessions")
    rotated_from_session: Mapped["AuthSession | None"] = relationship(remote_side=[id])


class AuthMagicLink(Base):
    __tablename__ = "auth_magic_links"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    flow: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    tenant: Mapped["Tenant | None"] = relationship()
