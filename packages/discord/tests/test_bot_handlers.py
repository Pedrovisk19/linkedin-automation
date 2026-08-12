"""Testes dos handlers de gateway (presentation) sem socket.

handle_message / handle_button sao funcoes puras: recebem os valores do evento
(channel_id, text, custom_id) e os use cases; nao dependem do client discord.py.
"""

from __future__ import annotations

import asyncio

from content_fakes import (
    FakeContentDraftRepository,
    FakePublicationQueueRepository,
)
from developer_brain_ai_content.application.use_cases import (
    CreateLinkedInDraft,
    EnqueueDraft,
    MarkPublished,
    RejectDraft,
)
from developer_brain_ai_discord.application.use_cases import (
    HandleApprovalReply,
    HandleInboundMessage,
)
from developer_brain_ai_discord.domain.value_objects import ChannelId, RequestStatus
from developer_brain_ai_discord.presentation.bot import handle_button, handle_message
from developer_brain_ai_shared.kernel.id import TenantId
from discord_fakes import (
    FakeDiscordRequestRepository,
    FakeJournalRepository,
    FakeMessenger,
)

CHANNEL = ChannelId(987654321)
OTHER_CHANNEL = ChannelId(111111)


def _inbound_uc(
    messenger: FakeMessenger,
    requests: FakeDiscordRequestRepository,
    drafts: FakeContentDraftRepository,
) -> HandleInboundMessage:
    return HandleInboundMessage(
        messenger=messenger,
        journal_repo=FakeJournalRepository(),
        requests=requests,
        create_draft=CreateLinkedInDraft(drafts),
        generate_draft=None,
    )


def _approval_uc(
    messenger: FakeMessenger,
    requests: FakeDiscordRequestRepository,
    drafts: FakeContentDraftRepository,
) -> HandleApprovalReply:
    queue = FakePublicationQueueRepository()
    return HandleApprovalReply(
        messenger=messenger,
        requests=requests,
        enqueue=EnqueueDraft(drafts, queue),
        publish=MarkPublished(drafts, queue),  # type: ignore[arg-type]
        reject=RejectDraft(drafts),
    )


def test_message_from_allowed_channel_creates_approval() -> None:
    messenger = FakeMessenger()
    requests = FakeDiscordRequestRepository()
    tid = TenantId.new()

    asyncio.run(
        handle_message(
            channel_id=CHANNEL.value,
            text="hoje aprendi sobre gateways",
            audio_url=None,
            tenant_id=tid,
            allowed_channel=CHANNEL,
            inbound_uc=_inbound_uc(messenger, requests, FakeContentDraftRepository()),
        )
    )

    assert messenger.sent[-1].kind == "approval"
    assert messenger.sent[-1].to == CHANNEL.value
    saved = asyncio.run(requests.get_pending_by_channel(tid, CHANNEL.value))
    assert saved is not None
    assert saved.status is RequestStatus.PENDING


def test_message_from_unknown_channel_ignored_when_allowlist_set() -> None:
    messenger = FakeMessenger()
    requests = FakeDiscordRequestRepository()

    asyncio.run(
        handle_message(
            channel_id=OTHER_CHANNEL.value,
            text="mensagem de canal errado",
            audio_url=None,
            tenant_id=TenantId.new(),
            allowed_channel=CHANNEL,
            inbound_uc=_inbound_uc(messenger, requests, FakeContentDraftRepository()),
        )
    )

    assert messenger.sent == []


def test_message_autobinds_when_no_allowlist() -> None:
    messenger = FakeMessenger()
    requests = FakeDiscordRequestRepository()

    asyncio.run(
        handle_message(
            channel_id=OTHER_CHANNEL.value,
            text="primeiro canal vira dono",
            audio_url=None,
            tenant_id=TenantId.new(),
            allowed_channel=None,
            inbound_uc=_inbound_uc(messenger, requests, FakeContentDraftRepository()),
        )
    )

    assert messenger.sent[-1].kind == "approval"
    assert messenger.sent[-1].to == OTHER_CHANNEL.value


def test_button_approve_processes_request() -> None:
    messenger = FakeMessenger()
    requests = FakeDiscordRequestRepository()
    drafts = FakeContentDraftRepository()
    tid = TenantId.new()

    asyncio.run(
        handle_message(
            channel_id=CHANNEL.value,
            text="conteudo para o botao",
            audio_url=None,
            tenant_id=tid,
            allowed_channel=CHANNEL,
            inbound_uc=_inbound_uc(messenger, requests, drafts),
        )
    )
    request_id = messenger.sent[-1].request_id

    asyncio.run(
        handle_button(
            channel_id=CHANNEL.value,
            custom_id=f"approve:{request_id}",
            tenant_id=tid,
            allowed_channel=CHANNEL,
            approval_uc=_approval_uc(messenger, requests, drafts),
        )
    )

    final = asyncio.run(requests.get_by_id(tid, request_id))
    assert final is not None
    assert final.status is RequestStatus.APPROVED
    assert messenger.sent[-1].kind == "text"


def test_button_reject_processes_request() -> None:
    messenger = FakeMessenger()
    requests = FakeDiscordRequestRepository()
    drafts = FakeContentDraftRepository()
    tid = TenantId.new()

    asyncio.run(
        handle_message(
            channel_id=CHANNEL.value,
            text="conteudo para rejeitar",
            audio_url=None,
            tenant_id=tid,
            allowed_channel=CHANNEL,
            inbound_uc=_inbound_uc(messenger, requests, drafts),
        )
    )
    request_id = messenger.sent[-1].request_id

    asyncio.run(
        handle_button(
            channel_id=CHANNEL.value,
            custom_id=f"reject:{request_id}",
            tenant_id=tid,
            allowed_channel=CHANNEL,
            approval_uc=_approval_uc(messenger, requests, drafts),
        )
    )

    final = asyncio.run(requests.get_by_id(tid, request_id))
    assert final is not None
    assert final.status is RequestStatus.REJECTED


def test_button_unknown_custom_id_ignored() -> None:
    messenger = FakeMessenger()
    requests = FakeDiscordRequestRepository()
    drafts = FakeContentDraftRepository()

    asyncio.run(
        handle_button(
            channel_id=CHANNEL.value,
            custom_id="some:other",
            tenant_id=TenantId.new(),
            allowed_channel=CHANNEL,
            approval_uc=_approval_uc(messenger, requests, drafts),
        )
    )

    assert messenger.sent == []


def test_button_unknown_channel_ignored() -> None:
    messenger = FakeMessenger()
    requests = FakeDiscordRequestRepository()
    drafts = FakeContentDraftRepository()

    asyncio.run(
        handle_button(
            channel_id=OTHER_CHANNEL.value,
            custom_id="approve:abc",
            tenant_id=TenantId.new(),
            allowed_channel=CHANNEL,
            approval_uc=_approval_uc(messenger, requests, drafts),
        )
    )

    assert messenger.sent == []
