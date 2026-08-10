"""RegisterTenant use case.

Cria um novo Tenant + um User admin vinculado a ele. Operacao atomica:
ambos persistidos ou nenhum. Idempotente por slug e email (undef uuids new).
"""

from __future__ import annotations

from developer_brain_ai_shared.auth.password import PasswordHasher
from developer_brain_ai_shared.errors.base import ConflictError
from developer_brain_ai_shared.kernel.id import TenantId, UserId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow

from developer_brain_ai_identity.application.dto import RegisterTenantInput, RegisterTenantOutput
from developer_brain_ai_identity.domain.repositories import TenantRepository, UserRepository
from developer_brain_ai_identity.domain.value_objects import (
    Email,
    PasswordHash,
    TenantSlug,
    UserRole,
)


class RegisterTenant:
    def __init__(
        self,
        tenants: TenantRepository,
        users: UserRepository,
        hasher: PasswordHasher,
    ) -> None:
        self._tenants = tenants
        self._users = users
        self._hasher = hasher

    async def execute(self, data: RegisterTenantInput) -> RegisterTenantOutput:
        slug = TenantSlug(data.tenant_slug)
        if await self._tenants.slug_exists(slug):
            raise ConflictError("tenant slug ja existe", details={"slug": str(slug)})

        email = Email(data.admin_email)
        if await self._users.email_exists(email):
            raise ConflictError("email ja cadastrado", details={"email": str(email)})

        now = utcnow()
        tenant_ts = Timestamps(created_at=now, updated_at=now)
        user_ts = Timestamps(created_at=now, updated_at=now)
        tenant_id = TenantId.new()
        user_id = UserId.new()

        from developer_brain_ai_identity.domain.tenant import Tenant
        from developer_brain_ai_identity.domain.user import User

        tenant = Tenant.register(
            id=tenant_id, slug=slug, name=data.tenant_name, timestamps=tenant_ts
        )
        password_hash = PasswordHash(self._hasher.hash(data.admin_password))
        user = User.register(
            id=user_id,
            tenant_id=tenant_id,
            email=email,
            name=data.admin_name,
            password_hash=password_hash,
            role=UserRole.ADMIN,
            timestamps=user_ts,
        )

        await self._tenants.save(tenant)
        await self._users.save(user)

        return RegisterTenantOutput(
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            email=str(user.email),
        )


__all__ = ["RegisterTenant"]
