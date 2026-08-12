"""Routers do modulo identity: /auth/*.

Endpoints:
- POST /auth/register       (publico)
- POST /auth/login          (publico)
- POST /auth/refresh        (publico)
- GET  /auth/api-keys       (autenticado)
- POST /auth/api-keys       (autenticado)
- DELETE /auth/api-keys/{id} (autenticado)

Os use cases sao injetados via Depends em providers definidos no composition root
(apps/api). Aqui apenas declaramos as Depends esperadas via Annotated tipado.

Nota: SEM `from __future__ import annotations` aqui —必备 para que FastAPI emita
corretamente os metadados Depends (anotacoes vivas, nao strings).
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from developer_brain_ai_identity.application.dto import (
    ApiKeyView,
    CreateApiKeyInput,
    CreateApiKeyOutput,
    LoginInput,
    RefreshInput,
    RegisterTenantInput,
    RegisterTenantOutput,
    TokenOutput,
)
from developer_brain_ai_identity.application.use_cases.create_api_key import CreateApiKey
from developer_brain_ai_identity.application.use_cases.login_user import LoginUser
from developer_brain_ai_identity.application.use_cases.manage_api_keys import (
    ListApiKeys,
    RevokeApiKey,
)
from developer_brain_ai_identity.application.use_cases.refresh_token import RefreshToken
from developer_brain_ai_identity.application.use_cases.register_tenant import RegisterTenant
from developer_brain_ai_identity.presentation.dependencies import CurrentUser, CurrentUserDependency


def build_router(
    *,
    register_uc: RegisterTenant,
    login_uc: LoginUser,
    refresh_uc: RefreshToken,
    create_api_key_uc: CreateApiKey,
    list_api_keys_uc: ListApiKeys,
    revoke_api_key_uc: RevokeApiKey,
    current_user_dep: CurrentUserDependency,
) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["identity"])

    @router.post("/register", response_model=RegisterTenantOutput, status_code=201)
    async def register(body: RegisterTenantInput) -> RegisterTenantOutput:
        return await register_uc.execute(body)

    @router.post("/login", response_model=TokenOutput)
    async def login(body: LoginInput) -> TokenOutput:
        return await login_uc.execute(body)

    @router.post("/refresh", response_model=TokenOutput)
    async def refresh(body: RefreshInput) -> TokenOutput:
        return await refresh_uc.execute(body)

    @router.get("/api-keys", response_model=list[ApiKeyView])
    async def list_api_keys(
        current_user: Annotated[CurrentUser, Depends(current_user_dep)],
    ) -> list[ApiKeyView]:
        return await list_api_keys_uc.execute(current_user.user_id)

    @router.post("/api-keys", response_model=CreateApiKeyOutput, status_code=201)
    async def create_api_key(
        current_user: Annotated[CurrentUser, Depends(current_user_dep)],
        body: CreateApiKeyInput,
    ) -> CreateApiKeyOutput:
        return await create_api_key_uc.execute(current_user.tenant_id, current_user.user_id, body)

    @router.delete("/api-keys/{api_key_id}", status_code=204)
    async def revoke_api_key(
        api_key_id: str,
        current_user: Annotated[CurrentUser, Depends(current_user_dep)],
    ) -> None:
        await revoke_api_key_uc.execute(api_key_id)

    return router


__all__ = ["build_router"]
