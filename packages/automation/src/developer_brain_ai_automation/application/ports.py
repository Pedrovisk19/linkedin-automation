"""Portas do pipeline diario (Fase 7a).

Automation nao conhece ai/journal/content: recebe por injeccao as portas abaixo
e o worker (app) faz o wiring com os adaptadores reais.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from developer_brain_ai_shared.kernel.id import TenantId


class TenantLister(Protocol):
    """Lista tenants ativos para rodar o pipeline."""

    async def list_active(self) -> list[TenantId]: ...


class DailyEntryReader(Protocol):
    """Le diario do tenant (entries do journal) para um dia especifico."""

    async def list_entries(self, *, tenant_id: TenantId, day: date) -> list[dict]: ...


class DailySummaryGenerator(Protocol):
    """Gera o resumo diario a partir das entries (SummaryAgent real no worker)."""

    async def generate(self, *, tenant_id: TenantId, entries: list[dict]) -> str: ...


class LinkedInDraftCreator(Protocol):
    """Cria o rascunho de post do LinkedIn a partir das entries.

    Retorna o id do draft criado (ContentDraft). Em caso de falha, raise.
    """

    async def create(self, *, tenant_id: TenantId, entries: list[dict]) -> str: ...


class DraftQueuer(Protocol):
    """Enfileira um draft ja criado para publicacao em scheduled_for."""

    async def enqueue(
        self, *, tenant_id: TenantId, draft_id: str, scheduled_for: datetime
    ) -> None: ...


__all__ = [
    "DailyEntryReader",
    "DailySummaryGenerator",
    "DraftQueuer",
    "LinkedInDraftCreator",
    "TenantLister",
]
