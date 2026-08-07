"""Testes dos erros de dominio + tradutor HTTP."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from developer_brain_ai_shared.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from developer_brain_ai_shared.errors.http import mount_domain_error_handlers


def test_error_to_dict_structure() -> None:
    err = NotFoundError("diario nao encontrado", details={"id": "x"})
    d = err.to_dict()
    assert d == {"code": "not_found", "message": "diario nao encontrado", "details": {"id": "x"}}


def test_error_codes_and_http_statuses() -> None:
    cases = [
        (NotFoundError("x"), 404, "not_found"),
        (ConflictError("x"), 409, "conflict"),
        (ValidationError("x"), 422, "validation_error"),
        (UnauthorizedError("x"), 401, "unauthorized"),
        (ForbiddenError("x"), 403, "forbidden"),
    ]
    for err, status, code in cases:
        assert err.http_status == status
        assert err.code == code


def test_domain_error_default_status() -> None:
    class CustomError(DomainError):
        pass

    assert CustomError("x").http_status == 500
    assert CustomError("x").code == "domain_error"


def test_mount_domain_error_handlers_translates_to_http() -> None:
    app = FastAPI()
    mount_domain_error_handlers(app)

    @app.get("/raise-not-found")
    async def _rnf() -> None:
        raise NotFoundError("missing")

    @app.get("/raise-conflict")
    async def _rc() -> None:
        raise ConflictError("dup")

    with TestClient(app) as client:
        r1 = client.get("/raise-not-found")
        assert r1.status_code == 404
        assert r1.json()["code"] == "not_found"
        r2 = client.get("/raise-conflict")
        assert r2.status_code == 409