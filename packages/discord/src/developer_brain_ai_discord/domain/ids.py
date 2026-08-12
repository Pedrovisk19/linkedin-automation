"""IDs do modulo discord."""

from __future__ import annotations

from developer_brain_ai_shared.kernel.id import TypedId


class DiscordRequestId(TypedId["DiscordRequestId"]):
    """Identificador de um pedido de aprovacao via Discord."""


__all__ = ["DiscordRequestId"]
