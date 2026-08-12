"""Arq worker composition root — executa o DailyPipeline (Fase 7a).

Cron: 07:00 UTC (ajustavel via settings). No startup monta o grafo de
dependencias (engine, repos, agentes, adaptadores) e registra no contexto. O
job itera tenants; o use case define ``SET LOCAL app.tenant_id`` por tenant
(RLS) antes de tocar qualquer repositorio (ver shared/persistence/session.py).
"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from typing import ClassVar

import httpx
from arq import cron
from arq.connections import RedisSettings
from developer_brain_ai_ai.application.dto import SummaryAgentInput
from developer_brain_ai_ai.application.prompt_engine import PromptEngine
from developer_brain_ai_ai.application.use_cases import (
    LinkedInAgent,
    NewsDigestAgent,
    SummaryAgent,
)
from developer_brain_ai_ai.domain.aggregates import AgentRun
from developer_brain_ai_ai.domain.repositories import AgentRunRepository
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
from developer_brain_ai_discord.application.use_cases import SendDraftToChannel
from developer_brain_ai_discord.domain.value_objects import ChannelId
from developer_brain_ai_discord.infrastructure.repositories import (
    SqlAlchemyDiscordRequestRepository,
)
from developer_brain_ai_discord.infrastructure.rest_messenger import RestDiscordMessenger
from developer_brain_ai_identity.infrastructure.orm import (
    TenantORM,  # noqa: F401 — registra tabela tenants no metadata
)
from developer_brain_ai_journal.infrastructure.repositories import (
    SqlAlchemyJournalEntryRepository,
)
from developer_brain_ai_news.application.use_cases import (
    FetchDailyNews,
    GenerateDailyDigest,
)
from developer_brain_ai_news.infrastructure.repositories import (
    SqlAlchemyNewsItemRepository,
)
from developer_brain_ai_news.infrastructure.rss_fetchers import (
    GitHubTrendingFetcher,
    HackerNewsFetcher,
    PepsFetcher,
    PyPiLatestFetcher,
    PythonInsiderFetcher,
    RealPythonFetcher,
)
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.logging import configure_logging
from developer_brain_ai_shared.persistence.session import EngineFactory
from openai import AsyncOpenAI
from sqlalchemy import text

from app.config import get_settings

_settings = get_settings()


def _noop_run_repo() -> AgentRunRepository:
    """AgentRunRepository no-op: agentes nao persistem runs no worker (Fase 7a)."""

    class _Noop:
        async def save(self, run: AgentRun) -> None:
            return None

        async def list_recent(
            self, tenant_id: TenantId, agent: str, limit: int = 50
        ) -> list[AgentRun]:
            return []

    return _Noop()


def _build_pipeline():

    _, session_factory = EngineFactory.build(
        _settings.database_url,
        pool_size=_settings.database_pool_size,
        max_overflow=_settings.database_max_overflow,
    )

    journal_repo = SqlAlchemyJournalEntryRepository(session_factory)
    drafts_repo = SqlAlchemyContentDraftRepository(session_factory)
    queue_repo = SqlAlchemyPublicationQueueRepository(session_factory)

    openai_client = AsyncOpenAI(api_key=_settings.openai_api_key)
    is_groq = "groq.com" in _settings.openai_base_url
    if _settings.openai_base_url.strip():
        openai_client = AsyncOpenAI(
            api_key=_settings.openai_api_key,
            base_url=_settings.openai_base_url.strip(),
            http_client=httpx.AsyncClient(timeout=60.0),
        )
    provider = OpenAIProvider(
        client=openai_client,
        chat_model=_settings.openai_chat_model,
        embedding_model=_settings.openai_embedding_model,
        use_structured_outputs=not is_groq,
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

    return RunDailyPipeline(
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


def _build_digest_notifier(session_factory):
    """Notifier do digest p/ aprovacao no Discord (REST, sem gateway).

    O bot do gateway roda na API; o worker nao pode abrir segunda conexao
    com o mesmo token (Discord desconecta a primeira). Usa a REST API com
    botoes approve:/reject: — o clique chega ao bot da API via gateway e o
    fluxo de aprovacao (enqueue + publish) roda la, como de costume.
    """
    token = _settings.discord_bot_token.strip()
    channel_raw = _settings.discord_allowed_channel_id.strip()
    discord_tenant_raw = _settings.discord_tenant_id.strip()
    if not token or not channel_raw or not discord_tenant_raw:
        return None
    try:
        channel = ChannelId(int(channel_raw))
        discord_tenant = TenantId(uuid.UUID(discord_tenant_raw))
    except TypeError, ValueError:
        return None

    requests_repo = SqlAlchemyDiscordRequestRepository(session_factory)
    send_draft = SendDraftToChannel(
        messenger=RestDiscordMessenger(token),
        requests=requests_repo,
    )

    class _DigestNotifier:
        async def send(self, *, tenant_id, draft_id, title, body) -> str:
            return await send_draft.execute(
                tenant_id=discord_tenant,
                channel_id=channel,
                draft_id=draft_id,
                title=title,
                body=body,
            )

    return _DigestNotifier()


def build_news_stack(session_factory, *, prompts_dir: Path = Path("prompts")):
    """Monta fetch + digest de news (usado pelo arq e pelo cron do GH Actions).

    Retorna (FetchDailyNews, GenerateDailyDigest). O notifier do digest usa a
    REST API do Discord, entao o GH Actions tambem consegue enviar o pedido de
    aprovacao sem gateway.
    """
    news_repo = SqlAlchemyNewsItemRepository(session_factory)
    fetch_uc = FetchDailyNews(
        fetchers=[
            RealPythonFetcher(),
            PythonInsiderFetcher(),
            PepsFetcher(),
            PyPiLatestFetcher(),
            HackerNewsFetcher(),
            GitHubTrendingFetcher(),
        ],
        repo=news_repo,
    )

    is_groq = "groq.com" in _settings.openai_base_url
    openai_client_news = AsyncOpenAI(
        api_key=_settings.openai_api_key,
        base_url=_settings.openai_base_url.strip() or None,
    )
    news_agent = NewsDigestAgent(
        provider=OpenAIProvider(
            client=openai_client_news,
            chat_model=_settings.openai_chat_model,
            embedding_model=_settings.openai_embedding_model,
            use_structured_outputs=not is_groq,
        ),
        prompt_engine=PromptEngine(prompts_dir),
        runs=_noop_run_repo(),
    )
    digest_notifier = _build_digest_notifier(session_factory)
    digest_uc = GenerateDailyDigest(
        news_repo=news_repo,
        drafts_repo=SqlAlchemyContentDraftRepository(session_factory),
        agent=news_agent,
        notifier=digest_notifier,
    )
    return fetch_uc, digest_uc


async def startup(ctx: dict) -> None:

    configure_logging(level=_settings.app_log_level, json_output=_settings.app_log_json)
    if not _settings.openai_api_key:
        ctx["ok"] = False
        ctx["pipeline"] = None
        ctx["news_fetch"] = None
        ctx["news_digest"] = None
        return
    ctx["pipeline"] = _build_pipeline()
    ctx["ok"] = True

    # ===== News: fetch RSS + digest via LLM (cron self-contained) ============
    _, news_session_factory = EngineFactory.build(
        _settings.database_url,
        pool_size=_settings.database_pool_size,
        max_overflow=_settings.database_max_overflow,
    )
    ctx["news_fetch"], ctx["news_digest"] = build_news_stack(news_session_factory)


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


async def news_fetch_job(ctx: dict) -> dict:
    """Cron: coleta fontes Python (RSS/HN/PyPI/GitHub) p/ o tenant config.

    Roda a cada 4h. Idempotente: dedupe por content_hash no banco.
    """
    fetch_uc = ctx.get("news_fetch")
    if fetch_uc is None:
        return {"status": "skipped", "reason": "openai_api_key nao configurada"}
    tenant_id_raw = _settings.news_tenant_id.strip()
    if not tenant_id_raw:
        return {"status": "skipped", "reason": "news_tenant_id nao configurado"}
    result = await fetch_uc.execute(tenant_id=TenantId(uuid.UUID(tenant_id_raw)))
    return {
        "status": "ok",
        "fetched": result.fetched,
        "inserted": result.inserted,
        "deduped": result.deduped,
        "errors": result.errors,
    }


async def news_digest_job(ctx: dict) -> dict:
    """Cron diario 08:00 UTC: gera digest Python p/ o tenant config.

    Envia o pedido de aprovacao via REST API do Discord (sem gateway) quando
    o notifier esta configurado; o clique nos botoes approva/rejeita chega ao
    bot da API e o fluxo de enqueue/publish roda la.
    """
    digest_uc = ctx.get("news_digest")
    if digest_uc is None:
        return {"status": "skipped", "reason": "openai_api_key nao configurada"}
    tenant_id_raw = _settings.news_tenant_id.strip()
    if not tenant_id_raw:
        return {"status": "skipped", "reason": "news_tenant_id nao configurado"}
    result = await digest_uc.execute(
        tenant_id=TenantId(uuid.UUID(tenant_id_raw)),
        ai_writing_tone=_settings.ai_writing_tone,
        ai_language=_settings.ai_language,
    )
    return {
        "status": "ok",
        "draft_id": result.draft_id,
        "title": result.title,
        "used_items": result.used_items,
    }


class WorkerSettings:
    functions: ClassVar[list] = [daily_pipeline, news_fetch_job, news_digest_job]
    cron_jobs: ClassVar[list] = [
        cron(
            daily_pipeline,
            hour=_settings.pipeline_hour,
            minute=_settings.pipeline_minute,
        ),
        cron(
            news_fetch_job,
            hour={int(h) for h in _settings.news_fetch_hour.split(",") if h.strip()},
            minute=_settings.news_fetch_minute,
        ),
        cron(
            news_digest_job,
            hour=_settings.news_digest_hour,
            minute=_settings.news_digest_minute,
        ),
    ]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(_settings.arq_redis_url)
    max_jobs = 2
    job_timeout = 90 * 60
    keep_result = 3600
