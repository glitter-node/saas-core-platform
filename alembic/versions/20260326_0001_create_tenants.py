"""create tenants table

Revision ID: 20260326_0001
Revises: 
Create Date: 2026-03-26 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260326_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("subdomain", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenants")),
        sa.UniqueConstraint("slug", name=op.f("uq_tenants_slug")),
        sa.UniqueConstraint("subdomain", name=op.f("uq_tenants_subdomain")),
    )
    op.create_index(op.f("ix_tenants_id"), "tenants", ["id"], unique=False)
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=False)
    op.create_index(op.f("ix_tenants_subdomain"), "tenants", ["subdomain"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tenants_subdomain"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_id"), table_name="tenants")
    op.drop_table("tenants")
