"""Base de entidades e Aggregate Root.

- ``Entity``: identidade via ``id`` + comparacao por id (nao por valor).
- ``AggregateRoot``: raiz de agregado; emite domain events.

Regras:
- Entidades NUNCA importam SQLAlchemy, FastAPI ou OpenAI.
- Domain events sao dataclasses puras; o dispatcher fica em application/shared.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from developer_brain_ai_shared.events.base import DomainEvent
from developer_brain_ai_shared.kernel.id import TypedId


@dataclass(eq=False)
class Entity:
    """Entidade base. Comparacao por tipo + id."""

    id: TypedId

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and other.id == self.id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.id))


@dataclass(eq=False)
class AggregateRoot(Entity):
    """Raiz de agregado. Mantem eventos pendentes para publicacao no UoW."""

    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def record_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        eventos, self._events = self._events, []
        return eventos

    def clear_events(self) -> None:
        self._events.clear()

    @property
    def pending_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._events)


__all__ = ["AggregateRoot", "Entity"]
