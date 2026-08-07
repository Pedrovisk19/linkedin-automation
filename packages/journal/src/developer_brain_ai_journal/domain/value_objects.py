"""Value objects do modulo journal."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


@dataclass(frozen=True)
class Tag:
    value: str

    def __post_init__(self) -> None:
        v = self.value.strip().lower()
        if not _TAG_RE.match(v):
            raise ValueError(f"tag invalida: {self.value!r}")
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class StudyMinutes:
    """Tempo estudado em minutos. Nao negativo."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("study minutes nao pode ser negativo")
        if self.value > 24 * 60:
            raise ValueError("study minutes excede 24h por sessao")

    def as_int(self) -> int:
        return self.value


@dataclass(frozen=True)
class EntryDate:
    """Data do diario (date only). Nao futura."""

    value: date

    def __post_init__(self) -> None:
        from datetime import date as _date

        if self.value > _date.today():
            raise ValueError("entry_date nao pode ser futura")

    def as_date(self) -> date:
        return self.value


__all__ = ["Tag", "StudyMinutes", "EntryDate"]