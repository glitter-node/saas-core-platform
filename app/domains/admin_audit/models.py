from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    admin_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    auth_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_auth_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    admin_account: Mapped["AdminAccount | None"] = relationship(back_populates="audit_logs")
    auth_session: Mapped["AdminAuthSession | None"] = relationship(back_populates="audit_logs")
