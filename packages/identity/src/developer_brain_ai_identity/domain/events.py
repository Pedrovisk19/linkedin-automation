"""Domain events do modulo identity.

Eventos carregam apenas dados necessarios para handlers. tenant_id ja vem da
classe base DomainEvent. Extra fields usam defaults p/ manter keyword-only
flexivel e evitar ripple quando novos campos aparecem.
"""

from __future__ import annotations

from dataclasses import dataclass

from developer_brain_ai_shared.events.base import DomainEvent
from developer_brain_ai_shared.kernel.id import ApiKeyId, UserId


@dataclass(frozen=True)
class TenantRegistered(DomainEvent):
    slug: str = ""
    name: str = ""


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    user_id: UserId | None = None
    email: str = ""


@dataclass(frozen=True)
class UserLoggedIn(DomainEvent):
    user_id: UserId | None = None


@dataclass(frozen=True)
class UserSuspended(DomainEvent):
    user_id: UserId | None = None


@dataclass(frozen=True)
class ApiKeyCreated(DomainEvent):
    api_key_id: ApiKeyId | None = None
    user_id: UserId | None = None


@dataclass(frozen=True)
class ApiKeyRevoked(DomainEvent):
    api_key_id: ApiKeyId | None = None


__all__ = [
    "ApiKeyCreated",
    "ApiKeyRevoked",
    "TenantRegistered",
    "UserLoggedIn",
    "UserRegistered",
    "UserSuspended",
]
