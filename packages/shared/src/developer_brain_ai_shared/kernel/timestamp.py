"""Value objects base e timestamp/audit comuns.

Value objects sao imutaveis, comparaveis por valor e sem identidade. Timestamps
``CreatedAt``/``UpdatedAt`` sao value objects de dominio (nao ORM) — a camada de
infra converte para DateTime do SQLAlchemy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


def utcnow() -> datetime:
    """UTC tz-aware. Centralizado para evitar ``datetime.utcnow()`` deprecado."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class Timestamps:
    created_at: datetime
    updated_at: datetime

    def touch(self, at: datetime | None = None) -> Timestamps:
        novo = at or utcnow()
        if novo < self.updated_at:
            raise ValueError("updated_at nao pode retroceder")
        return Timestamps(created_at=self.created_at, updated_at=novo)


class ValueObject:
    """Marcador para value objects. Subclasses devem ser frozen dataclasses."""

    __slots__ = ()


__all__ = ["Timestamps", "ValueObject", "utcnow"]
