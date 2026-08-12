"""news: criacao da tabela news_items (RLS) para fetch de fontes externas.

Revision ID: 0010_news
Revises: 0009_discord
Create Date: 2026-08-12

Cada item coletado de fonte externa (RSS, HN, PyPI) vira uma linha em
``news_items``. Dedupe por (tenant_id, content_hash) unico — inserções
concorrentes usam ON CONFLICT DO NOTHING. O campo ``source`` identifica a
fonte (realpython, pythoninsider, peps, hackernews, github_trending) para
o digest ranquear por diversidade.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_news"
down_revision = "0009_discord"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "news_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
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
    op.create_index("ix_news_items_tenant_id", "news_items", ["tenant_id"])
    op.create_index(
        "ix_news_items_tenant_id_id",
        "news_items",
        ["tenant_id", "id"],
        unique=True,
    )
    op.create_index(
        "ix_news_items_tenant_hash",
        "news_items",
        ["tenant_id", "content_hash"],
        unique=True,
    )
    op.create_index(
        "ix_news_items_tenant_published",
        "news_items",
        ["tenant_id", "published_at"],
    )

    bind.execute(sa.text("ALTER TABLE news_items ENABLE ROW LEVEL SECURITY"))
    bind.execute(
        sa.text(
            "CREATE POLICY tenant_isolation ON news_items "
            "USING (tenant_id::text = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))"
        )
    )
    bind.execute(sa.text("ALTER TABLE news_items FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE news_items NO FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation ON news_items"))
    bind.execute(sa.text("ALTER TABLE news_items DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_news_items_tenant_published", table_name="news_items")
    op.drop_index("ix_news_items_tenant_hash", table_name="news_items")
    op.drop_index("ix_news_items_tenant_id_id", table_name="news_items")
    op.drop_index("ix_news_items_tenant_id", table_name="news_items")
    op.drop_table("news_items")
