"""Value objects do content: ContentType + DraftStatus + Hashtag."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_HASHTAG_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{1,49}$")


class ContentType(str, Enum):
    LINKEDIN_POST = "linkedin_post"
    NEWSLETTER = "newsletter"
    README = "readme"
    CARD = "card"
    SUMMARY = "summary"


class DraftStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    QUEUED = "queued"
    PUBLISHED = "published"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Hashtag:
    value: str

    def __post_init__(self) -> None:
        v = self.value.strip()
        if v.startswith("#"):
            v = v[1:]
        if not _HASHTAG_RE.match(v):
            raise ValueError(f"hashtag invalida: {self.value!r}")
        object.__setattr__(self, "value", v.lower())

    def display(self) -> str:
        return f"#{self.value}"


__all__ = ["ContentType", "DraftStatus", "Hashtag"]
