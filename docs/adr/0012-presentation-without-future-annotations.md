# ADR-0012 — Sem `from __future__ import annotations` em presentation routers

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
O FastAPI interpreta os metadados `Depends(...)` em `Annotated[Tipo, Depends(dep)]` em
tempo de definição da função, lendo o `__annotations__` "vivo". Com `from __future__
import annotations` (PEP 563), todas as anotações viram strings forward refs; FastAPI
tenta reevaluar via `get_type_hints`, mas `Depends(current_user_dep)` (com variável de
closure capturada) não é resolúvel fora do escopo, gerando `PydanticUserError: ...
not fully defined`.

## Decision
**Módulos de `presentation/` NÃO usam `from __future__ import annotations`.** Anotações
permanecem vivas — necessárias para que Depends/FastAPI leiam os metadados em runtime.

Domain, application e infrastructure mantêm `from __future__ import annotations`
(otimização marginal, sem bug—nenhuma anotação é consumida via introspecção externa).

## Consequences
- ✅ Depends funciona em `Annotated[CurrentUser, Depends(dep)]`.
- ✅ Estilo consistente com o motivo de cada camada: presentation precisa de runtime
  lookup; outras camadas ficam em lazy/forward.
- ⚠️ ADR torna-se regra de arquitetura: testes `arch` (Fase 1) proibirão
  `from __future__ import annotations` em `**/presentation/**`.