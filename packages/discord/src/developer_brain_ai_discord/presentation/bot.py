"""Bot Discord (gateway): handlers puros + client discord.py.

Diferente do Telegram (Bot API HTTP com webhook/polling), o Discord exige uma
conexao persistente via Gateway (WebSocket). O dispatch e separado em funcoes
puras (handle_message / handle_button) testaveis sem socket; o client discord.py
apenas repassa os eventos do gateway para essas funcoes.

A allowlist e por channel_id; se nao configurada, o primeiro canal que falar
com o bot e tratado como dono (auto-bind) e logado.
"""

from __future__ import annotations

from typing import Any

import discord
from developer_brain_ai_shared.errors.base import DomainError
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.logging import get_logger
from developer_brain_ai_shared.persistence.tenant import (
    reset_tenant_context,
    set_tenant_context,
)

from developer_brain_ai_discord.application.use_cases import (
    HandleApprovalReply,
    HandleInboundMessage,
)
from developer_brain_ai_discord.domain.ports import Messenger
from developer_brain_ai_discord.domain.value_objects import ChannelId

_APPROVE_PREFIX = "approve:"
_REJECT_PREFIX = "reject:"


def _channel_id_or_none(raw: Any) -> ChannelId | None:
    try:
        return ChannelId(int(raw))
    except TypeError, ValueError:
        return None


def _is_allowed(channel_id: ChannelId, allowed_channel: ChannelId | None) -> bool:
    if allowed_channel is None:
        get_logger().info("discord auto-bind first channel", channel=channel_id.value)
        return True
    return channel_id == allowed_channel


def _allowed_channel_of(raw: Any, allowed_channel: ChannelId | None, kind: str) -> ChannelId | None:
    if raw is None:
        return None
    channel_id = _channel_id_or_none(raw)
    if channel_id is None or not _is_allowed(channel_id, allowed_channel):
        get_logger().warning(f"discord {kind} from unknown channel", channel=raw)
        return None
    return channel_id


async def handle_message(
    *,
    channel_id: Any,
    text: str | None,
    audio_url: str | None,
    tenant_id: TenantId,
    allowed_channel: ChannelId | None,
    inbound_uc: HandleInboundMessage,
    messenger: Messenger | None = None,
) -> None:
    """Processa uma mensagem de texto/audio recebida no canal."""
    target = _allowed_channel_of(channel_id, allowed_channel, "message")
    if target is None:
        return
    set_tenant_context(tenant_id)
    try:
        await inbound_uc.execute(
            tenant_id=tenant_id,
            channel_id=target,
            text=text,
            audio_media_id=audio_url,
        )
    except DomainError as exc:
        get_logger().warning("discord message domain error", message=str(exc.message))
        await _reply_error(messenger, target, f"Erro: {exc.message}")
    except Exception:
        get_logger().exception("discord message unexpected error")
        await _reply_error(
            messenger, target, "Erro interno ao processar a mensagem. Tente novamente."
        )
    finally:
        reset_tenant_context()


async def handle_button(
    *,
    channel_id: Any,
    custom_id: str | None,
    tenant_id: TenantId,
    allowed_channel: ChannelId | None,
    approval_uc: HandleApprovalReply,
    messenger: Messenger | None = None,
) -> None:
    """Processa o clique nos botoes approve:/reject: da mensagem de aprovacao."""
    target = _allowed_channel_of(channel_id, allowed_channel, "button")
    if target is None:
        return
    approved, request_id = _parse_approval(custom_id)
    if approved is None or not request_id:
        get_logger().warning("discord unknown button", custom_id=custom_id)
        return
    set_tenant_context(tenant_id)
    try:
        await approval_uc.execute(
            tenant_id=tenant_id,
            channel_id=target,
            approved=approved,
            request_id=request_id,
        )
    except DomainError as exc:
        get_logger().warning("discord button domain error", message=str(exc.message))
        await _reply_error(messenger, target, f"Erro: {exc.message}")
    except Exception:
        get_logger().exception("discord button unexpected error")
        await _reply_error(messenger, target, "Erro interno ao processar a aprovacao.")
    finally:
        reset_tenant_context()


