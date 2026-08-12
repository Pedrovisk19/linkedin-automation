"""discord: criacao da tabela discord_requests + RLS policies.

Revision ID: 0009_discord
Revises: 0008_telegram
Create Date: 2026-08-11

Espelha a tabela telegram_requests (que nasceu como whatsapp_requests): cada
mensagem aceita no canal gera um pedido de aprovacao de publicacao, com os
botoes do Discord em vez de callback keyboard.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_discord"
down_revision = "0008_telegram"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "discord_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("channel_id", sa.BigInteger, nullable=False),
        sa.Column(
            "draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
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
    op.create_index("ix_discord_requests_tenant_id", "discord_requests", ["tenant_id"])
    op.create_index(
        "ix_discord_requests_tenant_id_id",
        "discord_requests",
        ["tenant_id", "id"],
        unique=True,
    )
    op.create_index(
        "ix_discord_requests_tenant_channel_status",
        "discord_requests",
        ["tenant_id", "channel_id", "status"],
    )

    bind.execute(sa.text("ALTER TABLE discord_requests ENABLE ROW LEVEL SECURITY"))
    bind.execute(
        sa.text(
            "CREATE POLICY tenant_isolation ON discord_requests "
            "USING (tenant_id::text = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))"
        )
    )
    bind.execute(sa.text("ALTER TABLE discord_requests FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE discord_requests NO FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation ON discord_requests"))
    bind.execute(sa.text("ALTER TABLE discord_requests DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_discord_requests_tenant_channel_status", table_name="discord_requests")
    op.drop_index("ix_discord_requests_tenant_id_id", table_name="discord_requests")
    op.drop_index("ix_discord_requests_tenant_id", table_name="discord_requests")
    op.drop_table("discord_requests")
