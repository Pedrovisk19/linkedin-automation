"""Testes de dominio do automation: PipelineRun + transicoes."""

from __future__ import annotations

from datetime import date

from developer_brain_ai_automation.domain.aggregates import PipelineRun
from developer_brain_ai_automation.domain.ids import PipelineRunId
from developer_brain_ai_automation.domain.value_objects import PipelineRunStatus, PipelineStep
from developer_brain_ai_shared.kernel.id import TenantId

DAY = date(2026, 8, 7)


def _run() -> PipelineRun:
    return PipelineRun(
        id=PipelineRunId.new(),
        tenant_id=TenantId.new(),
        pipeline_date=DAY,
        step=PipelineStep.SUMMARY,
    )


def test_novo_run_pending_com_timestamps() -> None:
    run = _run()
    assert run.status == PipelineRunStatus.PENDING
    assert run.is_succeeded is False
    assert run.timestamps.created_at is not None
    assert run.pipeline_date == DAY


def test_step_nao_enum_e_rejeitado() -> None:
    try:
        PipelineRun(
            id=PipelineRunId.new(),
            tenant_id=TenantId.new(),
            pipeline_date=DAY,
            step="summary",  # type: ignore[arg-type]
        )
    except TypeError:
        return
    raise AssertionError("step fora do enum deveria levantar TypeError")


def test_start_marca_pending_e_limpa_estado_anterior() -> None:
    run = _run()
    run.mark_succeeded(output_summary="ok")
    run.start()
    assert run.status == PipelineRunStatus.PENDING
    assert run.output_summary == ""
    assert run.error is None
    assert run.started_at is not None
    assert run.finished_at is None


def test_mark_succeeded_guarda_output_e_trunca() -> None:
    run = _run()
    run.start()
    run.mark_succeeded(output_summary="x" * 600)
    assert run.is_succeeded
    assert len(run.output_summary) == 500
    assert run.error is None
    assert run.finished_at is not None


def test_mark_failed_guarda_error_trunca_e_permite_retry() -> None:
    run = _run()
    run.start()
    run.mark_failed(error="boom " * 300)
    assert run.is_failed
    assert run.error is not None
    assert len(run.error) == 1000
    # retry: succeed substitui o estado
    run.mark_succeeded(output_summary="ok")
    assert run.is_succeeded
    assert run.error is None
