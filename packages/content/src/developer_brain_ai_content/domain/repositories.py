"""Repository interfaces do content."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.pagination import PaginationParams

from developer_brain_ai_content.domain.aggregates import ContentDraft, PublicationQueueItem
from developer_brain_ai_content.domain.value_objects import ContentType, DraftStatus


class ContentDraftRepository(Protocol):
    async def get_by_id(self, tenant_id: TenantId, draft_id: object) -> ContentDraft | None: ...
    async def list(
        self,
        tenant_id: TenantId,
        *,
        content_type: ContentType | None = None,
        status: DraftStatus | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[ContentDraft]: ...
    async def save(self, draft: ContentDraft) -> None: ...


class PublicationQueueRepository(Protocol):
    async def enqueue(self, item: PublicationQueueItem) -> None: ...
    async def dequeue_next(
        self, tenant_id: TenantId, now: datetime
    ) -> PublicationQueueItem | None: ...
    async def save(self, item: PublicationQueueItem) -> None: ...
    async def list_pending(self, tenant_id: TenantId) -> list[PublicationQueueItem]: ...


__all__ = ["ContentDraftRepository", "PublicationQueueRepository"]
