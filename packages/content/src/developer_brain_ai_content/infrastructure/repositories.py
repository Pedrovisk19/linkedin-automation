"""Repositorios SQLAlchemy do content (drafts + fila de publicacao)."""

from __future__ import annotations

import uuid
from datetime import datetime

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.pagination import PaginationParams
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from developer_brain_ai_content.domain.aggregates import ContentDraft, PublicationQueueItem
from developer_brain_ai_content.domain.repositories import (
    ContentDraftRepository,
    PublicationQueueRepository,
)
from developer_brain_ai_content.domain.value_objects import ContentType, DraftStatus
from developer_brain_ai_content.infrastructure.mappers import (
    draft_from_orm,
    draft_to_orm,
    queue_item_from_orm,
    queue_item_to_orm,
)
from developer_brain_ai_content.infrastructure.orm import (
    ContentDraftORM,
    PublicationQueueItemORM,
)


def _ensure_id(aggregate: ContentDraft | PublicationQueueItem) -> None:
    if aggregate.id is None:
        object.__setattr__(aggregate, "id", uuid.uuid4())


class SqlAlchemyContentDraftRepository(ContentDraftRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def get_by_id(self, tenant_id: TenantId, draft_id: object) -> ContentDraft | None:
        try:
            draft_uuid = uuid.UUID(str(draft_id))
        except ValueError, TypeError:
            return None
        async with self._factory() as s:
            o = await s.get(ContentDraftORM, draft_uuid)
            if o is None or o.tenant_id != tenant_id.as_uuid():
                return None
            return draft_from_orm(o)

    async def list(
        self,
        tenant_id: TenantId,
        *,
        content_type: ContentType | None = None,
        status: DraftStatus | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[ContentDraft]:
        pagination = pagination or PaginationParams()
        stmt = select(ContentDraftORM).where(ContentDraftORM.tenant_id == tenant_id.as_uuid())
        if content_type:
            stmt = stmt.where(ContentDraftORM.content_type == content_type.value)
        if status:
            stmt = stmt.where(ContentDraftORM.status == status.value)
        limit, offset = pagination.clamp()
        stmt = stmt.order_by(ContentDraftORM.created_at.desc()).limit(limit).offset(offset)
        async with self._factory() as s:
            rows = (await s.execute(stmt)).scalars().all()
            return [draft_from_orm(o) for o in rows]

    async def save(self, draft: ContentDraft) -> None:
        _ensure_id(draft)
        async with self._factory() as s:
            await s.merge(draft_to_orm(draft))
            await s.commit()


class SqlAlchemyPublicationQueueRepository(PublicationQueueRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def enqueue(self, item: PublicationQueueItem) -> None:
        await self.save(item)

    async def dequeue_next(self, tenant_id: TenantId, now: datetime) -> PublicationQueueItem | None:
        stmt = (
            select(PublicationQueueItemORM)
            .where(
                PublicationQueueItemORM.tenant_id == tenant_id.as_uuid(),
                PublicationQueueItemORM.scheduled_for <= now,
                PublicationQueueItemORM.published_at.is_(None),
            )
            .order_by(PublicationQueueItemORM.scheduled_for)
            .limit(1)
        )
        async with self._factory() as s:
            o = (await s.execute(stmt)).scalar_one_or_none()
            return queue_item_from_orm(o) if o is not None else None

    async def save(self, item: PublicationQueueItem) -> None:
        _ensure_id(item)
        async with self._factory() as s:
            await s.merge(queue_item_to_orm(item))
            await s.commit()

    async def list_pending(self, tenant_id: TenantId) -> list[PublicationQueueItem]:
        stmt = (
            select(PublicationQueueItemORM)
            .where(
                PublicationQueueItemORM.tenant_id == tenant_id.as_uuid(),
                PublicationQueueItemORM.published_at.is_(None),
            )
            .order_by(PublicationQueueItemORM.scheduled_for)
        )
        async with self._factory() as s:
            rows = (await s.execute(stmt)).scalars().all()
            return [queue_item_from_orm(o) for o in rows]


__all__ = [
    "SqlAlchemyContentDraftRepository",
    "SqlAlchemyPublicationQueueRepository",
]
