"""create plans and subscriptions tables

Revision ID: 20260326_0003
Revises: 20260326_0002
Create Date: 2026-03-26 00:20:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260326_0003"
down_revision: Union[str, Sequence[str], None] = "20260326_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("limits_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plans")),
        sa.UniqueConstraint("code", name=op.f("uq_plans_code")),
    )
    op.create_index(op.f("ix_plans_code"), "plans", ["code"], unique=False)
    op.create_index(op.f("ix_plans_id"), "plans", ["id"], unique=False)

    plans_table = sa.table(
        "plans",
        sa.column("name", sa.String(length=120)),
        sa.column("code", sa.String(length=50)),
        sa.column("limits_json", sa.JSON()),
    )
    op.bulk_insert(
        plans_table,
        [
            {"name": "Free", "code": "free", "limits_json": {"members": 5, "projects": 1}},
            {"name": "Pro", "code": "pro", "limits_json": {"members": 25, "projects": 10}},
            {"name": "Enterprise", "code": "enterprise", "limits_json": {"members": 1000, "projects": 1000}},
        ],
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], name=op.f("fk_subscriptions_plan_id_plans")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_subscriptions_tenant_id_tenants"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
        sa.UniqueConstraint("stripe_customer_id", name=op.f("uq_subscriptions_stripe_customer_id")),
        sa.UniqueConstraint("stripe_subscription_id", name=op.f("uq_subscriptions_stripe_subscription_id")),
        sa.UniqueConstraint("tenant_id", name=op.f("uq_subscriptions_tenant_id")),
    )
    op.create_index(op.f("ix_subscriptions_id"), "subscriptions", ["id"], unique=False)
    op.create_index(op.f("ix_subscriptions_plan_id"), "subscriptions", ["plan_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_stripe_customer_id"), "subscriptions", ["stripe_customer_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_stripe_subscription_id"), "subscriptions", ["stripe_subscription_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_tenant_id"), "subscriptions", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_subscriptions_tenant_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_stripe_subscription_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_stripe_customer_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_plan_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_id"), table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index(op.f("ix_plans_id"), table_name="plans")
    op.drop_index(op.f("ix_plans_code"), table_name="plans")
    op.drop_table("plans")
