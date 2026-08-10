"""Domain events do modulo journal."""

from __future__ import annotations

from dataclasses import dataclass

from developer_brain_ai_shared.events.base import DomainEvent

from developer_brain_ai_journal.domain.ids import JournalEntryId


@dataclass(frozen=True)
class JournalEntryCreated(DomainEvent):
    journal_entry_id: JournalEntryId | None = None


@dataclass(frozen=True)
class JournalEntryUpdated(DomainEvent):
    journal_entry_id: JournalEntryId | None = None


@dataclass(frozen=True)
class JournalEntryDeleted(DomainEvent):
    journal_entry_id: JournalEntryId | None = None


__all__ = [
    "JournalEntryCreated",
    "JournalEntryDeleted",
    "JournalEntryUpdated",
]
