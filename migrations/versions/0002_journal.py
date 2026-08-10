"""journal: criacao de tabela journal_entries + tags + join + RLS policies.

Revision ID: 0002_journal
Revises: 0001_identity
Create Date: 2026-08-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_journal"
down_revision = "0001_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("study_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("technologies", sa.Text, nullable=False, server_default="[]"),
        sa.Column("project", sa.String(200), nullable=False, server_default=""),
        sa.Column("book", sa.String(200), nullable=False, server_default=""),
        sa.Column("course", sa.String(200), nullable=False, server_default=""),
        sa.Column("videos", sa.Text, nullable=False, server_default="[]"),
        sa.Column("links", sa.Text, nullable=False, server_default="[]"),
        sa.Column("difficulties", sa.Text, nullable=False, server_default=""),
        sa.Column("learnings", sa.Text, nullable=False, server_default=""),
        sa.Column("bugs_found", sa.Text, nullable=False, server_default="[]"),
        sa.Column("resolutions", sa.Text, nullable=False, server_default="[]"),
        sa.Column("next_steps", sa.Text, nullable=False, server_default=""),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
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
    op.create_index("ix_journal_entries_tenant_id", "journal_entries", ["tenant_id"])
    op.create_index(
        "ix_journal_entries_tenant_id_id", "journal_entries", ["tenant_id", "id"], unique=True
    )
    op.create_index(
        "ix_journal_entries_tenant_date", "journal_entries", ["tenant_id", "entry_date"]
    )

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("value", sa.String(40), nullable=False),
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
    op.create_index("ix_tags_tenant_id", "tags", ["tenant_id"])
    op.create_index("ix_tags_tenant_value", "tags", ["tenant_id", "value"], unique=True)

    op.create_table(
        "journal_entry_tags",
        sa.Column(
            "journal_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("journal_entries.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_jet_entry_tag", "journal_entry_tags", ["journal_entry_id", "tag_id"], unique=True
    )

    bind.execute(sa.text("ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY"))
    bind.execute(sa.text("ALTER TABLE tags ENABLE ROW LEVEL SECURITY"))
    bind.execute(
        sa.text(
            "CREATE POLICY tenant_isolation ON journal_entries "
            "USING (tenant_id::text = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))"
        )
    )
    bind.execute(
        sa.text(
            "CREATE POLICY tenant_isolation ON tags "
            "USING (tenant_id::text = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))"
        )
    )
    bind.execute(sa.text("ALTER TABLE journal_entries FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text("ALTER TABLE tags FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("ALTER TABLE tags NO FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text("ALTER TABLE journal_entries NO FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation ON tags"))
    bind.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation ON journal_entries"))
    bind.execute(sa.text("ALTER TABLE tags DISABLE ROW LEVEL SECURITY"))
    bind.execute(sa.text("ALTER TABLE journal_entries DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_jet_entry_tag", table_name="journal_entry_tags")
    op.drop_table("journal_entry_tags")
    op.drop_index("ix_tags_tenant_value", table_name="tags")
    op.drop_index("ix_tags_tenant_id", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_journal_entries_tenant_date", table_name="journal_entries")
    op.drop_index("ix_journal_entries_tenant_id_id", table_name="journal_entries")
    op.drop_index("ix_journal_entries_tenant_id", table_name="journal_entries")
    op.drop_table("journal_entries")
