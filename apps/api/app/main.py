"""Developer Brain AI â€” FastAPI composition root.

Boot order:
1. Carrega Settings (pydantic-settings).
2. Configura structlog (JSON em prod, console em dev).
3. Monta tratador de DomainError -> HTTP.
4. Rota /healthz.

Camadas de negocio (identity, journal, ...) sao montadas em suas respectivas fases
via routers proprios, adicionados aqui quando implementados.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path as _Path
from typing import Any

from developer_brain_ai_ai.application.prompt_engine import PromptEngine
from developer_brain_ai_ai.application.use_cases import (
    LinkedInAgent,
    LinkedInAgentConfig,
    NewsDigestAgent,
    NewsDigestAgentConfig,
)
from developer_brain_ai_ai.domain.aggregates import AgentRun
from developer_brain_ai_ai.infrastructure.openai_provider import OpenAIProvider
from developer_brain_ai_ai.presentation import mount_ai
from developer_brain_ai_content.infrastructure import (
    SqlAlchemyContentDraftRepository,
    SqlAlchemyPublicationQueueRepository,
)
from developer_brain_ai_content.presentation import (
    mount_content,
)
from developer_brain_ai_discord.presentation import mount_discord
from developer_brain_ai_discord.presentation.bot import run_discord_bot
from developer_brain_ai_identity.presentation import (
    mount_identity,
)
from developer_brain_ai_identity.presentation.dependencies import (
    get_current_user_factory,
)
from developer_brain_ai_integrations.infrastructure.adapters import LinkedInPostPublisher
from developer_brain_ai_integrations.infrastructure.linkedin_client import (
    HttpLinkedInApiClient,
)
from developer_brain_ai_integrations.infrastructure.repositories import (
    SqlAlchemyLinkedInTokenRepository,
)
from developer_brain_ai_integrations.presentation import mount_integrations
from developer_brain_ai_journal.infrastructure.repositories import (
    SqlAlchemyJournalEntryRepository,
)
from developer_brain_ai_journal.presentation import (
    mount_journal,
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
from developer_brain_ai_news.presentation import mount_news
from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.errors.http import (
    mount_domain_error_handlers,
)
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.logging import configure_logging
from developer_brain_ai_shared.persistence.session import (
    EngineFactory,
)
from developer_brain_ai_telegram.presentation import mount_telegram, telegram_poll_loop
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from app.config import get_settings

settings = get_settings()
configure_logging(level=settings.app_log_level, json_output=settings.app_log_json)

_, _session_factory = EngineFactory.build(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)
_jwt = JWTService(
    secret=settings.jwt_secret,
    algorithm=settings.jwt_alg,
    access_ttl_seconds=settings.jwt_access_ttl_seconds,
    refresh_ttl_seconds=settings.jwt_refresh_ttl_seconds,
)


def create_app() -> FastAPI:  # noqa: PLR0915 — composition root agrega todos os modulos
    telegram_wiring = None
    discord_wiring = None

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> Any:
        poll_task = None
        discord_task = None
        if telegram_wiring is not None and settings.telegram_polling:
            poll_task = asyncio.create_task(
                telegram_poll_loop(
                    client=telegram_wiring.client,
                    tenant_id=telegram_wiring.tenant_id,
                    allowed_chat=telegram_wiring.allowed_chat,
                    inbound_uc=telegram_wiring.inbound_uc,
                    approval_uc=telegram_wiring.approval_uc,
                    messenger=telegram_wiring.client,
                )
            )
        if discord_wiring is not None:
            discord_task = asyncio.create_task(
                run_discord_bot(
                    client=discord_wiring.client,
                    token=settings.discord_bot_token,
                )
            )
        try:
            yield
        finally:
            if poll_task is not None:
                poll_task.cancel()
                await asyncio.gather(poll_task, return_exceptions=True)
            if discord_task is not None:
                discord_task.cancel()
                await asyncio.gather(discord_task, return_exceptions=True)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Second brain for developers.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    mount_domain_error_handlers(app)

    current_user_dep = get_current_user_factory(_jwt)
    app.include_router(mount_identity(session_factory=_session_factory, jwt=_jwt))
    app.include_router(
        mount_journal(session_factory=_session_factory, current_user_dep=current_user_dep)
    )

    async def _list_journal_for_ai(
        tenant_id: TenantId,
        *,
        since: date | None,
        until: date | None,
    ) -> list[dict[str, Any]]:
        repo = SqlAlchemyJournalEntryRepository(_session_factory)
        entries = await repo.list(tenant_id, since=since, until=until)
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

    openai_client = None
    if settings.openai_api_key:
        try:
            client_kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
            if settings.openai_base_url.strip():
                client_kwargs["base_url"] = settings.openai_base_url.strip()
            openai_client = AsyncOpenAI(**client_kwargs)
        except ImportError:
            openai_client = None

    if openai_client is not None:

        class _NoopRunRepo:
            async def save(self, run: AgentRun) -> None:
                return None

            async def list_recent(
                self, tenant_id: TenantId, agent: str, limit: int = 50
            ) -> list[AgentRun]:
                return []

        app.include_router(
            mount_ai(
                openai_client=openai_client,
                prompts_dir=_Path("prompts"),
                journal_list_fn=_list_journal_for_ai,
                summary_runs_repo=_NoopRunRepo(),
                current_user_dep=current_user_dep,
                chat_model=settings.openai_chat_model,
                embedding_model=settings.openai_embedding_model,
            )
        )

    content_drafts_repo = SqlAlchemyContentDraftRepository(_session_factory)
    content_queue_repo = SqlAlchemyPublicationQueueRepository(_session_factory)

    linkedin_generator = None
    if openai_client is not None:
        use_structured = not settings.openai_base_url.strip() or "openai.com" in settings.openai_base_url
        linkedin_generator = LinkedInAgent(
            provider=OpenAIProvider(
                client=openai_client,
                chat_model=settings.openai_chat_model,
                embedding_model=settings.openai_embedding_model,
                use_structured_outputs=use_structured,
            ),
            prompt_engine=PromptEngine(_Path("prompts")),
            runs=_NoopRunRepo(),
            config=LinkedInAgentConfig(
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens,
            ),
        )

    news_digest_generator = None
    if openai_client is not None:
        use_structured = not settings.openai_base_url.strip() or "openai.com" in settings.openai_base_url
        news_digest_generator = NewsDigestAgent(
            provider=OpenAIProvider(
                client=openai_client,
                chat_model=settings.openai_chat_model,
                embedding_model=settings.openai_embedding_model,
                use_structured_outputs=use_structured,
            ),
            prompt_engine=PromptEngine(_Path("prompts")),
            runs=_NoopRunRepo(),
            config=NewsDigestAgentConfig(
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens,
            ),
        )

    linkedin_publisher = None
    if settings.linkedin_client_id and settings.linkedin_client_secret:
        tokens_repo = SqlAlchemyLinkedInTokenRepository(_session_factory)
        api_client = HttpLinkedInApiClient(
            client_id=settings.linkedin_client_id,
            client_secret=settings.linkedin_client_secret,
        )
        linkedin_publisher = LinkedInPostPublisher(tokens=tokens_repo, api=api_client)

        app.include_router(
            mount_integrations(
                tokens=tokens_repo,
                oauth_state_secret=settings.jwt_secret,
                linkedin_client_id=settings.linkedin_client_id,
                linkedin_client_secret=settings.linkedin_client_secret,
                linkedin_redirect_uri=settings.linkedin_redirect_uri,
                current_user_dep=current_user_dep,
            )
        )

    app.include_router(
        mount_content(
            drafts_repo=content_drafts_repo,
            queue_repo=content_queue_repo,
            linkedin_generator=linkedin_generator,
            linkedin_publisher=linkedin_publisher,
            current_user_dep=current_user_dep,
        )
    )

    if settings.telegram_bot_token and settings.telegram_tenant_id:
        telegram_wiring = mount_telegram(
            session_factory=_session_factory,
            bot_token=settings.telegram_bot_token,
            allowed_chat_id=settings.telegram_allowed_chat_id,
            tenant_id=TenantId(settings.telegram_tenant_id),
            drafts_repo=content_drafts_repo,
            queue_repo=content_queue_repo,
            linkedin_generator=linkedin_generator,
            linkedin_publisher=linkedin_publisher,
            openai_client=openai_client,
        )
        app.include_router(telegram_wiring.router)

    if settings.discord_bot_token and settings.discord_tenant_id:
        discord_wiring = mount_discord(
            session_factory=_session_factory,
            bot_token=settings.discord_bot_token,
            allowed_channel_id=settings.discord_allowed_channel_id,
            tenant_id=TenantId(settings.discord_tenant_id),
            drafts_repo=content_drafts_repo,
            queue_repo=content_queue_repo,
            linkedin_generator=linkedin_generator,
            linkedin_publisher=linkedin_publisher,
            openai_client=openai_client,
        )

    # ===== News: fetch RSS + digest via LLM + envio p/ aprovacao no Discord ==
    news_repo = SqlAlchemyNewsItemRepository(_session_factory)
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

    digest_notifier = None
    if (
        discord_wiring is not None
        and discord_wiring.allowed_channel is not None
        and discord_wiring.tenant_id == TenantId(settings.discord_tenant_id)
    ):
        _send_draft = discord_wiring.send_draft_uc
        _channel = discord_wiring.allowed_channel

        class _DigestNotifierAdapter:
            async def send(self, *, tenant_id: object, draft_id: str, title: str, body: str) -> str:
                return await _send_draft.execute(
                    tenant_id=discord_wiring.tenant_id,
                    channel_id=_channel,
                    draft_id=draft_id,
                    title=title,
                    body=body,
                )

        digest_notifier = _DigestNotifierAdapter()

    digest_uc: GenerateDailyDigest | None = None
    if news_digest_generator is not None:
        digest_uc = GenerateDailyDigest(
            news_repo=news_repo,
            drafts_repo=content_drafts_repo,
            agent=news_digest_generator,
            notifier=digest_notifier,
        )

    if digest_uc is not None:
        app.include_router(
            mount_news(
                fetch_uc=fetch_uc,
                digest_uc=digest_uc,
                repo=news_repo,
                current_user_dep=current_user_dep,
            )
        )

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
