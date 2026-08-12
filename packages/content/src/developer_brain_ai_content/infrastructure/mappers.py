"""Mappers ORM <-> ContentDraft / PublicationQueueItem.

Pre-condicao: o repo SQLAlchemy garante que agregados novos ja possuem
``id`` UUID (gera e atribui antes de mapear), entao aqui so convertemos.
"""

from __future__ import annotations

import uuid

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps

from developer_brain_ai_content.domain.aggregates import ContentDraft, PublicationQueueItem
from developer_brain_ai_content.domain.ids import ContentDraftId, PublicationQueueItemId
from developer_brain_ai_content.domain.value_objects import ContentType, DraftStatus, Hashtag
from developer_brain_ai_content.infrastructure.orm import (
    ContentDraftORM,
    PublicationQueueItemORM,
)


def draft_to_orm(draft: ContentDraft) -> ContentDraftORM:
    return ContentDraftORM(
        id=draft.id if isinstance(draft.id, uuid.UUID) else uuid.UUID(str(draft.id)),
        tenant_id=draft.tenant_id.as_uuid(),
        agent=draft.agent,
        content_type=draft.content_type.value,
        title=draft.title,
        body_markdown=draft.body_markdown,
        hashtags=[h.value for h in draft.hashtags],
        metadata_json=dict(draft.metadata or {}),
        status=draft.status.value,
        created_at=draft.timestamps.created_at,
        updated_at=draft.timestamps.updated_at,
    )


def draft_from_orm(o: ContentDraftORM) -> ContentDraft:
    return ContentDraft(
        id=ContentDraftId.from_uuid(o.id),
        tenant_id=TenantId(o.tenant_id),
        agent=o.agent,
        content_type=ContentType(o.content_type),
        title=o.title,
        body_markdown=o.body_markdown,
        hashtags=[Hashtag(t) for t in (o.hashtags or [])],
        metadata=dict(o.metadata_json or {}),
        status=DraftStatus(o.status),
        timestamps=Timestamps(created_at=o.created_at, updated_at=o.updated_at),
    )


def queue_item_to_orm(item: PublicationQueueItem) -> PublicationQueueItemORM:
    return PublicationQueueItemORM(
        id=item.id if isinstance(item.id, uuid.UUID) else uuid.UUID(str(item.id)),
        tenant_id=item.tenant_id.as_uuid(),
        draft_id=(
            item.draft_id if isinstance(item.draft_id, uuid.UUID) else uuid.UUID(str(item.draft_id))
        ),
        scheduled_for=item.scheduled_for,
        queued_at=item.queued_at,
        published_at=item.published_at,
        created_at=item.timestamps.created_at,
        updated_at=item.timestamps.updated_at,
    )


def queue_item_from_orm(o: PublicationQueueItemORM) -> PublicationQueueItem:
    return PublicationQueueItem(
        id=PublicationQueueItemId.from_uuid(o.id),
        tenant_id=TenantId(o.tenant_id),
        draft_id=ContentDraftId.from_uuid(o.draft_id),
        scheduled_for=o.scheduled_for,
        queued_at=o.queued_at,
        published_at=o.published_at,
        timestamps=Timestamps(created_at=o.created_at, updated_at=o.updated_at),
    )


__all__ = [
    "draft_from_orm",
    "draft_to_orm",
    "queue_item_from_orm",
    "queue_item_to_orm",
]
