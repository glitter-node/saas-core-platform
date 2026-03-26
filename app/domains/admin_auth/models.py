import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AdminRole(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"


class AdminAccount(Base):
    __tablename__ = "admin_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole, native_enum=False, validate_strings=True),
        nullable=False,
        default=AdminRole.admin,
        server_default=AdminRole.admin.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="1")
    mfa_enabled: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="0")
    mfa_secret_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_admin_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bootstrap_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="admin_account")
    sessions: Mapped[list["AdminAuthSession"]] = relationship(back_populates="admin_account", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AdminAuditLog"]] = relationship(back_populates="admin_account")

    @property
    def email(self) -> str:
        return self.user.email

    @property
    def full_name(self) -> str:
        return self.user.full_name


class AdminAuthSession(Base):
    __tablename__ = "admin_auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    admin_account_id: Mapped[int] = mapped_column(ForeignKey("admin_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    token_family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rotated_from_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_auth_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    admin_account: Mapped["AdminAccount"] = relationship(back_populates="sessions")
    audit_logs: Mapped[list["AdminAuditLog"]] = relationship(back_populates="auth_session")
    rotated_from_session: Mapped["AdminAuthSession | None"] = relationship(remote_side=[id])
