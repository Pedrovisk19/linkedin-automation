"""Portas de persistencia do integrations (LinkedInToken)."""

from __future__ import annotations

from typing import Protocol

from developer_brain_ai_shared.kernel.id import TenantId

from developer_brain_ai_integrations.domain.aggregates import LinkedInToken


class LinkedInTokenRepository(Protocol):
    async def get(self, tenant_id: TenantId) -> LinkedInToken | None: ...

    async def save(self, token: LinkedInToken) -> None: ...

    async def delete(self, tenant_id: TenantId) -> None: ...


__all__ = ["LinkedInTokenRepository"]
