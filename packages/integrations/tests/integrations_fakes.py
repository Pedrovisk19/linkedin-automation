"""Fakes para tests do integrations (sem DB/HTTP real)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from developer_brain_ai_integrations.application.ports import (
    LinkedInTokenData,
    LinkedInUserInfo,
)
from developer_brain_ai_integrations.domain.aggregates import LinkedInToken
from developer_brain_ai_shared.kernel.id import TenantId


def make_token(
    *,
    tenant_id: TenantId | None = None,
    access_expires_in: int = 3600,
    refresh_expires_in: int = 2_592_000,
) -> LinkedInToken:
    now = datetime.now(UTC)
    return LinkedInToken(
        id=object(),
        tenant_id=tenant_id or TenantId.new(),
        access_token="access-123",
        refresh_token="refresh-456",
        access_expires_at=now + timedelta(seconds=access_expires_in),
        refresh_expires_at=now + timedelta(seconds=refresh_expires_in),
        member_urn="urn:li:person:abc123",
        member_name="Fulano de Tal",
    )


class FakeLinkedInTokenRepository:
    def __init__(self) -> None:
        self._tokens: dict[str, LinkedInToken] = {}
        self.saved: list[LinkedInToken] = []
        self.deleted: list[TenantId] = []

    async def get(self, tenant_id: TenantId) -> LinkedInToken | None:
        return self._tokens.get(str(tenant_id.as_uuid()))

    async def save(self, token: LinkedInToken) -> None:
        self._tokens[str(token.tenant_id.as_uuid())] = token
        self.saved.append(token)

    async def delete(self, tenant_id: TenantId) -> None:
        self._tokens.pop(str(tenant_id.as_uuid()), None)
        self.deleted.append(tenant_id)


class FakeLinkedInApiClient:
    """Client fake: permite simular code exchange, refresh e userinfo."""

    def __init__(self) -> None:
        self.exchange_codes: list[tuple[str, str]] = []
        self.refreshed: list[str] = []
        self.userinfo_calls: list[str] = []
        self.posts: list[tuple[str, str, str]] = []

    async def exchange_code(self, code: str, redirect_uri: str) -> LinkedInTokenData:
        self.exchange_codes.append((code, redirect_uri))
        return _token_data()

    async def refresh_tokens(self, refresh_token: str) -> LinkedInTokenData:
        self.refreshed.append(refresh_token)
        return _token_data(access="access-refreshed", refresh="refresh-new")

    async def get_userinfo(self, access_token: str) -> LinkedInUserInfo:
        self.userinfo_calls.append(access_token)
        return LinkedInUserInfo(member_urn="urn:li:person:abc123", name="Fulano de Tal")

    async def publish_post(self, access_token: str, member_urn: str, commentary: str) -> str:
        self.posts.append((access_token, member_urn, commentary))
        return "urn:li:share:999"


def _token_data(
    *,
    access: str = "access-123",
    refresh: str = "refresh-456",
    has_refresh: bool = True,
) -> LinkedInTokenData:
    now = datetime.now(UTC)
    return LinkedInTokenData(
        access_token=access,
        access_expires_at=now + timedelta(seconds=3600),
        refresh_token=refresh if has_refresh else None,
        refresh_expires_at=(now + timedelta(seconds=2_592_000) if has_refresh else None),
    )


__all__ = [
    "FakeLinkedInApiClient",
    "FakeLinkedInTokenRepository",
    "make_token",
]
