"""Composition helper do telegram."""

from __future__ import annotations

from dataclasses import dataclass

from developer_brain_ai_content.application.ports import (
    LinkedInGenerator,
    LinkedInPostPublisher,
)
from developer_brain_ai_content.application.use_cases import (
    CreateLinkedInDraft,
    EnqueueDraft,
    GenerateLinkedInDraft,
    MarkPublished,
    RejectDraft,
)
from developer_brain_ai_content.domain.repositories import (
    ContentDraftRepository,
    PublicationQueueRepository,
)
from developer_brain_ai_journal.infrastructure.repositories import (
    SqlAlchemyJournalEntryRepository,
)
from developer_brain_ai_shared.kernel.id import TenantId
from fastapi import APIRouter
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from developer_brain_ai_telegram.application.use_cases import (
    HandleApprovalReply,
    HandleInboundMessage,
)
from developer_brain_ai_telegram.domain.value_objects import ChatId
from developer_brain_ai_telegram.infrastructure.repositories import (
    SqlAlchemyTelegramRequestRepository,
)
from developer_brain_ai_telegram.infrastructure.telegram_client import HttpTelegramClient
from developer_brain_ai_telegram.infrastructure.transcriber import (
    OpenAIWhisperTranscriber,
)
from developer_brain_ai_telegram.presentation.routers import (
    build_router,
    telegram_poll_loop,
)


@dataclass
class TelegramWiring:
    """Pecas montadas para o webhook e para o polling loop."""

    router: APIRouter
    client: HttpTelegramClient
    inbound_uc: HandleInboundMessage
    approval_uc: HandleApprovalReply
    tenant_id: TenantId
    allowed_chat: ChatId | None


def mount_telegram(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    bot_token: str,
    allowed_chat_id: str,
    tenant_id: TenantId,
    drafts_repo: ContentDraftRepository,
    queue_repo: PublicationQueueRepository,
    linkedin_generator: LinkedInGenerator | None = None,
    linkedin_publisher: LinkedInPostPublisher | None = None,
    openai_client: AsyncOpenAI | None = None,
) -> TelegramWiring:
    """Monta o router /integrations/telegram com DI injetada pelo composition root."""

    client = HttpTelegramClient(token=bot_token)

    requests_repo = SqlAlchemyTelegramRequestRepository(session_factory)
    journal_repo = SqlAlchemyJournalEntryRepository(session_factory)

    create_draft = CreateLinkedInDraft(drafts_repo)
    generate_draft = (
        GenerateLinkedInDraft(drafts_repo, linkedin_generator)
        if linkedin_generator is not None
        else None
    )

    inbound_uc = HandleInboundMessage(
        messenger=client,
        journal_repo=journal_repo,
        requests=requests_repo,
        create_draft=create_draft,
        generate_draft=generate_draft,
        transcriber=OpenAIWhisperTranscriber(openai_client) if openai_client else None,
        downloader=client,
    )

    approval_uc = HandleApprovalReply(
        messenger=client,
        requests=requests_repo,
        enqueue=EnqueueDraft(drafts_repo, queue_repo),
        publish=MarkPublished(drafts_repo, queue_repo, publisher=linkedin_publisher),
        reject=RejectDraft(drafts_repo),
    )

    allowed_chat = None
    if allowed_chat_id.strip():
        try:
            allowed_chat = ChatId(int(allowed_chat_id.strip()))
        except ValueError:
            allowed_chat = None

    router = build_router(
        allowed_chat=allowed_chat,
        tenant_id=tenant_id,
        inbound_uc=inbound_uc,
        approval_uc=approval_uc,
        messenger=client,
    )

    return TelegramWiring(
        router=router,
        client=client,
        inbound_uc=inbound_uc,
        approval_uc=approval_uc,
        tenant_id=tenant_id,
        allowed_chat=allowed_chat,
    )


__all__ = ["TelegramWiring", "mount_telegram", "telegram_poll_loop"]
