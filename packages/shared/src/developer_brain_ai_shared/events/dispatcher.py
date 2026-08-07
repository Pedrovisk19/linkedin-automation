"""Dispatcher de eventos de dominio (application layer hook).

Domain puro: nao conhece filas/HTTP. Apenas acumula handlers in-memory aqui p/
testes. Em producao o composition root registra um AsyncEventDispatcher que
publica em uma outbox (Fase 11).
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeAlias

from developer_brain_ai_shared.events.base import DomainEvent

EventHandler: TypeAlias = Callable[[DomainEvent], Awaitable[None] | None]


class EventDispatcher:
    """Registro síncrono de handlers — útil em testes e em process local."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        for h in handlers:
            res = h(event)
            if res is not None:
                await res

    def clear(self) -> None:
        self._handlers.clear()


__all__ = ["EventDispatcher", "EventHandler"]