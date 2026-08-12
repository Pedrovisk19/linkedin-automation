"""Cliente Discord (discord.py): messenger com botoes + downloader de audio.

O ``DiscordMessenger`` implementa o port ``Messenger`` por cima do client do
gateway (discord.py): resolve o canal pelo id (cache -> fetch) e envia texto
ou pedido de aprovacao com componentes de botoes (custom_id approve:/reject:).

O ``HttpAudioDownloader`` baixa anexos de audio via URL direta do CDN.
"""

from __future__ import annotations

from typing import cast

import discord
import httpx
from developer_brain_ai_shared.errors.base import IntegrationError

from developer_brain_ai_discord.domain.ports import AudioMedia, Messenger
from developer_brain_ai_discord.domain.value_objects import ChannelId

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

_DISCORD_MSG_LIMIT = 2000
_CHUNK_BODY_LIMIT = 1900


def _chunk_messages(title: str, body: str) -> list[str]:
    """Quebra (title + body) em mensagens <= limite do Discord."""
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
    return out


class DiscordMessenger(Messenger):
    """Envia mensagens/componentes pelo gateway (canal resolvido do cache)."""

    def __init__(self, client: discord.Client, *, timeout: float = 60.0) -> None:
        self._client = client
        self._timeout = timeout

    async def send_text(self, *, to: ChannelId, text: str) -> None:
        channel = await self._resolve_channel(to)
        await channel.send(text)

    async def send_approval_request(
        self, *, to: ChannelId, request_id: str, title: str, body: str
    ) -> None:
        view = discord.ui.View(timeout=None)
        view.add_item(
            discord.ui.Button(
                label="Publicar",
                style=discord.ButtonStyle.success,
                custom_id=f"{_APPROVE_ID}:{request_id}",
            )
        )
        view.add_item(
            discord.ui.Button(
                label="Nao publicar",
                style=discord.ButtonStyle.danger,
                custom_id=f"{_REJECT_ID}:{request_id}",
            )
        )
        channel = await self._resolve_channel(to)
        chunks = _chunk_messages(title, body)
        for i, chunk in enumerate(chunks):
            if i == len(chunks) - 1:
                await channel.send(chunk, view=view)
            else:
                await channel.send(chunk)

    async def answer_callback(self, callback_query_id: str) -> None:
        # No Discord o ACK de interacao e feito via interaction.response no
        # presentation layer (janela de 3s); nada a fazer aqui.
        return None

    async def _resolve_channel(self, to: ChannelId) -> discord.abc.Messageable:
        channel = self._client.get_channel(to.value)
        if channel is not None and getattr(channel, "send", None) is not None:
            return cast(discord.abc.Messageable, channel)
        fetched = await self._client.fetch_channel(to.value)
        if fetched is None or getattr(fetched, "send", None) is None:
            raise IntegrationError(
                "canal do Discord nao encontrado ou sem envio de texto",
                details={"channel_id": to.value},
            )
        return cast(discord.abc.Messageable, fetched)


class HttpAudioDownloader:
    """Baixa o anexo de audio pela URL direta (media_id = url)."""

    def __init__(self, *, timeout: float = 120.0) -> None:
        self._timeout = timeout

    async def download_audio(self, media_id: str) -> AudioMedia:
        url = str(media_id)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                raise IntegrationError(
                    "download de audio do Discord falhou",
                    details={"status_code": resp.status_code},
                )
        content_type = resp.headers.get("content-type", "audio/ogg").split(";")[0]
        ext = url.rsplit(".", 1)[-1].lower() if "." in url else "ogg"
        mime = _MIME_BY_EXT.get(ext, content_type)
        return AudioMedia(data=resp.content, mime_type=mime)


__all__ = ["DiscordMessenger", "HttpAudioDownloader"]
