"""DTOs dos agentes — cada agente tem seu proprio DTO in/out p/ clareza.

SummaryAgent:
  input = SummaryAgentInput (list of journal entry dicts + period)
  output = SummaryAgentOutput (title + sections em markdown)
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SummaryAgentInput(BaseModel):
    period_kind: str = Field(pattern=r"^(daily|weekly|monthly)$")
    start_date: date
    end_date: date
    entries: list[dict] = Field(default_factory=list)


class SummaryAgentOutput(BaseModel):
    period_kind: str
    start_date: date
    end_date: date
    title: str
    markdown: str
    top_learnings: list[str] = Field(default_factory=list)
    metrics: dict[str, int] = Field(default_factory=dict)


__all__ = ["SummaryAgentInput", "SummaryAgentOutput"]
