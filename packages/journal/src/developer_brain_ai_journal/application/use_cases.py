"""Use cases do modulo journal.

- CreateJournalEntry
- GetJournalEntry
- ListJournalEntries (com filtros + paginacao)
- UpdateJournalEntry
- DeleteJournalEntry

Use cases sao agnosticos a infra. Recebem (TenantId, JournalEntryRepository, ...)
e opera atraves do protocol. TenantId extraido do CurrentUser (presentation).
"""

from __future__ import annotations

from datetime import date

from developer_brain_ai_shared.errors.base import NotFoundError, ValidationError
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow
from developer_brain_ai_shared.pagination import PaginationParams

from developer_brain_ai_journal.application.dto import (
    CreateJournalEntryInput,
    JournalEntryOut,
    UpdateJournalEntryInput,
)
from developer_brain_ai_journal.domain.entry import JournalEntry
from developer_brain_ai_journal.domain.ids import JournalEntryId
from developer_brain_ai_journal.domain.repositories import JournalEntryRepository
from developer_brain_ai_journal.domain.value_objects import EntryDate, StudyMinutes, Tag


def _to_out(entry: JournalEntry) -> JournalEntryOut:
    return JournalEntryOut(
        id=str(entry.id),
        title=entry.title,
        entry_date=entry.entry_date.as_date(),
        study_minutes=entry.study_minutes.as_int(),
        technologies=entry.technologies,
        project=entry.project,
        book=entry.book,
        course=entry.course,
        videos=entry.videos,
        links=[str(l) for l in entry.links],
        difficulties=entry.difficulties,
        learnings=entry.learnings,
        bugs_found=entry.bugs_found,
        resolutions=entry.resolutions,
        next_steps=entry.next_steps,
        notes=entry.notes,
        tags=[str(t) for t in entry.tags],
        created_at=entry.timestamps.created_at,
        updated_at=entry.timestamps.updated_at,
    )


def _parse_tags(raw: list[str]) -> list[Tag]:
    return [Tag(t) for t in raw]


class CreateJournalEntry:
    def __init__(self, repo: JournalEntryRepository) -> None:
        self._repo = repo

    async def execute(self, tenant_id: TenantId, data: CreateJournalEntryInput) -> JournalEntryOut:
        if len(data.bugs_found) != len(data.resolutions):
            raise ValidationError(
                "bugs_found e resolutions precisam ter mesmo tamanho",
                details={"bugs_found": len(data.bugs_found), "resolutions": len(data.resolutions)},
            )
        try:
            entry_date = EntryDate(data.entry_date)
            study_minutes = StudyMinutes(data.study_minutes)
            tags = _parse_tags(data.tags)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        now = utcnow()
        entry = JournalEntry.create(
            id=JournalEntryId.new(),
            tenant_id=tenant_id,
            title=data.title,
            entry_date=entry_date,
            study_minutes=study_minutes,
            timestamps=Timestamps(created_at=now, updated_at=now),
            technologies=data.technologies,
            project=data.project,
            book=data.book,
            course=data.course,
            videos=data.videos,
            links=[str(l) for l in data.links],
            difficulties=data.difficulties,
            learnings=data.learnings,
            bugs_found=data.bugs_found,
            resolutions=data.resolutions,
            next_steps=data.next_steps,
            notes=data.notes,
            tags=tags,
        )
        await self._repo.save(entry)
        return _to_out(entry)


class GetJournalEntry:
    def __init__(self, repo: JournalEntryRepository) -> None:
        self._repo = repo

    async def execute(self, tenant_id: TenantId, entry_id: str) -> JournalEntryOut:
        entry = await self._repo.get_by_id(tenant_id, JournalEntryId(entry_id))
        if entry is None:
            raise NotFoundError("journal entry nao encontrada", details={"id": entry_id})
        return _to_out(entry)


class ListJournalEntries:
    def __init__(self, repo: JournalEntryRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        tenant_id: TenantId,
        *,
        since: date | None = None,
        until: date | None = None,
        tag: str | None = None,
        technology: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[JournalEntryOut], int]:
        pagination = PaginationParams(limit=page_size, offset=(page - 1) * page_size)
        tag_vo = Tag(tag) if tag else None
        items = await self._repo.list(
            tenant_id,
            since=since,
            until=until,
            tag=tag_vo,
            technology=technology,
            pagination=pagination,
        )
        return [_to_out(e) for e in items], len(items)


class UpdateJournalEntry:
    def __init__(self, repo: JournalEntryRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        tenant_id: TenantId,
        entry_id: str,
        data: UpdateJournalEntryInput,
    ) -> JournalEntryOut:
        entry = await self._repo.get_by_id(tenant_id, JournalEntryId(entry_id))
        if entry is None:
            raise NotFoundError("journal entry nao encontrada", details={"id": entry_id})

        updates: dict = {}
        dirty = data.model_dump(exclude_unset=True)
        if "bugs_found" in dirty and "resolutions" in dirty:
            if len(dirty["bugs_found"]) != len(dirty["resolutions"]):
                raise ValidationError("bugs_found e resolutions precisam ter mesmo tamanho")
        elif ("bugs_found" in dirty) ^ ("resolutions" in dirty):
            raise ValidationError("bugs_found e resolutions devem vir juntos")

        for k, v in dirty.items():
            if v is None:
                continue
            if k == "entry_date":
                updates["entry_date"] = EntryDate(v)
            elif k == "study_minutes":
                updates["study_minutes"] = StudyMinutes(v)
            elif k == "links":
                updates["links"] = [str(l) for l in v]
            elif k == "tags":
                updates["tags"] = _parse_tags(v)
            else:
                updates[k] = v

        if updates:
            entry.update(**updates)
            await self._repo.save(entry)
        return _to_out(entry)


class DeleteJournalEntry:
    def __init__(self, repo: JournalEntryRepository) -> None:
        self._repo = repo

    async def execute(self, tenant_id: TenantId, entry_id: str) -> None:
        ok = await self._repo.delete(tenant_id, JournalEntryId(entry_id))
        if not ok:
            raise NotFoundError("journal entry nao encontrada", details={"id": entry_id})


__all__ = [
    "CreateJournalEntry",
    "DeleteJournalEntry",
    "GetJournalEntry",
    "ListJournalEntries",
    "UpdateJournalEntry",
]
