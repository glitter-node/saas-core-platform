from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domains.tenants.models import TenantOwnedMixin
from app.db.base import Base


class Organization(TenantOwnedMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("tenant_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="organization")
