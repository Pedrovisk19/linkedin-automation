"""Traducao de DomainError para respostas HTTP (FastAPI handler).

Vive em ``shared.errors.http`` — NAO em ``shared.errors.base``. Razao: domain
nao conhece HTTP. Esta traducao e registrada no composition root (apps/api).
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from developer_brain_ai_shared.errors.base import DomainError


def mount_domain_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


__all__ = ["mount_domain_error_handlers"]