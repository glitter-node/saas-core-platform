"""add usage counter period start

Revision ID: 20260327_0008
Revises: 20260327_0007
Create Date: 2026-03-27 02:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260327_0008"
down_revision: Union[str, Sequence[str], None] = "20260327_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usage_counters",
        sa.Column(
            "period_start",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("'1970-01-01 00:00:00'"),
        ),
    )
    op.drop_constraint(op.f("uq_usage_counters_tenant_id"), "usage_counters", type_="unique")
    op.create_unique_constraint(
        op.f("uq_usage_counters_tenant_id"),
        "usage_counters",
        ["tenant_id", "metric_code", "period_start"],
    )
    op.alter_column("usage_counters", "period_start", server_default=None)


def downgrade() -> None:
    op.drop_constraint(op.f("uq_usage_counters_tenant_id"), "usage_counters", type_="unique")
    op.create_unique_constraint(op.f("uq_usage_counters_tenant_id"), "usage_counters", ["tenant_id", "metric_code"])
    op.drop_column("usage_counters", "period_start")
