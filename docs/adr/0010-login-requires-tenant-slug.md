# ADR-0010 — Login exige `tenant_slug` (lookup sob RLS já ativa)

- **Status:** Accepted
- **Date:** 2026-08-06

## Context
Em multi-tenant, o email pode existir em múltiplos tenants. Autenticar apenas por
`(email, password)` ambigua o `tenant_id` e obriga a uma rota de "selecione seu tenant"
ou a uma tabela global `UserLookup` paralela à `users` — e esta última sofistica RLS:

- Cada query de login teria de bypassar RLS para achar o user, abrindo janela de
  isca (tenant enumeration via timing).
- Ou seria necessário uma role `auth_role` com `BYPASSRLS` só para login.

## Decision
Login exige **`(tenant_slug, email, password)`**. O fluxo dentro do `LoginUser` use_case:

1. `TenantRepository.get_by_slug(slug)` — tabela `tenants` é legível sem RLS.
2. `set_tenant_context(tenant.id)` antes de qualquer query em `users`/`api_keys`.
3. `UserRepository.get_by_email(email)` — agora viaja sob RLS por `tenant_id` correto.
4. Validar password hash do user; se inválido, `UnauthorizedError` (mesma mensagem
   ambos os casos → evita user enumeration).

O frontend (Fase 10) pode pré-popular `tenant_slug` por subdomínio ou persistir em
cookie pós-primeiro login.

## Consequences
- ✅ Sem bypass de RLS para auth; defesa em profundidade mantida.
- ✅ Erros indistinguíveis entre "tenant não existe", "user não existe", "senha errada".
- ✅ Lookup de tenant por slug é O(1) com índice UNIQUE em `tenants.slug`.
- ⚠️ UX leve atrito extra: usuário precisa saber o slug. Mitigado por subdomínio/cookie.
- ⚠️ Em SaaS futuro, self-serve signup cria slug a partir de organização; register
  use_case já valida unicidade de slug globalmente.