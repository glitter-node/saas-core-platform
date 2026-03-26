from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domains.tenants.models import TenantOwnedMixin
from app.db.base import Base


class Notification(TenantOwnedMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("dedupe_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
