"""Routers do content. SEM from __future__ import annotations (ADR-0012)."""

from datetime import datetime
from typing import Annotated

from developer_brain_ai_identity.presentation.dependencies import (
    CurrentUser,
    CurrentUserDependency,
)
from fastapi import APIRouter, Body, Depends

from developer_brain_ai_content.application.dto import (
    CreateLinkedInDraftInput,
    GenerateLinkedInInput,
    LinkedInDraftOutput,
    ListDraftsOutput,
)
from developer_brain_ai_content.application.use_cases import (
    CreateLinkedInDraft,
    EnqueueDraft,
    GenerateLinkedInDraft,
    GetDraft,
    ListDrafts,
    MarkPublished,
    RejectDraft,
)


def build_router(
    *,
    create_linkedin_uc: CreateLinkedInDraft,
    list_drafts_uc: ListDrafts,
    get_draft_uc: GetDraft,
    enqueue_uc: EnqueueDraft,
    mark_published_uc: MarkPublished,
    reject_uc: RejectDraft,
    current_user_dep: CurrentUserDependency,
    generate_linkedin_uc: GenerateLinkedInDraft | None = None,
) -> APIRouter:

    UserDep = Annotated[CurrentUser, Depends(current_user_dep)]
    router = APIRouter(prefix="/content", tags=["content"])

    @router.post("/linkedin", response_model=LinkedInDraftOutput, status_code=201)
    async def create_linkedin(
        current: UserDep, body: CreateLinkedInDraftInput
    ) -> LinkedInDraftOutput:
        return await create_linkedin_uc.execute(current.tenant_id, body)

    if generate_linkedin_uc is not None:

        @router.post("/linkedin/generate", response_model=LinkedInDraftOutput, status_code=201)
        async def generate_linkedin(
            current: UserDep, body: GenerateLinkedInInput
        ) -> LinkedInDraftOutput:
            return await generate_linkedin_uc.execute(current.tenant_id, body)

    @router.get("/drafts", response_model=list[ListDraftsOutput])
    async def list_drafts(
        current: UserDep,
        content_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[ListDraftsOutput]:
        return await list_drafts_uc.execute(
            current.tenant_id,
            content_type=content_type,
            status=status,
            page=page,
            page_size=page_size,
        )

    @router.get("/drafts/{draft_id}", response_model=LinkedInDraftOutput)
    async def get_draft(current: UserDep, draft_id: str) -> LinkedInDraftOutput:
        return await get_draft_uc.execute(current.tenant_id, draft_id)

    @router.post("/drafts/{draft_id}/enqueue", status_code=202)
    async def enqueue(
        current: UserDep,
        draft_id: str,
        scheduled_for: Annotated[datetime | None, Body()] = None,
    ) -> None:
        await enqueue_uc.execute(current.tenant_id, draft_id, scheduled_for)

    @router.post("/drafts/{draft_id}/publish", status_code=200)
    async def publish(current: UserDep, draft_id: str) -> dict[str, str]:
        return await mark_published_uc.execute(current.tenant_id, draft_id)

    @router.post("/drafts/{draft_id}/reject", status_code=200)
    async def reject(
        current: UserDep, draft_id: str, reason: Annotated[str | None, Body()] = None
    ) -> dict[str, str]:
        await reject_uc.execute(current.tenant_id, draft_id, reason)
        return {"status": "rejected"}

    return router


__all__ = ["build_router"]
