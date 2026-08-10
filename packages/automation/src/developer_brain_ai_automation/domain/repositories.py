"""Protocolos de persistencia do automation (injetados em application)."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from developer_brain_ai_shared.kernel.id import TenantId

from developer_brain_ai_automation.domain.aggregates import PipelineRun
from developer_brain_ai_automation.domain.value_objects import PipelineStep


class PipelineRunRepository(Protocol):
    """Persistencia de PipelineRun.

    Garante a invariante de idempotencia da Fase 7a: o par (pipeline_date, step)
    dentro de um tenant eh uma chave unica (UX no banco + dedupe em memoria aqui).
    """

    async def get_by_key(
        self, *, tenant_id: TenantId, pipeline_date: date, step: PipelineStep
    ) -> PipelineRun | None:
        """Retorna o run existente de (tenant, date, step) ou None."""
        ...

    async def save(self, run: PipelineRun) -> PipelineRun:
        """Persiste o run (insert/update) e devolve a versao salva."""
        ...


__all__ = ["PipelineRunRepository"]
