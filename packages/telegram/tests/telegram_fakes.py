"""Fakes para telegram tests (sem DB e sem HTTP)."""

from __future__ import annotations

from dataclasses import dataclass

from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_telegram.domain.aggregates import TelegramRequest
from developer_brain_ai_telegram.domain.ports import AudioMedia


class FakeTelegramRequestRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, TelegramRequest] = {}

    async def get_by_id(
        self, tenant_id: TenantId, request_id: object
    ) -> TelegramRequest | None:
        r = self._by_id.get(str(request_id))
        if r is None or r.tenant_id != tenant_id:
            return None
        return r

    async def get_pending_by_chat(
        self, tenant_id: TenantId, chat_id: int
    ) -> TelegramRequest | None:
        for r in self._by_id.values():
            if r.tenant_id == tenant_id and r.chat_id.value == chat_id and r.is_pending:
                return r
        return None

    async def save(self, request: TelegramRequest) -> None:
        self._by_id[str(request.id)] = request


@dataclass
class _SentMessage:
    kind: str
    to: int
    text: str = ""
    request_id: str = ""
    title: str = ""
    body: str = ""


class FakeMessenger:
    def __init__(self) -> None:
        self.sent: list[_SentMessage] = []
        self.answered: list[str] = []

    async def send_text(self, *, to, text: str) -> None:
        self.sent.append(_SentMessage(kind="text", to=to.value, text=text))

    async def send_approval_request(
        self, *, to, request_id: str, title: str, body: str
    ) -> None:
        self.sent.append(
            _SentMessage(
                kind="approval",
                to=to.value,
                request_id=request_id,
                title=title,
                body=body,
            )
        )

    async def answer_callback(self, callback_query_id: str) -> None:
        self.answered.append(callback_query_id)


class FakeJournalRepository:
    def __init__(self) -> None:
        self.entries: list[object] = []

    async def save(self, entry) -> None:
        self.entries.append(entry)

    async def list(self, tenant_id, *, since=None, until=None) -> list[object]:
        return self.entries


class FakeTranscriber:
    def __init__(self, text: str = "aprendizado do audio") -> None:
        self._text = text
        self.calls = 0

    async def transcribe(self, media: AudioMedia) -> str:
        self.calls += 1
        return self._text


class FakeDownloader:
    def __init__(self, mime: str = "audio/ogg") -> None:
        self._mime = mime
        self.calls = 0

    async def download_audio(self, media_id: str) -> AudioMedia:
        self.calls += 1
        return AudioMedia(data=b"audio-bytes", mime_type=self._mime)


__all__ = [
    "FakeDownloader",
    "FakeJournalRepository",
    "FakeMessenger",
    "FakeTelegramRequestRepository",
    "FakeTranscriber",
]
