"""Routers do LinkedIn: /integrations/linkedin/*.

- GET  /auth-url     (auth)     -> URL de autorizacao OAuth do LinkedIn
- GET  /callback     (publico)  -> recebe code+state apos consentimento
- GET  /status       (auth)     -> conexao atual do tenant
- DELETE /           (auth)     -> desconecta (remove token)

O callback e PUBLICO: o browser do usuario chega direto na API apos o
consentimento no LinkedIn (sem header Authorization). A identificacao do
tenant vem do ``state`` assinado (HMAC) gerado em ``/auth-url``.

Nota: SEM `from __future__ import annotations` (ADR-0012) — Depends precisa
das anotacoes vivas p/ resolver o metadata do FastAPI.
"""

from typing import Annotated

from developer_brain_ai_identity.presentation.dependencies import (
    CurrentUser,
    CurrentUserDependency,
)
from developer_brain_ai_shared.persistence.tenant import (
    reset_tenant_context,
    set_tenant_context,
)
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from developer_brain_ai_integrations.application.dto import (
    LinkedInAuthUrlOutput,
    LinkedInStatusOutput,
)
from developer_brain_ai_integrations.application.oauth_state import verify_oauth_state
from developer_brain_ai_integrations.application.use_cases import (
    ConnectLinkedIn,
    DisconnectLinkedIn,
    GetLinkedInStatus,
    LinkedInAuthUrlBuilder,
)


def build_router(
    *,
    auth_url_builder: LinkedInAuthUrlBuilder,
    connect_uc: ConnectLinkedIn,
    status_uc: GetLinkedInStatus,
    disconnect_uc: DisconnectLinkedIn,
    oauth_state_secret: str,
    current_user_dep: CurrentUserDependency,
) -> APIRouter:

    UserDep = Annotated[CurrentUser, Depends(current_user_dep)]
    router = APIRouter(prefix="/integrations/linkedin", tags=["integrations"])

    @router.get("/auth-url", response_model=LinkedInAuthUrlOutput)
    async def auth_url(current: UserDep) -> LinkedInAuthUrlOutput:
        return auth_url_builder.execute(current.tenant_id)

    @router.get("/callback", response_class=HTMLResponse)
    async def callback(
        code: Annotated[str, Query()],
        state: Annotated[str, Query()],
    ) -> HTMLResponse:
        tenant_id = verify_oauth_state(oauth_state_secret, state)
        set_tenant_context(tenant_id)
        try:
            status = await connect_uc.execute(tenant_id, code)
        finally:
            reset_tenant_context()
        return HTMLResponse(
            f"""<!doctype html><html lang="pt-BR"><body style="font-family:sans-serif;
text-align:center;padding-top:4rem">
<h2>LinkedIn conectado!</h2>
<p>Conta: <strong>{status.member_name or status.member_urn}</strong></p>
<p>Pode fechar esta aba e voltar para a API.</p>
</body></html>"""
        )

    @router.get("/status", response_model=LinkedInStatusOutput)
    async def status(current: UserDep) -> LinkedInStatusOutput:
        return await status_uc.execute(current.tenant_id)

    @router.delete("", status_code=204)
    async def disconnect(current: UserDep) -> None:
        await disconnect_uc.execute(current.tenant_id)

    return router


__all__ = ["build_router"]
