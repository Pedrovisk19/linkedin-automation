"""Use cases do news: FetchDailyNews (fontes -> dedupe) e GenerateDailyDigest.

FetchDailyNews: agrega N fetchers, dedupe por content_hash, persiste itens
novos.

GenerateDailyDigest: pega itens recentes (janela de X horas), chama o
``NewsDigestAgent`` (LLM) e persiste um ``ContentDraft`` (newsletter) para
revisao. Nao envia para Discord/fila — isso fica no composition root.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from developer_brain_ai_ai.application.use_cases import (
    NewsDigestAgent,
    NewsDigestDraft,
)
from developer_brain_ai_content.domain.aggregates import ContentDraft
from developer_brain_ai_content.domain.ids import ContentDraftId
from developer_brain_ai_content.domain.repositories import ContentDraftRepository
from developer_brain_ai_content.domain.value_objects import (
    ContentType,
    DraftStatus,
    Hashtag,
)
from developer_brain_ai_shared.errors.base import ValidationError
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow
from developer_brain_ai_shared.logging import get_logger
from developer_brain_ai_shared.persistence.tenant import (
    reset_tenant_context,
    set_tenant_context,
)

from developer_brain_ai_news.application.ports import DigestNotifier, NewsFetcher
from developer_brain_ai_news.domain.aggregates import NewsItem
from developer_brain_ai_news.domain.ids import NewsItemId
from developer_brain_ai_news.domain.repositories import NewsItemRepository

# ============================================================
# FetchDailyNews
# ============================================================


@dataclass
class FetchNewsResult:
    fetched: int
    inserted: int
    deduped: int
    errors: int


class FetchDailyNews:
    """Agrega N fetchers, dedupe por content_hash e persiste itens novos.

    - Roda dentro do contexto RLS (tenant corrente setado pelo chamador).
    - Cada fetcher e defensivo: erros viram ``errors`` no resultado, nao
      derrubam o job.
    - Dedupe deterministica: ``content_hash`` (sha256 de url) eh unico por
      tenant. Repository faz UPSERT com ON CONFLICT DO NOTHING.
    """

    def __init__(
        self,
        *,
        fetchers: Iterable[NewsFetcher],
        repo: NewsItemRepository,
    ) -> None:
        self._fetchers = list(fetchers)
        self._repo = repo

    async def execute(self, *, tenant_id: TenantId) -> FetchNewsResult:
        set_tenant_context(tenant_id)
        try:
            fetched_total = 0
            inserted = 0
            deduped = 0
            errors = 0

            for fetcher in self._fetchers:
                try:
                    items = await fetcher.fetch()
                except Exception as exc:
                    get_logger().warning(
                        "news fetcher crashed",
                        source=getattr(fetcher, "name", "?"),
                        error=str(exc),
                    )
                    errors += 1
                    continue
                fetched_total += len(items)

                for raw in items:
                    now = utcnow()
                    item = NewsItem(
                        id=NewsItemId.new(),
                        tenant_id=tenant_id,
                        source=raw.source,
                        title=raw.title,
                        url=raw.url,
                        published_at=raw.published_at or now,
                        timestamps=Timestamps(created_at=now, updated_at=now),
                    )
                    inserted_new = await self._repo.save(item)
                    if inserted_new:
                        inserted += 1
                    else:
                        deduped += 1

            get_logger().info(
                "news fetch done",
                fetched=fetched_total,
                inserted=inserted,
                deduped=deduped,
                errors=errors,
            )
            return FetchNewsResult(
                fetched=fetched_total,
                inserted=inserted,
                deduped=deduped,
                errors=errors,
            )
        finally:
            reset_tenant_context()


# ============================================================
# GenerateDailyDigest
# ============================================================


@dataclass
class DigestResult:
    draft_id: str
    title: str
    texto: str
    used_items: int
    notification_request_id: str = ""


class GenerateDailyDigest:
    """Gera um digest diario a partir dos news_items recentes.

    Fluxo:
    1. Lista top N itens publicados nas ultimas ``window_hours``.
    2. Chama ``NewsDigestAgent.execute`` com os itens em formato dict.
    3. Persiste um ``ContentDraft`` (content_type=NEWSLETTER) para revisao
       posterior (Discord approval, fila de publicacao).
    4. Se um ``DigestNotifier`` estiver injetado, envia o draft para
       aprovacao (ex.: botao no Discord) e popula ``notification_request_id``.
    """

    def __init__(
        self,
        *,
        news_repo: NewsItemRepository,
        drafts_repo: ContentDraftRepository,
        agent: NewsDigestAgent,
        notifier: DigestNotifier | None = None,
        window_hours: int = 24,
        max_items: int = 6,
    ) -> None:
        self._news_repo = news_repo
        self._drafts = drafts_repo
        self._agent = agent
        self._notifier = notifier
        self._window_hours = window_hours
        self._max_items = max_items

    async def execute(
        self,
        *,
        tenant_id: TenantId,
        ai_writing_tone: str = "engenheiro-senior-confiante-dona-do-aprendizado",
        ai_language: str = "pt-BR",
    ) -> DigestResult:
        set_tenant_context(tenant_id)
        try:
            since = datetime.now(UTC) - timedelta(hours=self._window_hours)
            items = await self._news_repo.list_since(tenant_id, since)
            if not items:
                raise ValidationError(
                    "nenhuma noticia encontrada na janela",
                    details={"window_hours": self._window_hours},
                )

            selected = items[: self._max_items]
            payload: list[dict[str, Any]] = [
                {
                    "id": str(i.id),
                    "source": i.source,
                    "title": i.title,
                    "url": i.url,
                    "summary": i.summary,
                    "published_at": i.published_at.isoformat(),
                }
                for i in selected
            ]

            try:
                draft_out: NewsDigestDraft = await self._agent.execute(
                    tenant_id,
                    items=payload,
                    ai_writing_tone=ai_writing_tone,
                    ai_language=ai_language,
                )
            except Exception as exc:
                get_logger().exception("news digest agent failed")
                raise ValidationError(
                    "falha ao gerar digest",
                    details={"error": str(exc)[:300]},
                ) from exc

            try:
                hashtags = [Hashtag(h) for h in draft_out.hashtags]
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

            now = utcnow()
            draft = ContentDraft(
                id=ContentDraftId.new(),
                tenant_id=tenant_id,
                agent="news_digest",
                content_type=ContentType.NEWSLETTER,
                title=draft_out.title or "Digest Python",
                body_markdown=draft_out.texto or "(digest vazio)",
                hashtags=hashtags,
                metadata={
                    "gancho": draft_out.gancho,
                    "conclusao": draft_out.conclusao,
                    "pergunta": draft_out.pergunta,
                    "cta": draft_out.cta,
                    "source_url_ids": draft_out.source_url_ids,
                    "source_items": [str(i.id) for i in selected],
                },
                status=DraftStatus.PENDING_REVIEW,
                timestamps=Timestamps(created_at=now, updated_at=now),
            )
            await self._drafts.save(draft)

            notification_request_id = ""
            if self._notifier is not None:
                try:
                    notification_request_id = await self._notifier.send(
                        tenant_id=tenant_id,
                        draft_id=str(draft.id),
                        title=draft.title,
                        body=draft.body_markdown,
                    )
                except Exception as exc:
                    get_logger().warning(
                        "news digest notify failed",
                        draft_id=str(draft.id),
                        error=str(exc)[:300],
                    )

            get_logger().info(
                "news digest created",
                draft_id=str(draft.id),
                used_items=len(selected),
                notified=bool(notification_request_id),
            )
            return DigestResult(
                draft_id=str(draft.id),
                title=draft.title,
                texto=draft.body_markdown,
                used_items=len(selected),
                notification_request_id=notification_request_id,
            )
        finally:
            reset_tenant_context()


__all__ = [
    "DigestResult",
    "FetchDailyNews",
    "FetchNewsResult",
    "GenerateDailyDigest",
]
