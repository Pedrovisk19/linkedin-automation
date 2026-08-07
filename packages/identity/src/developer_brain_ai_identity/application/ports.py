"""Application ports do identity. Interfaces para Clock (tempo injetavel)."""
from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


__all__ = ["Clock"]