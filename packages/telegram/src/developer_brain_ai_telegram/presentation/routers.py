"""Routers do telegram: webhook POST + dispatch compartilhado + polling.

- POST /integrations/telegram/webhook  -> updates entregues pelo Telegram
- telegram_poll_loop                    -> getUpdates long-polling (sem tunel)

O dispatch (handle_update) e compartilhado entre webhook e polling para nao
processar duas vezes. A allowlist e por chat_id; se nao configurada, o primeiro
chat que falar com o bot e tratado como dono (auto-bind) e logado.
"""

from __future__ import annotations

import asyncio
from typing import Any

from developer_brain_ai_shared.errors.base import DomainError
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.logging import get_logger
from developer_brain_ai_shared.persistence.tenant import (
    reset_tenant_context,
    set_tenant_context,
)
from fastapi import APIRouter, Request

from developer_brain_ai_telegram.application.use_cases import (
    HandleApprovalReply,
    HandleInboundMessage,
)
from developer_brain_ai_telegram.domain.ports import Messenger
from developer_brain_ai_telegram.domain.value_objects import ChatId
from developer_brain_ai_telegram.infrastructure.telegram_client import HttpTelegramClient


def build_router(
    *,
    allowed_chat: ChatId | None,
    tenant_id: TenantId,
    inbound_uc: HandleInboundMessage,
    approval_uc: HandleApprovalReply,
    messenger: Messenger,
) -> APIRouter:
    router = APIRouter(prefix="/integrations/telegram", tags=["telegram"])

    @router.post("/webhook", status_code=200)
    async def webhook(request: Request) -> dict[str, str]:
        try:
            payload = await request.json()
        except ValueError:
            return {"status": "ok"}
        await handle_update(
            update=payload,
            tenant_id=tenant_id,
            allowed_chat=allowed_chat,
            inbound_uc=inbound_uc,
            approval_uc=approval_uc,
            messenger=messenger,
        )
        return {"status": "ok"}

    return router


async def handle_update(
    *,
    update: dict[str, Any],
    tenant_id: TenantId,
    allowed_chat: ChatId | None,
    inbound_uc: HandleInboundMessage,
    approval_uc: HandleApprovalReply,
    messenger: Messenger,
) -> None:
    callback = _callback_query(update)
    if callback is not None:
        await _handle_callback(
            callback=callback,
            tenant_id=tenant_id,
            allowed_chat=allowed_chat,
            approval_uc=approval_uc,
            messenger=messenger,
        )
        return
    message = _message(update)
    if message is not None:
        await _handle_message(
            message=message,
            tenant_id=tenant_id,
            allowed_chat=allowed_chat,
            inbound_uc=inbound_uc,
        )


async def _handle_callback(
    *,
    callback: dict[str, Any],
    tenant_id: TenantId,
    allowed_chat: ChatId | None,
    approval_uc: HandleApprovalReply,
    messenger: Messenger,
) -> None:
    chat_id = _allowed_chat_of(_callback_chat_id(callback), allowed_chat, "callback")
    if chat_id is None:
        return
    set_tenant_context(tenant_id)
    try:
        data = str(callback.get("data", ""))
        if data.startswith("approve:"):
            await approval_uc.execute(
                tenant_id=tenant_id,
                chat_id=chat_id,
                approved=True,
                request_id=data.split(":", 1)[1],
            )
        elif data.startswith("reject:"):
            await approval_uc.execute(
                tenant_id=tenant_id,
                chat_id=chat_id,
                approved=False,
                request_id=data.split(":", 1)[1],
            )
        cq_id = callback.get("id")
        if cq_id:
            await messenger.answer_callback(str(cq_id))
    except DomainError as exc:
        get_logger().warning("telegram webhook domain error", message=str(exc.message))
    except Exception:
        get_logger().exception("telegram webhook unexpected error")
    finally:
        reset_tenant_context()


async def _handle_message(
    *,
    message: dict[str, Any],
    tenant_id: TenantId,
    allowed_chat: ChatId | None,
    inbound_uc: HandleInboundMessage,
) -> None:
    chat_id = _allowed_chat_of(_message_chat_id(message), allowed_chat, "message")
    if chat_id is None:
        return
    set_tenant_context(tenant_id)
    try:
        await inbound_uc.execute(
            tenant_id=tenant_id,
            chat_id=chat_id,
            text=_message_text(message),
            audio_media_id=_message_audio_id(message),
        )
    except DomainError as exc:
        get_logger().warning("telegram webhook domain error", message=str(exc.message))
    except Exception:
        get_logger().exception("telegram webhook unexpected error")
    finally:
        reset_tenant_context()


def _allowed_chat_of(
    raw: Any, allowed_chat: ChatId | None, kind: str
) -> ChatId | None:
    if raw is None:
        return None
    chat_id = _chat_id_or_none(raw)
    if chat_id is None or not _is_allowed(chat_id, allowed_chat):
        get_logger().warning(f"telegram {kind} from unknown chat", chat=raw)
        return None
    return chat_id


async def telegram_poll_loop(
    *,
    client: HttpTelegramClient,
    tenant_id: TenantId,
    allowed_chat: ChatId | None,
    inbound_uc: HandleInboundMessage,
    approval_uc: HandleApprovalReply,
    messenger: Messenger,
    poll_timeout: int = 25,
    poll_interval: float = 0.5,
) -> None:
    """Loop infinito de long polling (task de background da API)."""

    offset: int | None = None
    while True:
        try:
            updates = await client.get_updates(offset=offset, timeout=poll_timeout)
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = update_id + 1
                await handle_update(
                    update=update,
                    tenant_id=tenant_id,
                    allowed_chat=allowed_chat,
                    inbound_uc=inbound_uc,
                    approval_uc=approval_uc,
                    messenger=messenger,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            get_logger().exception("telegram poll error")
        await asyncio.sleep(poll_interval)


def _is_allowed(chat_id: ChatId, allowed_chat: ChatId | None) -> bool:
    if allowed_chat is None:
        get_logger().info("telegram auto-bind first chat", chat=chat_id.value)
        return True
    return chat_id == allowed_chat


def _chat_id_or_none(raw: Any) -> ChatId | None:
    try:
        return ChatId(int(raw))
    except (TypeError, ValueError):
        return None


def _message(update: dict[str, Any]) -> dict[str, Any] | None:
    m = update.get("message")
    return m if isinstance(m, dict) else None


def _callback_query(update: dict[str, Any]) -> dict[str, Any] | None:
    c = update.get("callback_query")
    return c if isinstance(c, dict) else None


def _message_chat_id(message: dict[str, Any]) -> Any:
    chat = message.get("chat")
    return chat.get("id") if isinstance(chat, dict) else None


def _callback_chat_id(callback: dict[str, Any]) -> Any:
    msg = callback.get("message")
    return _message_chat_id(msg) if isinstance(msg, dict) else None


def _message_text(message: dict[str, Any]) -> str | None:
    text = message.get("text")
    return str(text) if text is not None else None


def _message_audio_id(message: dict[str, Any]) -> str | None:
    audio = message.get("audio") or message.get("voice")
    if not isinstance(audio, dict):
        return None
    file_id = audio.get("file_id")
    return str(file_id) if file_id else None


__all__ = ["build_router", "handle_update", "telegram_poll_loop"]
