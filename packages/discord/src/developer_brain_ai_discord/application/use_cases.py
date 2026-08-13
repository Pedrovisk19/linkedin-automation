"""Use cases do discord: receber mensagem e processar aprovacao."""

from __future__ import annotations

from datetime import date
from typing import Any

from developer_brain_ai_content.application.dto import (
    CreateLinkedInDraftInput,
    GenerateLinkedInInput,
)
from developer_brain_ai_content.application.use_cases import (
    CreateLinkedInDraft,
    EnqueueDraft,
    GenerateLinkedInDraft,
    MarkPublished,
    RejectDraft,
)
from developer_brain_ai_journal.domain.entry import JournalEntry
from developer_brain_ai_journal.domain.ids import JournalEntryId
from developer_brain_ai_journal.domain.repositories import JournalEntryRepository
from developer_brain_ai_journal.domain.value_objects import EntryDate, StudyMinutes, Tag
from developer_brain_ai_shared.errors.base import DomainError, ValidationError
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow

from developer_brain_ai_discord.domain.aggregates import DiscordRequest
from developer_brain_ai_discord.domain.ids import DiscordRequestId
from developer_brain_ai_discord.domain.ports import (
    AudioDownloader,
    AudioTranscriber,
    Messenger,
)
from developer_brain_ai_discord.domain.repositories import DiscordRequestRepository
from developer_brain_ai_discord.domain.value_objects import ChannelId, RequestStatus


class HandleInboundMessage:
    """Processa uma mensagem recebida: texto/audio -> journal + draft + pedido.

    Fluxo:
    1. Normaliza o texto (transcricao se audio).
    2. Persiste um JournalEntry com o aprendizado.
    3. Gera o draft (IA se disponivel, senao texto cru).
    4. Cria um DiscordRequest pendente e envia os botoes de aprovacao.
    """

    def __init__(
        self,
        *,
        messenger: Messenger,
        journal_repo: JournalEntryRepository,
        requests: DiscordRequestRepository,
        create_draft: CreateLinkedInDraft,
        generate_draft: GenerateLinkedInDraft | None,
        transcriber: AudioTranscriber | None = None,
        downloader: AudioDownloader | None = None,
    ) -> None:
        self._messenger = messenger
        self._journal_repo = journal_repo
        self._requests = requests
        self._create_draft = create_draft
        self._generate_draft = generate_draft
        self._transcriber = transcriber
        self._downloader = downloader

    async def execute(
        self,
        *,
        tenant_id: TenantId,
        channel_id: ChannelId,
        text: str | None,
        audio_media_id: str | None,
    ) -> DiscordRequest:
        raw_text = text or ""
        if audio_media_id:
            if self._transcriber is None or self._downloader is None:
                raise ValidationError(
                    "transcricao de audio nao configurada no servidor",
                    details={"reason": "audio_unsupported"},
                )
            media = await self._downloader.download_audio(audio_media_id)
            raw_text = (await self._transcriber.transcribe(media)).strip()

        if not raw_text or not raw_text.strip():
            raise ValidationError(
                "mensagem vazia (sem texto e sem audio com fala)",
                details={"reason": "empty_message"},
            )

        entry = JournalEntry.create(
            id=JournalEntryId.new(),
            tenant_id=tenant_id,
            title=_first_line_or_truncate(raw_text),
            entry_date=EntryDate(date.today()),
            study_minutes=StudyMinutes(0),
            timestamps=Timestamps(created_at=utcnow(), updated_at=utcnow()),
            learnings=raw_text[:1200],
            tags=[Tag("discord")],
        )
        await self._journal_repo.save(entry)

        draft = await self._generate_or_fallback(tenant_id, entry, raw_text)

        now = utcnow()
        request = DiscordRequest(
            id=DiscordRequestId.new(),
            tenant_id=tenant_id,
            channel_id=channel_id,
            draft_id=str(draft.draft_id),
            timestamps=Timestamps(created_at=now, updated_at=now),
        )
        await self._requests.save(request)
        await self._messenger.send_approval_request(
            to=channel_id,
            request_id=str(request.id),
            title=_short_title(draft.title),
            body=_format_draft_body(draft),
        )
        return request

    async def _generate_or_fallback(
        self,
        tenant_id: TenantId,
        entry: JournalEntry,
        raw_text: str,
    ) -> Any:
        entries = [_entry_as_dict(entry)]
        if self._generate_draft is not None:
            return await self._generate_draft.execute(
                tenant_id,
                GenerateLinkedInInput(entries=entries),
            )
        return await self._create_draft.execute(
            tenant_id,
            CreateLinkedInDraftInput(
                title=_first_line_or_truncate(raw_text),
                texto=raw_text,
                source_entry_ids=[str(entry.id)],
            ),
        )


