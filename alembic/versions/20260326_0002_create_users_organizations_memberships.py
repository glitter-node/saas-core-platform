"""create users organizations and memberships tables

Revision ID: 20260326_0002
Revises: 20260326_0001
Create Date: 2026-03-26 00:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260326_0002"
down_revision: Union[str, Sequence[str], None] = "20260326_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_organizations_tenant_id_tenants"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("tenant_id", name=op.f("uq_organizations_tenant_id")),
    )
    op.create_index(op.f("ix_organizations_id"), "organizations", ["id"], unique=False)
    op.create_index(op.f("ix_organizations_tenant_id"), "organizations", ["tenant_id"], unique=False)

    membership_role = sa.Enum("owner", "admin", "member", name="membershiprole", native_enum=False)
    op.create_table(
        "memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", membership_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_memberships_tenant_id_tenants"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_memberships_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memberships")),
        sa.UniqueConstraint("tenant_id", "user_id", name=op.f("uq_memberships_tenant_id")),
    )
    op.create_index(op.f("ix_memberships_id"), "memberships", ["id"], unique=False)
    op.create_index(op.f("ix_memberships_tenant_id"), "memberships", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_memberships_user_id"), "memberships", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_memberships_user_id"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_tenant_id"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_id"), table_name="memberships")
    op.drop_table("memberships")
    op.drop_index(op.f("ix_organizations_tenant_id"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_id"), table_name="organizations")
    op.drop_table("organizations")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
