# ADR-0002 — UV como gerenciador de pacotes

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
Stack pede Poetry ou UV; Python 3.14-alvo. Poetry é maduro; UV é ~10–100x mais rápido,
locks determinísticos e suporte first-class a workspaces (PEP 735).

## Decision
Adotar **UV** + lockfile `uv.lock`. Monorepo via `[tool.uv.workspace]` com membros em
`apps/*` e `packages/*`.

## Consequences
- ✅ Installs/CI muito mais rápidos.
- ✅ Workspace PEP 735 substitui dependabot-extração manual de path.
- ⚠️ Ecossistema mais jovem; mitigado com pins no `uv.lock`.
- ⚠️ Alguns docs/tutoriais ainda assumem Poetry.