"""automation: tabela pipeline_runs para rastreio idempotente do DailyPipeline + RLS.

Revision ID: 0004_automation
Revises: 0003_content
Create Date: 2026-08-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_automation"
down_revision = "0003_content"
branch_labels = None
depends_on = None

TABLE = "pipeline_runs"


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("pipeline_date", sa.Date(), nullable=False),
        sa.Column("step", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("output_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_pipeline_runs_tenant_id", TABLE, ["tenant_id"])
    op.create_index(
        "ux_pipeline_runs_tenant_date_step",
        TABLE,
        ["tenant_id", "pipeline_date", "step"],
        unique=True,
    )
    op.create_index("ix_pipeline_runs_tenant_date", TABLE, ["tenant_id", "pipeline_date"])

    bind.execute(sa.text(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY"))
    bind.execute(
        sa.text(
            f"CREATE POLICY tenant_isolation ON {TABLE} "
            "USING (tenant_id::text = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))"
        )
    )
    bind.execute(sa.text(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(f"ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY"))
    bind.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {TABLE}"))
    bind.execute(sa.text(f"ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_pipeline_runs_tenant_date", table_name=TABLE)
    op.drop_index("ux_pipeline_runs_tenant_date_step", table_name=TABLE)
    op.drop_index("ix_pipeline_runs_tenant_id", table_name=TABLE)
    op.drop_table(TABLE)
