"""Fakes reutilizaveis para os testes do journal (sem DB)."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from developer_brain_ai_journal.domain.entry import JournalEntry
from developer_brain_ai_journal.domain.ids import JournalEntryId
from developer_brain_ai_journal.domain.value_objects import Tag
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.pagination import PaginationParams


class FakeJournalEntryRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, JournalEntry] = {}
        self._by_tenant: dict[str, list[str]] = defaultdict(list)

    async def get_by_id(self, tenant_id: TenantId, entry_id: JournalEntryId) -> JournalEntry | None:
        e = self._by_id.get(str(entry_id))
        if e is None or e.tenant_id != tenant_id:
            return None
        return e

    async def list(
        self,
        tenant_id: TenantId,
        *,
        since: date | None = None,
        until: date | None = None,
        tag: Tag | None = None,
        technology: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[JournalEntry]:
        items = [self._by_id[i] for i in self._by_tenant.get(str(tenant_id), [])]
        if since:
            items = [e for e in items if e.entry_date.as_date() >= since]
        if until:
            items = [e for e in items if e.entry_date.as_date() <= until]
        if tag:
            tv = str(tag)
            items = [e for e in items if any(str(t) == tv for t in e.tags)]
        if technology:
            items = [e for e in items if technology in e.technologies]
        pagination = pagination or PaginationParams()
        limit, offset = pagination.clamp()
        return items[offset : offset + limit]

    async def save(self, entry: JournalEntry) -> None:
        self._by_id[str(entry.id)] = entry
        if str(entry.id) not in self._by_tenant[str(entry.tenant_id)]:
            self._by_tenant[str(entry.tenant_id)].append(str(entry.id))

    async def delete(self, tenant_id: TenantId, entry_id: JournalEntryId) -> bool:
        e = self._by_id.pop(str(entry_id), None)
        if e is None or e.tenant_id != tenant_id:
            return False
        self._by_tenant[str(tenant_id)] = [
            i for i in self._by_tenant[str(tenant_id)] if i != str(entry_id)
        ]
        return True


__all__ = ["FakeJournalEntryRepository"]