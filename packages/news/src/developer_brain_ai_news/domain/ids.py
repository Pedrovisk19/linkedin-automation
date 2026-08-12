"""IDs tipados do news."""

from developer_brain_ai_shared.kernel.id import TypedId


class NewsItemId(TypedId["NewsItemId"]):
    """Identificador de NewsItem."""


__all__ = ["NewsItemId"]
