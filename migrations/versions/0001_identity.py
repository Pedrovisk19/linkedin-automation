"""identity: tenants, users, api_keys + RLS policies + app.tenant_id GUC

Revision ID: 0001_identity
Revises:
Create Date: 2026-08-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_tenant_id_id", "users", ["tenant_id", "id"], unique=True)
    op.create_index("ix_users_tenant_email", "users", ["tenant_id", "email"], unique=True)

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("key_prefix", sa.String(24), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_revoked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("ix_api_keys_tenant_id_id", "api_keys", ["tenant_id", "id"], unique=True)
    op.create_index("ix_api_keys_tenant_prefix", "api_keys", ["tenant_id", "key_prefix"])

    bind.execute(sa.text("ALTER TABLE tenants SET (autovacuum_enabled = true)"))

    bind.execute(sa.text("ALTER TABLE users ENABLE ROW LEVEL SECURITY"))
    bind.execute(sa.text("ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY"))

    bind.execute(
        sa.text(
            "CREATE POLICY tenant_isolation ON users "
            "USING (tenant_id::text = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))"
        )
    )
    bind.execute(
        sa.text(
            "CREATE POLICY tenant_isolation ON api_keys "
            "USING (tenant_id::text = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))"
        )
    )

    bind.execute(sa.text("ALTER TABLE users FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text("ALTER TABLE api_keys FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation ON api_keys"))
    bind.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation ON users"))
    bind.execute(sa.text("ALTER TABLE api_keys NO FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text("ALTER TABLE users NO FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text("ALTER TABLE api_keys DISABLE ROW LEVEL SECURITY"))
    bind.execute(sa.text("ALTER TABLE users DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_api_keys_tenant_prefix", table_name="api_keys")
    op.drop_index("ix_api_keys_tenant_id_id", table_name="api_keys")
    op.drop_index("ix_api_keys_tenant_id", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index("ix_users_tenant_email", table_name="users")
    op.drop_index("ix_users_tenant_id_id", table_name="users")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
