"""Routers do modulo ai. SEM `from __future__ import annotations` (ADR-0012)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from developer_brain_ai_ai.application.dto import SummaryAgentInput
from developer_brain_ai_ai.application.use_cases import SummaryAgent
from developer_brain_ai_ai.presentation.dto import RunSummaryInput, RunSummaryOutput


def build_router(
    *,
    summary_agent: SummaryAgent,
    journal_list_fn,
    current_user_dep,
) -> APIRouter:
    from developer_brain_ai_identity.presentation.dependencies import CurrentUser

    UserDep = Annotated[CurrentUser, Depends(current_user_dep)]
    router = APIRouter(prefix="/ai", tags=["ai"])

    @router.post("/summary", response_model=RunSummaryOutput)
    async def run_summary(current: UserDep, body: RunSummaryInput) -> RunSummaryOutput:
        entries = await journal_list_fn(
            current.tenant_id,
            since=body.start_date,
            until=body.end_date,
        )
        result = await summary_agent.execute(
            current.tenant_id,
            SummaryAgentInput(
                period_kind=body.period_kind,
                start_date=body.start_date,
                end_date=body.end_date,
                entries=entries,
            ),
        )
        return RunSummaryOutput(
            period_kind=result.period_kind,
            start_date=result.start_date,
            end_date=result.end_date,
            title=result.title,
            markdown=result.markdown,
            top_learnings=result.top_learnings,
            metrics=result.metrics,
        )

    return router


__all__ = ["build_router"]
