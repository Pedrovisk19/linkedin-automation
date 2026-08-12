"""Testes do HttpLinkedInApiClient com respx (sem rede real)."""

from __future__ import annotations

import httpx
import pytest
import respx
from developer_brain_ai_integrations.infrastructure.linkedin_client import (
    HttpLinkedInApiClient,
)
from developer_brain_ai_shared.errors.base import IntegrationError, ValidationError

TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
POSTS_URL = "https://api.linkedin.com/rest/posts"

CLIENT = HttpLinkedInApiClient(client_id="cid", client_secret="csecret")


@respx.mock
async def test_exchange_code_posts_form_and_parses() -> None:
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": 3600,
                "refresh_token_expires_in": 2592000,
            },
        )
    )
    data = await CLIENT.exchange_code("code-1", "http://localhost:8001/callback")
    assert data.access_token == "at"
    assert data.refresh_token == "rt"
    form = route.calls.last.request.content.decode()
    assert "grant_type=authorization_code" in form
    assert "code=code-1" in form
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8001%2Fcallback" in form
    assert "client_id=cid" in form
    assert "client_secret=csecret" in form
    assert "code_verifier" not in form
    assert "Authorization" not in route.calls.last.request.headers


@respx.mock
async def test_refresh_tokens_uses_refresh_grant() -> None:
    route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "at2",
                "refresh_token": "rt2",
                "expires_in": 3600,
                "refresh_token_expires_in": 2592000,
            },
        )
    )
    data = await CLIENT.refresh_tokens("rt-old")
    assert data.access_token == "at2"
    form = route.calls.last.request.content.decode()
    assert "grant_type=refresh_token" in form
    assert "refresh_token=rt-old" in form


@respx.mock
async def test_exchange_code_missing_access_token_raises() -> None:
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"scope": "x"}))
    with pytest.raises(ValidationError):
        await CLIENT.exchange_code("c", "http://localhost:8001/callback")


@respx.mock
async def test_exchange_code_without_refresh_token_parses() -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "at", "expires_in": 5_183_999},
        )
    )
    data = await CLIENT.exchange_code("c", "http://localhost:8001/callback")
    assert data.access_token == "at"
    assert data.refresh_token is None
    assert data.refresh_expires_at is None


@respx.mock
async def test_token_error_raises_integration_error() -> None:
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(400, text="bad request"))
    with pytest.raises(IntegrationError):
        await CLIENT.exchange_code("c", "http://localhost:8001/callback")


@respx.mock
async def test_get_userinfo_builds_person_urn() -> None:
    route = respx.get(USERINFO_URL).mock(
        return_value=httpx.Response(200, json={"sub": "abc123", "name": "Fulano"})
    )
    user = await CLIENT.get_userinfo("at")
    assert user.member_urn == "urn:li:person:abc123"
    assert user.name == "Fulano"
    assert route.calls.last.request.headers["Authorization"] == "Bearer at"


@respx.mock
async def test_get_userinfo_without_sub_raises() -> None:
    respx.get(USERINFO_URL).mock(return_value=httpx.Response(200, json={"name": "X"}))
    with pytest.raises(ValidationError):
        await CLIENT.get_userinfo("at")


@respx.mock
async def test_publish_post_sends_member_payload_and_returns_urn() -> None:
    route = respx.post(POSTS_URL).mock(
        return_value=httpx.Response(201, headers={"x-restli-id": "urn:li:share:999"})
    )
    urn = await CLIENT.publish_post("at", "urn:li:person:abc", "Meu post")
    assert urn == "urn:li:share:999"
    req = route.calls.last.request
    assert req.headers["Authorization"] == "Bearer at"
    assert req.headers["LinkedIn-Version"] == "202604"
    body = req.content
    assert b'"author": "urn:li:person:abc"' in body or b'"author":"urn:li:person:abc"' in body
    assert b'"commentary": "Meu post"' in body or b'"commentary":"Meu post"' in body
    assert b'"visibility": "PUBLIC"' in body or b'"visibility":"PUBLIC"' in body
    assert b'"lifecycleState": "PUBLISHED"' in body or b'"lifecycleState":"PUBLISHED"' in body


@respx.mock
async def test_publish_post_rejects_overlong_commentary() -> None:
    with pytest.raises(ValidationError):
        await CLIENT.publish_post("at", "urn:li:person:abc", "x" * 3001)


@respx.mock
async def test_publish_post_error_raises_integration_error() -> None:
    respx.post(POSTS_URL).mock(return_value=httpx.Response(401, text="expired token"))
    with pytest.raises(IntegrationError):
        await CLIENT.publish_post("at", "urn:li:person:abc", "post")
