"""Ports do LinkedIn: cliente HTTP (OAuth2 + Marketing API) injetavel."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class LinkedInTokenData:
    access_token: str
    access_expires_at: datetime
    refresh_token: str | None = None
    refresh_expires_at: datetime | None = None


@dataclass(frozen=True)
class LinkedInUserInfo:
    member_urn: str  # urn:li:person:<id>
    name: str


class LinkedInApiClient(Protocol):
    """Face da LinkedIn API usada pelo use case ConnectLinkedIn."""

    async def exchange_code(self, code: str, redirect_uri: str) -> LinkedInTokenData: ...

    async def refresh_tokens(self, refresh_token: str) -> LinkedInTokenData: ...

    async def get_userinfo(self, access_token: str) -> LinkedInUserInfo: ...

    async def publish_post(self, access_token: str, member_urn: str, commentary: str) -> str: ...


__all__ = ["LinkedInApiClient", "LinkedInTokenData", "LinkedInUserInfo"]
