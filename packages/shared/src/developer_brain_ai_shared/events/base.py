"""Domain events base.

Eventos sao dataclasses puras (sem side effects). Odispatcher (application layer)
coleta eventos dos AggregateRoots apos cada use_case e publica.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import utcnow


@dataclass(frozen=True)
class DomainEvent:
    """Evento de dominio imutavel. Carrega ocorreu_em e tenant p/ auditoria."""

    occurred_at: datetime = field(default_factory=utcnow)
    tenant_id: TenantId | None = None

    @property
    def event_type(self) -> str:
        return type(self).__name__


@dataclass(frozen=True)
class EventEnvelope:
    """Envelope seguro para transporte; payload serializavel."""

    event_type: str
    payload: dict[str, Any]
    occurred_at: datetime
    tenant_id: str | None


__all__ = ["DomainEvent", "EventEnvelope"]