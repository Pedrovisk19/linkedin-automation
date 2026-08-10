"""Testes do RLS por transacao (listener de begin no EngineFactory)."""

from __future__ import annotations

from unittest.mock import MagicMock

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.persistence.session import _begin_handler, _bind_tenant_rls
from developer_brain_ai_shared.persistence.tenant import reset_tenant_context, set_tenant_context
from sqlalchemy import create_engine, event, text


def test_begin_handler_emits_set_local_when_context_present() -> None:
    tenant = TenantId.new()
    set_tenant_context(tenant)
    conn = MagicMock()
    try:
        _begin_handler()(conn)
    finally:
        reset_tenant_context()

    conn.execute.assert_called_once()
    args, _kwargs = conn.execute.call_args
    assert "set_config" in str(args[0])
    assert "app.tenant_id" in str(args[0])
    assert args[1]["tid"] == str(tenant.as_uuid())


def test_begin_handler_does_nothing_without_context() -> None:
    reset_tenant_context()
    conn = MagicMock()
    _begin_handler()(conn)
    conn.execute.assert_not_called()


def test_bind_tenant_rls_registers_handler_on_engine() -> None:
    engine = create_engine("sqlite://")
    fake_async = MagicMock()
    fake_async.sync_engine = engine
    handler = _begin_handler()
    _bind_tenant_rls(fake_async, handler)  # type: ignore[arg-type]

    try:
        # sem tenant context, uma conexao simples nao deve quebrar (nem emitir SET).
        reset_tenant_context()
        with engine.connect() as conn:
            conn.execute(text("select 1"))

        assert event.contains(engine, "begin", handler)
    finally:
        engine.dispose()
