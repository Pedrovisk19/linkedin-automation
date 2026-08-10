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

from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.errors.http import (
    mount_domain_error_handlers,
)
from developer_brain_ai_shared.logging import configure_logging
from developer_brain_ai_shared.persistence.session import (
    EngineFactory,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Second brain for developers.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    mount_domain_error_handlers(app)

    from developer_brain_ai_ai.presentation import mount_ai
    from developer_brain_ai_content.infrastructure import (
        SqlAlchemyContentDraftRepository,
        SqlAlchemyPublicationQueueRepository,
    )
    from developer_brain_ai_content.presentation import (
        mount_content,
    )
    from developer_brain_ai_identity.presentation import (
        mount_identity,
    )
    from developer_brain_ai_identity.presentation.dependencies import (
        get_current_user_factory,
    )
    from developer_brain_ai_journal.infrastructure.repositories import (
        SqlAlchemyJournalEntryRepository,
    )
    from developer_brain_ai_journal.presentation import (
        mount_journal,
    )

    current_user_dep = get_current_user_factory(_jwt)
    app.include_router(mount_identity(session_factory=_session_factory, jwt=_jwt))
    app.include_router(
        mount_journal(session_factory=_session_factory, current_user_dep=current_user_dep)
    )

    async def _list_journal_for_ai(tenant_id, *, since, until):
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

    from pathlib import Path as _Path

    openai_client = None
    if settings.openai_api_key:
        try:
            from openai import AsyncOpenAI

            openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        except ImportError:
            openai_client = None

    if openai_client is not None:

        class _NoopRunRepo:
            async def save(self, run):
                return None

            async def list_recent(self, tenant_id, agent, limit=50):
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
        from developer_brain_ai_ai.application.prompt_engine import PromptEngine
        from developer_brain_ai_ai.application.use_cases import LinkedInAgent
        from developer_brain_ai_ai.infrastructure.openai_provider import OpenAIProvider

        linkedin_generator = LinkedInAgent(
            provider=OpenAIProvider(
                client=openai_client,
                chat_model=settings.openai_chat_model,
                embedding_model=settings.openai_embedding_model,
            ),
            prompt_engine=PromptEngine(_Path("prompts")),
            runs=_NoopRunRepo(),
        )

    app.include_router(
        mount_content(
            drafts_repo=content_drafts_repo,
            queue_repo=content_queue_repo,
            linkedin_generator=linkedin_generator,
            current_user_dep=current_user_dep,
        )
    )

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
