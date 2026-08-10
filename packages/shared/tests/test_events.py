"""Testes do EventDispatcher (sincrono + async handlers)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from developer_brain_ai_shared.events import DomainEvent, EventDispatcher


@dataclass(frozen=True)
class FooDone(DomainEvent):
    pass


@dataclass(frozen=True)
class BarDone(DomainEvent):
    pass


def _mark(value: str) -> dict[str, str]:
    return {"received": value}


@pytest.mark.asyncio
async def test_sync_handler_invoked() -> None:
    disp = EventDispatcher()
    received: dict[str, str] = {}
    disp.subscribe(FooDone, lambda ev: received.update({"called": "yes"}))
    await disp.publish(FooDone())
    assert received == {"called": "yes"}


@pytest.mark.asyncio
async def test_async_handler_awaited() -> None:
    disp = EventDispatcher()
    received: list[str] = []

    async def handler(ev: DomainEvent) -> None:
        received.append("async")

    disp.subscribe(FooDone, handler)
    await disp.publish(FooDone())
    assert received == ["async"]


@pytest.mark.asyncio
async def test_multiple_handlers_called_in_order() -> None:
    disp = EventDispatcher()
    order: list[int] = []
    disp.subscribe(FooDone, lambda ev: order.append(1))
    disp.subscribe(FooDone, lambda ev: order.append(2))
    await disp.publish(FooDone())
    assert order == [1, 2]


@pytest.mark.asyncio
async def test_unsubscribed_event_type_no_handler_does_not_error() -> None:
    disp = EventDispatcher()
    await disp.publish(BarDone())


@pytest.mark.asyncio
async def test_clear_wipes_registry() -> None:
    disp = EventDispatcher()
    called: list[int] = []
    disp.subscribe(FooDone, lambda ev: called.append(1))
    disp.clear()
    await disp.publish(FooDone())
    assert called == []
