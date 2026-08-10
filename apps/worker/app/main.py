"""Arq worker composition root — executa o DailyPipeline (Fase 7a).

Cron: 07:00 UTC (ajustavel via settings). No startup monta o grafo de
dependencias (engine, repos, agentes, adaptadores) e registra no contexto. O
job itera tenants; o use case define ``SET LOCAL app.tenant_id`` por tenant
(RLS) antes de tocar qualquer repositorio (ver shared/persistence/session.py).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings

_settings = get_settings()


def _noop_run_repo():
    """AgentRunRepository no-op: agentes nao persistem runs no worker (Fase 7a)."""

    class _Noop:
        async def save(self, run):
            return None

        async def list_recent(self, tenant_id, agent, limit=50):
            return []

    return _Noop()


def _build_pipeline():
    from developer_brain_ai_ai.application.prompt_engine import PromptEngine
    from developer_brain_ai_ai.application.use_cases import LinkedInAgent, SummaryAgent
    from developer_brain_ai_ai.infrastructure.openai_provider import OpenAIProvider
    from developer_brain_ai_automation.application.dto import PipelineConfig
    from developer_brain_ai_automation.application.use_cases import RunDailyPipeline
    from developer_brain_ai_automation.infrastructure.repositories import (
        SqlAlchemyPipelineRunRepository,
    )
    from developer_brain_ai_content.application.dto import GenerateLinkedInInput
    from developer_brain_ai_content.application.use_cases import (
        EnqueueDraft,
        GenerateLinkedInDraft,
    )
    from developer_brain_ai_content.infrastructure import (
        SqlAlchemyContentDraftRepository,
        SqlAlchemyPublicationQueueRepository,
    )
    from developer_brain_ai_journal.infrastructure.repositories import (
        SqlAlchemyJournalEntryRepository,
    )
    from developer_brain_ai_shared.kernel.id import TenantId
    from developer_brain_ai_shared.persistence.session import EngineFactory
    from openai import AsyncOpenAI
    from sqlalchemy import text

    _, session_factory = EngineFactory.build(
        _settings.database_url,
        pool_size=_settings.database_pool_size,
        max_overflow=_settings.database_max_overflow,
    )

    journal_repo = SqlAlchemyJournalEntryRepository(session_factory)
    drafts_repo = SqlAlchemyContentDraftRepository(session_factory)
    queue_repo = SqlAlchemyPublicationQueueRepository(session_factory)

    openai_client = AsyncOpenAI(api_key=_settings.openai_api_key)
    provider = OpenAIProvider(
        client=openai_client,
        chat_model=_settings.openai_chat_model,
        embedding_model=_settings.openai_embedding_model,
    )
    prompt_engine = PromptEngine(Path("prompts"))
    runs_repo = _noop_run_repo()

    summary_agent = SummaryAgent(provider=provider, prompt_engine=prompt_engine, runs=runs_repo)
    linkedin_agent = LinkedInAgent(provider=provider, prompt_engine=prompt_engine, runs=runs_repo)
    generate_draft = GenerateLinkedInDraft(drafts=drafts_repo, generator=linkedin_agent)
    enqueue_draft = EnqueueDraft(drafts=drafts_repo, queue=queue_repo)

    async def _list_active() -> list[TenantId]:
        async with session_factory() as s:
            rows = (await s.execute(text("SELECT id FROM tenants"))).scalars().all()
        return [TenantId(uuid) for uuid in rows]

    async def _list_entries(*, tenant_id: TenantId, day: date) -> list[dict]:
        entries = await journal_repo.list(tenant_id, since=day, until=day)
        return [
            {
                "title": e.title,
                "entry_date": str(e.entry_date.as_date()),
                "study_minutes": e.study_minutes.as_int(),
                "technologies": e.technologies,
                "learnings": e.learnings[:1200],
                "difficulties": e.difficulties[:600],
                "bugs_found": e.bugs_found,
                "resolutions": e.resolutions,
            }
            for e in entries
        ]

    async def _generate_summary(*, tenant_id: TenantId, entries: list[dict]) -> str:
        from developer_brain_ai_ai.application.dto import SummaryAgentInput

        hoje = date.today()
        out = await summary_agent.execute(
            tenant_id,
            SummaryAgentInput(period_kind="daily", start_date=hoje, end_date=hoje, entries=entries),
        )
        return out.markdown

    async def _create_linkedin_draft(*, tenant_id: TenantId, entries: list[dict]) -> str:
        out = await generate_draft.execute(
            tenant_id,
            GenerateLinkedInInput(
                entries=entries,
                ai_writing_tone=_settings.ai_writing_tone,
                ai_language=_settings.ai_language,
            ),
        )
        return out.draft_id

    async def _enqueue(*, tenant_id: TenantId, draft_id: str, scheduled_for) -> None:
        await enqueue_draft.execute(tenant_id, draft_id, scheduled_for)

    pipeline = RunDailyPipeline(
        pipeline_runs=SqlAlchemyPipelineRunRepository(session_factory),
        tenants=_TenantListerAdapter(_list_active),
        entries=_Adapter(_list_entries),
        summaries=_Adapter(_generate_summary),
        drafts=_Adapter(_create_linkedin_draft),
        queue=_Adapter(_enqueue),
        config=PipelineConfig(
            ai_language=_settings.ai_language,
            ai_writing_tone=_settings.ai_writing_tone,
        ),
    )
    return pipeline


class _Adapter:
    """Envolve um callable assincrono no formato da port."""

    def __init__(self, fn) -> None:
        self._fn = fn

    async def list_entries(self, *, tenant_id, day):
        return await self._fn(tenant_id=tenant_id, day=day)

    async def generate(self, *, tenant_id, entries):
        return await self._fn(tenant_id=tenant_id, entries=entries)

    async def create(self, *, tenant_id, entries):
        return await self._fn(tenant_id=tenant_id, entries=entries)

    async def enqueue(self, *, tenant_id, draft_id, scheduled_for):
        return await self._fn(tenant_id=tenant_id, draft_id=draft_id, scheduled_for=scheduled_for)


class _TenantListerAdapter:
    def __init__(self, fn) -> None:
        self._fn = fn

    async def list_active(self) -> list:
        return await self._fn()


async def startup(ctx: dict) -> None:
    from developer_brain_ai_shared.logging import configure_logging

    configure_logging(level=_settings.app_log_level, json_output=_settings.app_log_json)
    if not _settings.openai_api_key:
        ctx["ok"] = False
        ctx["pipeline"] = None
        return
    ctx["pipeline"] = _build_pipeline()
    ctx["ok"] = True


async def daily_pipeline(ctx: dict) -> dict:
    """Job do cron: roda o pipeline diario para todos os tenants (idempotente)."""
    pipeline = ctx.get("pipeline")
    if pipeline is None:
        return {"status": "skipped", "reason": "openai_api_key nao configurada"}
    report = await pipeline.execute(pipeline_date=date.today())
    return {
        "status": "ok",
        "pipeline_date": report.pipeline_date.isoformat(),
        "tenants": report.tenants,
        "steps": [s.model_dump() for s in report.steps],
    }


class WorkerSettings:
    functions: list = [daily_pipeline]
    cron_jobs = [
        cron(
            daily_pipeline,
            hour=_settings.pipeline_hour,
            minute=_settings.pipeline_minute,
        )
    ]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(_settings.arq_redis_url)
    max_jobs = 2
    job_timeout = 90 * 60
    keep_result = 3600
