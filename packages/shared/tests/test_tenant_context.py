"""Testes do TenantContext (contextvars) — puros, sem DB."""
from __future__ import annotations

import pytest

from developer_brain_ai_shared.errors import ForbiddenError, UnauthorizedError
from developer_brain_ai_shared.persistence import (
    get_tenant_context,
    get_tenant_context_optional,
    reset_tenant_context,
    set_tenant_context,
)
from developer_brain_ai_shared.kernel import TenantId


def test_default_context_is_none() -> None:
    reset_tenant_context()
    assert get_tenant_context_optional() is None


def test_get_without_context_raises_unauthorized() -> None:
    reset_tenant_context()
    with pytest.raises(UnauthorizedError):
        get_tenant_context()


def test_set_and_get_roundtrip() -> None:
    tid = TenantId.new()
    set_tenant_context(tid)
    try:
        assert get_tenant_context() == tid
        assert get_tenant_context_optional() == tid
    finally:
        reset_tenant_context()


def test_reset_clears_context() -> None:
    set_tenant_context(TenantId.new())
    reset_tenant_context()
    assert get_tenant_context_optional() is None


def test_require_tenant_or_403_mismatch_raises() -> None:
    from developer_brain_ai_shared.persistence.tenant import require_tenant_or_403

    a, b = TenantId.new(), TenantId.new()
    set_tenant_context(a)
    try:
        with pytest.raises(ForbiddenError):
            require_tenant_or_403(b)
        assert require_tenant_or_403(a) == a
    finally:
        reset_tenant_context()