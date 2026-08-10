"""Fakes para content tests (sem DB)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from developer_brain_ai_ai.application.use_cases import LinkedInDraft
from developer_brain_ai_content.domain.aggregates import ContentDraft, PublicationQueueItem
from developer_brain_ai_content.domain.value_objects import ContentType, DraftStatus
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.pagination import PaginationParams


def _fresh_id() -> object:
    return uuid.uuid4()


class FakeContentDraftRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, ContentDraft] = {}
        self._by_tenant: dict[str, list[str]] = defaultdict(list)

    async def get_by_id(self, tenant_id: TenantId, draft_id: object) -> ContentDraft | None:
        d = self._by_id.get(str(draft_id))
        if d is None or d.tenant_id != tenant_id:
            return None
        return d

    async def list(
        self,
        tenant_id: TenantId,
        *,
        content_type: ContentType | None = None,
        status: DraftStatus | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[ContentDraft]:
        items = [self._by_id[i] for i in self._by_tenant.get(str(tenant_id), [])]
        if content_type:
            items = [d for d in items if d.content_type == content_type]
        if status:
            items = [d for d in items if d.status == status]
        pagination = pagination or PaginationParams()
        limit, offset = pagination.clamp()
        return items[offset : offset + limit]

    async def save(self, draft: ContentDraft) -> None:
        sid = str(draft.id)
        if sid not in self._by_id:
            self._by_tenant[str(draft.tenant_id)].append(sid)
        self._by_id[sid] = draft


class FakePublicationQueueRepository:
    def __init__(self) -> None:
        self._items: list[PublicationQueueItem] = []

    async def enqueue(self, item: PublicationQueueItem) -> None:
        self._items.append(item)

    async def dequeue_next(self, tenant_id: TenantId, now: datetime) -> PublicationQueueItem | None:
        for i in self._items:
            if i.tenant_id == tenant_id and i.published_at is None and i.scheduled_for <= now:
                return i
        return None

    async def save(self, item: PublicationQueueItem) -> None:
        self._items.append(item)

    async def list_pending(self, tenant_id: TenantId) -> list[PublicationQueueItem]:
        return [i for i in self._items if i.tenant_id == tenant_id and i.published_at is None]


class FakeLinkedInGenerator:
    """Fake do port LinkedInGenerator: devolve um LinkedInDraft fixo."""

    def __init__(self, draft: LinkedInDraft | None = None) -> None:
        self._draft = draft or LinkedInDraft(
            title="Post de teste",
            gancho="gancho",
            texto="# corpo do post",
            conclusao="conclusao",
            pergunta="pergunta",
            cta="cta",
            hashtags=["#FastAPI", "python"],
            source_entry_ids=["abc-1"],
        )
        self.calls: list[dict] = []

    async def execute(self, tenant_id, *, entries, ai_writing_tone="...", ai_language="..."):
        self.calls.append(
            {
                "tenant_id": tenant_id,
                "entries": entries,
                "tone": ai_writing_tone,
                "lang": ai_language,
            }
        )
        return self._draft


__all__ = [
    "FakeContentDraftRepository",
    "FakeLinkedInGenerator",
    "FakePublicationQueueRepository",
    "_fresh_id",
]
