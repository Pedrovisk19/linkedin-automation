"""Repositorio SQLAlchemy do news (com dedupe por content_hash)."""

from __future__ import annotations

import uuid
from datetime import datetime

from developer_brain_ai_shared.kernel.id import TenantId
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from developer_brain_ai_news.domain.aggregates import NewsItem
from developer_brain_ai_news.infrastructure.mappers import item_from_orm
from developer_brain_ai_news.infrastructure.orm import NewsItemORM


def _ensure_id(item: NewsItem) -> None:
    if item.id is None:
        object.__setattr__(item, "id", uuid.uuid4())


class SqlAlchemyNewsItemRepository:
    """Repo com dedupe via ON CONFLICT (content_hash) por tenant.

    ``save`` retorna True se o item era novo (inseriu), False se ja existia
    (dedupe). Usa ``pg_insert(...).on_conflict_do_nothing(index_elements=...)``
    para race-free multi-worker.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def exists_by_hash(self, tenant_id: TenantId, content_hash: str) -> bool:
        stmt = (
            select(NewsItemORM.id)
            .where(
                NewsItemORM.tenant_id == tenant_id.as_uuid(),
                NewsItemORM.content_hash == content_hash,
            )
            .limit(1)
        )
        async with self._factory() as s:
            return (await s.execute(stmt)).first() is not None

    async def save(self, item: NewsItem) -> bool:
        _ensure_id(item)
        async with self._factory() as s:
            stmt = (
                pg_insert(NewsItemORM)
                .values(
                    id=item.id if isinstance(item.id, uuid.UUID) else uuid.UUID(str(item.id)),
                    tenant_id=item.tenant_id.as_uuid(),
                    source=item.source,
                    title=item.title,
                    url=item.url,
                    summary=item.summary,
                    published_at=item.published_at,
                    content_hash=item.content_hash,
                    created_at=item.timestamps.created_at,
                    updated_at=item.timestamps.updated_at,
                )
                .on_conflict_do_nothing(index_elements=["tenant_id", "content_hash"])
                .returning(NewsItemORM.id)
            )
            result = await s.execute(stmt)
            inserted = result.first() is not None
            await s.commit()
            return inserted

    async def list_since(
        self, tenant_id: TenantId, since: datetime, limit: int = 50
    ) -> list[NewsItem]:
        stmt = (
            select(NewsItemORM)
            .where(
                NewsItemORM.tenant_id == tenant_id.as_uuid(),
                NewsItemORM.published_at >= since,
            )
            .order_by(NewsItemORM.published_at.desc())
            .limit(limit)
        )
        async with self._factory() as s:
            rows = (await s.execute(stmt)).scalars().all()
            return [item_from_orm(o) for o in rows]


__all__ = ["SqlAlchemyNewsItemRepository"]
