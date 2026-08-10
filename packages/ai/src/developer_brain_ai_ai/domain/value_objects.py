"""Value objects do modulo ai."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptName:
    """Nome do prompt (ex.: 'linkedin', 'summary'). [a-z0-9_-]{1,40}."""

    value: str

    def __post_init__(self) -> None:
        v = self.value.strip().lower()
        if not v or len(v) > 40 or not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError(f"prompt name invalido: {self.value!r}")
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PromptVersion:
    """Hash SHA-256 do conteudo do prompt. Invariante p/ reprodutibilidade."""

    value: str

    def __post_init__(self) -> None:
        if len(self.value) != 64:
            raise ValueError("prompt version deve ter 64 chars (sha-256)")

    @classmethod
    def from_content(cls, content: str) -> PromptVersion:
        return cls(hashlib.sha256(content.encode("utf-8")).hexdigest())


@dataclass(frozen=True)
class AgentName:
    """Nome logico de um agente (ex.: 'linkedin', 'summary')."""

    value: str

    def __post_init__(self) -> None:
        v = self.value.strip().lower()
        if not v or len(v) > 40 or not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError(f"agent name invalido: {self.value!r}")
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


__all__ = ["AgentName", "PromptName", "PromptVersion"]
