"""content: criacao de tabela content_drafts + publication_queue_items + RLS policies.

Revision ID: 0003_content
Revises: 0002_journal
Create Date: 2026-08-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_content"
down_revision = "0002_journal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "content_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("agent", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body_markdown", sa.Text, nullable=False),
        sa.Column(
            "hashtags",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "metadata",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending_review"),
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
    op.create_index("ix_content_drafts_tenant_id", "content_drafts", ["tenant_id"])
    op.create_index(
        "ix_content_drafts_tenant_id_id", "content_drafts", ["tenant_id", "id"], unique=True
    )
    op.create_index("ix_content_drafts_tenant_status", "content_drafts", ["tenant_id", "status"])

    op.create_table(
        "publication_queue_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_publication_queue_tenant_id", "publication_queue_items", ["tenant_id"])
    op.create_index(
        "ix_publication_queue_tenant_id_id",
        "publication_queue_items",
        ["tenant_id", "id"],
        unique=True,
    )
    op.create_index(
        "ix_publication_queue_tenant_scheduled",
        "publication_queue_items",
        ["tenant_id", "scheduled_for"],
    )

    for table in ("content_drafts", "publication_queue_items"):
        bind.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        bind.execute(
            sa.text(
                f"CREATE POLICY tenant_isolation ON {table} "
                "USING (tenant_id::text = current_setting('app.tenant_id', true)) "
                "WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))"
            )
        )
        bind.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("content_drafts", "publication_queue_items"):
        bind.execute(sa.text(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY"))
        bind.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        bind.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_publication_queue_tenant_scheduled", table_name="publication_queue_items")
    op.drop_index("ix_publication_queue_tenant_id_id", table_name="publication_queue_items")
    op.drop_index("ix_publication_queue_tenant_id", table_name="publication_queue_items")
    op.drop_table("publication_queue_items")
    op.drop_index("ix_content_drafts_tenant_status", table_name="content_drafts")
    op.drop_index("ix_content_drafts_tenant_id_id", table_name="content_drafts")
    op.drop_index("ix_content_drafts_tenant_id", table_name="content_drafts")
    op.drop_table("content_drafts")
