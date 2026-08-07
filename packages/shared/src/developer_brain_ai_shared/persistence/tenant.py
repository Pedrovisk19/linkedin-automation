"""Contexto de tenant via contextvars (async-safe).

A camada application (middleware FastAPI / UoW) seta o tenant corrente a partir
do JWT. A camada de persistencia le esse contexto p/ emitir
``SET LOCAL app.tenant_id`` no inicio da transacao — garantindo RLS transparente
para os repos que NAO precisam (e nem devem) lembrar de filtrar por tenant.

Por que contextvars? Async-safe, propagado por await; mais correto que
threadlocal no asyncio. Para process fork (Arq) o worker seta o tenant no
modulo do job manualmente via ``set_tenant_context``.
"""
from __future__ import annotations

from contextvars import ContextVar

from developer_brain_ai_shared.errors.base import ForbiddenError, UnauthorizedError
from developer_brain_ai_shared.kernel.id import TenantId

_current_tenant: ContextVar[TenantId | None] = ContextVar("current_tenant", default=None)


def set_tenant_context(tenant_id: TenantId) -> None:
    _current_tenant.set(tenant_id)


def get_tenant_context() -> TenantId:
    tenant = _current_tenant.get()
    if tenant is None:
        raise UnauthorizedError("Contexto de tenant ausente — middleware nao configurado")
    return tenant


def get_tenant_context_optional() -> TenantId | None:
    return _current_tenant.get()


def require_tenant_or_403(expected: TenantId) -> TenantId:
    current = get_tenant_context()
    if current != expected:
        raise ForbiddenError("Tenant mismatch")
    return current


def reset_tenant_context() -> None:
    _current_tenant.set(None)


__all__ = [
    "set_tenant_context",
    "get_tenant_context",
    "get_tenant_context_optional",
    "require_tenant_or_403",
    "reset_tenant_context",
]