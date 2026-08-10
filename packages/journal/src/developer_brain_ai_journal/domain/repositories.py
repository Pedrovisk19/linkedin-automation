"""Repository interface (Port) do JournalEntry."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.pagination import PaginationParams

from developer_brain_ai_journal.domain.entry import JournalEntry
from developer_brain_ai_journal.domain.ids import JournalEntryId
from developer_brain_ai_journal.domain.value_objects import Tag


class JournalEntryRepository(Protocol):
    async def get_by_id(
        self, tenant_id: TenantId, entry_id: JournalEntryId
    ) -> JournalEntry | None: ...
    async def list(
        self,
        tenant_id: TenantId,
        *,
        since: date | None = None,
        until: date | None = None,
        tag: Tag | None = None,
        technology: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[JournalEntry]: ...
    async def save(self, entry: JournalEntry) -> None: ...
    async def delete(self, tenant_id: TenantId, entry_id: JournalEntryId) -> bool: ...


__all__ = ["JournalEntryRepository"]
