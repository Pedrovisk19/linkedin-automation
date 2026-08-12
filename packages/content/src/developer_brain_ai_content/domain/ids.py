"""IDs tipados do content (ContentDraft e fila de publicacao)."""

from developer_brain_ai_shared.kernel.id import TypedId


class ContentDraftId(TypedId["ContentDraftId"]):
    """Identificador de ContentDraft."""


class PublicationQueueItemId(TypedId["PublicationQueueItemId"]):
    """Identificador de PublicationQueueItem."""


__all__ = ["ContentDraftId", "PublicationQueueItemId"]
