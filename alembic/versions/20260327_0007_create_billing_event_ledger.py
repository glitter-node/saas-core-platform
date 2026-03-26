"""create billing event ledger

Revision ID: 20260327_0007
Revises: 20260326_0006
Create Date: 2026-03-27 01:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260327_0007"
down_revision: Union[str, Sequence[str], None] = "20260326_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_event_ledger",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_event_ledger")),
        sa.UniqueConstraint("stripe_event_id", name=op.f("uq_billing_event_ledger_stripe_event_id")),
    )
    op.create_index(op.f("ix_billing_event_ledger_id"), "billing_event_ledger", ["id"], unique=False)
    op.create_index(op.f("ix_billing_event_ledger_stripe_event_id"), "billing_event_ledger", ["stripe_event_id"], unique=False)
    op.create_index(op.f("ix_billing_event_ledger_event_type"), "billing_event_ledger", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_billing_event_ledger_event_type"), table_name="billing_event_ledger")
    op.drop_index(op.f("ix_billing_event_ledger_stripe_event_id"), table_name="billing_event_ledger")
    op.drop_index(op.f("ix_billing_event_ledger_id"), table_name="billing_event_ledger")
    op.drop_table("billing_event_ledger")
