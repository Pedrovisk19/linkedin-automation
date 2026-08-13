"""Composition helper do discord."""

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
from developer_brain_ai_integrations.application.use_cases import (
    DisconnectLinkedIn,
    GetLinkedInStatus,
    LinkedInAuthUrlBuilder,
)
from developer_brain_ai_integrations.infrastructure.repositories import (
    SqlAlchemyLinkedInTokenRepository,
)
from developer_brain_ai_journal.infrastructure.repositories import (
    SqlAlchemyJournalEntryRepository,
)
from developer_brain_ai_shared.kernel.id import TenantId
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from developer_brain_ai_discord.application.use_cases import (
    HandleApprovalReply,
    HandleInboundMessage,
    SendDraftToChannel,
)
from developer_brain_ai_discord.domain.value_objects import ChannelId
from developer_brain_ai_discord.infrastructure.discord_client import (
    DiscordMessenger,
    HttpAudioDownloader,
)
from developer_brain_ai_discord.infrastructure.repositories import (
    SqlAlchemyDiscordRequestRepository,
)
from developer_brain_ai_discord.infrastructure.transcriber import (
    OpenAIWhisperTranscriber,
)
from developer_brain_ai_discord.presentation.bot import BrainBot, build_bot


@dataclass
class DiscordWiring:
    """Pecas montadas para o bot rodar no lifespan da API."""

    client: BrainBot
    inbound_uc: HandleInboundMessage
    approval_uc: HandleApprovalReply
    send_draft_uc: SendDraftToChannel
    tenant_id: TenantId
    allowed_channel: ChannelId | None
    messenger: DiscordMessenger


def mount_discord(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    bot_token: str,
    allowed_channel_id: str,
    tenant_id: TenantId,
    drafts_repo: ContentDraftRepository,
    queue_repo: PublicationQueueRepository,
    linkedin_generator: LinkedInGenerator | None = None,
    linkedin_publisher: LinkedInPostPublisher | None = None,
    openai_client: AsyncOpenAI | None = None,
    linkedin_auth_builder: LinkedInAuthUrlBuilder | None = None,
) -> DiscordWiring:
    """Monta o bot de gateway com DI injetada pelo composition root."""

    requests_repo = SqlAlchemyDiscordRequestRepository(session_factory)
    journal_repo = SqlAlchemyJournalEntryRepository(session_factory)

    linkedin_tokens_repo = SqlAlchemyLinkedInTokenRepository(session_factory)
    linkedin_status_uc = GetLinkedInStatus(linkedin_tokens_repo)
    linkedin_disconnect_uc = DisconnectLinkedIn(linkedin_tokens_repo)

    create_draft = CreateLinkedInDraft(drafts_repo)
    generate_draft = (
        GenerateLinkedInDraft(drafts_repo, linkedin_generator)
        if linkedin_generator is not None
        else None
    )

    allowed_channel = None
    if allowed_channel_id.strip():
        try:
            allowed_channel = ChannelId(int(allowed_channel_id.strip()))
        except ValueError:
            allowed_channel = None

    client = build_bot(
        tenant_id=tenant_id,
        allowed_channel=allowed_channel,
    )
    messenger = DiscordMessenger(client)

    inbound_uc = HandleInboundMessage(
        messenger=messenger,
        journal_repo=journal_repo,
        requests=requests_repo,
        create_draft=create_draft,
        generate_draft=generate_draft,
        transcriber=OpenAIWhisperTranscriber(openai_client) if openai_client else None,
        downloader=HttpAudioDownloader(),
        linkedin_auth_builder=linkedin_auth_builder,
        linkedin_status_uc=linkedin_status_uc,
        linkedin_disconnect_uc=linkedin_disconnect_uc,
    )
    approval_uc = HandleApprovalReply(
        messenger=messenger,
        requests=requests_repo,
        enqueue=EnqueueDraft(drafts_repo, queue_repo),
        publish=MarkPublished(drafts_repo, queue_repo, publisher=linkedin_publisher),
        reject=RejectDraft(drafts_repo),
    )
    send_draft_uc = SendDraftToChannel(messenger=messenger, requests=requests_repo)
    client.attach_handlers(
        inbound_uc=inbound_uc,
        approval_uc=approval_uc,
        messenger=messenger,
    )

    return DiscordWiring(
        client=client,
        inbound_uc=inbound_uc,
        approval_uc=approval_uc,
        send_draft_uc=send_draft_uc,
        tenant_id=tenant_id,
        allowed_channel=allowed_channel,
        messenger=messenger,
    )


__all__ = ["DiscordWiring", "mount_discord"]
