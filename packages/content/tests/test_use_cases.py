"""Testes dos use cases do content com fake repos."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from content_fakes import (
    FakeContentDraftRepository,
    FakeLinkedInGenerator,
    FakePublicationQueueRepository,
)
from developer_brain_ai_content.application.dto import (
    CreateLinkedInDraftInput,
    GenerateLinkedInInput,
)
from developer_brain_ai_content.application.use_cases import (
    CreateLinkedInDraft,
    EnqueueDraft,
    GenerateLinkedInDraft,
    GetDraft,
    ListDrafts,
    MarkPublished,
    RejectDraft,
)
from developer_brain_ai_shared.errors.base import NotFoundError, ValidationError
from developer_brain_ai_shared.kernel.id import TenantId


def _create() -> tuple[
    FakeContentDraftRepository, FakePublicationQueueRepository, CreateLinkedInDraft
]:
    drafts = FakeContentDraftRepository()
    queue = FakePublicationQueueRepository()
    uc = CreateLinkedInDraft(drafts)
    return drafts, queue, uc


def test_create_linkedin_returns_dto_with_metadata_fields() -> None:
    drafts, _, uc = _create()
    out = asyncio.run(
        uc.execute(
            TenantId.new(),
            CreateLinkedInDraftInput(
                title="DI é vida",
                gancho="Você já usou DI no FastAPI?",
                texto="hoje aprendi...",
                conclusao="mudou tudo",
                pergunta="qual seu pattern favorito?",
                cta="comenta ae",
                hashtags=["#FastAPI", "Python", "di"],
            ),
        )
    )
    assert out.title == "DI é vida"
    assert out.gancho.startswith("Você já")
    assert "#di" in out.hashtags
    assert out.status == "pending_review"


def test_create_rejects_invalid_hashtag_with_422() -> None:
    _, _, uc = _create()
    with pytest.raises(ValidationError):
        asyncio.run(
            uc.execute(
                TenantId.new(),
                CreateLinkedInDraftInput(
                    title="x",
                    texto="y",
                    hashtags=["#1invalid"],
                ),
            )
        )


def test_list_filters_by_content_type_and_status() -> None:
    drafts, _, create_uc = _create()
    tid = TenantId.new()
    asyncio.run(create_uc.execute(tid, CreateLinkedInDraftInput(title="x", texto="y")))
    items = asyncio.run(ListDrafts(drafts).execute(tid, content_type="linkedin_post"))
    assert len(items) == 1
    items_pending = asyncio.run(ListDrafts(drafts).execute(tid, status="pending_review"))
    assert len(items_pending) == 1


def test_list_paginates() -> None:
    drafts, _, create_uc = _create()
    tid = TenantId.new()
    for _ in range(5):
        asyncio.run(create_uc.execute(tid, CreateLinkedInDraftInput(title="x", texto="y")))
    p1 = asyncio.run(ListDrafts(drafts).execute(tid, page=1, page_size=2))
    p2 = asyncio.run(ListDrafts(drafts).execute(tid, page=2, page_size=2))
    assert len(p1) == 2
    assert len(p2) == 2
    assert {x.id for x in p1}.isdisjoint({x.id for x in p2})


def test_get_unknown_raises_not_found() -> None:
    drafts = FakeContentDraftRepository()
    with pytest.raises(NotFoundError):
        asyncio.run(GetDraft(drafts).execute(TenantId.new(), "abc"))


def test_get_returns_full_dto() -> None:
    drafts, _, create_uc = _create()
    tid = TenantId.new()
    out = asyncio.run(create_uc.execute(tid, CreateLinkedInDraftInput(title="X", texto="Y")))
    got = asyncio.run(GetDraft(drafts).execute(tid, out.draft_id))
    assert got.title == "X"
    assert got.texto == "Y"


def test_enqueue_marks_queued_and_creates_queue_item() -> None:
    drafts, queue, create_uc = _create()
    tid = TenantId.new()
    out = asyncio.run(create_uc.execute(tid, CreateLinkedInDraftInput(title="x", texto="y")))
    scheduled = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
    asyncio.run(EnqueueDraft(drafts, queue).execute(tid, out.draft_id, scheduled_for=scheduled))
    items = asyncio.run(queue.list_pending(tid))
    assert len(items) == 1
    assert items[0].scheduled_for == scheduled

    d = asyncio.run(drafts.get_by_id(tid, out.draft_id))
    assert d.status.value == "queued"


def test_enqueue_unknown_raises_not_found() -> None:
    drafts = FakeContentDraftRepository()
    queue = FakePublicationQueueRepository()
    with pytest.raises(NotFoundError):
        asyncio.run(EnqueueDraft(drafts, queue).execute(TenantId.new(), "abc"))


def test_publish_requires_queued() -> None:
    drafts, queue, create_uc = _create()
    tid = TenantId.new()
    out = asyncio.run(create_uc.execute(tid, CreateLinkedInDraftInput(title="x", texto="y")))
    with pytest.raises(ValidationError):
        asyncio.run(MarkPublished(drafts, queue).execute(tid, out.draft_id))


def test_publish_marks_draft_published() -> None:
    drafts, queue, create_uc = _create()
    tid = TenantId.new()
    out = asyncio.run(create_uc.execute(tid, CreateLinkedInDraftInput(title="x", texto="y")))
    asyncio.run(EnqueueDraft(drafts, queue).execute(tid, out.draft_id))
    asyncio.run(MarkPublished(drafts, queue).execute(tid, out.draft_id))
    d = asyncio.run(drafts.get_by_id(tid, out.draft_id))
    assert d.status.value == "published"


def test_reject_marks_rejected() -> None:
    drafts, _, create_uc = _create()
    tid = TenantId.new()
    out = asyncio.run(create_uc.execute(tid, CreateLinkedInDraftInput(title="x", texto="y")))
    asyncio.run(RejectDraft(drafts).execute(tid, out.draft_id, "nao aprovado"))
    d = asyncio.run(drafts.get_by_id(tid, out.draft_id))
    assert d.status.value == "rejected"


def test_isolation_between_tenants() -> None:
    drafts, _, create_uc = _create()
    t1, t2 = TenantId.new(), TenantId.new()
    out1 = asyncio.run(create_uc.execute(t1, CreateLinkedInDraftInput(title="x", texto="y")))
    with pytest.raises(NotFoundError):
        asyncio.run(GetDraft(drafts).execute(t2, out1.draft_id))


def test_generate_linkedin_persists_draft_from_agent() -> None:
    drafts = FakeContentDraftRepository()
    generator = FakeLinkedInGenerator()
    uc = GenerateLinkedInDraft(drafts, generator)
    tid = TenantId.new()
    out = asyncio.run(
        uc.execute(
            tid,
            GenerateLinkedInInput(
                entries=[{"id": "abc-1", "title": "Estudei X"}],
                ai_writing_tone="dev-evolutiva",
                ai_language="pt-BR",
            ),
        )
    )
    assert out.title == "Post de teste"
    assert "#fastapi" in out.hashtags
    assert out.status == "pending_review"
    assert out.gancho == "gancho"
    assert len(generator.calls) == 1
    assert generator.calls[0]["tone"] == "dev-evolutiva"
    assert generator.calls[0]["lang"] == "pt-BR"

    d = asyncio.run(drafts.get_by_id(tid, out.draft_id))
    assert d is not None
    assert d.metadata["source_entry_ids"] == ["abc-1"]


def test_generate_linkedin_without_source_entries_allowed() -> None:
    drafts = FakeContentDraftRepository()
    uc = GenerateLinkedInDraft(drafts, FakeLinkedInGenerator())
    out = asyncio.run(uc.execute(TenantId.new(), GenerateLinkedInInput(entries=[])))
    assert out.title == "Post de teste"
