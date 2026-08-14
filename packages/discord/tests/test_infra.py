"""Testes da infrastrutura discord sem gateway real.

- DiscordMessenger: fake de client/channel captura envios e componentes.
- HttpAudioDownloader: respx simula o CDN do Discord.
- OpenAIWhisperTranscriber: client OpenAI fake.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx
from developer_brain_ai_discord.domain.ports import AudioMedia
from developer_brain_ai_discord.domain.value_objects import ChannelId
from developer_brain_ai_discord.infrastructure.discord_client import (
    DiscordMessenger,
    HttpAudioDownloader,
)
from developer_brain_ai_discord.infrastructure.transcriber import OpenAIWhisperTranscriber
from developer_brain_ai_discord.presentation.bot import (
    _first_audio_attachment,
    _parse_approval,
)
from developer_brain_ai_shared.errors.base import IntegrationError

CHANNEL = ChannelId(987654321)


class _FakeChannel:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object | None, object | None]] = []

    async def send(
        self,
        content: str,
        *,
        view: object | None = None,
        file: object | None = None,
    ) -> None:
        self.sent.append((content, view, file))


class _FakeClient:
    def __init__(self, channel: _FakeChannel | None, *, cached: bool = True) -> None:
        self._channel = channel
        self._cached = cached
        self._fetches = 0

    def get_channel(self, channel_id: int) -> _FakeChannel | None:
        return self._channel if self._cached else None

    async def fetch_channel(self, channel_id: int) -> _FakeChannel | None:
        self._fetches += 1
        return self._channel


def test_messenger_send_text_uses_cached_channel() -> None:
    channel = _FakeChannel()
    messenger = DiscordMessenger(_FakeClient(channel))  # type: ignore[arg-type]

    asyncio.run(messenger.send_text(to=CHANNEL, text="oi"))

    assert channel.sent == [("oi", None, None)]


def test_messenger_send_approval_creates_buttons() -> None:
    channel = _FakeChannel()
    messenger = DiscordMessenger(_FakeClient(channel))  # type: ignore[arg-type]

    asyncio.run(
        messenger.send_approval_request(
            to=CHANNEL, request_id="req-1", title="Titulo", body="Corpo"
        )
    )

    (content, view, _file) = channel.sent[0]
    assert content == "Titulo\n\nCorpo"
    custom_ids = [item.custom_id for item in view.children]
    assert "approve:req-1" in custom_ids
    assert "reject:req-1" in custom_ids


def test_messenger_send_approval_attaches_full_post_and_marks_continuation() -> None:
    channel = _FakeChannel()
    messenger = DiscordMessenger(_FakeClient(channel))  # type: ignore[arg-type]
    title = "Titulo"
    body = "".join(f"linha {i}\n" for i in range(700))

    asyncio.run(
        messenger.send_approval_request(
            to=CHANNEL, request_id="req-2", title=title, body=body
        )
    )

    assert len(channel.sent) >= 2
    for chunk, _view, _file in channel.sent[:-1]:
        assert len(chunk) <= 2000
        assert "→ continua na próxima mensagem" in chunk
    (last_content, last_view, last_file) = channel.sent[-1]
    assert "linha 699" in last_content
    custom_ids = [item.custom_id for item in last_view.children]
    assert "approve:req-2" in custom_ids
    assert last_file is not None
    assert getattr(last_file, "filename", None) == "post.md"


def test_messenger_fetches_channel_when_not_cached() -> None:
    channel = _FakeChannel()
    client = _FakeClient(channel, cached=False)
    messenger = DiscordMessenger(client)  # type: ignore[arg-type]

    asyncio.run(messenger.send_text(to=CHANNEL, text="via fetch"))

    assert client._fetches == 1
    assert channel.sent == [("via fetch", None, None)]


@pytest.mark.asyncio
async def test_messenger_missing_channel_raises_integration_error() -> None:
    messenger = DiscordMessenger(_FakeClient(None))  # type: ignore[arg-type]

    with pytest.raises(IntegrationError) as exc:
        await messenger.send_text(to=CHANNEL, text="oi")

    assert "canal do Discord" in str(exc.value.message)


@pytest.mark.asyncio
async def test_messenger_answer_callback_is_noop() -> None:
    messenger = DiscordMessenger(_FakeClient(_FakeChannel()))  # type: ignore[arg-type]
    await messenger.answer_callback("any")


def test_audio_downloader_downloads_and_maps_mime() -> None:
    with respx.mock:
        route = respx.get("https://cdn.example/audio/a.mp3").mock(
            return_value=httpx.Response(
                200, content=b"audio-bytes", headers={"content-type": "audio/mpeg"}
            )
        )
        downloader = HttpAudioDownloader()

        media = asyncio.run(downloader.download_audio("https://cdn.example/audio/a.mp3"))

    assert route.called
    assert media.data == b"audio-bytes"
    assert media.mime_type == "audio/mpeg"


def test_audio_downloader_failure_raises() -> None:
    with respx.mock:
        respx.get("https://cdn.example/broken.ogg").mock(return_value=httpx.Response(404))
        downloader = HttpAudioDownloader()

        with pytest.raises(IntegrationError):
            asyncio.run(downloader.download_audio("https://cdn.example/broken.ogg"))


class _FakeAudioTranscriptions:
    """Objeta o path client.audio.transcriptions do AsyncOpenAI."""

    def __init__(self, text: str = "transcricao fake") -> None:
        self._text = text
        self.files: list[tuple] = []

    async def create(self, *, model: str, file) -> object:
        _ = model
        self.files.append(file)

        class _Resp:
            text = self._text

        return _Resp()


class _FakeWhisperClient:
    def __init__(self, transcriptions: _FakeAudioTranscriptions) -> None:
        self.audio = _FakeAudio(transcriptions)


class _FakeAudio:
    def __init__(self, transcriptions: _FakeAudioTranscriptions) -> None:
        self.transcriptions = transcriptions


@pytest.mark.asyncio
async def test_transcriber_sends_audio_and_returns_text() -> None:
    transcriptions = _FakeAudioTranscriptions("aprendizado transcrito")
    transcriber = OpenAIWhisperTranscriber(_FakeWhisperClient(transcriptions))  # type: ignore[arg-type]

    text = await transcriber.transcribe(AudioMedia(data=b"x", mime_type="audio/ogg"))

    assert text == "aprendizado transcrito"
    filename, payload, mime = transcriptions.files[0]
    assert filename == "audio.ogg"
    assert mime == "audio/ogg"
    assert payload.read() == b"x"


@pytest.mark.asyncio
async def test_transcriber_failure_raises_integration_error() -> None:
    class _FailingAudio:
        async def create(self, *, model: str, file) -> object:
            raise RuntimeError("openai down")

    class _FailingClient:
        audio = _FailingAudio()

    transcriber = OpenAIWhisperTranscriber(_FailingClient())  # type: ignore[arg-type]

    with pytest.raises(IntegrationError) as exc:
        await transcriber.transcribe(AudioMedia(data=b"x"))

    assert "transcrever audio" in str(exc.value.message)


def test_parse_approval_custom_ids() -> None:
    assert _parse_approval("approve:abc-123") == (True, "abc-123")
    assert _parse_approval("reject:abc-123") == (False, "abc-123")
    assert _parse_approval("other:x") == (None, "")
    assert _parse_approval(None) == (None, "")


def test_first_audio_attachment_picks_audio_only() -> None:
    class _Att:
        def __init__(self, content_type: str, url: str | None) -> None:
            self.content_type = content_type
            self.url = url

    attachments = [
        _Att("image/png", "https://cdn/x.png"),
        _Att("audio/ogg", "https://cdn/a.ogg"),
    ]
    assert _first_audio_attachment(attachments) == "https://cdn/a.ogg"
    assert _first_audio_attachment([]) is None
    assert _first_audio_attachment([_Att("text/plain", "https://cdn/t.txt")]) is None
