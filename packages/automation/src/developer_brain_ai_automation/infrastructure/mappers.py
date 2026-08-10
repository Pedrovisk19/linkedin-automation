"""Mappers ORM <-> domain do automation."""

from __future__ import annotations

from datetime import UTC, datetime

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_automation.domain.aggregates import PipelineRun
from developer_brain_ai_automation.domain.ids import PipelineRunId
from developer_brain_ai_automation.domain.value_objects import PipelineRunStatus, PipelineStep
from developer_brain_ai_automation.infrastructure.orm import PipelineRunORM

_UTC = UTC


def run_to_orm(run: PipelineRun) -> PipelineRunORM:
    return PipelineRunORM(
        id=run.id.as_uuid(),
        tenant_id=run.tenant_id.as_uuid(),
        pipeline_date=run.pipeline_date,
        step=run.step.value,
        status=run.status.value,
        output_summary=run.output_summary,
        error=run.error,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.timestamps.created_at,
        updated_at=run.timestamps.updated_at,
    )


def run_from_orm(o: PipelineRunORM) -> PipelineRun:
    return PipelineRun(
        id=PipelineRunId(o.id),
        tenant_id=TenantId(o.tenant_id),
        pipeline_date=o.pipeline_date,
        step=PipelineStep(o.step),
        status=PipelineRunStatus(o.status),
        output_summary=o.output_summary or "",
        error=o.error,
        started_at=_as_utc(o.started_at),
        finished_at=_as_utc(o.finished_at),
        timestamps=Timestamps(created_at=o.created_at, updated_at=o.updated_at),
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=_UTC)
    return value.astimezone(_UTC)


__all__ = ["run_from_orm", "run_to_orm"]
