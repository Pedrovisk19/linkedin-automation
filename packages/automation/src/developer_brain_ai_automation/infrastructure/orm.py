"""ORM models do automation (Fase 7a).

Tabela ``pipeline_runs`` (TenantScoped): rastreio idempotente de execucao do
DailyPipeline. Chave unica (tenant_id, pipeline_date, step) garante dedupe:
re-rodar o job no mesmo dia nunca duplica trabalho.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from developer_brain_ai_shared.persistence.base import Base, TenantScopedMixin, TimestampMixin
from sqlalchemy import Date, DateTime, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column


class PipelineRunORM(TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        Index(
            "ux_pipeline_runs_tenant_date_step",
            "tenant_id",
            "pipeline_date",
            "step",
            unique=True,
        ),
        Index("ix_pipeline_runs_tenant_date", "tenant_id", "pipeline_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    pipeline_date: Mapped[date] = mapped_column(Date, nullable=False)
    step: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    output_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


__all__ = ["PipelineRunORM"]
