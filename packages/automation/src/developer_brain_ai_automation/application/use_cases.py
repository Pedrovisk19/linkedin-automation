"""Use case RunDailyPipeline: orquestra journal -> summary -> linkedin -> queue.

Idempotencia (Fase 7a):
- Cada (tenant, pipeline_date, step) eh chave unica na tabela ``pipeline_runs``.
- Sucesso re-rodado no mesmo dia nao refaz trabalho (early-return).
- Falha fica registrada (``failed``) e o retry substitui a linha, sem duplicar.
- Tenant sem entries no dia eh SKIPPED (nada persiste).

Contexto RLS: o use case itera tenants e define o tenant corrente no contextvar
(shared kernel) por tenant; os bancos do shared emitem ``SET LOCAL`` por conexao.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, datetime, time, timedelta

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import utcnow
from developer_brain_ai_shared.persistence.tenant import reset_tenant_context, set_tenant_context

from developer_brain_ai_automation.application.dto import (
    PipelineConfig,
    PipelineStepResult,
    RunPipelineOut,
)
from developer_brain_ai_automation.application.ports import (
    DailyEntryReader,
    DailySummaryGenerator,
    DraftQueuer,
    LinkedInDraftCreator,
    TenantLister,
)
from developer_brain_ai_automation.domain.aggregates import PipelineRun
from developer_brain_ai_automation.domain.ids import PipelineRunId
from developer_brain_ai_automation.domain.repositories import PipelineRunRepository
from developer_brain_ai_automation.domain.value_objects import PipelineStep


class StepSkipped(RuntimeError):
    """Lanca dentro de um step quando nao ha base (ex.: sem entries no dia)."""


class RunDailyPipeline:
    """Executa o pipeline diario para todos os tenants.

    Um step que falha nao derruba os demais tenants: vira ``failed`` no banco
    (rastreavel/refazivel) e o job continua.
    """

    def __init__(
        self,
        *,
        pipeline_runs: PipelineRunRepository,
        tenants: TenantLister,
        entries: DailyEntryReader,
        summaries: DailySummaryGenerator,
        drafts: LinkedInDraftCreator,
        queue: DraftQueuer,
        config: PipelineConfig | None = None,
    ) -> None:
        self._runs = pipeline_runs
        self._tenants = tenants
        self._entries = entries
        self._summaries = summaries
        self._drafts = drafts
        self._queue = queue
        self._config = config or PipelineConfig()

    async def execute(self, *, pipeline_date: date | None = None) -> RunPipelineOut:
        day = pipeline_date or utcnow().date()
        report = RunPipelineOut(pipeline_date=day, tenants=0)
        for tenant in await self._tenants.list_active():
            set_tenant_context(tenant)
            try:
                report.steps.append(
                    await self._run_step(tenant, day, PipelineStep.SUMMARY, self._do_summary)
                )
                report.steps.append(
                    await self._run_step(tenant, day, PipelineStep.LINKEDIN, self._do_linkedin)
                )
            finally:
                reset_tenant_context()
            report.tenants += 1
        return report

    async def _run_step(
        self,
        tenant: TenantId,
        day: date,
        step: PipelineStep,
        handler: Callable[[TenantId, date], Awaitable[str]],
    ) -> PipelineStepResult:
        existing = await self._runs.get_by_key(tenant_id=tenant, pipeline_date=day, step=step)
        if existing is not None and existing.is_succeeded:
            return PipelineStepResult(
                tenant_id=str(tenant.as_uuid()),
                step=step,
                status="succeeded",
                output_summary=existing.output_summary,
            )

        run = existing
        if run is None:
            run = PipelineRun(
                id=PipelineRunId.new(), tenant_id=tenant, pipeline_date=day, step=step
            )
        run.start()
        try:
            log = await handler(tenant, day)
        except StepSkipped as exc:
            return PipelineStepResult(
                tenant_id=str(tenant.as_uuid()),
                step=step,
                status="skipped",
                output_summary=str(exc),
            )
        except Exception as exc:
            run.mark_failed(error=f"{type(exc).__name__}: {exc}")
            await self._runs.save(run)
            return PipelineStepResult(
                tenant_id=str(tenant.as_uuid()),
                step=step,
                status="failed",
                error=run.error,
            )
        run.mark_succeeded(output_summary=log)
        await self._runs.save(run)
        return PipelineStepResult(
            tenant_id=str(tenant.as_uuid()),
            step=step,
            status="succeeded",
            output_summary=log,
        )

    async def _do_summary(self, tenant: TenantId, day: date) -> str:
        entries = await self._entries.list_entries(tenant_id=tenant, day=day)
        if not entries:
            raise StepSkipped("sem entries no dia")
        return await self._summaries.generate(tenant_id=tenant, entries=entries)

    async def _do_linkedin(self, tenant: TenantId, day: date) -> str:
        entries = await self._entries.list_entries(tenant_id=tenant, day=day)
        if not entries:
            raise StepSkipped("sem entries no dia")
        draft_id = await self._drafts.create(tenant_id=tenant, entries=entries)
        quando = self._config.publish_scheduled_for or _proximo_dia_util(day)
        await self._queue.enqueue(tenant_id=tenant, draft_id=draft_id, scheduled_for=quando)
        return f"draft {draft_id} agendado para {quando.isoformat()}"


def _proximo_dia_util(day: date) -> datetime:
    """Proximo dia util (seg-sex) as 09:00 UTC, a partir de day."""
    d = day + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return datetime.combine(d, time(9, 0))


__all__ = ["RunDailyPipeline"]
