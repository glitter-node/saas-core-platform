"""add admin roles

Revision ID: 20260327_0012
Revises: 20260327_0011
Create Date: 2026-03-27 01:12:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260327_0012"
down_revision: str | None = "20260327_0011"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "admin_accounts",
        sa.Column("role", sa.String(length=32), nullable=False, server_default="admin"),
    )


def downgrade() -> None:
    op.drop_column("admin_accounts", "role")
