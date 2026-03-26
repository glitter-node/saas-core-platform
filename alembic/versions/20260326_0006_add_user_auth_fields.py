"""add user auth fields

Revision ID: 20260326_0006
Revises: 20260326_0005
Create Date: 2026-03-26 02:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260326_0006"
down_revision: Union[str, Sequence[str], None] = "20260326_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=False, server_default="!"))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("users", "password_hash", server_default=None)
    op.alter_column("users", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_active")
    op.drop_column("users", "password_hash")
