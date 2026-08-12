"""Composition helper do content."""

from developer_brain_ai_identity.presentation.dependencies import CurrentUserDependency
from fastapi import APIRouter

from developer_brain_ai_content.application.ports import (
    LinkedInGenerator,
    LinkedInPostPublisher,
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
from developer_brain_ai_content.domain.repositories import (
    ContentDraftRepository,
    PublicationQueueRepository,
)
from developer_brain_ai_content.presentation.routers import build_router


def mount_content(
    *,
    drafts_repo: ContentDraftRepository,
    queue_repo: PublicationQueueRepository,
    current_user_dep: CurrentUserDependency,
    linkedin_generator: LinkedInGenerator | None = None,
    linkedin_publisher: LinkedInPostPublisher | None = None,
) -> APIRouter:

    create = CreateLinkedInDraft(drafts_repo)
    list_uc = ListDrafts(drafts_repo)
    get_uc = GetDraft(drafts_repo)
    enqueue_uc = EnqueueDraft(drafts_repo, queue_repo)
    publish_uc = MarkPublished(drafts_repo, queue_repo, publisher=linkedin_publisher)
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
