"""Fetchers de noticias Python: RSS (feedparser) + APIs JSON (httpx).

Padrao: cada fetcher expoe ``name`` e ``async def fetch() -> list[FetchedItem]``.
Sao defensivos: timeout/parse falho -> lista vazia + log (NUNCA levanta —
o use case agrega multiplas fontes e uma offline nao derruba o batch).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import httpx
from developer_brain_ai_shared.logging import get_logger

from developer_brain_ai_news.application.ports import FetchedItem

_PY_KEYWORDS = (
    "python",
    "django",
    "flask",
    "fastapi",
    "pytorch",
    "pandas",
    "numpy",
    "scikit-learn",
    "scikit",
    "tensorflow",
    "cpython",
    "pypy",
    "pytest",
    "pylance",
    "pyenv",
    "asyncio",
)
_HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
_HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
_GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


def _parse_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(UTC)
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except TypeError, ValueError:
        return datetime.now(UTC)


def _sanitize(value: str, limit: int) -> str:
    truncated = value.strip()
    return truncated if len(truncated) <= limit else truncated[: limit - 1] + "…"


class _AsyncRssFetcher:
    """Template async: baixa via httpx (async) e parseia via feedparser (sync)."""

    name: str = "rss"
    _url: str = ""
    _source_label: str = "rss"
    _timeout: float = 15.0

    def __init__(self, *, url: str | None = None, timeout: float | None = None) -> None:
        if url is not None:
            self._url = url
        if timeout is not None:
            self._timeout = timeout

    async def fetch(self) -> list[FetchedItem]:
        if not self._url:
            return []
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers={"User-Agent": "developer-brain-ai-news/0.1 (+local)"},
            ) as client:
                resp = await client.get(self._url)
                if resp.status_code >= 400:
                    get_logger().warning(
                        "news fetch http error",
                        source=self._source_label,
                        status_code=resp.status_code,
                    )
                    return []
                body = resp.content
        except Exception as exc:
            get_logger().warning("news fetch failed", source=self._source_label, error=str(exc))
            return []

        parsed = feedparser.parse(body)
        items: list[FetchedItem] = []
        for entry in parsed.entries[:20]:
            title = _sanitize(getattr(entry, "title", "") or "", 500)
            url = _sanitize(getattr(entry, "link", "") or "", 2000)
            if not title or not url:
                continue
            summary = _sanitize(
                getattr(entry, "summary", "") or getattr(entry, "description", "") or "",
                4000,
            )
            published = _parse_date(getattr(entry, "published", None))
            items.append(
                FetchedItem(
                    source=self._source_label,
                    title=title,
                    url=url,
                    summary=summary,
                    published_at=published,
                )
            )
        get_logger().info("news fetched", source=self._source_label, count=len(items))
        return items


class RealPythonFetcher(_AsyncRssFetcher):
    name = "realpython"
    _source_label = "realpython"
    _url = "https://realpython.com/atom.xml"


class PythonInsiderFetcher(_AsyncRssFetcher):
    name = "pythoninsider"
    _source_label = "pythoninsider"
    _url = "https://pythoninsider.blogspot.com/feeds/posts/default"


class PepsFetcher(_AsyncRssFetcher):
    name = "peps"
    _source_label = "peps"
    _url = "https://www.python.org/dev/peps/peps.rss"


class PyPiLatestFetcher(_AsyncRssFetcher):
    name = "pypi"
    _source_label = "pypi"
    _url = "https://pypi.org/rss/updates.xml"


class HackerNewsFetcher:
    """Top stories do Hacker News filtradas por keywords Python.

    Usa a API publica do Firebase (sem auth) — pega top 30 stories, fetch
    item por item e filtra titulo/url no conjunto de keywords Python.
    Defensive: timeout/erro -> lista vazia + log.
    """

    name = "hackernews"
    _timeout: float = 20.0
    _sample_size: int = 30

    def __init__(self, *, sample_size: int | None = None, timeout: float | None = None) -> None:
        if sample_size is not None:
            self._sample_size = sample_size
        if timeout is not None:
            self._timeout = timeout

    async def fetch(self) -> list[FetchedItem]:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers={"User-Agent": "developer-brain-ai-news/0.1 (+local)"},
            ) as client:
                ids_resp = await client.get(_HN_TOP_STORIES_URL)
                if ids_resp.status_code >= 400:
                    get_logger().warning(
                        "news fetch http error",
                        source=self.name,
                        status_code=ids_resp.status_code,
                    )
                    return []
                story_ids = ids_resp.json()[: self._sample_size]

                items: list[FetchedItem] = []
                for sid in story_ids:
                    item_resp = await client.get(_HN_ITEM_URL.format(item_id=sid))
                    if item_resp.status_code >= 400:
                        continue
                    data = item_resp.json()
                    title = (data.get("title") or "").strip()
                    url = (data.get("url") or f"https://news.ycombinator.com/item?id={sid}").strip()
                    score = data.get("score") or 0
                    blob = f"{title} {url}".lower()
                    if not any(kw in blob for kw in _PY_KEYWORDS):
                        continue
                    ts = data.get("time") or 0
                    published = datetime.fromtimestamp(ts, tz=UTC) if ts else datetime.now(UTC)
                    items.append(
                        FetchedItem(
                            source=self.name,
                            title=_sanitize(title, 500),
                            url=_sanitize(url, 2000),
                            summary=f"HN score: {score}",
                            published_at=published,
                        )
                    )
                get_logger().info("news fetched", source=self.name, count=len(items))
                return items
        except Exception as exc:
            get_logger().warning("news fetch failed", source=self.name, error=str(exc))
            return []


class GitHubTrendingFetcher:
    """Repositorios Python em alta via GitHub Search API.

    Busca repos criados nos ultimos 7 dias, linguagem Python, ordenados por
    estrelas. Sem auth (rate limit 10 req/min — suficiente para 1 fetch/dia).
    Defensive: timeout/rate-limit -> lista vazia + log.
    """

    name = "github_trending"
    _timeout: float = 20.0
    _max_items: int = 10

    def __init__(self, *, max_items: int | None = None, timeout: float | None = None) -> None:
        if max_items is not None:
            self._max_items = max_items
        if timeout is not None:
            self._timeout = timeout

    async def fetch(self) -> list[FetchedItem]:
        try:
            since_date = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%d")
            params = {
                "q": f"language:python created:>{since_date}",
                "sort": "stars",
                "order": "desc",
                "per_page": self._max_items,
            }
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers={
                    "User-Agent": "developer-brain-ai-news/0.1 (+local)",
                    "Accept": "application/vnd.github+json",
                },
            ) as client:
                resp = await client.get(_GITHUB_SEARCH_URL, params=params)
                if resp.status_code >= 400:
                    get_logger().warning(
                        "news fetch http error",
                        source=self.name,
                        status_code=resp.status_code,
                    )
                    return []
                data = resp.json()
                if not isinstance(data, dict):
                    get_logger().warning(
                        "news fetch bad payload", source=self.name, payload_type=type(data).__name__
                    )
                    return []
                repos = data.get("items") or []
                items: list[FetchedItem] = []
                for repo in repos[: self._max_items]:
                    if not isinstance(repo, dict):
                        continue
                    full_name = repo.get("full_name", "") or ""
                    description = repo.get("description") or ""
                    html_url = repo.get("html_url", "") or ""
                    stars = repo.get("stargazers_count", 0) or 0
                    forks = repo.get("forks_count", 0) or 0
                    created_raw = repo.get("created_at", "") or ""
                    try:
                        published = (
                            datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                            if created_raw
                            else datetime.now(UTC)
                        )
                    except ValueError, TypeError:
                        published = datetime.now(UTC)
                    items.append(
                        FetchedItem(
                            source=self.name,
                            title=_sanitize(f"{full_name} — {description}", 500),
                            url=_sanitize(html_url, 2000),
                            summary=f"stars: {stars} | forks: {forks} | {description[:300]}",
                            published_at=published,
                        )
                    )
                get_logger().info("news fetched", source=self.name, count=len(items))
                return items
        except Exception as exc:
            get_logger().warning("news fetch failed", source=self.name, error=str(exc))
            return []


__all__ = [
    "GitHubTrendingFetcher",
    "HackerNewsFetcher",
    "PepsFetcher",
    "PyPiLatestFetcher",
    "PythonInsiderFetcher",
    "RealPythonFetcher",
]
