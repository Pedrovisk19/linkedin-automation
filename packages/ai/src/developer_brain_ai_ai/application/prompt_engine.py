"""PromptEngine: le prompts/*.md do FS, cacheia por sha256, renderiza variaveis."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from developer_brain_ai_ai.domain.aggregates import PromptTemplate
from developer_brain_ai_ai.domain.value_objects import PromptName, PromptVersion


class PromptNotFound(LookupError):
    pass


class PromptEngine:
    """Loader de templates .md. Construido com root_dir (Path) injetavel.

    Uso:
        engine = PromptEngine(Path("./prompts"))
        tpl = engine.load(PromptName("linkedin"))
        rendered = tpl.render({"ai_writing_tone": "..."})
    """

    def __init__(self, root_dir: Path, *, suffix: str = ".md") -> None:
        self._root = Path(root_dir)
        self._suffix = suffix

    @lru_cache(maxsize=64)
    def load(self, name: PromptName) -> PromptTemplate:
        path = self._root / f"{name}{self._suffix}"
        if not path.is_file():
            raise PromptNotFound(f"prompt nao encontrado: {path}")
        content = path.read_text(encoding="utf-8")
        version = PromptVersion.from_content(content)
        return PromptTemplate(
            id=object(),
            prompt_name=name,
            version=version,
            content=content,
        )

    def refresh(self, name: PromptName) -> PromptTemplate:
        """Forca releitura apos edicao (em dev)."""
        self.load.cache_clear()
        return self.load(name)


__all__ = ["PromptEngine", "PromptNotFound"]
