# ADR-0008 — Ciclo de import resolvido via TYPE_CHECKING entre `kernel.entity` e `events.base`

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
O `AggregateRoot` referencia `DomainEvent` (type hint do campo `_events`). O `DomainEvent`
por sua vez referencia `TenantId` (em `kernel.id`). Importar `kernel` disparava `kernel.entity`
que importava `events.base` que importava `kernel.id` — e como `kernel/__init__.py` roda antes
de `kernel.id` resolver, o Python não encontra `DomainEvent` ainda parcialmente inicializado.

## Decision
Em `kernel.entity`, mover o import de `DomainEvent` para `if TYPE_CHECKING:` e usar
**string forward refs** (`"DomainEvent"`) em todas as anotações (`_events`,
`record_event`, `pull_events`, `pending_events`). Cycle runtime quebrado; tipos
preservados para mypy.

## Consequences
- ✅ Imports em runtime linearizados; sem cycle.
- ✅ Mypy resolve normalmente via TYPE_CHECKING.
- ⚠️ mypy precisa de `from __future__ import annotations` ou forward refs explícitos — já presente.
- ⚠️ Serviram para detectar fragilidade: reexports em `__init__.py` podem iniciar cycles. Será
  adicionado teste de arquitetura (Fase 1) que garante que `from developer_brain_ai_shared.X import Y`
  sempre resolve sem side-effects colaterais.