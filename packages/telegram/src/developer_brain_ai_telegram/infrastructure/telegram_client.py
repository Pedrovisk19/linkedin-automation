"""Cliente da Telegram Bot API (httpx) — envio, botoes, downloads e polling.

Metodos:
- send_text / send_approval_request (inline keyboard)
- download_audio (getFile + download do file_path)
- get_updates (long polling) / answer_callback (para o spinner do botao)
"""

from __future__ import annotations

from typing import Any

import httpx
from developer_brain_ai_shared.errors.base import IntegrationError
from developer_brain_ai_shared.logging import get_logger

from developer_brain_ai_telegram.domain.ports import AudioMedia
from developer_brain_ai_telegram.domain.value_objects import ChatId

_API_BASE = "https://api.telegram.org"
_APPROVE_ID = "approve"
_REJECT_ID = "reject"

_MIME_BY_EXT = {
    "ogg": "audio/ogg",
    "oga": "audio/ogg",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "wav": "audio/wav",
    "webm": "audio/webm",
    "amr": "audio/amr",
    "opus": "audio/ogg",
}


class HttpTelegramClient:
    """Implementa Messenger + AudioDownloader + polling sobre a Bot API."""

    def __init__(
        self,
        token: str,
        *,
        base_url: str = _API_BASE,
        timeout: float = 60.0,
    ) -> None:
        self._token = token
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    async def send_text(self, *, to: ChatId, text: str) -> None:
        await self._call("sendMessage", {"chat_id": to.value, "text": text})

    async def send_approval_request(
        self, *, to: ChatId, request_id: str, title: str, body: str
    ) -> None:
        payload = {
            "chat_id": to.value,
            "text": f"{title}\n\n{body}",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "Publicar",
                            "callback_data": f"{_APPROVE_ID}:{request_id}",
                        },
                        {
                            "text": "Nao publicar",
                            "callback_data": f"{_REJECT_ID}:{request_id}",
                        },
                    ]
                ]
            },
        }
        await self._call("sendMessage", payload)

    async def answer_callback(self, callback_query_id: str) -> None:
        await self._call(
            "answerCallbackQuery", {"callback_query_id": callback_query_id}
        )

    async def download_audio(self, media_id: str) -> AudioMedia:
        file_info = await self._call("getFile", {"file_id": media_id})
        file_path = file_info.get("file_path")
        if not isinstance(file_path, str):
            raise IntegrationError(
                "download de midia do Telegram sem file_path",
                details={"file_id": media_id},
            )
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "ogg"
        url = f"{self._base}/file/bot{self._token}/{file_path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                raise IntegrationError(
                    "download de midia do Telegram falhou",
                    details={"status_code": resp.status_code},
                )
        return AudioMedia(data=resp.content, mime_type=_MIME_BY_EXT.get(ext, "audio/ogg"))

    async def get_updates(
        self, *, offset: int | None = None, timeout: int = 25
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message", "callback_query"],
        }
        if offset is not None:
            payload["offset"] = offset
        data = await self._call("getUpdates", payload)
        updates = data.get("result", [])
        return [u for u in updates if isinstance(u, dict)]

    async def _call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}/bot{self._token}/{method}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                get_logger().warning(
                    "telegram bot api error",
                    method=method,
                    status_code=resp.status_code,
                    body=resp.text[:1000],
                )
                raise IntegrationError(
                    "falha na Telegram Bot API",
                    details={
                        "method": method,
                        "status_code": resp.status_code,
                        "response": resp.text[:500],
                    },
                )
            data = resp.json()
            if not data.get("ok"):
                raise IntegrationError(
                    "falha na Telegram Bot API",
                    details={"method": method, "response": str(data)[:500]},
                )
            result = data.get("result")
            if isinstance(result, dict):
                return result
            return {"result": result}


__all__ = ["HttpTelegramClient"]
