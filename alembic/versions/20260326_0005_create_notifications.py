"""create notifications table

Revision ID: 20260326_0005
Revises: 20260326_0004
Create Date: 2026-03-26 00:40:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260326_0005"
down_revision: Union[str, Sequence[str], None] = "20260326_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_notifications_tenant_id_tenants"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
        sa.UniqueConstraint("dedupe_key", name=op.f("uq_notifications_dedupe_key")),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_tenant_id"), "notifications", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_notifications_type"), "notifications", ["type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_tenant_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")
