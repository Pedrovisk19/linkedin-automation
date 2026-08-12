"""Domain do modulo news."""

from developer_brain_ai_news.domain.aggregates import NewsItem
from developer_brain_ai_news.domain.ids import NewsItemId
from developer_brain_ai_news.domain.repositories import NewsItemRepository

__all__ = ["NewsItem", "NewsItemId", "NewsItemRepository"]
