"""add tenant deleted_at

Revision ID: 20260327_0013
Revises: 20260327_0012
Create Date: 2026-03-27 09:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_0013"
down_revision = "20260327_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tenants_deleted_at", "tenants", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tenants_deleted_at", table_name="tenants")
    op.drop_column("tenants", "deleted_at")
