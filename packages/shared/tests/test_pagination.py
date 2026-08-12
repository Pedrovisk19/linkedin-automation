"""Testes de pagination: PaginationParams + Page[T]."""

from __future__ import annotations

import pytest
from developer_brain_ai_shared.pagination import Page, PaginationParams
from pydantic import ValidationError


def test_pagination_params_defaults() -> None:
    p = PaginationParams()
    assert p.limit == 20
    assert p.offset == 0


def test_pagination_params_clamp() -> None:
    p = PaginationParams(limit=50, offset=100)
    assert p.clamp() == (50, 100)


def test_pagination_params_rejects_negative_offset() -> None:
    with pytest.raises(ValidationError):
        PaginationParams(offset=-1)


def test_pagination_params_rejects_zero_limit() -> None:
    with pytest.raises(ValidationError):
        PaginationParams(limit=0)


def test_page_has_next_and_has_prev() -> None:
    page = Page[int](items=[1, 2, 3], total=10, limit=3, offset=0)
    assert page.has_next
    assert not page.has_prev


def test_page_last_no_next() -> None:
    page = Page[int](items=[10], total=10, limit=3, offset=9)
    assert not page.has_next
    assert page.has_prev
