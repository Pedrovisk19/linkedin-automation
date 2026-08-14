"""Messenger Discord via REST API (sem gateway) p/ processos sem bot.

O gateway (discord.py) roda apenas na API — o worker nao pode abrir uma
segunda conexao com o mesmo token (Discord desconecta a primeira). Para o
cron de news enviar o pedido de aprovacao, este messenger usa a REST API
(``POST /channels/{id}/messages``) com os mesmos custom_ids approve:/reject:
que o bot do gateway processa. A interacao (clique no botao) chega ao bot via
gateway e o fluxo de aprovacao roda na API, como sempre.
"""

from __future__ import annotations

import io
import json
from typing import Any

import httpx
from developer_brain_ai_shared.errors.base import IntegrationError
from developer_brain_ai_shared.logging import get_logger

from developer_brain_ai_discord.domain.ports import Messenger
from developer_brain_ai_discord.domain.value_objects import ChannelId

_APPROVE_ID = "approve"
_REJECT_ID = "reject"

_DISCORD_API = "https://discord.com/api/v10"
_DISCORD_MSG_LIMIT = 2000
_CHUNK_BODY_LIMIT = 1900

_HEADERS = {"Content-Type": "application/json"}

_CONTINUATION_MARKER = "\n_→ continua na próxima mensagem_"


def _chunk_messages(title: str, body: str) -> list[str]:
    """Quebra (title + body) em mensagens <= limite do Discord (igual ao gateway)."""
    full = f"{title}\n\n{body}" if title else body
    if len(full) <= _DISCORD_MSG_LIMIT:
        return [full]
    out: list[str] = []
    out.append(f"{title}\n\n")
    remaining = body
    while remaining:
        if len(remaining) <= _CHUNK_BODY_LIMIT:
            out.append(remaining)
            break
        cut = remaining.rfind("\n", 0, _CHUNK_BODY_LIMIT)
        if cut == -1:
            cut = _CHUNK_BODY_LIMIT
        out.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    for i in range(len(out) - 1):
        out[i] = f"{out[i].rstrip()}{_CONTINUATION_MARKER}"
    return out


class RestDiscordMessenger(Messenger):
    """Envia texto/pedido de aprovacao via REST (token do bot).

    Nao exige conexao com o gateway — usa ``Authorization: Bot <token>``.
    Os botoes usam custom_id ``approve:<request_id>`` / ``reject:<request_id>``,
    identicos aos do gateway, para que o bot da API processe o clique.
    """

    def __init__(self, bot_token: str, *, timeout: float = 30.0) -> None:
        if not bot_token or not bot_token.strip():
            raise ValueError("bot_token do Discord nao pode ser vazio")
        self._token = bot_token.strip()
        self._timeout = timeout

    async def send_text(self, *, to: ChannelId, text: str) -> None:
        await self._post_channel_message(to, {"content": text})

    async def send_approval_request(
        self, *, to: ChannelId, request_id: str, title: str, body: str
    ) -> None:
        full = f"{title}\n\n{body}" if title else body
        chunks = _chunk_messages(title, body)
        for i, chunk in enumerate(chunks):
            payload: dict[str, Any] = {"content": chunk}
            if i == len(chunks) - 1:
                payload["components"] = [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "label": "Publicar",
                                "style": 3,
                                "custom_id": f"{_APPROVE_ID}:{request_id}",
                            },
                            {
                                "type": 2,
                                "label": "Nao publicar",
                                "style": 4,
                                "custom_id": f"{_REJECT_ID}:{request_id}",
                            },
                        ],
                    }
                ]
            await self._post_channel_message(to, payload, full if i == len(chunks) - 1 else None)

    async def answer_callback(self, callback_query_id: str) -> None:
        return None

    async def _post_channel_message(
        self, to: ChannelId, payload: dict[str, Any], full: str | None = None
    ) -> None:
        url = f"{_DISCORD_API}/channels/{to.value}/messages"
        headers = {**_HEADERS, "Authorization": f"Bot {self._token}"}
        if full is not None:
            files = {"files[0]": ("post.md", io.BytesIO(full.encode("utf-8")), "text/markdown")}
            data = {"payload_json": json.dumps(payload)}
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, data=data, files=files, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            get_logger().warning(
                "discord rest send failed",
                channel_id=to.value,
                status_code=resp.status_code,
                body=resp.text[:300],
            )
            raise IntegrationError(
                "envio de mensagem p/ Discord via REST falhou",
                details={"status_code": resp.status_code, "channel_id": to.value},
            )


__all__ = ["RestDiscordMessenger"]
