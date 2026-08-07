"""Repositorio SQLAlchemy para JournalEntry (com suporte a tags + filtros + paginacao)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from developer_brain_ai_journal.domain.entry import JournalEntry
from developer_brain_ai_journal.domain.ids import JournalEntryId
from developer_brain_ai_journal.domain.repositories import JournalEntryRepository
from developer_brain_ai_journal.domain.value_objects import Tag
from developer_brain_ai_journal.infrastructure.mappers import entry_from_orm, entry_to_orm
from developer_brain_ai_journal.infrastructure.orm import (
    JournalEntryORM,
    JournalEntryTagORM,
    TagORM,
)
from developer_brain_ai_shared.errors.base import DomainError
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.pagination import PaginationParams


def _tags_for(entry_id) -> select:
    return (
        select(TagORM.value)
        .join(JournalEntryTagORM, JournalEntryTagORM.tag_id == TagORM.id)
        .where(JournalEntryTagORM.journal_entry_id == entry_id)
        .order_by(TagORM.value)
    )


class SqlAlchemyJournalEntryRepository(JournalEntryRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def _load_tags(self, s: AsyncSession, entry_id) -> list[str]:
        r = await s.execute(_tags_for(entry_id))
        return [t for (t,) in r.all()]

    async def _upsert_tags(self, s: AsyncSession, tenant_id, tags: list[Tag]) -> list:
        existing_q = select(TagORM).where(
            TagORM.tenant_id == tenant_id,
            TagORM.value.in_([str(t) for t in tags]),
        )
        existing = {t.value: t for t in (await s.execute(existing_q)).scalars().all()}
        out: list = []
        for tag in tags:
            v = str(tag)
            if v in existing:
                out.append(existing[v])
                continue
            new = TagORM(id=tenant_id, tenant_id=tenant_id, value=v)
            s.add(new)
            await s.flush()
            out.append(new)
        return out

    async def _sync_tags(self, s: AsyncSession, entry_id, tag_orms: list) -> None:
        await s.execute(
            delete(JournalEntryTagORM).where(JournalEntryTagORM.journal_entry_id == entry_id)
        )
        for t in tag_orms:
            s.add(JournalEntryTagORM(journal_entry_id=entry_id, tag_id=t.id))

    async def get_by_id(self, tenant_id: TenantId, entry_id: JournalEntryId) -> JournalEntry | None:
        async with self._factory() as s:
            o = await s.get(JournalEntryORM, entry_id.as_uuid())
            if o is None or o.tenant_id != tenant_id.as_uuid():
                return None
            tags = await self._load_tags(s, o.id)
            return entry_from_orm(o, tags)

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
        pagination = pagination or PaginationParams()
        from sqlalchemy import func

        async with self._factory() as s:
            stmt = select(JournalEntryORM).where(JournalEntryORM.tenant_id == tenant_id.as_uuid())
            if since:
                stmt = stmt.where(JournalEntryORM.entry_date >= since)
            elif until:
                stmt = stmt.where(JournalEntryORM.entry_date <= until)

            if tag:
                stmt = stmt.join(
                    JournalEntryTagORM,
                    JournalEntryTagORM.journal_entry_id == JournalEntryORM.id,
                ).join(TagORM, TagORM.id == JournalEntryTagORM.tag_id).where(TagORM.value == str(tag))

            if technology:
                stmt = stmt.where(JournalEntryORM.technologies.like(f'%"{technology}"%'))

            limit, offset = pagination.clamp()
            stmt = stmt.order_by(JournalEntryORM.entry_date.desc()).limit(limit).offset(offset)
            rows = (await s.execute(stmt)).scalars().all()

            results: list[JournalEntry] = []
            for o in rows:
                tags = await self._load_tags(s, o.id)
                results.append(entry_from_orm(o, tags))
            return results

    async def save(self, entry: JournalEntry) -> None:
        async with self._factory() as s:
            orm = entry_to_orm(entry)
            await s.merge(orm)
            await s.flush()
            tag_orms = await self._upsert_tags(s, entry.tenant_id.as_uuid(), entry.tags)
            await self._sync_tags(s, entry.id.as_uuid(), tag_orms)
            await s.commit()

    async def delete(self, tenant_id: TenantId, entry_id: JournalEntryId) -> bool:
        async with self._factory() as s:
            o = await s.get(JournalEntryORM, entry_id.as_uuid())
            if o is None or o.tenant_id != tenant_id.as_uuid():
                return False
            await s.delete(o)
            await s.commit()
            return True


__all__ = ["SqlAlchemyJournalEntryRepository"]