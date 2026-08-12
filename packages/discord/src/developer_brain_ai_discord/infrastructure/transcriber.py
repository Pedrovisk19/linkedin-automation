"""Transcricao de audio via OpenAI Whisper (audio.transcriptions)."""

from __future__ import annotations

import io

from developer_brain_ai_shared.errors.base import IntegrationError
from developer_brain_ai_shared.logging import get_logger
from openai import AsyncOpenAI

from developer_brain_ai_discord.domain.ports import AudioMedia

_EXTENSIONS = {
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/wav": "wav",
    "audio/webm": "webm",
    "audio/amr": "amr",
}


class OpenAIWhisperTranscriber:
    def __init__(self, client: AsyncOpenAI, *, model: str = "whisper-1") -> None:
        self._client = client
        self._model = model

    async def transcribe(self, media: AudioMedia) -> str:
        ext = _EXTENSIONS.get(media.mime_type, "ogg")
        try:
            response = await self._client.audio.transcriptions.create(
                model=self._model,
                file=(f"audio.{ext}", io.BytesIO(media.data), media.mime_type),
            )
        except Exception as exc:
            get_logger().warning("whisper transcription failed", error=str(exc))
            raise IntegrationError(
                "falha ao transcrever audio do Discord",
                details={"error": str(exc)[:300]},
            ) from exc
        return response.text


__all__ = ["OpenAIWhisperTranscriber"]