async def _reply_error(messenger: Messenger | None, to: ChannelId, text: str) -> None:
    if messenger is None:
        return
    try:
        await messenger.send_text(to=to, text=text)
    except Exception:
        get_logger().warning("discord error reply failed", text=text)


def _parse_approval(custom_id: str | None) -> tuple[bool | None, str]:
    if not custom_id:
        return None, ""
    if custom_id.startswith(_APPROVE_PREFIX):
        return True, custom_id[len(_APPROVE_PREFIX) :]
    if custom_id.startswith(_REJECT_PREFIX):
        return False, custom_id[len(_REJECT_PREFIX) :]
    return None, ""


def _first_audio_attachment(attachments: Any) -> str | None:
    if not attachments:
        return None
    for attachment in attachments:
        content_type = getattr(attachment, "content_type", None)
        if content_type and str(content_type).startswith("audio/"):
            url = getattr(attachment, "url", None)
            if url:
                return str(url)
    return None


class BrainBot(discord.Client):
    """Client do gateway; os use cases sao anexados apos o ``mount_discord``.

    A separacao evita a referencia circular client <-> messenger <-> use cases.
    """

    def __init__(
        self,
        *,
        tenant_id: TenantId,
        allowed_channel: ChannelId | None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._tenant_id = tenant_id
        self._allowed_channel = allowed_channel
        self._inbound_uc: HandleInboundMessage | None = None
        self._approval_uc: HandleApprovalReply | None = None
        self._messenger: Messenger | None = None

    def attach_handlers(
        self,
        *,
        inbound_uc: HandleInboundMessage,
        approval_uc: HandleApprovalReply,
        messenger: Messenger | None = None,
    ) -> None:
        self._inbound_uc = inbound_uc
        self._approval_uc = approval_uc
        self._messenger = messenger

    async def on_message(self, message: Any) -> None:
        if (
            self._inbound_uc is None
            or message.author is None
            or self.user is None
            or message.author == self.user
        ):
            return
        audio_url = _first_audio_attachment(message.attachments)
        await handle_message(
            channel_id=message.channel.id,
            text=message.content if message.content else None,
            audio_url=audio_url,
            tenant_id=self._tenant_id,
            allowed_channel=self._allowed_channel,
            inbound_uc=self._inbound_uc,
            messenger=self._messenger,
        )

    async def on_interaction(self, interaction: Any) -> None:
        if self._approval_uc is None or interaction.type is not discord.InteractionType.component:
            return
        custom_id = ""
        if interaction.data:
            custom_id = str(interaction.data.get("custom_id", ""))
        if _parse_approval(custom_id)[0] is None:
            return
        try:
            await interaction.response.defer()
        except Exception:
            get_logger().warning("discord interaction already acknowledged", custom_id=custom_id)
        await handle_button(
            channel_id=interaction.channel_id,
            custom_id=custom_id,
            tenant_id=self._tenant_id,
            allowed_channel=self._allowed_channel,
            approval_uc=self._approval_uc,
            messenger=self._messenger,
        )


def build_bot(
    *,
    tenant_id: TenantId,
    allowed_channel: ChannelId | None,
) -> BrainBot:
    """Monta o client do gateway (handlers sao anexados via ``attach_handlers``)."""
    intents = discord.Intents.default()
    intents.message_content = True
    return BrainBot(
        tenant_id=tenant_id,
        allowed_channel=allowed_channel,
        intents=intents,
    )


async def run_discord_bot(client: BrainBot, token: str) -> None:
    """Task de background: conecta ao gateway e segura o processamento.

    Uso no lifespan do FastAPI: ``asyncio.create_task(run_discord_bot(...))``.
    Emite ``client.close()`` ao sair (erro, cancelamento ou shutdown).
    """
    try:
        await client.start(token)
    except Exception:
        get_logger().exception("discord bot connection error")
    finally:
        try:
            await client.close()
        except Exception:
            get_logger().exception("discord client close failed")


__all__ = ["BrainBot", "build_bot", "handle_button", "handle_message", "run_discord_bot"]
