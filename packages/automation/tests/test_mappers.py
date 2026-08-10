"""Testes dos mappers ORM <-> domain do automation."""

from __future__ import annotations

from datetime import UTC, date, datetime

from developer_brain_ai_automation.domain.aggregates import PipelineRun
from developer_brain_ai_automation.domain.ids import PipelineRunId
from developer_brain_ai_automation.domain.value_objects import PipelineRunStatus, PipelineStep
from developer_brain_ai_automation.infrastructure.mappers import run_from_orm, run_to_orm
from developer_brain_ai_shared.kernel.id import TenantId

DAY = date(2026, 8, 7)


def _run() -> PipelineRun:
    run = PipelineRun(
        id=PipelineRunId.new(),
        tenant_id=TenantId.new(),
        pipeline_date=DAY,
        step=PipelineStep.LINKEDIN,
    )
    run.start()
    run.mark_succeeded(output_summary="draft publicado")
    return run


def test_roundtrip_preserva_campos() -> None:
    run = _run()

    orm = run_to_orm(run)
    back = run_from_orm(orm)

    assert back.id == run.id
    assert back.tenant_id == run.tenant_id
    assert back.pipeline_date == DAY
    assert back.step == PipelineStep.LINKEDIN
    assert back.status == PipelineRunStatus.SUCCEEDED
    assert back.output_summary == "draft publicado"
    assert back.started_at == run.started_at
    assert back.finished_at == run.finished_at
    assert back.timestamps == run.timestamps


def test_to_orm_guarda_datetime_naive_em_utc() -> None:
    run = _run()
    orm = run_to_orm(run)
    assert orm.pipeline_date == DAY
    assert orm.step == "linkedin"
    assert orm.status == "succeeded"


def test_from_orm_aceita_datetime_sem_tz() -> None:
    run = _run()
    orm = run_to_orm(run)
    orm.started_at = datetime(2026, 8, 7, 5, 0)
    back = run_from_orm(orm)
    assert back.started_at is not None
    assert back.started_at.tzinfo == UTC
