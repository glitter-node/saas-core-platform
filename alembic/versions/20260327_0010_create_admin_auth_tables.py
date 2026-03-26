"""create admin auth tables

Revision ID: 20260327_0010
Revises: 20260327_0009
Create Date: 2026-03-27 00:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260327_0010"
down_revision: str | None = "20260327_0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("mfa_secret_encrypted", sa.String(length=255), nullable=True),
        sa.Column("last_admin_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bootstrap_source", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_admin_accounts_id"), "admin_accounts", ["id"], unique=False)
    op.create_index(op.f("ix_admin_accounts_user_id"), "admin_accounts", ["user_id"], unique=True)

    op.create_table(
        "admin_auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_account_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_family_id", sa.String(length=64), nullable=False),
        sa.Column("rotated_from_session_id", sa.Integer(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["admin_account_id"], ["admin_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rotated_from_session_id"], ["admin_auth_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_admin_auth_sessions_admin_account_id"), "admin_auth_sessions", ["admin_account_id"], unique=False)
    op.create_index(op.f("ix_admin_auth_sessions_id"), "admin_auth_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_admin_auth_sessions_rotated_from_session_id"), "admin_auth_sessions", ["rotated_from_session_id"], unique=False)
    op.create_index(op.f("ix_admin_auth_sessions_token_family_id"), "admin_auth_sessions", ["token_family_id"], unique=False)
    op.create_index(op.f("ix_admin_auth_sessions_token_hash"), "admin_auth_sessions", ["token_hash"], unique=True)

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_account_id", sa.Integer(), nullable=True),
        sa.Column("auth_session_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detail_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["admin_account_id"], ["admin_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["auth_session_id"], ["admin_auth_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_audit_logs_action"), "admin_audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_admin_audit_logs_admin_account_id"), "admin_audit_logs", ["admin_account_id"], unique=False)
    op.create_index(op.f("ix_admin_audit_logs_auth_session_id"), "admin_audit_logs", ["auth_session_id"], unique=False)
    op.create_index(op.f("ix_admin_audit_logs_created_at"), "admin_audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_admin_audit_logs_id"), "admin_audit_logs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_audit_logs_id"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_created_at"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_auth_session_id"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_admin_account_id"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_action"), table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")

    op.drop_index(op.f("ix_admin_auth_sessions_token_hash"), table_name="admin_auth_sessions")
    op.drop_index(op.f("ix_admin_auth_sessions_token_family_id"), table_name="admin_auth_sessions")
    op.drop_index(op.f("ix_admin_auth_sessions_rotated_from_session_id"), table_name="admin_auth_sessions")
    op.drop_index(op.f("ix_admin_auth_sessions_id"), table_name="admin_auth_sessions")
    op.drop_index(op.f("ix_admin_auth_sessions_admin_account_id"), table_name="admin_auth_sessions")
    op.drop_table("admin_auth_sessions")

    op.drop_index(op.f("ix_admin_accounts_user_id"), table_name="admin_accounts")
    op.drop_index(op.f("ix_admin_accounts_id"), table_name="admin_accounts")
    op.drop_table("admin_accounts")
