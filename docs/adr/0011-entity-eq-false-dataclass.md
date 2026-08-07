# ADR-0011 — Entidades usam `@dataclass(eq=False)` + `__eq__`/`__hash__` custom

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
`@dataclass` por default usa `eq=True` e `frozen=False`. Neste caso, o decorator
**zera** `__hash__` (`__hash__ = None`) — mesmo se a subclasse define `__hash__`
no corpo da classe, o decorator sobrescreve ao final. Resultado: entidades ficavam
`unhashable`, não podiam ser usadas em sets/dicts, e o `__hash__` custom (baseado em
id) era perdido.

## Decision
Padronizar todas as entidades de domínio (subclasses de `Entity` / `AggregateRoot`)
usando `@dataclass(eq=False)` e prover `__eq__` / `__hash__` explicitamente no corpo.
Com `eq=False`, o dataclass não toca em `__hash__`, preservando a lógica custom.

Regra aplicada em:
- `Entity`, `AggregateRoot` (em `shared.kernel.entity`).
- Subclasses (`Tenant`, `User`, `ApiKey` e futuras) usam `@dataclass(eq=False)`.
- Testes que criam entidades dummy idem.

## Consequences
- ✅ Entidades são hashable (baseado em `type(self).__name__ + id`) e estáveis.
- ✅ Igualdade por identidade (não por valor de campos) — preserva semântica DDD.
- ✅ Value objects (`PasswordHash`, `Email`, etc.) continuam `frozen=True` puro.
- ⚠️ Boilerplate: cada `@dataclass` de entidade deve explicitar `eq=False`. Mitigado
  por lint/ADR — linha de adicionar teste de arquitetura (Fase 1) que detecta
  entidades sem `eq=False`.