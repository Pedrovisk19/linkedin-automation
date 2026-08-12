"""Ports do discord: colaboradores injetados sem acoplamento a infra."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from developer_brain_ai_discord.domain.value_objects import ChannelId


@dataclass
class AudioMedia:
    """Audio baixado da integracao, pronto para transcricao."""

    data: bytes
    mime_type: str = "audio/ogg"


class Messenger(Protocol):
    """Envia mensagens de texto e pedidos de aprovacao com botoes."""

    async def send_text(self, *, to: ChannelId, text: str) -> None: ...

    async def send_approval_request(
        self, *, to: ChannelId, request_id: str, title: str, body: str
    ) -> None: ...

    async def answer_callback(self, callback_query_id: str) -> None: ...


class AudioDownloader(Protocol):
    """Baixa um audio pelo id da midia (URL do anexo no Discord)."""

    async def download_audio(self, media_id: str) -> AudioMedia: ...


class AudioTranscriber(Protocol):
    """Transcreve audio em texto (OpenAI Whisper)."""

    async def transcribe(self, media: AudioMedia) -> str: ...


__all__ = ["AudioDownloader", "AudioMedia", "AudioTranscriber", "Messenger"]
