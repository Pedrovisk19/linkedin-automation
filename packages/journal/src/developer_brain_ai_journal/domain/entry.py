"""Aggregate root JournalEntry.

Campos solicitados pelo brief:
- title, entry_date, study_minutes
- technologies (list[str]), project, book, course
- videos (list[str]), links (list[str])
- difficulties (Markdown str), learnings (Markdown str)
- bugs_found (list[str]), resolutions (list[str] paralelo)
- next_steps (Markdown str), notes (Markdown str)
- tags (list[Tag] deduped)

Invariantes:
- title nao vazio, max 200.
- resolutions.len == bugs_found.len — resolucao por bug; pode ser "" p/ nao-resolvidos.
- entry_date nao futura (validado por EntryDate).
- study_minutes >= 0 (validado por StudyMinutes).
- tags unicas (case-insensitive pos-normalizacao).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow

from developer_brain_ai_journal.domain.events import (
    JournalEntryCreated,
    JournalEntryDeleted,
    JournalEntryUpdated,
)
from developer_brain_ai_journal.domain.ids import JournalEntryId
from developer_brain_ai_journal.domain.value_objects import EntryDate, StudyMinutes, Tag


def _dedupe_tags(tags: list[Tag]) -> list[Tag]:
    seen: set[str] = set()
    out: list[Tag] = []
    for t in tags:
        v = str(t)
        if v in seen:
            continue
        seen.add(v)
        out.append(t)
    return out


@dataclass(eq=False)
class JournalEntry(AggregateRoot):
    id: JournalEntryId
    tenant_id: TenantId
    title: str
    entry_date: EntryDate
    study_minutes: StudyMinutes
    technologies: list[str] = field(default_factory=list)
    project: str = ""
    book: str = ""
    course: str = ""
    videos: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    difficulties: str = ""
    learnings: str = ""
    bugs_found: list[str] = field(default_factory=list)
    resolutions: list[str] = field(default_factory=list)
    next_steps: str = ""
    notes: str = ""
    tags: list[Tag] = field(default_factory=list)
    timestamps: Timestamps = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError("title nao pode ser vazio")
        if len(self.title) > 200:
            raise ValueError("title excede 200 caracteres")
        if self.timestamps is None:
            now = utcnow()
            object.__setattr__(self, "timestamps", Timestamps(created_at=now, updated_at=now))
        if len(self.bugs_found) != len(self.resolutions):
            raise ValueError("bugs_found e resolutions devem ter mesmo tamanho")
        for t in self.technologies:
            if not t or not t.strip():
                raise ValueError("tecnologia nao pode ser string vazia")
        for v in self.videos:
            if not v or not v.strip():
                raise ValueError("video nao pode ser string vazia")
        for link in self.links:
            if not link or not link.strip():
                raise ValueError("link nao pode ser string vazia")
        object.__setattr__(self, "tags", _dedupe_tags(self.tags))

    @classmethod
    def create(
        cls,
        *,
        id: JournalEntryId,
        tenant_id: TenantId,
        title: str,
        entry_date: EntryDate,
        study_minutes: StudyMinutes,
        timestamps: Timestamps,
        **fields: Any,
    ) -> JournalEntry:
        entry = cls(
            id=id,
            tenant_id=tenant_id,
            title=title,
            entry_date=entry_date,
            study_minutes=study_minutes,
            timestamps=timestamps,
            **fields,
        )
        entry.record_event(JournalEntryCreated(journal_entry_id=id))
        return entry

    def update(self, **fields: Any) -> None:
        if "title" in fields:
            v = fields["title"]
            if not v or not v.strip() or len(v) > 200:
                raise ValueError("title invalido")
        if "entry_date" in fields and not isinstance(fields["entry_date"], EntryDate):
            fields["entry_date"] = EntryDate(fields["entry_date"])
        if "study_minutes" in fields and not isinstance(fields["study_minutes"], StudyMinutes):
            fields["study_minutes"] = StudyMinutes(fields["study_minutes"])
        if "bugs_found" in fields and "resolutions" not in fields:
            raise ValueError("bugs_found e resolutions devem ser atualizados juntos")
        if "resolutions" in fields and "bugs_found" not in fields:
            raise ValueError("bugs_found e resolutions devem ser atualizados juntos")

        for k, v in fields.items():
            object.__setattr__(self, k, v)

        if (
            "bugs_found" in fields
            and "resolutions" in fields
            and len(self.bugs_found) != len(self.resolutions)
        ):
            raise ValueError("bugs_found e resolutions devem ter mesmo tamanho")
        if "tags" in fields:
            raw = fields["tags"]
            converted = [Tag(t) if isinstance(t, str) else t for t in raw]
            object.__setattr__(self, "tags", _dedupe_tags(converted))

        object.__setattr__(self, "timestamps", self.timestamps.touch(at=utcnow()))
        self.record_event(JournalEntryUpdated(journal_entry_id=self.id))

    def mark_deleted(self) -> None:
        self.record_event(JournalEntryDeleted(journal_entry_id=self.id))


__all__ = ["JournalEntry"]
