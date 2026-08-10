"""Testes do RunDailyPipeline: idempotencia, skip, falha e contexto RLS."""

from __future__ import annotations

from datetime import UTC, date, datetime

from automation_fakes import (
    FakeEntryReader,
    FakeLinkedInDraftCreator,
    FakePipelineRunRepository,
    FakeQueuer,
    FakeSummaryGenerator,
    FakeTenantLister,
)
from developer_brain_ai_automation.application.dto import PipelineConfig
from developer_brain_ai_automation.application.use_cases import RunDailyPipeline
from developer_brain_ai_automation.domain.value_objects import PipelineStep
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.persistence.tenant import get_tenant_context_optional

DAY = date(2026, 8, 7)


def _pipeline(
    tenants,
    *,
    repo=None,
    reader=None,
    summary=None,
    drafts=None,
    queue=None,
    config=None,
):
    return RunDailyPipeline(
        pipeline_runs=repo or FakePipelineRunRepository(),
        tenants=tenants,
        entries=reader or FakeEntryReader(),
        summaries=summary or FakeSummaryGenerator(),
        drafts=drafts or FakeLinkedInDraftCreator(),
        queue=queue or FakeQueuer(),
        config=config
        or PipelineConfig(publish_scheduled_for=datetime(2026, 8, 8, 9, 0, tzinfo=UTC)),
    )


def _tenant_a() -> TenantId:
    return TenantId.new()


def _with_entries(reader: FakeEntryReader, tenant: TenantId) -> None:
    reader.set_entries(tenant, [{"id": "1"}, {"id": "2"}])


def test_fluxo_feliz_gera_summary_draft_e_agenda() -> None:
    tenant = _tenant_a()
    reader = FakeEntryReader()
    _with_entries(reader, tenant)
    queue = FakeQueuer()
    repo = FakePipelineRunRepository()
    pipeline = _pipeline(FakeTenantLister([tenant]), repo=repo, reader=reader, queue=queue)

    report = __import__("asyncio").run(pipeline.execute(pipeline_date=DAY))

    assert report.tenants == 1
    assert [s.status for s in report.steps] == ["succeeded", "succeeded"]
    assert repo.count(PipelineStep.SUMMARY) == 1
    assert repo.count(PipelineStep.LINKEDIN) == 1
    assert len(queue.items) == 1
    assert queue.items[0][0] == "draft-1"
    assert queue.items[0][1].tzinfo is not None


def test_idempotencia_segunda_rodada_nao_duplica() -> None:
    tenant = _tenant_a()
    reader = FakeEntryReader()
    _with_entries(reader, tenant)
    repo = FakePipelineRunRepository()
    pipeline = _pipeline(FakeTenantLister([tenant]), repo=repo, reader=reader, queue=FakeQueuer())

    __import__("asyncio").run(pipeline.execute(pipeline_date=DAY))
    __import__("asyncio").run(pipeline.execute(pipeline_date=DAY))

    assert repo.count(PipelineStep.SUMMARY) == 1
    assert repo.count(PipelineStep.LINKEDIN) == 1
    assert len(repo.saved) == 2  # nada re-executado na 2a rodada


def test_tenant_sem_entries_fica_skipped_e_nao_persiste() -> None:
    tenant = _tenant_a()
    repo = FakePipelineRunRepository()
    pipeline = _pipeline(
        FakeTenantLister([tenant]),
        repo=repo,
        reader=FakeEntryReader(),
        queue=FakeQueuer(),
    )

    report = __import__("asyncio").run(pipeline.execute(pipeline_date=DAY))

    assert [s.status for s in report.steps] == ["skipped", "skipped"]
    assert repo.count(PipelineStep.SUMMARY) == 0
    assert repo.count(PipelineStep.LINKEDIN) == 0


def test_falha_do_step_registra_failed_e_continua_outro_tenant() -> None:
    a, b = _tenant_a(), TenantId.new()
    reader = FakeEntryReader()
    _with_entries(reader, a)
    _with_entries(reader, b)
    repo = FakePipelineRunRepository()
    pipeline = _pipeline(
        FakeTenantLister([a, b]),
        repo=repo,
        reader=reader,
        summary=FakeSummaryGenerator(fail=True),
        queue=FakeQueuer(),
    )

    report = __import__("asyncio").run(pipeline.execute(pipeline_date=DAY))

    assert report.tenants == 2
    statuses = [s.status for s in report.steps]
    assert statuses.count("failed") == 2  # summary falhou nos 2 tenants
    assert statuses.count("succeeded") == 2  # linkedin seguiu em ambos
    failed = [s for s in report.steps if s.status == "failed"]
    assert failed[0].error and "summary boom" in failed[0].error
    assert repo.count(PipelineStep.SUMMARY) == 2


def test_retry_apos_falha_substitui_linha_sem_duplicar() -> None:
    tenant = _tenant_a()
    reader = FakeEntryReader()
    _with_entries(reader, tenant)
    repo = FakePipelineRunRepository()
    failing = FakeSummaryGenerator(fail=True)
    pipeline = _pipeline(
        FakeTenantLister([tenant]),
        repo=repo,
        reader=reader,
        summary=failing,
        queue=FakeQueuer(),
    )

    __import__("asyncio").run(pipeline.execute(pipeline_date=DAY))
    assert repo.count(PipelineStep.SUMMARY) == 1

    ok = FakeSummaryGenerator()
    pipeline2 = _pipeline(
        FakeTenantLister([tenant]),
        repo=repo,
        reader=reader,
        summary=ok,
        queue=FakeQueuer(),
    )
    report = __import__("asyncio").run(pipeline2.execute(pipeline_date=DAY))

    assert repo.count(PipelineStep.SUMMARY) == 1  # sem duplicar
    summary_step = next(s for s in report.steps if s.step == PipelineStep.SUMMARY)
    assert summary_step.status == "succeeded"


def test_contexto_rls_define_tenant_por_tenant() -> None:
    a, b = _tenant_a(), TenantId.new()
    reader = FakeEntryReader()
    _with_entries(reader, a)
    _with_entries(reader, b)
    seen = []

    class _Probe:
        async def list_entries(self, *, tenant_id, day):
            seen.append(get_tenant_context_optional())
            return [{"id": "x"}]

    pipeline = _pipeline(FakeTenantLister([a, b]), reader=_Probe(), queue=FakeQueuer())
    __import__("asyncio").run(pipeline.execute(pipeline_date=DAY))

    assert {str(s.as_uuid()) for s in seen if s} == {str(a.as_uuid()), str(b.as_uuid())}
