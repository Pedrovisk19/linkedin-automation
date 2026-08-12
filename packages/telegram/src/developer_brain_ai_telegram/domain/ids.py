"""IDs do modulo telegram."""

from __future__ import annotations

from developer_brain_ai_shared.kernel.id import TypedId


class TelegramRequestId(TypedId["TelegramRequestId"]):
    """Identificador de um pedido de aprovacao via Telegram."""


__all__ = ["TelegramRequestId"]
