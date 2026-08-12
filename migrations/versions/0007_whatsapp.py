"""whatsapp: criacao da tabela whatsapp_requests + RLS policies.

Revision ID: 0007_whatsapp
Revises: 0006_linkedin_optional_refresh
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_whatsapp"
down_revision = "0006_linkedin_optional_refresh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "whatsapp_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column(
            "draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
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
    op.create_index("ix_whatsapp_requests_tenant_id", "whatsapp_requests", ["tenant_id"])
    op.create_index(
        "ix_whatsapp_requests_tenant_id_id",
        "whatsapp_requests",
        ["tenant_id", "id"],
        unique=True,
    )
    op.create_index(
        "ix_whatsapp_requests_tenant_phone_status",
        "whatsapp_requests",
        ["tenant_id", "phone", "status"],
    )

    bind.execute(sa.text("ALTER TABLE whatsapp_requests ENABLE ROW LEVEL SECURITY"))
    bind.execute(
        sa.text(
            "CREATE POLICY tenant_isolation ON whatsapp_requests "
            "USING (tenant_id::text = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))"
        )
    )
    bind.execute(sa.text("ALTER TABLE whatsapp_requests FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE whatsapp_requests NO FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation ON whatsapp_requests"))
    bind.execute(sa.text("ALTER TABLE whatsapp_requests DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_whatsapp_requests_tenant_phone_status", table_name="whatsapp_requests")
    op.drop_index("ix_whatsapp_requests_tenant_id_id", table_name="whatsapp_requests")
    op.drop_index("ix_whatsapp_requests_tenant_id", table_name="whatsapp_requests")
    op.drop_table("whatsapp_requests")
