# ADR-0006 — Sincronização Obsidian read-only

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
Obsidian mantém seu vault local em Markdown. Precisamos "ler automaticamente" o vault
(Markdown, tags, links, pastas, diários).

## Decision
Sincronização **unidirecional read-only** (Obsidian → DB). Um job escaneia o vault via
configuração `OBSIDIAN_VAULT_PATH`, ingere arquivos via anti-corruption layer
`ObsidianVaultClient`, e mapeia tags/Backlinks para o módulo `library`/`journal`.

## Consequences
- ✅ Zero risco de corromper o vault do usuário.
- ✅ Re-sync seguro (idempotente por path+hash).
- ⚠️ Edições na nossa plataforma não refletem no vault (aceito por agora).
- ⚠️ Falso bidirecional não rola — futura feature requer modelagem de conflitos.