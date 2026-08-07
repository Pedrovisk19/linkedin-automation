"""Aggregate root Tenant. Raiz do modulo identity."""
from __future__ import annotations

from dataclasses import dataclass, field

from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_identity.domain.events import TenantRegistered
from developer_brain_ai_identity.domain.value_objects import TenantSlug


@dataclass(eq=False)
class Tenant(AggregateRoot):
    id: TenantId
    slug: TenantSlug
    name: str
    timestamps: Timestamps

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("tenant name nao pode ser vazio")
        if len(self.name) > 120:
            raise ValueError("tenant name excede 120 caracteres")

    @classmethod
    def register(cls, *, id: TenantId, slug: TenantSlug, name: str, timestamps: Timestamps) -> Tenant:
        tenant = cls(id=id, slug=slug, name=name, timestamps=timestamps)
        tenant.record_event(TenantRegistered(tenant_id=id, slug=str(slug), name=name))
        return tenant


__all__ = ["Tenant"]