"""LoginUser use case.

Fluxo (alinhado ao ADR-0010):
1. Resolve Tenant por slug (lookup sem RLS).
2. Seta TenantContext (RLS ativa para queries seguintes).
3. Busca User por email dentro do tenant.
4. Valida senha; em caso de falha retorna UnauthorizedError (mensagem unica p/
   evitar enumeration).
"""

from __future__ import annotations

from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.auth.password import PasswordHasher
from developer_brain_ai_shared.errors.base import UnauthorizedError
from developer_brain_ai_shared.persistence.tenant import set_tenant_context

from developer_brain_ai_identity.application.dto import LoginInput, TokenOutput
from developer_brain_ai_identity.domain.repositories import TenantRepository, UserRepository
from developer_brain_ai_identity.domain.value_objects import Email, TenantSlug


class LoginUser:
    def __init__(
        self,
        tenants: TenantRepository,
        users: UserRepository,
        hasher: PasswordHasher,
        jwt: JWTService,
    ) -> None:
        self._tenants = tenants
        self._users = users
        self._hasher = hasher
        self._jwt = jwt

    async def execute(self, data: LoginInput) -> TokenOutput:
        tenant = await self._tenants.get_by_slug(TenantSlug(data.tenant_slug))
        if tenant is None:
            raise UnauthorizedError("credenciais invalidas")

        set_tenant_context(tenant.id)
        try:
            user = await self._users.get_by_email(Email(data.email))
        finally:
            from developer_brain_ai_shared.persistence.tenant import reset_tenant_context

            reset_tenant_context()

        if user is None or not user.is_active:
            raise UnauthorizedError("credenciais invalidas")

        if not self._hasher.verify(data.password, user.password_hash.value):
            raise UnauthorizedError("credenciais invalidas")

        user.mark_logged_in()
        await self._users.save(user)

        pair = self._jwt.issue_pair(user_id=user.id, tenant_id=user.tenant_id)
        return TokenOutput(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            expires_at=pair.access_expires_at,
        )


__all__ = ["LoginUser"]
