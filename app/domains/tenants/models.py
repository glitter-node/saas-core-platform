from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.db.base import Base


class TenantOwnedMixin:
    @declared_attr
    def tenant_id(cls) -> Mapped[int]:
        return mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    subdomain: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization: Mapped["Organization | None"] = relationship(
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )
    memberships: Mapped[list["Membership"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship(
        secondary="memberships",
        back_populates="tenants",
        viewonly=True,
    )
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )
