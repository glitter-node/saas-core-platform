import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domains.tenants.models import TenantOwnedMixin
from app.db.base import Base


class MembershipRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class Membership(TenantOwnedMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, native_enum=False, validate_strings=True),
        nullable=False,
        default=MembershipRole.member,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")
