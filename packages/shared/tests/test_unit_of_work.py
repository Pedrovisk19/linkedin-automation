"""Testes do UnitOfWork com AsyncSession mockada (sem Postgres real).

Cobre:
- sem TenantContext -> RuntimeError (defesa em profundidade).
- com TenantContext -> SET LOCAL app.tenant_id emitido.
- __aexit__ com exc=None commit; com exc rollback.
- commit_and_publish coleta eventos dos aggregates.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from developer_brain_ai_shared.events import EventDispatcher
from developer_brain_ai_shared.kernel import AggregateRoot, TenantId
from developer_brain_ai_shared.kernel.id import UserId
from developer_brain_ai_shared.events.base import DomainEvent
from developer_brain_ai_shared.persistence import (
    set_tenant_context,
    reset_tenant_context,
)
from developer_brain_ai_shared.persistence.session import UnitOfWork


def _make_session_mock() -> MagicMock:
    s = MagicMock()
    s.execute = AsyncMock()
    s.commit = AsyncMock()
    s.rollback = AsyncMock()
    s.close = AsyncMock()
    return s


def test_uow_without_tenant_raises_runtime_error() -> None:
    factory = MagicMock()
    factory.return_value = _make_session_mock()
    uow = UnitOfWork(factory, EventDispatcher())  # type: ignore[arg-type]

    async def run() -> None:
        async with uow:
            pass

    with pytest.raises(RuntimeError):
        asyncio.run(run())


def test_uow_emits_set_local_tenant_id() -> None:
    session = _make_session_mock()
    factory = MagicMock(return_value=session)
    tenant = TenantId.new()
    set_tenant_context(tenant)

    uow = UnitOfWork(factory, EventDispatcher())  # type: ignore[arg-type]

    async def run() -> None:
        async with uow:
            pass

    try:
        asyncio.run(run())
    finally:
        reset_tenant_context()

    session.execute.assert_awaited_once()
    args, kwargs = session.execute.call_args
    assert "SET LOCAL app.tenant_id" in str(args[0])
    assert args[1]["tid"] == str(tenant.as_uuid())


def test_uow_with_explicit_tenant_overrides_context_var() -> None:
    session = _make_session_mock()
    factory = MagicMock(return_value=session)
    tenant = TenantId.new()

    uow = UnitOfWork(factory, EventDispatcher(), tenant_id=tenant)  # type: ignore[arg-type]

    async def run() -> None:
        async with uow:
            pass

    asyncio.run(run())

    _, kwargs = session.execute.call_args
    args_pos, _ = session.execute.call_args
    assert args_pos[1]["tid"] == str(tenant.as_uuid())


def test_uow_commits_on_no_exception() -> None:
    session = _make_session_mock()
    factory = MagicMock(return_value=session)
    set_tenant_context(TenantId.new())

    uow = UnitOfWork(factory, EventDispatcher())  # type: ignore[arg-type]

    async def run() -> None:
        async with uow:
            pass

    try:
        asyncio.run(run())
    finally:
        reset_tenant_context()

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


def test_uow_rolls_back_on_exception() -> None:
    session = _make_session_mock()
    factory = MagicMock(return_value=session)
    set_tenant_context(TenantId.new())

    uow = UnitOfWork(factory, EventDispatcher())  # type: ignore[arg-type]

    async def run() -> None:
        async with uow:
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(run())
    reset_tenant_context()

    assert session.rollback.await_count == 1
    session.commit.assert_not_awaited()


def test_uow_commit_and_publish_collects_events() -> None:
    session = _make_session_mock()
    factory = MagicMock(return_value=session)
    disp = EventDispatcher()
    received: list[str] = []
    from dataclasses import dataclass as dc

    @dc(frozen=True)
    class EvX(DomainEvent):
        pass

    @dataclass(eq=False)
    class Agg(AggregateRoot):
        pass

    a = Agg(id=UserId.new())
    a.record_event(EvX())
    disp.subscribe(EvX, lambda ev: received.append(ev.event_type))

    uow = UnitOfWork(factory, disp)  # type: ignore[arg-type]
    uow.session = session

    async def run() -> None:
        return await uow.commit_and_publish([a])

    count = asyncio.run(run())
    assert count == 1
    assert received == ["EvX"]
    session.commit.assert_awaited_once()


def test_uow_commit_and_publish_without_session_raises() -> None:
    disp = EventDispatcher()
    uow = UnitOfWork(MagicMock(), disp)  # type: ignore[arg-type]
    uow.session = None

    async def run() -> None:
        await uow.commit_and_publish([])

    with pytest.raises(RuntimeError):
        asyncio.run(run())


def test_uow_close_after_exit_clears_session() -> None:
    session = _make_session_mock()
    factory = MagicMock(return_value=session)
    set_tenant_context(TenantId.new())
    uow = UnitOfWork(factory, EventDispatcher())  # type: ignore[arg-type]

    async def run() -> None:
        async with uow:
            pass

    try:
        asyncio.run(run())
    finally:
        reset_tenant_context()

    session.close.assert_awaited_once()
    assert uow.session is None