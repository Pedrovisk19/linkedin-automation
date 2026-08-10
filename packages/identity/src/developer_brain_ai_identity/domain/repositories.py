"""Repository interfaces (Ports) do modulo identity.

Estes Protocols vivem no dominio. Implementacoes concretas (SQLAlchemy)
ficam em ``identity.infrastructure.repositories``. Use cases dependem destas
interfaces — nunca da implementacao.
"""

from __future__ import annotations

from typing import Protocol

from developer_brain_ai_shared.kernel.id import TenantId, UserId

from developer_brain_ai_identity.domain.tenant import Tenant
from developer_brain_ai_identity.domain.user import User
from developer_brain_ai_identity.domain.value_objects import Email, TenantSlug


class TenantRepository(Protocol):
    async def get_by_id(self, tenant_id: TenantId) -> Tenant | None: ...
    async def get_by_slug(self, slug: TenantSlug) -> Tenant | None: ...
    async def save(self, tenant: Tenant) -> None: ...
    async def slug_exists(self, slug: TenantSlug) -> bool: ...


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UserId) -> User | None: ...
    async def get_by_email(self, email: Email) -> User | None: ...
    async def save(self, user: User) -> None: ...
    async def email_exists(self, email: Email) -> bool: ...


__all__ = ["TenantRepository", "UserRepository"]
