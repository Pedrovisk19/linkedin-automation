"""Repositorio de TelegramRequest (Protocol, implementado na infra)."""

from __future__ import annotations

from typing import Protocol

from developer_brain_ai_shared.kernel.id import TenantId

from developer_brain_ai_telegram.domain.aggregates import TelegramRequest


class TelegramRequestRepository(Protocol):
    async def get_by_id(
        self, tenant_id: TenantId, request_id: object
    ) -> TelegramRequest | None: ...

    async def get_pending_by_chat(
        self, tenant_id: TenantId, chat_id: int
    ) -> TelegramRequest | None: ...

    async def save(self, request: TelegramRequest) -> None: ...


__all__ = ["TelegramRequestRepository"]
