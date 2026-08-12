"""Agregado NewsItem: 1 item coletado de uma fonte externa (RSS/HN/PyPI).

Imutavel apos criacao. A dedupe e garantida pelo ``content_hash`` (sha256 de
url+published_at) unico no banco por tenant. O ``source`` identifica a fonte
(realpython, pythoninsider, peps, hackernews, github_trending) para que o
digest possa ranquear por diversidade.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime

from developer_brain_ai_shared.errors.base import ValidationError
from developer_brain_ai_shared.kernel import AggregateRoot
from developer_brain_ai_shared.kernel.id import TenantId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow

from developer_brain_ai_news.domain.ids import NewsItemId


def _hash(url: str, published_at: datetime) -> str:
    # Hash so por url: items RSS tem URL unica por fonte, independente de
    # microsegundos/tz do published_at (que pode variar entre parses).
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


@dataclass(eq=False)
class NewsItem(AggregateRoot):
    id: NewsItemId
    tenant_id: TenantId
    source: str
    title: str
    url: str
    published_at: datetime
    summary: str = ""
    content_hash: str = ""
    timestamps: Timestamps = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValidationError("title nao pode ser vazio", details={"field": "title"})
        if len(self.title) > 500:
            raise ValidationError("title excede 500 chars", details={"field": "title"})
        if not self.url or not self.url.strip():
            raise ValidationError("url nao pode ser vazio", details={"field": "url"})
        if len(self.url) > 2000:
            raise ValidationError("url excede 2000 chars", details={"field": "url"})
        if not self.source or not self.source.strip():
            raise ValidationError("source nao pode ser vazio", details={"field": "source"})
        if len(self.source) > 64:
            raise ValidationError("source excede 64 chars", details={"field": "source"})
        if len(self.summary) > 4000:
            raise ValidationError("summary excede 4000 chars", details={"field": "summary"})
        if not self.content_hash:
            object.__setattr__(self, "content_hash", _hash(self.url, self.published_at))
        if self.timestamps is None:
            now = utcnow()
            object.__setattr__(self, "timestamps", Timestamps(created_at=now, updated_at=now))


__all__ = ["NewsItem"]
