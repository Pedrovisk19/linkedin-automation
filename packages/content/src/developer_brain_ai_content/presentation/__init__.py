"""Composition helper do content."""

from fastapi import APIRouter

from developer_brain_ai_content.application.ports import LinkedInGenerator
from developer_brain_ai_content.application.use_cases import (
    CreateLinkedInDraft,
    EnqueueDraft,
    GenerateLinkedInDraft,
    GetDraft,
    ListDrafts,
    MarkPublished,
    RejectDraft,
)


def mount_content(
    *,
    drafts_repo,
    queue_repo,
    current_user_dep,
    linkedin_generator: LinkedInGenerator | None = None,
) -> APIRouter:
    from developer_brain_ai_content.presentation.routers import build_router

    create = CreateLinkedInDraft(drafts_repo)
    list_uc = ListDrafts(drafts_repo)
    get_uc = GetDraft(drafts_repo)
    enqueue_uc = EnqueueDraft(drafts_repo, queue_repo)
    publish_uc = MarkPublished(drafts_repo, queue_repo)
    reject_uc = RejectDraft(drafts_repo)
    generate_uc = (
        GenerateLinkedInDraft(drafts_repo, linkedin_generator) if linkedin_generator else None
    )

    return build_router(
        create_linkedin_uc=create,
        list_drafts_uc=list_uc,
        get_draft_uc=get_uc,
        enqueue_uc=enqueue_uc,
        mark_published_uc=publish_uc,
        reject_uc=reject_uc,
        generate_linkedin_uc=generate_uc,
        current_user_dep=current_user_dep,
    )


__all__ = ["mount_content"]
