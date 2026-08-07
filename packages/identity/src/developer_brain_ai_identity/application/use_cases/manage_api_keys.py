"""ListApiKeys + RevokeApiKey use cases."""
from __future__ import annotations

from developer_brain_ai_identity.application.dto import ApiKeyView
from developer_brain_ai_identity.domain.api_key_repository import ApiKeyRepository
from developer_brain_ai_shared.errors.base import NotFoundError
from developer_brain_ai_shared.kernel.id import ApiKeyId, UserId


class ListApiKeys:
    def __init__(self, api_keys: ApiKeyRepository) -> None:
        self._api_keys = api_keys

    async def execute(self, user_id: UserId) -> list[ApiKeyView]:
        items = await self._api_keys.list_by_user(user_id)
        return [
            ApiKeyView(
                id=str(k.id),
                label=k.label,
                prefix=k.key_prefix,
                expires_at=k.expires_at,
                last_used_at=k.last_used_at,
                is_revoked=k.is_revoked,
            )
            for k in items
        ]


class RevokeApiKey:
    def __init__(self, api_keys: ApiKeyRepository) -> None:
        self._api_keys = api_keys

    async def execute(self, api_key_id: str) -> None:
        key = await self._api_keys.get_by_id(ApiKeyId(api_key_id))
        if key is None:
            raise NotFoundError("api key nao encontrada", details={"id": api_key_id})
        key.revoke()
        await self._api_keys.save(key)


__all__ = ["ListApiKeys", "RevokeApiKey"]