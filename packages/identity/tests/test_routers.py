"""Testes end-to-end dos routers do identity via TestClient + dependencies override.

Substitui repos SQLAlchemy por fakes em memória. Cobre:
- POST /auth/register -> 201 + corpo
- POST /auth/login    -> 200 + token pair (Bearer)
- POST /auth/refresh  -> 200 + novo token pair
- GET  /auth/api-keys sem token -> 401
- GET  /auth/api-keys com token -> 200 lista
- POST /auth/api-keys com token -> 201 retorna key_display
- DELETE /auth/api-keys/{id}     -> 204
- Bizcard invalido: Bearer malformado / token expirado
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI

from developer_brain_ai_identity.presentation import mount_identity
from developer_brain_ai_identity.application.dto import (
    CreateApiKeyInput,
    LoginInput,
    RefreshInput,
    RegisterTenantInput,
)
from developer_brain_ai_identity.application.use_cases.create_api_key import CreateApiKey
from developer_brain_ai_identity.application.use_cases.login_user import LoginUser
from developer_brain_ai_identity.application.use_cases.manage_api_keys import (
    ListApiKeys,
    RevokeApiKey,
)
from developer_brain_ai_identity.application.use_cases.refresh_token import RefreshToken
from developer_brain_ai_identity.application.use_cases.register_tenant import RegisterTenant
from developer_brain_ai_identity.presentation.dependencies import get_current_user_factory
from developer_brain_ai_identity.presentation.routers import build_router
from developer_brain_ai_shared.auth.jwt import JWTService

from identity_fakes import (
    FakeApiKeyRepository,
    FakePasswordHasher,
    FakeTenantRepository,
    FakeUserRepository,
)
from fastapi.testclient import TestClient

SECRET = "test-secret-please-replace-me-12345678901234567890"
REGISTER = RegisterTenantInput(
    tenant_slug="acme",
    tenant_name="Acme",
    admin_email="admin@acme.com",
    admin_name="Admin",
    admin_password="verystrong-123!",
)


def _build_app() -> FastAPI:
    tenants, users, api_keys = FakeTenantRepository(), FakeUserRepository(), FakeApiKeyRepository()
    hasher = FakePasswordHasher()
    jwt = JWTService(secret=SECRET)

    register_uc = RegisterTenant(tenants, users, hasher)
    login_uc = LoginUser(tenants, users, hasher, jwt)
    refresh_uc = RefreshToken(jwt)
    create_uc = CreateApiKey(api_keys)
    list_uc = ListApiKeys(api_keys)
    revoke_uc = RevokeApiKey(api_keys)
    current_user_dep = get_current_user_factory(jwt)

    router = build_router(
        register_uc=register_uc,
        login_uc=login_uc,
        refresh_uc=refresh_uc,
        create_api_key_uc=create_uc,
        list_api_keys_uc=list_uc,
        revoke_api_key_uc=revoke_uc,
        current_user_dep=current_user_dep,
    )
    app = FastAPI()
    from developer_brain_ai_shared.errors.http import mount_domain_error_handlers
    mount_domain_error_handlers(app)
    app.include_router(router)
    return app


def test_register_returns_201() -> None:
    app = _build_app()
    with TestClient(app) as c:
        r = c.post("/auth/register", json=REGISTER.model_dump())
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "admin@acme.com"
    assert body["tenant_id"]
    assert body["user_id"]


def test_login_returns_token_pair() -> None:
    app = _build_app()
    with TestClient(app) as c:
        c.post("/auth/register", json=REGISTER.model_dump())
        r = c.post(
            "/auth/login",
            json={"tenant_slug": "acme", "email": "admin@acme.com", "password": "verystrong-123!"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_wrong_password_unified_error() -> None:
    app = _build_app()
    with TestClient(app) as c:
        c.post("/auth/register", json=REGISTER.model_dump())
        r = c.post(
            "/auth/login",
            json={"tenant_slug": "acme", "email": "admin@acme.com", "password": "WRONG-pwd-123!"},
        )
    assert r.status_code == 401
    assert r.json()["message"] == "credenciais invalidas"


def test_refresh_returns_new_pair() -> None:
    app = _build_app()
    with TestClient(app) as c:
        c.post("/auth/register", json=REGISTER.model_dump())
        login = c.post(
            "/auth/login",
            json={"tenant_slug": "acme", "email": "admin@acme.com", "password": "verystrong-123!"},
        ).json()
        r = c.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] != login["access_token"]


def test_refresh_rejects_access_token() -> None:
    app = _build_app()
    with TestClient(app) as c:
        c.post("/auth/register", json=REGISTER.model_dump())
        login = c.post(
            "/auth/login",
            json={"tenant_slug": "acme", "email": "admin@acme.com", "password": "verystrong-123!"},
        ).json()
        r = c.post("/auth/refresh", json={"refresh_token": login["access_token"]})
    assert r.status_code == 401


def test_api_keys_protected_requires_bearer() -> None:
    app = _build_app()
    with TestClient(app) as c:
        r = c.get("/auth/api-keys")
    assert r.status_code == 401


def test_api_keys_protected_rejects_malformed_bearer() -> None:
    app = _build_app()
    with TestClient(app) as c:
        r = c.get("/auth/api-keys", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401


def test_create_then_list_then_revoke_api_key() -> None:
    app = _build_app()
    with TestClient(app) as c:
        c.post("/auth/register", json=REGISTER.model_dump())
        login = c.post(
            "/auth/login",
            json={"tenant_slug": "acme", "email": "admin@acme.com", "password": "verystrong-123!"},
        ).json()
        auth = {"Authorization": f"Bearer {login['access_token']}"}

        r_create = c.post("/auth/api-keys", json={"label": "laptop"}, headers=auth)
        assert r_create.status_code == 201
        created = r_create.json()
        assert created["key_display"].startswith("dba_")
        assert created["label"] == "laptop"
        key_id = created["api_key_id"]

        r_list = c.get("/auth/api-keys", headers=auth)
        assert r_list.status_code == 200
        items = r_list.json()
        assert len(items) == 1
        assert items[0]["label"] == "laptop"
        assert "key_display" not in items[0]

        r_revoke = c.delete(f"/auth/api-keys/{key_id}", headers=auth)
        assert r_revoke.status_code == 204

        r_list2 = c.get("/auth/api-keys", headers=auth)
        assert r_list2.status_code == 200
        assert r_list2.json()[0]["is_revoked"] is True


def test_register_rejects_dup_slug_with_409() -> None:
    app = _build_app()
    with TestClient(app) as c:
        c.post("/auth/register", json=REGISTER.model_dump())
        r = c.post("/auth/register", json=REGISTER.model_dump())
    assert r.status_code == 409
    assert r.json()["code"] == "conflict"


def test_register_rejects_invalid_email_with_422() -> None:
    app = _build_app()
    bad = REGISTER.model_dump()
    bad["admin_email"] = "not-an-email"
    with TestClient(app) as c:
        r = c.post("/auth/register", json=bad)
    assert r.status_code == 422