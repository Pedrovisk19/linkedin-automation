"""Testes e2e dos routers /integrations/linkedin via TestClient + DI."""

from __future__ import annotations

from developer_brain_ai_identity.presentation.dependencies import get_current_user_factory
from developer_brain_ai_integrations.application.oauth_state import build_oauth_state
from developer_brain_ai_integrations.application.use_cases import (
    ConnectLinkedIn,
    DisconnectLinkedIn,
    GetLinkedInStatus,
    LinkedInAuthUrlBuilder,
)
from developer_brain_ai_integrations.presentation.routers import build_router
from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.errors.http import mount_domain_error_handlers
from developer_brain_ai_shared.kernel.id import TenantId, UserId
from fastapi import FastAPI
from fastapi.testclient import TestClient
from integrations_fakes import (
    FakeLinkedInApiClient,
    FakeLinkedInTokenRepository,
)

SECRET = "test-secret-please-replace-me-12345678901234567890"
REDIRECT = "http://localhost:8001/integrations/linkedin/callback"


def _build_app() -> FastAPI:
    repo = FakeLinkedInTokenRepository()
    api = FakeLinkedInApiClient()
    jwt = JWTService(secret=SECRET)
    current_user_dep = get_current_user_factory(jwt)

    app = FastAPI()
    mount_domain_error_handlers(app)
    app.include_router(
        build_router(
            auth_url_builder=LinkedInAuthUrlBuilder(
                oauth_secret=SECRET,
                client_id="cid",
                redirect_uri=REDIRECT,
            ),
            connect_uc=ConnectLinkedIn(repo, api, redirect_uri=REDIRECT),
            status_uc=GetLinkedInStatus(repo),
            disconnect_uc=DisconnectLinkedIn(repo),
            oauth_state_secret=SECRET,
            current_user_dep=current_user_dep,
        )
    )
    return app


def _token(tid: str, uid: str) -> str:
    return JWTService(secret=SECRET).issue_pair(UserId(uid), TenantId(tid)).access_token


def test_auth_url_requires_bearer() -> None:
    with TestClient(_build_app()) as c:
        r = c.get("/integrations/linkedin/auth-url")
    assert r.status_code == 401


def test_auth_url_returns_linkedin_url() -> None:
    with TestClient(_build_app()) as c:
        tid = TenantId.new()
        auth = {"Authorization": f"Bearer {_token(str(tid), str(UserId.new()))}"}
        r = c.get("/integrations/linkedin/auth-url", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert "https://www.linkedin.com/oauth/v2/authorization" in body["authorization_url"]
    assert "state=" in body["authorization_url"]


def test_callback_connects_tenant_from_state() -> None:
    tid = TenantId.new()
    state = build_oauth_state(SECRET, tid)
    with TestClient(_build_app()) as c:
        r = c.get(f"/integrations/linkedin/callback?code=abc&state={state}")
    assert r.status_code == 200
    assert "LinkedIn conectado" in r.text


def test_callback_rejects_tampered_state() -> None:
    tid = TenantId.new()
    state = build_oauth_state(SECRET, tid) + "tampered"
    with TestClient(_build_app()) as c:
        r = c.get(f"/integrations/linkedin/callback?code=abc&state={state}")
    assert r.status_code == 422


def test_status_disconnected_initial() -> None:
    with TestClient(_build_app()) as c:
        tid = TenantId.new()
        auth = {"Authorization": f"Bearer {_token(str(tid), str(UserId.new()))}"}
        r = c.get("/integrations/linkedin/status", headers=auth)
    assert r.status_code == 200
    assert r.json() == {
        "connected": False,
        "member_name": None,
        "member_urn": None,
        "access_expires_at": None,
    }


def test_disconnect_requires_connection() -> None:
    with TestClient(_build_app()) as c:
        tid = TenantId.new()
        auth = {"Authorization": f"Bearer {_token(str(tid), str(UserId.new()))}"}
        r = c.delete("/integrations/linkedin", headers=auth)
    assert r.status_code == 404
