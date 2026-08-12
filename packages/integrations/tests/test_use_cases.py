"""Testes dos use cases do LinkedIn (connect/status/disconnect/auth-url)."""

from __future__ import annotations

import asyncio

import pytest
from developer_brain_ai_integrations.application.oauth_state import (
    build_oauth_state,
    verify_oauth_state,
)
from developer_brain_ai_integrations.application.use_cases import (
    ConnectLinkedIn,
    DisconnectLinkedIn,
    GetLinkedInStatus,
    LinkedInAuthUrlBuilder,
)
from developer_brain_ai_shared.errors.base import NotFoundError, ValidationError
from developer_brain_ai_shared.kernel.id import TenantId
from integrations_fakes import (
    FakeLinkedInApiClient,
    FakeLinkedInTokenRepository,
    make_token,
)

SECRET = "oauth-test-secret-1234567890"
REDIRECT = "http://localhost:8001/integrations/linkedin/callback"


def test_auth_url_builder_contains_state_and_scope() -> None:
    tid = TenantId.new()
    builder = LinkedInAuthUrlBuilder(
        oauth_secret=SECRET,
        client_id="client-1",
        redirect_uri=REDIRECT,
    )
    out = builder.execute(tid)
    assert "oauth/v2/authorization" in out.authorization_url
    assert "client_id=client-1" in out.authorization_url
    assert "w_member_social" in out.authorization_url
    assert "state=" in out.authorization_url
    assert "code_challenge=" in out.authorization_url
    assert "code_challenge_method=S256" in out.authorization_url


def test_connect_persists_token_and_returns_status() -> None:

    repo = FakeLinkedInTokenRepository()
    api = FakeLinkedInApiClient()
    tid = TenantId.new()
    uc = ConnectLinkedIn(repo, api, redirect_uri=REDIRECT)

    out = asyncio.run(uc.execute(tid, code="the-code"))
    assert out.connected is True
    assert out.member_name == "Fulano de Tal"
    assert out.member_urn == "urn:li:person:abc123"
    assert api.exchange_codes == [("the-code", REDIRECT)]
    assert len(repo.saved) == 1
    assert repo.saved[0].tenant_id == tid


def test_status_disconnected_when_no_token() -> None:

    repo = FakeLinkedInTokenRepository()
    out = asyncio.run(GetLinkedInStatus(repo).execute(TenantId.new()))
    assert out.connected is False
    assert out.member_name is None


def test_status_connected_returns_member() -> None:

    repo = FakeLinkedInTokenRepository()
    token = make_token()
    asyncio.run(repo.save(token))
    out = asyncio.run(GetLinkedInStatus(repo).execute(token.tenant_id))
    assert out.connected is True
    assert out.member_name == "Fulano de Tal"
    assert out.access_expires_at is not None


def test_disconnect_removes_token() -> None:

    repo = FakeLinkedInTokenRepository()
    token = make_token()
    asyncio.run(repo.save(token))
    asyncio.run(DisconnectLinkedIn(repo).execute(token.tenant_id))
    assert repo.deleted == [token.tenant_id]
    assert asyncio.run(repo.get(token.tenant_id)) is None


def test_disconnect_raises_when_never_connected() -> None:

    repo = FakeLinkedInTokenRepository()
    with pytest.raises(NotFoundError):
        asyncio.run(DisconnectLinkedIn(repo).execute(TenantId.new()))


def test_oauth_state_roundtrip() -> None:
    tid = TenantId.new()
    state = build_oauth_state(SECRET, tid)
    assert verify_oauth_state(SECRET, state) == tid


def test_oauth_state_rejects_tampered() -> None:

    tid = TenantId.new()
    state = build_oauth_state(SECRET, tid)
    with pytest.raises(ValidationError):
        verify_oauth_state(SECRET, state + "x")


def test_oauth_state_rejects_wrong_secret() -> None:

    tid = TenantId.new()
    state = build_oauth_state(SECRET, tid)
    with pytest.raises(ValidationError):
        verify_oauth_state("outra-secret", state)
