"""create auth sessions

Revision ID: 20260327_0009
Revises: 20260327_0008
Create Date: 2026-03-27 02:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260327_0009"
down_revision: Union[str, Sequence[str], None] = "20260327_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_family_id", sa.String(length=64), nullable=False),
        sa.Column("rotated_from_session_id", sa.Integer(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["rotated_from_session_id"], ["auth_sessions.id"], name=op.f("fk_auth_sessions_rotated_from_session_id_auth_sessions"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_auth_sessions_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_auth_sessions_token_hash")),
    )
    op.create_index(op.f("ix_auth_sessions_id"), "auth_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_auth_sessions_token_hash"), "auth_sessions", ["token_hash"], unique=False)
    op.create_index(op.f("ix_auth_sessions_token_family_id"), "auth_sessions", ["token_family_id"], unique=False)
    op.create_index(op.f("ix_auth_sessions_rotated_from_session_id"), "auth_sessions", ["rotated_from_session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_sessions_rotated_from_session_id"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_token_family_id"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_token_hash"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_user_id"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_id"), table_name="auth_sessions")
    op.drop_table("auth_sessions")
