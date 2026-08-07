"""Developer Brain AI — FastAPI composition root.

Boot order:
1. Carrega Settings (pydantic-settings).
2. Configura structlog (JSON em prod, console em dev).
3. Monta tratador de DomainError -> HTTP.
4. Rota /healthz.

Camadas de negocio (identity, journal, ...) sao montadas em suas respectivas fases
via routers proprios, adicionados aqui quando implementados.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from developer_brain_ai_shared.auth.jwt import JWTService  # type: ignore[import-not-found]
from developer_brain_ai_shared.errors.http import mount_domain_error_handlers  # type: ignore[import-not-found]
from developer_brain_ai_shared.logging import configure_logging  # type: ignore[import-not-found]
from developer_brain_ai_shared.persistence.session import EngineFactory  # type: ignore[import-not-found]

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

    from developer_brain_ai_identity.presentation import mount_identity  # type: ignore[import-not-found]

    app.include_router(mount_identity(session_factory=_session_factory, jwt=_jwt))

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()