"""Smoke do mount_identity: monta router via composition helper sem DB real."""

from __future__ import annotations

from unittest.mock import MagicMock

from developer_brain_ai_identity.presentation import mount_identity
from developer_brain_ai_shared.auth.jwt import JWTService
from fastapi import FastAPI
from fastapi.testclient import TestClient

SECRET = "test-secret-please-replace-me-12345678901234567890"


def test_mount_identity_registers_routes() -> None:
    fake_factory = MagicMock()
    jwt = JWTService(secret=SECRET)

    router = mount_identity(session_factory=fake_factory, jwt=jwt)

    paths = {r.path for r in router.routes}
    assert "/auth/register" in paths
    assert "/auth/login" in paths
    assert "/auth/refresh" in paths
    assert "/auth/api-keys" in paths
    assert "/auth/api-keys/{api_key_id}" in paths


def test_mount_identity_protected_paths_require_bearer() -> None:
    fake_factory = MagicMock()
    jwt = JWTService(secret=SECRET)
    router = mount_identity(session_factory=fake_factory, jwt=jwt)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        r = c.get("/auth/api-keys")
    assert r.status_code == 401
    assert r.json()["detail"] == "bearer token ausente"
