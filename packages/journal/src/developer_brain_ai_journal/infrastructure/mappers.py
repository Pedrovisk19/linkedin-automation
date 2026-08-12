"""Mappers ORM <-> JournalEntry. Listas serializam como JSON em colunas TEXT."""

from __future__ import annotations

import json

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_journal.domain.entry import JournalEntry
from developer_brain_ai_journal.domain.ids import JournalEntryId
from developer_brain_ai_journal.domain.value_objects import EntryDate, StudyMinutes, Tag
from developer_brain_ai_journal.infrastructure.orm import JournalEntryORM


def _jdump(value: list[str]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _jload(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError, TypeError:
        return []
    assert isinstance(parsed, list)
    return [str(x) for x in parsed]


def entry_to_orm(entry: JournalEntry) -> JournalEntryORM:
    return JournalEntryORM(
        id=entry.id.as_uuid(),
        tenant_id=entry.tenant_id.as_uuid(),
        title=entry.title,
        entry_date=entry.entry_date.as_date(),
        study_minutes=entry.study_minutes.as_int(),
        technologies=_jdump(entry.technologies),
        project=entry.project,
        book=entry.book,
        course=entry.course,
        videos=_jdump(entry.videos),
        links=_jdump(entry.links),
        difficulties=entry.difficulties,
        learnings=entry.learnings,
        bugs_found=_jdump(entry.bugs_found),
        resolutions=_jdump(entry.resolutions),
        next_steps=entry.next_steps,
        notes=entry.notes,
        created_at=entry.timestamps.created_at,
        updated_at=entry.timestamps.updated_at,
    )


def entry_from_orm(o: JournalEntryORM, tag_values: list[str] | None = None) -> JournalEntry:
    tags = [Tag(t) for t in (tag_values or [])]
    return JournalEntry(
        id=JournalEntryId(o.id),
        tenant_id=TenantId(o.tenant_id),
        title=o.title,
        entry_date=EntryDate(o.entry_date),
        study_minutes=StudyMinutes(o.study_minutes),
        technologies=_jload(o.technologies),
        project=o.project,
        book=o.book,
        course=o.course,
        videos=_jload(o.videos),
        links=_jload(o.links),
        difficulties=o.difficulties,
        learnings=o.learnings,
        bugs_found=_jload(o.bugs_found),
        resolutions=_jload(o.resolutions),
        next_steps=o.next_steps,
        notes=o.notes,
        tags=tags,
        timestamps=Timestamps(created_at=o.created_at, updated_at=o.updated_at),
    )


__all__ = ["entry_from_orm", "entry_to_orm"]
