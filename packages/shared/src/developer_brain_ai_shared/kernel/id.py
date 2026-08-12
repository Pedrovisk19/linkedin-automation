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
from typing import Annotated, Any, TypeVar

from sqlalchemy import Uuid

type UUIDType = Annotated[uuid.UUID, Uuid]

T_TypedId = TypeVar("T_TypedId", bound="TypedId[Any]")


class TypedId[T_TypedId]:
    """Base para IDs tipados (UUID v4). Imutável e comparável por valor."""

    _value: uuid.UUID
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
    def new(cls) -> T_TypedId:
        """Gera um novo id UUID v4 com o tipo concreto da subclasse."""

        return cls(uuid.uuid4())  # type: ignore[return-value]

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> T_TypedId:
        """Reconstroi um id a partir de um UUID (mappers/ORM)."""

        return cls(value)  # type: ignore[return-value]

    @property
    def value(self) -> uuid.UUID:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and other._value == self._value

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._value))

    def __lt__(self, other: TypedId[Any]) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._value < other._value

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value})"

    def as_uuid(self) -> uuid.UUID:
        return self._value


class TenantId(TypedId["TenantId"]):
    """Identificador de tenant (multi-tenancy)."""


class UserId(TypedId["UserId"]):
    """Identificador de usuário."""


class ApiKeyId(TypedId["ApiKeyId"]):
    """Identificador de API key."""


__all__ = ["ApiKeyId", "TenantId", "TypedId", "UUIDType", "UserId"]
