"""Repository interface para ApiKey + dto para autenticacao por chave."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from developer_brain_ai_shared.kernel.id import ApiKeyId, TenantId, UserId

from developer_brain_ai_identity.domain.api_key import ApiKey


class ApiKeyRepository(Protocol):
    async def get_by_id(self, api_key_id: ApiKeyId) -> ApiKey | None: ...
    async def get_by_prefix(self, tenant_id: TenantId, prefix: str) -> ApiKey | None: ...
    async def save(self, api_key: ApiKey) -> None: ...
    async def list_by_user(self, user_id: UserId) -> list[ApiKey]: ...
    async def update_last_used(self, api_key_id: ApiKeyId, at: datetime) -> None: ...
    async def revoke(self, api_key_id: ApiKeyId) -> None: ...


__all__ = ["ApiKeyRepository"]
