"""Composition helper do news — monta fetchers + repo + router com DI."""

from developer_brain_ai_identity.presentation.dependencies import CurrentUserDependency

from developer_brain_ai_news.application.ports import DigestNotifier
from developer_brain_ai_news.application.use_cases import (
    FetchDailyNews,
    GenerateDailyDigest,
)
from developer_brain_ai_news.domain.repositories import NewsItemRepository
from developer_brain_ai_news.presentation.routers import build_router


def mount_news(
    *,
    fetch_uc: FetchDailyNews,
    digest_uc: GenerateDailyDigest,
    repo: NewsItemRepository,
    current_user_dep: CurrentUserDependency,
):
    return build_router(
        fetch_uc=fetch_uc,
        digest_uc=digest_uc,
        repo=repo,
        current_user_dep=current_user_dep,
    )


__all__ = ["DigestNotifier", "mount_news"]
