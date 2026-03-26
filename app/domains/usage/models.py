from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domains.tenants.models import TenantOwnedMixin
from app.db.base import Base


class UsageEvent(TenantOwnedMixin, Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    metric_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UsageCounter(TenantOwnedMixin, Base):
    __tablename__ = "usage_counters"
    __table_args__ = (UniqueConstraint("tenant_id", "metric_code", "period_start"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    metric_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
