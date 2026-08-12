"""Repositorio de DiscordRequest (Protocol, implementado na infra)."""

from __future__ import annotations

from typing import Protocol

from developer_brain_ai_shared.kernel.id import TenantId

from developer_brain_ai_discord.domain.aggregates import DiscordRequest


class DiscordRequestRepository(Protocol):
    async def get_by_id(self, tenant_id: TenantId, request_id: object) -> DiscordRequest | None: ...

    async def get_pending_by_channel(
        self, tenant_id: TenantId, channel_id: int
    ) -> DiscordRequest | None: ...

    async def save(self, request: DiscordRequest) -> None: ...


__all__ = ["DiscordRequestRepository"]
