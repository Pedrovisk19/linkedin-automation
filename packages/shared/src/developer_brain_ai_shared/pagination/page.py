"""Paginacao generica (offset/limit) + Page[T].

Evita reimplementar em cada modulo. Para cursor pagination futura: nova classe
``CursorPage`` (YAGNI ate必要时).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    def clamp(self) -> tuple[int, int]:
        return self.limit, self.offset


class Page(BaseModel, Generic[T]):
    """Pagina generica. ``total``eh o total absoluto (antes do limit/offset)."""

    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_next(self) -> bool:
        return self.offset + len(self.items) < self.total

    @property
    def has_prev(self) -> bool:
        return self.offset > 0


@dataclass(frozen=True)
class PageMeta:
    total: int
    limit: int
    offset: int


__all__ = ["Page", "PageMeta", "PaginationParams"]
