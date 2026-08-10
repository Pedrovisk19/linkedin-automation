"""Aggregate root ApiKey. Pertence a (tenant, user)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from developer_brain_ai_shared.errors.base import ValidationError
from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import ApiKeyId, TenantId, UserId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_identity.domain.events import ApiKeyCreated, ApiKeyRevoked
from developer_brain_ai_identity.domain.value_objects import ApiKeyPlain


@dataclass(eq=False)
class ApiKey(AggregateRoot):
    id: ApiKeyId
    tenant_id: TenantId
    user_id: UserId
    label: str
    key_hash: str
    key_prefix: str
    expires_at: datetime | None
    last_used_at: datetime | None
    is_revoked: bool
    timestamps: Timestamps

    def __post_init__(self) -> None:
        if not self.label or not self.label.strip():
            raise ValueError("api key label nao pode ser vazio")
        if len(self.label) > 80:
            raise ValueError("api key label excede 80 caracteres")
        if not self.key_prefix:
            raise ValueError("key_prefix obrigatorio")
        if not self.key_hash:
            raise ValueError("key_hash obrigatorio")

    @classmethod
    def issue(
        cls,
        *,
        id: ApiKeyId,
        tenant_id: TenantId,
        user_id: UserId,
        label: str,
        plain: ApiKeyPlain,
        expires_at: datetime | None,
        timestamps: Timestamps,
    ) -> ApiKey:
        if not plain.secret:
            raise ValidationError("Api key invalida (sem segredo)")
        key = cls(
            id=id,
            tenant_id=tenant_id,
            user_id=user_id,
            label=label,
            key_hash=plain.hashed_value(),
            key_prefix=plain.prefix,
            expires_at=expires_at,
            last_used_at=None,
            is_revoked=False,
            timestamps=timestamps,
        )
        key.record_event(ApiKeyCreated(tenant_id=tenant_id, api_key_id=id, user_id=user_id))
        return key

    def revoke(self) -> None:
        if self.is_revoked:
            return
        object.__setattr__(self, "is_revoked", True)
        self.record_event(ApiKeyRevoked(tenant_id=self.tenant_id, api_key_id=self.id))

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at

    def touch_used(self, now: datetime) -> None:
        object.__setattr__(self, "last_used_at", now)


__all__ = ["ApiKey"]
