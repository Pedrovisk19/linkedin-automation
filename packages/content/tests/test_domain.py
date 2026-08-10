"""Testes do dominio do content."""

from __future__ import annotations

import pytest
from developer_brain_ai_content.domain.aggregates import ContentDraft
from developer_brain_ai_content.domain.value_objects import ContentType, DraftStatus, Hashtag
from developer_brain_ai_shared.errors.base import ValidationError
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow


def test_hashtag_normalizes_and_strips_leading_hash() -> None:
    h = Hashtag("#PyConBR")
    assert h.value == "pyconbr"
    assert h.display() == "#pyconbr"


def test_hashtag_rejects_invalid() -> None:
    for bad in ["", "9abc", "with space", "_" + "a" * 60, "#hashtag with"]:
        with pytest.raises(ValueError):
            Hashtag(bad)


def test_content_type_enum_values() -> None:
    assert ContentType.LINKEDIN_POST.value == "linkedin_post"
    assert ContentType.NEWSLETTER.value == "newsletter"
    assert ContentType.README.value == "readme"


def _mk_draft(**overrides) -> ContentDraft:
    now = utcnow()
    base = dict(
        id=object(),
        tenant_id=TenantId.new(),
        agent="linkedin",
        content_type=ContentType.LINKEDIN_POST,
        title="Post sobre DI",
        body_markdown="# DI is life",
        hashtags=[Hashtag("fastapi")],
        metadata={"gancho": "pegador"},
        status=DraftStatus.PENDING_REVIEW,
        timestamps=Timestamps(created_at=now, updated_at=now),
    )
    base.update(overrides)
    return ContentDraft(**base)


def test_draft_rejects_empty_title() -> None:
    with pytest.raises(ValueError):
        _mk_draft(title="   ")


def test_draft_rejects_title_too_long() -> None:
    with pytest.raises(ValueError):
        _mk_draft(title="x" * 201)


def test_draft_rejects_empty_body() -> None:
    with pytest.raises(ValueError):
        _mk_draft(body_markdown="")


def test_draft_rejects_body_too_long() -> None:
    with pytest.raises(ValueError):
        _mk_draft(body_markdown="y" * 20001)


def test_draft_rejects_wrong_content_type() -> None:
    with pytest.raises(TypeError):
        _mk_draft(content_type="linkedin_post")  # type: ignore[arg-type]


def test_draft_dedupes_hashtags_case_insensitive() -> None:
    d = _mk_draft(hashtags=[Hashtag("FastAPI"), Hashtag("fastapi"), Hashtag("pydantic")])
    assert {h.value for h in d.hashtags} == {"fastapi", "pydantic"}


def test_draft_default_timestamps_set_if_missing() -> None:
    d = ContentDraft(
        id=object(),
        tenant_id=TenantId.new(),
        agent="linkedin",
        content_type=ContentType.LINKEDIN_POST,
        title="x",
        body_markdown="y",
    )
    assert d.timestamps is not None


def test_queue_for_publication_transition() -> None:
    d = _mk_draft()
    d.queue_for_publication()
    assert d.status == DraftStatus.QUEUED


def test_queue_for_publication_rejects_if_already_queued() -> None:
    d = _mk_draft()
    d.queue_for_publication()
    with pytest.raises(ValidationError):
        d.queue_for_publication()


def test_mark_published_requires_queued_first() -> None:
    d = _mk_draft()
    with pytest.raises(ValidationError):
        d.mark_published()

    d.queue_for_publication()
    d.mark_published()
    assert d.status == DraftStatus.PUBLISHED


def test_mark_rejected_blocks_when_published() -> None:
    d = _mk_draft()
    d.queue_for_publication()
    d.mark_published()
    with pytest.raises(ValidationError):
        d.mark_rejected()


def test_mark_rejected_from_pending_review_ok() -> None:
    d = _mk_draft()
    d.mark_rejected("nao curti o hook")
    assert d.status == DraftStatus.REJECTED