class HandleApprovalReply:
    """Processa o clique nos botoes: aprova/rejeita e publica (ou nao)."""

    def __init__(
        self,
        *,
        messenger: Messenger,
        requests: DiscordRequestRepository,
        enqueue: EnqueueDraft,
        publish: MarkPublished,
        reject: RejectDraft,
    ) -> None:
        self._messenger = messenger
        self._requests = requests
        self._enqueue = enqueue
        self._publish = publish
        self._reject = reject

    async def execute(
        self,
        *,
        tenant_id: TenantId,
        channel_id: ChannelId,
        approved: bool,
        request_id: str,
    ) -> None:
        request = await self._requests.get_by_id(tenant_id, request_id)
        if request is None:
            await self._messenger.send_text(
                to=channel_id,
                text="Nao encontrei esse pedido de publicacao.",
            )
            return

        if request.status is not RequestStatus.PENDING:
            kind = "aprovado" if request.status is RequestStatus.APPROVED else "rejeitado"
            await self._messenger.send_text(
                to=channel_id,
                text=f"Esse pedido ja foi {kind}.",
            )
            return

        try:
            if approved:
                await self._enqueue.execute(tenant_id, request.draft_id)
                result = await self._publish.execute(tenant_id, request.draft_id)
                request.approve()
                await self._requests.save(request)
                urn = result.get("linkedin_post_urn", "")
                if urn:
                    await self._messenger.send_text(
                        to=channel_id,
                        text=f"Publicado no LinkedIn! Post: {urn}",
                    )
                else:
                    await self._messenger.send_text(
                        to=channel_id,
                        text="Marcado como publicado, mas LinkedIn nao esta conectado (sem OAuth token). Conecte em /integrations/linkedin",
                    )
            else:
                await self._reject.execute(tenant_id, request.draft_id)
                request.reject()
                await self._requests.save(request)
                await self._messenger.send_text(
                    to=channel_id,
                    text="Ok, nao publiquei esse conteudo.",
                )
        except DomainError as exc:
            await self._messenger.send_text(
                to=channel_id,
                text=f"Ops, nao deu para publicar: {exc.message}",
            )


def _entry_as_dict(entry: JournalEntry) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "title": entry.title,
        "entry_date": str(entry.entry_date.as_date()),
        "study_minutes": entry.study_minutes.as_int(),
        "technologies": entry.technologies,
        "learnings": entry.learnings[:1200],
        "difficulties": entry.difficulties[:600],
        "bugs_found": entry.bugs_found,
        "resolutions": entry.resolutions,
    }


class SendDraftToChannel:
    """Envia um draft ja persistido ( qualquer origem ) para aprovacao no Discord.

    Cria um ``DiscordRequest`` pendente e repassa para o ``Messenger`` com os
    botoes Publicar/Nao publicar. Reusado pelo digest de news (ou qualquer
    outro agente que queira aprovacao pelo mesmo canal do bot).
    """

    def __init__(
        self,
        *,
        messenger: Messenger,
        requests: DiscordRequestRepository,
    ) -> None:
        self._messenger = messenger
        self._requests = requests

    async def execute(
        self,
        *,
        tenant_id: TenantId,
        channel_id: ChannelId,
        draft_id: str,
        title: str,
        body: str,
    ) -> str:
        now = utcnow()
        request = DiscordRequest(
            id=DiscordRequestId.new(),
            tenant_id=tenant_id,
            channel_id=channel_id,
            draft_id=draft_id,
            timestamps=Timestamps(created_at=now, updated_at=now),
        )
        await self._requests.save(request)
        await self._messenger.send_approval_request(
            to=channel_id,
            request_id=str(request.id),
            title=_short_title(title),
            body=body,
        )
        return str(request.id)


def _first_line_or_truncate(text: str) -> str:
    first = text.strip().splitlines()[0] if text.strip() else text
    return _truncate(first, 200)


def _format_draft_body(draft: Any) -> str:
    """Formatacao legivel para o Discord: gancho + texto + conclusao + pergunta + cta + hashtags."""
    parts: list[str] = []
    if getattr(draft, "gancho", ""):
        parts.append(f"> {draft.gancho}\n")
    if getattr(draft, "texto", ""):
        parts.append(draft.texto)
    if getattr(draft, "conclusao", ""):
        parts.append(f"\n**Conclusão:**\n{draft.conclusao}")
    if getattr(draft, "pergunta", ""):
        parts.append(f"\n**Pergunta:** {draft.pergunta}")
    if getattr(draft, "cta", ""):
        parts.append(f"\n**CTA:** {draft.cta}")
    tags = getattr(draft, "hashtags", []) or []
    if tags:
        hashtags_str = " ".join(f"#{t}" for t in tags)
        parts.append(f"\n{hashtags_str}")
    return "\n".join(parts)


def _short_title(title: str) -> str:
    return _truncate(title, 60)


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


__all__ = ["HandleApprovalReply", "HandleInboundMessage", "SendDraftToChannel"]
