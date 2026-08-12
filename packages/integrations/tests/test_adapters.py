"""Testes do adaptador LinkedInPostPublisher (port do content)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from developer_brain_ai_integrations.infrastructure.adapters import LinkedInPostPublisher
from developer_brain_ai_shared.errors.base import ConflictError, IntegrationError
from developer_brain_ai_shared.kernel.id import TenantId
from integrations_fakes import (
    FakeLinkedInApiClient,
    FakeLinkedInTokenRepository,
    make_token,
)


def test_publish_raises_conflict_when_not_connected() -> None:
    repo = FakeLinkedInTokenRepository()
    publisher = LinkedInPostPublisher(tokens=repo, api=FakeLinkedInApiClient())
    with pytest.raises(ConflictError):
        asyncio.run(publisher.publish(TenantId.new(), text="x"))


def test_publish_appends_hashtags_to_commentary() -> None:
    api = FakeLinkedInApiClient()
    urn = asyncio.run(_publish(api=api, hashtags=["#python", "#dev"]))
    assert urn == "urn:li:share:999"
    assert api.posts[0][1] == "urn:li:person:abc123"
    assert api.posts[0][2] == "post\n\n#python #dev"


def test_publish_refreshes_expired_access_token() -> None:
    repo = FakeLinkedInTokenRepository()
    api = FakeLinkedInApiClient()
    token = make_token(access_expires_in=0)  # expirado (skew)
    asyncio.run(repo.save(token))

    publisher = LinkedInPostPublisher(tokens=repo, api=api)
    urn = asyncio.run(publisher.publish(token.tenant_id, text="post"))
    assert urn == "urn:li:share:999"
    assert api.refreshed == [token.refresh_token]
    assert repo.saved[-1].access_token == "access-refreshed"


def test_publish_raises_integration_error_when_refresh_expired() -> None:
    repo = FakeLinkedInTokenRepository()
    api = FakeLinkedInApiClient()
    token = make_token(access_expires_in=0)
    object.__setattr__(token, "refresh_expires_at", datetime.now(UTC) - timedelta(seconds=1))
    asyncio.run(repo.save(token))

    publisher = LinkedInPostPublisher(tokens=repo, api=api)
    with pytest.raises(IntegrationError):
        asyncio.run(publisher.publish(token.tenant_id, text="post"))


def test_publish_without_hashtags_works() -> None:
    api = FakeLinkedInApiClient()
    urn = asyncio.run(_publish(api=api, hashtags=[]))
    assert urn == "urn:li:share:999"
    assert api.posts[0][2] == "post"


async def _publish(api=None, *, text="post", hashtags=None) -> str:
    repo = FakeLinkedInTokenRepository()
    api = api or FakeLinkedInApiClient()
    token = make_token()
    await repo.save(token)
    publisher = LinkedInPostPublisher(tokens=repo, api=api)
    return await publisher.publish(token.tenant_id, text=text, hashtags=hashtags or [])
