"""CreateApiKey use case. Gera chave legivel (uma vez), persiste hash SHA-256."""
from __future__ import annotations

from developer_brain_ai_identity.application.dto import CreateApiKeyInput, CreateApiKeyOutput
from developer_brain_ai_identity.domain.api_key import ApiKey
from developer_brain_ai_identity.domain.api_key_repository import ApiKeyRepository
from developer_brain_ai_shared.kernel.id import ApiKeyId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow


class CreateApiKey:
    def __init__(self, api_keys: ApiKeyRepository) -> None:
        self._api_keys = api_keys

    async def execute(
        self,
        tenant_id,
        user_id,
        data: CreateApiKeyInput,
    ) -> CreateApiKeyOutput:
        from developer_brain_ai_identity.domain.value_objects import ApiKeyPlain

        plain = ApiKeyPlain.generate()
        now = utcnow()
        api_key = ApiKey.issue(
            id=ApiKeyId.new(),
            tenant_id=tenant_id,
            user_id=user_id,
            label=data.label,
            plain=plain,
            expires_at=data.expires_at,
            timestamps=Timestamps(created_at=now, updated_at=now),
        )
        await self._api_keys.save(api_key)
        return CreateApiKeyOutput(
            api_key_id=str(api_key.id),
            label=api_key.label,
            key_display=plain.display,
            prefix=api_key.key_prefix,
            expires_at=api_key.expires_at,
        )


__all__ = ["CreateApiKey"]