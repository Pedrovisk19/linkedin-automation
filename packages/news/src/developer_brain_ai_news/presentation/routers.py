"""Routers do news — POST /news/fetch + POST /news/digest + GET /news/recent.

NAO usa `from __future__ import annotations` (ADR-0012).
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from developer_brain_ai_identity.presentation.dependencies import (
    CurrentUser,
    CurrentUserDependency,
)
from fastapi import APIRouter, Depends, Query

from developer_brain_ai_news.application.use_cases import (
    DigestResult,
    FetchDailyNews,
    FetchNewsResult,
    GenerateDailyDigest,
)
from developer_brain_ai_news.domain.aggregates import NewsItem
from developer_brain_ai_news.domain.repositories import NewsItemRepository


def _item_to_out(item: NewsItem) -> dict[str, object]:
    return {
        "id": str(item.id),
        "source": item.source,
        "title": item.title,
        "url": item.url,
        "summary": item.summary,
        "published_at": item.published_at.isoformat(),
    }


def build_router(
    *,
    fetch_uc: FetchDailyNews,
    digest_uc: GenerateDailyDigest,
    repo: NewsItemRepository,
    current_user_dep: CurrentUserDependency,
) -> APIRouter:

    UserDep = Annotated[CurrentUser, Depends(current_user_dep)]
    router = APIRouter(prefix="/news", tags=["news"])

    @router.post("/fetch", response_model=FetchNewsResult, status_code=200)
    async def fetch(current: UserDep) -> FetchNewsResult:
        return await fetch_uc.execute(tenant_id=current.tenant_id)

    @router.post("/digest", response_model=DigestResult, status_code=200)
    async def digest(current: UserDep) -> DigestResult:
        return await digest_uc.execute(tenant_id=current.tenant_id)

    @router.get("/recent")
    async def recent(
        current: UserDep,
        hours: Annotated[int, Query(ge=1, le=168)] = 24,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> list[dict[str, object]]:
        since = datetime.now(UTC) - timedelta(hours=hours)
        items = await repo.list_since(current.tenant_id, since, limit=limit)
        return [_item_to_out(i) for i in items]

    return router


__all__ = ["build_router"]
