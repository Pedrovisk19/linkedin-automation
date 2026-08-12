"""Bounded context: news — fetch de fontes externas + dedupe + digest."""

from developer_brain_ai_news.domain import NewsItem, NewsItemId, NewsItemRepository

__all__ = ["NewsItem", "NewsItemId", "NewsItemRepository"]
