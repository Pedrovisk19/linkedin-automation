"""Ports do news: NewsFetcher (fonte externa) e NewsItemRepository (persistencia)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class FetchedItem:
    """Item cru retornado por um NewsFetcher (ainda sem tenant/id)."""

    source: str
    title: str
    url: str
    summary: str
    published_at: datetime


class NewsFetcher(Protocol):
    """Fonte externa de noticias (RSS, API, scrape).

    Implementacoes devem ser defensivas: timeout, parse falho, HTTP 5xx →
    retornar lista vazia, nunca levantar (o use case agrega multiplas fontes).
    """

    name: str

    async def fetch(self) -> list[FetchedItem]: ...


class DigestNotifier(Protocol):
    """Envia um draft gerado para aprovacao (ex.: botao no Discord).

    O composition root injeta o adapter concreto (SendDraftToChannel do
    modulo discord). Se None, o digest apenas fica persistido para revisao
    manual via endpoints /content/drafts/...
    """

    async def send(
        self,
        *,
        tenant_id: object,
        draft_id: str,
        title: str,
        body: str,
    ) -> str: ...


__all__ = ["DigestNotifier", "FetchedItem", "NewsFetcher"]
