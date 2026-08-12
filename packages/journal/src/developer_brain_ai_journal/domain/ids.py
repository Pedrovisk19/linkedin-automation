"""Novo id tipado JournalEntryId (em shared para reuso cross-package).

Mantemos todos os TypedId em shared.kernel.id para que outros contexts possam
referenciar via import (ex.: ai agent referencia JournalEntryId).
"""

from developer_brain_ai_shared.kernel.id import TypedId


class JournalEntryId(TypedId["JournalEntryId"]):
    """Identificador de entrada de diario."""


__all__ = ["JournalEntryId"]
