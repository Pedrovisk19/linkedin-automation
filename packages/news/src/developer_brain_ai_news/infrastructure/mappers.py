"""Mappers ORM <-> NewsItem."""

from __future__ import annotations

import uuid

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_news.domain.aggregates import NewsItem
from developer_brain_ai_news.domain.ids import NewsItemId
from developer_brain_ai_news.infrastructure.orm import NewsItemORM


def item_to_orm(item: NewsItem) -> NewsItemORM:
    return NewsItemORM(
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


def item_from_orm(o: NewsItemORM) -> NewsItem:
    return NewsItem(
        id=NewsItemId.from_uuid(o.id),
        tenant_id=TenantId(o.tenant_id),
        source=o.source,
        title=o.title,
        url=o.url,
        summary=o.summary,
        published_at=o.published_at,
        content_hash=o.content_hash,
        timestamps=Timestamps(created_at=o.created_at, updated_at=o.updated_at),
    )


__all__ = ["item_from_orm", "item_to_orm"]
