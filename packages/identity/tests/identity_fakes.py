"""Fakes reutilizaveis para testes do identity (sem DB, sem passlib)."""

from __future__ import annotations

from collections import defaultdict

from developer_brain_ai_identity.domain.api_key import ApiKey
from developer_brain_ai_identity.domain.tenant import Tenant
from developer_brain_ai_identity.domain.user import User
from developer_brain_ai_identity.domain.value_objects import Email, TenantSlug
from developer_brain_ai_shared.kernel.id import ApiKeyId, TenantId, UserId


class FakePasswordHasher:
    """Hasher deterministica para testes: hash = 'fake$' + plain."""

    def hash(self, plain: str) -> str:
        return "fake$" + plain

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == "fake$" + plain


class FakeTenantRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Tenant] = {}
        self._by_slug: dict[str, Tenant] = {}

    async def get_by_id(self, tenant_id: TenantId) -> Tenant | None:
        return self._by_id.get(str(tenant_id))

    async def get_by_slug(self, slug: TenantSlug) -> Tenant | None:
        return self._by_slug.get(str(slug))

    async def save(self, tenant: Tenant) -> None:
        self._by_id[str(tenant.id)] = tenant
        self._by_slug[str(tenant.slug)] = tenant

    async def slug_exists(self, slug: TenantSlug) -> bool:
        return str(slug) in self._by_slug


class FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}
        self._by_email: dict[str, User] = {}

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self._by_id.get(str(user_id))

    async def get_by_email(self, email: Email) -> User | None:
        return self._by_email.get(str(email))

    async def save(self, user: User) -> None:
        self._by_id[str(user.id)] = user
        self._by_email[str(user.email)] = user

    async def email_exists(self, email: Email) -> bool:
        return str(email) in self._by_email


class FakeApiKeyRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, ApiKey] = {}
        self._by_user: dict[str, list[ApiKey]] = defaultdict(list)

    async def get_by_id(self, api_key_id: ApiKeyId) -> ApiKey | None:
        return self._by_id.get(str(api_key_id))

    async def get_by_prefix(self, tenant_id: TenantId, prefix: str) -> ApiKey | None:
        for k in self._by_id.values():
            if k.key_prefix == prefix and k.tenant_id == tenant_id:
                return k
        return None

    async def save(self, api_key: ApiKey) -> None:
        self._by_id[str(api_key.id)] = api_key
        self._by_user[str(api_key.user_id)].append(api_key)

    async def list_by_user(self, user_id: UserId) -> list[ApiKey]:
        return list(self._by_user.get(str(user_id), []))

    async def update_last_used(self, api_key_id: ApiKeyId, at) -> None:
        k = self._by_id.get(str(api_key_id))
        if k is not None:
            k.touch_used(at)

    async def revoke(self, api_key_id: ApiKeyId) -> None:
        k = self._by_id.get(str(api_key_id))
        if k is not None:
            k.revoke()


__all__ = [
    "FakeApiKeyRepository",
    "FakePasswordHasher",
    "FakeTenantRepository",
    "FakeUserRepository",
]
