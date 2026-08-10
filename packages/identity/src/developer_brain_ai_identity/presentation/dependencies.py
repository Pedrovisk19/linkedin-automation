"""Auth dependencies: extrai user/tenant do JWT e seta TenantContext no request scope.

Use em endpoints:

    @router.get("/me")
    async def me(current: CurrentUser) -> UserOut:
        ...

O Depends resolve ``CurrentUser`` (com tenant_id/user_id) e garante que
``set_tenant_context`` esteja ativo durante o request. FastAPI roda Depends em
uma task; contextvars sao propagadas dentro da mesma task.

Nota: SEM `from __future__ import annotations` para preservar Depends metadata vivo.
"""

from dataclasses import dataclass
from typing import Annotated

from developer_brain_ai_shared.auth.jwt import JWTService
from developer_brain_ai_shared.errors.base import UnauthorizedError
from developer_brain_ai_shared.kernel.id import TenantId, UserId
from developer_brain_ai_shared.persistence.tenant import reset_tenant_context, set_tenant_context
from fastapi import Header, HTTPException, Request, status


@dataclass(frozen=True)
class CurrentUser:
    user_id: UserId
    tenant_id: TenantId


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bearer token ausente")
    return authorization.split(" ", 1)[1].strip()


def get_current_user_factory(jwt: JWTService):
    """Factory pois JWTService e injetavel (nao global)."""

    async def _dep(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> CurrentUser:
        token = _extract_bearer(authorization)
        try:
            payload = jwt.decode(token, expected_type="access")
        except UnauthorizedError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message
            ) from exc

        set_tenant_context(payload.tenant_id)

        async def _reset() -> None:
            reset_tenant_context()

        request.scope.setdefault("dba_cleanup", []).append(_reset)
        return CurrentUser(user_id=payload.user_id, tenant_id=payload.tenant_id)

    return _dep


__all__ = ["CurrentUser", "get_current_user_factory"]
