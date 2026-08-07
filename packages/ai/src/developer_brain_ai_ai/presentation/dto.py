"""DTOs de apresentacao do ai (routers)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class RunSummaryInput(BaseModel):
    period_kind: str = Field(pattern=r"^(daily|weekly|monthly)$")
    start_date: date
    end_date: date


class RunSummaryOutput(BaseModel):
    period_kind: str
    start_date: date
    end_date: date
    title: str
    markdown: str
    top_learnings: list[str]
    metrics: dict[str, int]


__all__ = ["RunSummaryInput", "RunSummaryOutput"]