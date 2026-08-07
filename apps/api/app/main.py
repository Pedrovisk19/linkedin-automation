"""Developer Brain AI — FastAPI composition root."""
from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Second brain for developers.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()