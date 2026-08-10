"""Testes dos mappers ORM <-> agregados do content."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from developer_brain_ai_content.domain.aggregates import ContentDraft, PublicationQueueItem
from developer_brain_ai_content.domain.value_objects import ContentType, DraftStatus, Hashtag
from developer_brain_ai_content.infrastructure.mappers import (
    draft_from_orm,
    draft_to_orm,
    queue_item_from_orm,
    queue_item_to_orm,
)
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow


def _draft() -> ContentDraft:
    now = utcnow()
    return ContentDraft(
        id=uuid.uuid4(),
        tenant_id=TenantId.new(),
        agent="linkedin",
        content_type=ContentType.LINKEDIN_POST,
        title="Post sobre DI",
        body_markdown="# DI is life",
        hashtags=[Hashtag("fastapi"), Hashtag("python")],
        metadata={"gancho": "pegador", "source_entry_ids": ["abc"]},
        status=DraftStatus.PENDING_REVIEW,
        timestamps=Timestamps(created_at=now, updated_at=now),
    )


def test_draft_roundtrip_preserves_all_fields() -> None:
    d = _draft()
    o = draft_to_orm(d)
    assert o.id == d.id
    assert o.tenant_id == d.tenant_id.as_uuid()
    assert o.content_type == "linkedin_post"
    assert o.hashtags == ["fastapi", "python"]
    assert o.metadata_json["gancho"] == "pegador"

    back = draft_from_orm(o)
    assert back.id == d.id
    assert back.title == d.title
    assert back.metadata["source_entry_ids"] == ["abc"]
    assert {h.value for h in back.hashtags} == {"fastapi", "python"}
    assert back.status == DraftStatus.PENDING_REVIEW


def test_draft_roundtrip_empty_lists() -> None:
    d = _draft()
    d = ContentDraft(
        id=d.id,
        tenant_id=d.tenant_id,
        agent=d.agent,
        content_type=d.content_type,
        title=d.title,
        body_markdown=d.body_markdown,
        timestamps=d.timestamps,
    )
    back = draft_from_orm(draft_to_orm(d))
    assert back.hashtags == []
    assert back.metadata == {}


def test_queue_item_roundtrip() -> None:
    now = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    item = PublicationQueueItem(
        id=uuid.uuid4(),
        tenant_id=TenantId.new(),
        draft_id=uuid.uuid4(),
        scheduled_for=now,
        queued_at=now,
        published_at=None,
        timestamps=Timestamps(created_at=now, updated_at=now),
    )
    o = queue_item_to_orm(item)
    assert o.scheduled_for == now
    back = queue_item_from_orm(o)
    assert back.id == item.id
    assert back.draft_id == item.draft_id
    assert back.published_at is None


def test_queue_item_roundtrip_with_published_at() -> None:
    now = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    published = datetime(2026, 8, 10, 12, 30, tzinfo=UTC)
    item = PublicationQueueItem(
        id=uuid.uuid4(),
        tenant_id=TenantId.new(),
        draft_id=uuid.uuid4(),
        scheduled_for=now,
        queued_at=now,
        published_at=published,
        timestamps=Timestamps(created_at=now, updated_at=now),
    )
    back = queue_item_from_orm(queue_item_to_orm(item))
    assert back.published_at == published
