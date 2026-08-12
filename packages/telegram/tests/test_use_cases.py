"""Testes dos use cases do telegram com fakes."""

from __future__ import annotations

import asyncio

import pytest
from content_fakes import (
    FakeContentDraftRepository,
    FakeLinkedInGenerator,
    FakePublicationQueueRepository,
)
from developer_brain_ai_content.application.use_cases import (
    CreateLinkedInDraft,
    EnqueueDraft,
    GenerateLinkedInDraft,
    MarkPublished,
    RejectDraft,
)
from developer_brain_ai_shared.errors.base import DomainError, ValidationError
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_telegram.application.use_cases import (
    HandleApprovalReply,
    HandleInboundMessage,
)
from developer_brain_ai_telegram.domain.value_objects import ChatId, RequestStatus
from telegram_fakes import (
    FakeDownloader,
    FakeJournalRepository,
    FakeMessenger,
    FakeTelegramRequestRepository,
    FakeTranscriber,
)

CHAT = ChatId(123456789)


def _inbound_uc(**overrides) -> tuple[HandleInboundMessage, FakeMessenger]:
    messenger = FakeMessenger()
    args = {
        "messenger": messenger,
        "journal_repo": FakeJournalRepository(),
        "requests": FakeTelegramRequestRepository(),
        "create_draft": CreateLinkedInDraft(FakeContentDraftRepository()),
        "generate_draft": None,
    }
    args.update(overrides)
    return HandleInboundMessage(**args), messenger


def test_inbound_text_creates_journal_draft_and_approval_message() -> None:
    uc, messenger = _inbound_uc()
    tid = TenantId.new()

    request = asyncio.run(
        uc.execute(
            tenant_id=tid,
            chat_id=CHAT,
            text="hoje aprendi sobre typed id no python",
            audio_media_id=None,
        )
    )

    assert request.status is RequestStatus.PENDING
    assert request.chat_id == CHAT
    assert request.draft_id
    approval = messenger.sent[-1]
    assert approval.kind == "approval"
    assert approval.to == CHAT.value
    assert str(request.id) in [str(m.request_id) for m in messenger.sent]


def test_inbound_empty_message_rejected() -> None:
    uc, _ = _inbound_uc()
    with pytest.raises(ValidationError) as exc:
        asyncio.run(
            uc.execute(
                tenant_id=TenantId.new(),
                chat_id=CHAT,
                text="   ",
                audio_media_id=None,
            )
        )
    assert "vazia" in str(exc.value.message)


def test_inbound_audio_without_transcriber_rejected() -> None:
    uc, _ = _inbound_uc()
    with pytest.raises(ValidationError) as exc:
        asyncio.run(
            uc.execute(
                tenant_id=TenantId.new(),
                chat_id=CHAT,
                text=None,
                audio_media_id="file-123",
            )
        )
    assert "transcricao de audio nao configurada" in str(exc.value.message)


def test_inbound_audio_transcribed_and_persisted() -> None:
    transcriber = FakeTranscriber()
    downloader = FakeDownloader()
    journal = FakeJournalRepository()
    uc, messenger = _inbound_uc(
        transcriber=transcriber,
        downloader=downloader,
        journal_repo=journal,
    )
    tid = TenantId.new()

    asyncio.run(
        uc.execute(
            tenant_id=tid,
            chat_id=CHAT,
            text=None,
            audio_media_id="file-456",
        )
    )

    assert transcriber.calls == 1
    assert downloader.calls == 1
    assert len(journal.entries) == 1
    assert len(messenger.sent) == 1


def test_inbound_with_generator_uses_ai_draft() -> None:
    generator = FakeLinkedInGenerator()
    drafts = FakeContentDraftRepository()
    uc, messenger = _inbound_uc(
        generate_draft=GenerateLinkedInDraft(drafts, generator),
    )
    tid = TenantId.new()

    request = asyncio.run(
        uc.execute(
            tenant_id=tid,
            chat_id=CHAT,
            text="hoje estudei sqlalchemy async",
            audio_media_id=None,
        )
    )

    assert len(generator.calls) == 1
    assert request.draft_id
    assert messenger.sent[-1].kind == "approval"


