"""create auth magic links

Revision ID: 20260327_0011
Revises: 20260327_0010
Create Date: 2026-03-27 01:11:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260327_0011"
down_revision: str | None = "20260327_0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_magic_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("flow", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_auth_magic_links_id"), "auth_magic_links", ["id"], unique=False)
    op.create_index(op.f("ix_auth_magic_links_email"), "auth_magic_links", ["email"], unique=False)
    op.create_index(op.f("ix_auth_magic_links_token_hash"), "auth_magic_links", ["token_hash"], unique=True)
    op.create_index(op.f("ix_auth_magic_links_flow"), "auth_magic_links", ["flow"], unique=False)
    op.create_index(op.f("ix_auth_magic_links_tenant_id"), "auth_magic_links", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_magic_links_tenant_id"), table_name="auth_magic_links")
    op.drop_index(op.f("ix_auth_magic_links_flow"), table_name="auth_magic_links")
    op.drop_index(op.f("ix_auth_magic_links_token_hash"), table_name="auth_magic_links")
    op.drop_index(op.f("ix_auth_magic_links_email"), table_name="auth_magic_links")
    op.drop_index(op.f("ix_auth_magic_links_id"), table_name="auth_magic_links")
    op.drop_table("auth_magic_links")
