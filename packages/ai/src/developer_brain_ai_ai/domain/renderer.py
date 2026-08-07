"""Renderer: substitui {{var}} em template mantendo chaves desconhecidas literais.

Usa regex (nao string.Formatter) porque templates usam {{var}} como convencao
TipScript / Mustache-like. string.Formatter trataria {{var}} como escape de {var},
o que colidiria com a sintaxe dos nossos prompts.
"""
from __future__ import annotations

import re

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def render(template: str, variables: dict[str, str]) -> str:
    def _replace(m: re.Match[str]) -> str:
        key = m.group(1)
        if key in variables:
            return str(variables[key])
        return m.group(0)

    return _PLACEHOLDER_RE.sub(_replace, template)


__all__ = ["render"]