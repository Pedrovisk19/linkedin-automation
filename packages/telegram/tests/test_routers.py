"""Testes dos routers do telegram (webhook + dispatch) via TestClient."""

from __future__ import annotations

import asyncio

from content_fakes import (
    FakeContentDraftRepository,
    FakePublicationQueueRepository,
)
from developer_brain_ai_content.application.use_cases import (
    CreateLinkedInDraft,
    EnqueueDraft,
    MarkPublished,
    RejectDraft,
)
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_telegram.application.use_cases import (
    HandleApprovalReply,
    HandleInboundMessage,
)
from developer_brain_ai_telegram.domain.value_objects import ChatId
from developer_brain_ai_telegram.presentation.routers import build_router
from fastapi import FastAPI
from fastapi.testclient import TestClient
from telegram_fakes import (
    FakeJournalRepository,
    FakeMessenger,
    FakeTelegramRequestRepository,
)

CHAT = ChatId(123456789)
TID = TenantId.new()


def _build_app(
    allowed_chat: ChatId | None = CHAT,
) -> tuple[FastAPI, FakeMessenger, FakeTelegramRequestRepository, FakeContentDraftRepository]:
    messenger = FakeMessenger()
    requests = FakeTelegramRequestRepository()
    drafts = FakeContentDraftRepository()
    queue = FakePublicationQueueRepository()
    inbound_uc = HandleInboundMessage(
        messenger=messenger,
        journal_repo=FakeJournalRepository(),
        requests=requests,
        create_draft=CreateLinkedInDraft(drafts),
        generate_draft=None,
    )
    approval_uc = HandleApprovalReply(
        messenger=messenger,
        requests=requests,
        enqueue=EnqueueDraft(drafts, queue),
        publish=MarkPublished(drafts, queue),  # type: ignore[arg-type]
        reject=RejectDraft(drafts),
    )
    app = FastAPI()
    app.include_router(
        build_router(
            allowed_chat=allowed_chat,
            tenant_id=TID,
            inbound_uc=inbound_uc,
            approval_uc=approval_uc,
            messenger=messenger,
        )
    )
    return app, messenger, requests, drafts


def _update(message: dict | None = None, callback: dict | None = None) -> dict:
    update: dict = {"update_id": 1}
    if message is not None:
        update["message"] = message
    if callback is not None:
        update["callback_query"] = callback
    return update


def _text_message(chat_id: int, text: str) -> dict:
    return {
        "message_id": 10,
        "date": 1750000000,
        "chat": {"id": chat_id, "type": "private"},
        "from": {"id": chat_id},
        "text": text,
    }


def test_webhook_ignores_unknown_chat() -> None:
    app, messenger, requests, _ = _build_app()
    payload = _update(message=_text_message(999888777, "ola"))
    with TestClient(app) as c:
        r = c.post("/integrations/telegram/webhook", json=payload)
    assert r.status_code == 200
    assert messenger.sent == []
    assert len(requests._by_id) == 0


def test_webhook_text_message_creates_approval() -> None:
    app, messenger, requests, _ = _build_app()
    payload = _update(message=_text_message(CHAT.value, "hoje aprendi sobre testes de webhook"))
    with TestClient(app) as c:
        r = c.post("/integrations/telegram/webhook", json=payload)
    assert r.status_code == 200
    assert len(requests._by_id) == 1
    assert messenger.sent[-1].kind == "approval"


def test_webhook_auto_bind_when_no_allowlist() -> None:
    app, _messenger, requests, _ = _build_app(allowed_chat=None)
    payload = _update(message=_text_message(555000111, "mensagem de qualquer chat"))
    with TestClient(app) as c:
        r = c.post("/integrations/telegram/webhook", json=payload)
    assert r.status_code == 200
    assert len(requests._by_id) == 1


def test_webhook_callback_unknown_request_notifies() -> None:
    app, messenger, _requests, _ = _build_app()
    callback = {
        "id": "cq-1",
        "from": {"id": CHAT.value},
        "message": _text_message(CHAT.value, "previa"),
        "data": "approve:nao-existe",
    }
    payload = _update(callback=callback)
    with TestClient(app) as c:
        r = c.post("/integrations/telegram/webhook", json=payload)
    assert r.status_code == 200
    assert messenger.answered == ["cq-1"]
    assert messenger.sent[-1].kind == "text"
    assert "Nao encontrei" in messenger.sent[-1].text


def test_webhook_callback_approve_flow_with_created_request() -> None:
    app, messenger, requests, drafts = _build_app()
    inbound_uc = HandleInboundMessage(
        messenger=messenger,
        journal_repo=FakeJournalRepository(),
        requests=requests,
        create_draft=CreateLinkedInDraft(drafts),
        generate_draft=None,
    )
    request = asyncio.run(
        inbound_uc.execute(
            tenant_id=TID,
            chat_id=CHAT,
            text="conteudo para publicar via webhook",
            audio_media_id=None,
        )
    )
    before = len(messenger.sent)

    callback = {
        "id": "cq-2",
        "from": {"id": CHAT.value},
        "message": _text_message(CHAT.value, "previa"),
        "data": f"approve:{request.id}",
    }
    with TestClient(app) as c:
        r = c.post("/integrations/telegram/webhook", json=_update(callback=callback))
    assert r.status_code == 200
    assert len(messenger.sent) == before + 1
    assert messenger.sent[-1].kind == "text"
    assert messenger.answered == ["cq-2"]


def test_webhook_callback_reject_flow() -> None:
    app, messenger, requests, drafts = _build_app()
    inbound_uc = HandleInboundMessage(
        messenger=messenger,
        journal_repo=FakeJournalRepository(),
        requests=requests,
        create_draft=CreateLinkedInDraft(drafts),
        generate_draft=None,
    )
    request = asyncio.run(
        inbound_uc.execute(
            tenant_id=TID,
            chat_id=CHAT,
            text="conteudo que sera rejeitado via webhook",
            audio_media_id=None,
        )
    )
    before = len(messenger.sent)

    callback = {
        "id": "cq-3",
        "from": {"id": CHAT.value},
        "message": _text_message(CHAT.value, "previa"),
        "data": f"reject:{request.id}",
    }
    with TestClient(app) as c:
        r = c.post("/integrations/telegram/webhook", json=_update(callback=callback))
    assert r.status_code == 200
    assert len(messenger.sent) == before + 1
    assert "nao publiquei" in messenger.sent[-1].text


def test_webhook_malformed_json_returns_ok() -> None:
    app, _, _, _ = _build_app()
    with TestClient(app) as c:
        r = c.post(
            "/integrations/telegram/webhook",
            content="not-json{",
            headers={"Content-Type": "application/json"},
        )
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
