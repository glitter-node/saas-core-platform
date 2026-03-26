from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domains.tenants.models import TenantOwnedMixin
from app.db.base import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    limits_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Subscription(TenantOwnedMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("tenant_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="subscription")
    plan: Mapped[Plan] = relationship(back_populates="subscriptions")


class BillingEventLedger(Base):
    __tablename__ = "billing_event_ledger"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stripe_event_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
