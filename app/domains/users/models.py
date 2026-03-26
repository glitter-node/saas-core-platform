from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="1")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    auth_sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    admin_account: Mapped["AdminAccount | None"] = relationship(back_populates="user", cascade="all, delete-orphan")
    tenants: Mapped[list["Tenant"]] = relationship(
        secondary="memberships",
        back_populates="users",
        viewonly=True,
    )
