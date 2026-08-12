"""Repository interface do news."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from developer_brain_ai_shared.kernel.id import TenantId

from developer_brain_ai_news.domain.aggregates import NewsItem


class NewsItemRepository(Protocol):
    async def exists_by_hash(self, tenant_id: TenantId, content_hash: str) -> bool: ...
    async def save(self, item: NewsItem) -> bool: ...

    async def list_since(
        self, tenant_id: TenantId, since: datetime, limit: int = 50
    ) -> list[NewsItem]: ...


__all__ = ["NewsItemRepository"]
