"""create usage tables and update plan limits

Revision ID: 20260326_0004
Revises: 20260326_0003
Create Date: 2026-03-26 00:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260326_0004"
down_revision: Union[str, Sequence[str], None] = "20260326_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("metric_code", sa.String(length=50), nullable=False),
        sa.Column("value", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_usage_events_tenant_id_tenants"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_events")),
    )
    op.create_index(op.f("ix_usage_events_id"), "usage_events", ["id"], unique=False)
    op.create_index(op.f("ix_usage_events_metric_code"), "usage_events", ["metric_code"], unique=False)
    op.create_index(op.f("ix_usage_events_tenant_id"), "usage_events", ["tenant_id"], unique=False)

    op.create_table(
        "usage_counters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("metric_code", sa.String(length=50), nullable=False),
        sa.Column("current_value", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_usage_counters_tenant_id_tenants"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_counters")),
        sa.UniqueConstraint("tenant_id", "metric_code", name=op.f("uq_usage_counters_tenant_id")),
    )
    op.create_index(op.f("ix_usage_counters_id"), "usage_counters", ["id"], unique=False)
    op.create_index(op.f("ix_usage_counters_metric_code"), "usage_counters", ["metric_code"], unique=False)
    op.create_index(op.f("ix_usage_counters_tenant_id"), "usage_counters", ["tenant_id"], unique=False)

    plans_table = sa.table(
        "plans",
        sa.column("code", sa.String(length=50)),
        sa.column("limits_json", sa.JSON()),
    )
    op.execute(
        plans_table.update().where(plans_table.c.code == "free").values(
            limits_json={"api_requests": 1000, "member_seats": 3}
        )
    )
    op.execute(
        plans_table.update().where(plans_table.c.code == "pro").values(
            limits_json={"api_requests": 10000, "member_seats": 20}
        )
    )
    op.execute(
        plans_table.update().where(plans_table.c.code == "enterprise").values(
            limits_json={"api_requests": 1000000, "member_seats": 1000}
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_counters_tenant_id"), table_name="usage_counters")
    op.drop_index(op.f("ix_usage_counters_metric_code"), table_name="usage_counters")
    op.drop_index(op.f("ix_usage_counters_id"), table_name="usage_counters")
    op.drop_table("usage_counters")
    op.drop_index(op.f("ix_usage_events_tenant_id"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_metric_code"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_id"), table_name="usage_events")
    op.drop_table("usage_events")
