"""DTOs do automation (application layer)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from developer_brain_ai_automation.domain.value_objects import PipelineStep


class PipelineConfig(BaseModel):
    """Configuracao do job diario (lida do app config no worker)."""

    ai_language: str = "pt-BR"
    ai_writing_tone: str = "Natural e envolvente, sem exageros"
    publish_scheduled_for: datetime | None = None
    #: quando None, agenda para o proximo dia util as 09:00


class PipelineStepResult(BaseModel):
    """Resultado de um step para um tenant (para o relatorio do job)."""

    tenant_id: str
    step: PipelineStep
    status: Literal["succeeded", "failed", "skipped"]
    output_summary: str = ""
    error: str | None = None


class RunPipelineOut(BaseModel):
    """Relatorio da execucao do RunDailyPipeline."""

    pipeline_date: date
    steps: list[PipelineStepResult] = Field(default_factory=list)
    tenants: int = 0


__all__ = ["PipelineConfig", "PipelineStepResult", "RunPipelineOut"]