def test_approval_publishes_and_notifies() -> None:
    drafts = FakeContentDraftRepository()
    queue = FakePublicationQueueRepository()
    messenger = FakeMessenger()
    requests = FakeTelegramRequestRepository()
    tid = TenantId.new()

    inbound, _ = _inbound_uc(
        requests=requests,
        create_draft=CreateLinkedInDraft(drafts),
    )
    request = asyncio.run(
        inbound.execute(
            tenant_id=tid,
            chat_id=CHAT,
            text="conteudo para publicar",
            audio_media_id=None,
        )
    )

    class _FakePublisher:
        async def publish(self, tenant_id, *, text, hashtags) -> str:
            return "urn:li:share:999"

    approval_uc = HandleApprovalReply(
        messenger=messenger,
        requests=requests,
        enqueue=EnqueueDraft(drafts, queue),
        publish=MarkPublished(drafts, queue, _FakePublisher()),
        reject=RejectDraft(drafts),
    )
    asyncio.run(
        approval_uc.execute(
            tenant_id=tid,
            chat_id=CHAT,
            approved=True,
            request_id=str(request.id),
        )
    )

    final = asyncio.run(requests.get_by_id(tid, str(request.id)))
    assert final is not None
    assert final.status is RequestStatus.APPROVED
    assert messenger.sent[-1].kind == "text"
    assert "urn:li:share:999" in messenger.sent[-1].text


def test_rejection_rejects_draft_and_notifies() -> None:
    drafts = FakeContentDraftRepository()
    queue = FakePublicationQueueRepository()
    messenger = FakeMessenger()
    requests = FakeTelegramRequestRepository()
    tid = TenantId.new()

    inbound, _ = _inbound_uc(
        requests=requests,
        create_draft=CreateLinkedInDraft(drafts),
    )
    request = asyncio.run(
        inbound.execute(
            tenant_id=tid,
            chat_id=CHAT,
            text="conteudo que sera rejeitado",
            audio_media_id=None,
        )
    )

    approval_uc = HandleApprovalReply(
        messenger=messenger,
        requests=requests,
        enqueue=EnqueueDraft(drafts, queue),
        publish=MarkPublished(drafts, queue),  # type: ignore[arg-type]
        reject=RejectDraft(drafts),
    )
    asyncio.run(
        approval_uc.execute(
            tenant_id=tid,
            chat_id=CHAT,
            approved=False,
            request_id=str(request.id),
        )
    )

    final = asyncio.run(requests.get_by_id(tid, str(request.id)))
    assert final is not None
    assert final.status is RequestStatus.REJECTED
    assert messenger.sent[-1].kind == "text"
    assert "nao publiquei" in messenger.sent[-1].text


def test_approval_unknown_request_notifies() -> None:
    messenger = FakeMessenger()
    approval_uc = HandleApprovalReply(
        messenger=messenger,
        requests=FakeTelegramRequestRepository(),
        enqueue=EnqueueDraft(FakeContentDraftRepository(), FakePublicationQueueRepository()),
        publish=MarkPublished(FakeContentDraftRepository(), FakePublicationQueueRepository()),  # type: ignore[arg-type]
        reject=RejectDraft(FakeContentDraftRepository()),
    )
    asyncio.run(
        approval_uc.execute(
            tenant_id=TenantId.new(),
            chat_id=CHAT,
            approved=True,
            request_id="missing-id",
        )
    )
    assert messenger.sent[-1].kind == "text"
    assert "Nao encontrei" in messenger.sent[-1].text


def test_approval_domain_error_notifies_instead_of_crashing() -> None:
    drafts = FakeContentDraftRepository()
    queue = FakePublicationQueueRepository()
    messenger = FakeMessenger()
    requests = FakeTelegramRequestRepository()
    tid = TenantId.new()

    inbound, _ = _inbound_uc(
        requests=requests,
        create_draft=CreateLinkedInDraft(drafts),
    )
    request = asyncio.run(
        inbound.execute(
            tenant_id=tid,
            chat_id=CHAT,
            text="conteudo",
            audio_media_id=None,
        )
    )

    class _FailingPublisher:
        async def publish(self, tenant_id, *, text, hashtags) -> str:
            raise ValidationError("linkedin nao conectado")

    approval_uc = HandleApprovalReply(
        messenger=messenger,
        requests=requests,
        enqueue=EnqueueDraft(drafts, queue),
        publish=MarkPublished(drafts, queue, _FailingPublisher()),
        reject=RejectDraft(drafts),
    )
    asyncio.run(
        approval_uc.execute(
            tenant_id=tid,
            chat_id=CHAT,
            approved=True,
            request_id=str(request.id),
        )
    )
    assert messenger.sent[-1].kind == "text"
    assert "nao deu para publicar" in messenger.sent[-1].text
    final = asyncio.run(requests.get_by_id(tid, str(request.id)))
    assert final is not None
    assert final.status is RequestStatus.PENDING


def test_domain_error_base_has_message() -> None:
    err = DomainError("boom")
    assert err.message == "boom"
