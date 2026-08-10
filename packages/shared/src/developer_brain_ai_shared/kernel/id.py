"""Typed identifiers.

Cada ID de domínio é uma subclasse de TypedId com UUID subjacente, expondo
``new()`` para geração e aceitando UUID/str no construtor. Usa ``Annotated``
para que o SQLAlchemy 2 mapeie corretamente (UUIDType).

Justificativa: em vez de ``UUID`` solto por todo o código (e tipos trocáveis em
assinaturas), IDs tipados tornam ``user_id`` e ``tenant_id`` distintos para o
type-checker — bug de troca é pego em tempo de compilação.
"""

from __future__ import annotations

import uuid
from typing import Annotated, TypeAlias

from sqlalchemy import Uuid

UUIDType: TypeAlias = Annotated[uuid.UUID, Uuid]


class TypedId:
    """Base para IDs tipados (UUID v4). Imutável e comparável por valor."""

    __slots__ = ("_value",)

    def __init__(self, value: uuid.UUID | str) -> None:
        if isinstance(value, str):
            value = uuid.UUID(value)
        if not isinstance(value, uuid.UUID):
            raise TypeError(
                f"{type(self).__name__} requires UUID or str, got {type(value).__name__}"
            )
        object.__setattr__(self, "_value", value)

    @classmethod
    def new(cls) -> TypedId:
        return cls(uuid.uuid4())

    @property
    def value(self) -> uuid.UUID:
        return self._value  # type: ignore[no-any-return]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and other._value == self._value

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._value))

    def __lt__(self, other: TypedId) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._value < other._value

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value})"

    def as_uuid(self) -> uuid.UUID:
        return self._value


class TenantId(TypedId):
    """Identificador de tenant (multi-tenancy)."""


class UserId(TypedId):
    """Identificador de usuário."""


class ApiKeyId(TypedId):
    """Identificador de API key."""


__all__ = ["ApiKeyId", "TenantId", "TypedId", "UUIDType", "UserId"]
