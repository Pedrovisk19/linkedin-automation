"""integrations: criacao de tabela linkedin_tokens + RLS policies.

Revision ID: 0005_linkedin_tokens
Revises: 0004_automation
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_linkedin_tokens"
down_revision = "0004_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "linkedin_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("access_token", sa.Text, nullable=False),
        sa.Column("refresh_token", sa.Text, nullable=False),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("member_urn", sa.String(128), nullable=False),
        sa.Column("member_name", sa.String(200), nullable=False),
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
    op.create_index("ix_linkedin_tokens_tenant_id", "linkedin_tokens", ["tenant_id"], unique=True)

    bind.execute(sa.text("ALTER TABLE linkedin_tokens ENABLE ROW LEVEL SECURITY"))
    bind.execute(
        sa.text(
            "CREATE POLICY tenant_isolation ON linkedin_tokens "
            "USING (tenant_id::text = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))"
        )
    )
    bind.execute(sa.text("ALTER TABLE linkedin_tokens FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE linkedin_tokens NO FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation ON linkedin_tokens"))
    bind.execute(sa.text("ALTER TABLE linkedin_tokens DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_linkedin_tokens_tenant_id", table_name="linkedin_tokens")
    op.drop_table("linkedin_tokens")
