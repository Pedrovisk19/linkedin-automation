"""Agregado PipelineRun: execucao de um step do pipeline diario, idempotente.

Cada (tenant, pipeline_date, step) tem UMA linha. Estado avanca por transicoes
explicitas:
- start()        -> PENDING
- mark_succeeded -> SUCCEEDED (guarda output_summary)
- mark_failed    -> FAILED (guarda error, permitindo retry que substitui a linha)

A chave composta garante dedupe: re-rodar o job no mesmo dia nao duplica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow

from developer_brain_ai_automation.domain.ids import PipelineRunId
from developer_brain_ai_automation.domain.value_objects import PipelineRunStatus, PipelineStep


@dataclass(eq=False)
class PipelineRun(AggregateRoot):
    id: PipelineRunId
    tenant_id: TenantId
    pipeline_date: date
    step: PipelineStep
    status: PipelineRunStatus = PipelineRunStatus.PENDING
    output_summary: str = ""
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    timestamps: Timestamps = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not isinstance(self.step, PipelineStep):
            raise TypeError("step deve ser PipelineStep")
        if not isinstance(self.status, PipelineRunStatus):
            raise TypeError("status deve ser PipelineRunStatus")
        if not isinstance(self.pipeline_date, date):
            raise TypeError("pipeline_date deve ser date")
        if self.timestamps is None:
            now = utcnow()
            object.__setattr__(self, "timestamps", Timestamps(created_at=now, updated_at=now))

    @property
    def is_succeeded(self) -> bool:
        return self.status == PipelineRunStatus.SUCCEEDED

    @property
    def is_failed(self) -> bool:
        return self.status == PipelineRunStatus.FAILED

    def start(self, *, at: datetime | None = None) -> None:

        object.__setattr__(self, "status", PipelineRunStatus.PENDING)
        object.__setattr__(self, "started_at", at or utcnow())
        object.__setattr__(self, "finished_at", None)
        object.__setattr__(self, "error", None)
        object.__setattr__(self, "output_summary", "")
        _touch(self)

    def mark_succeeded(self, *, output_summary: str = "", at: datetime | None = None) -> None:

        object.__setattr__(self, "status", PipelineRunStatus.SUCCEEDED)
        object.__setattr__(self, "output_summary", (output_summary or "")[:500])
        object.__setattr__(self, "finished_at", at or utcnow())
        object.__setattr__(self, "error", None)
        _touch(self)

    def mark_failed(self, *, error: str, at: datetime | None = None) -> None:

        object.__setattr__(self, "status", PipelineRunStatus.FAILED)
        object.__setattr__(self, "error", (error or "")[:1000])
        object.__setattr__(self, "finished_at", at or utcnow())
        _touch(self)


def _touch(run: PipelineRun) -> None:

    object.__setattr__(run, "timestamps", run.timestamps.touch(at=utcnow()))


__all__ = ["PipelineRun"]
