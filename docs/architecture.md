# Arquitetura — Developer Brain AI

> Decisões em `docs/adr/`. Resumo executivo das ADRs em `docs/adr/README.md`.

## 1. Visão C4 — Nível Container (contexto)

```mermaid
flowchart LR
    U([Usuário / Dev])
    WEB[Next.js Web<br/>TypeScript + Tailwind + Shadcn]
    API[FastAPI<br/>apps/api]
    WKR[Arq Worker<br/>apps/worker]
    PG[(PostgreSQL<br/>+ pgvector)]
    REDIS[(Redis)]
    OBS[(Obsidian Vault<br/>local)]
    GH[GitHub API]
    LI[LinkedIn API]
    OA[OpenAI API]

    U --> WEB --> API
    API --> PG
    API --> REDIS
    WKR --> REDIS
    WKR --> PG
    WKR --> OBS
    WKR --> GH
    WKR --> LI
    WKR --> OA
    API --> OA
    API --> GH
```

## 2. Clean Architecture (por bounded context)

```mermaid
flowchart TB
    subgraph Domain[domain — puro, sem framework]
        ENT[Entities]
        VO[Value Objects]
        EVT[Domain Events]
        RI[Repository Interfaces]
    end
    subgraph App[application]
        UC[Use Cases]
        DTO[DTOs Pydantic]
        PORT[Ports: AIProvider, Clock, Storage]
    end
    subgraph Infra[infrastructure]
        REPO[Repos SQLAlchemy]
        AIP[AIProvider impls]
        CLIENT[GitHub/LinkedIn/Obsidian clients]
        S3[Storage local/S3]
    end
    subgraph Pres[presentation]
        ROUT[FastAPI Routers]
        SCH[Schemas]
        MW[Middleware: tenant, auth, logging]
    end

    Pres --> App --> Domain
    Inf --> App
    Inf -. implementa .-> RI
```

**Regra:** dependências apontam sempre para dentro (`domain`): nenhum `import` de domínio
para SQLAlchemy/FastAPI/OpenAI. Testes de arquitetura proíbem esse direction.

## 3. Bounded Contexts

```mermaid
flowchart LR
    IDT[identity]
    JRN[journal]
    RDM[roadmap]
    PRJ[projects]
    STD[studies]
    LIB[library]
    AIZ[ai]
    CNT[content]
    INT[integrations]
    RAG[rag]
    AUT[automation]
    SHR[shared kernel]

    JRN --> AIZ
    RDM --> AIZ
    PRJ --> AIZ
    AIZ --> CNT
    AIZ --> RAG
    AIZ --> LIB
    AUT --> JRN
    AUT --> AIZ
    AUT --> CNT
    AUT --> PRJ
    INT --> PRJ
    INT --> JRN
    IDT --> SHR
    JRN --> SHR
```

## 4. Modelo de domínio (resumo ER)

```mermaid
erDiagram
    TENANT ||--o{ USER : has
    TENANT ||--o{ JOURNAL_ENTRY : owns
    JOURNAL_ENTRY ||--o{ TAG : "tagged by"
    TENANT ||--|| ROADMAP : has
    ROADMAP ||--o{ SKILL : contains
    ROADMAP ||--o{ GOAL : contains
    ROADMAP ||--o{ CERTIFICATION : contains
    TENANT ||--o{ PROJECT : owns
    PROJECT ||--o{ COMMIT : tracks
    PROJECT ||--o{ BACKLOG_ITEM : has
    PROJECT ||--o{ SPRINT : plans
    TENANT ||--o{ STUDY_SESSION : logs
    STUDY_SESSION }o--|| RESOURCE : targets
    TENANT ||--o{ LIBRARY_ITEM : stores
    TENANT ||--o{ CONTENT_DRAFT : produces
    CONTENT_DRAFT ||--|| PUBLICATION_QUEUE : queues
    TENANT ||--o{ MEMORY_FRAGMENT : remembers
    TENANT ||--o{ DOCUMENT : ingests
    DOCUMENT ||--o{ CHUNK : splits
    CHUNK ||--|| EMBEDDING : "vectorized"
    TENANT ||--o| GITHUB_CONNECTION : connects
    TENANT ||--o{ OBSIDIAN_VAULT : watches
```

Multi-tenancy: TODAS as tabelas de domínio carregam `tenant_id UUID NOT NULL`; RLS do
Postgres filtra por `app.tenant_id` (SET no início da transação via UoW).

## 5. Pipeline diário (automação)

```mermaid
flowchart TB
    A[Job diário Arq] --> B[Ler diários novos]
    B --> C[Atualizar banco + tags]
    C --> D[Summary Agent: resumo diário/semanal]
    D --> E[LinkedIn Agent: gerar post]
    D --> F[GitHub Agent: atualizar README/badges]
    D --> G[Newsletter + Cards]
    E --> H[Fila de publicação]
    F --> I[Commit no repo]
    G --> H
    H --> J[Atualizar Dashboard]
    J --> K[Salvar histórico + MemoryFragment]
    K --> L[Fim (idempotente por data)]
```

Cada step é um **use_case idempotente**; re-rodar o job no mesmo dia não duplica
conteúdo (dedupe via chave composta `tenant_id + pipeline_date + step_name`).

## 6. Camada de IA

```mermaid
flowchart LR
    subgraph AI[modulo ai]
        PROVIDER[AIProvider - Protocol]
        REG[ProviderRegistry]
        OPENAI[OpenAIProvider]
        CLAUDE[ClaudeProvider - futuro]
        GEM[GeminiProvider - futuro]
        AGENTS[Agentes: LinkedIn, GitHub, Planner, Summary, Career, PromptEngineer]
        MEM[MemoryService - similaridade p/ evitar repetição]
        PE[PromptEngine - le/cacha prompts/]
    end
    OPENAI -. implements .-> PROVIDER
    CLAUDE -. implements .-> PROVIDER
    GEM -. implements .-> PROVIDER
    AGENTS --> PROVIDER
    AGENTS --> MEM
    AGENTS --> PE
```

## 7. Roadmap de fases

| Fase | Entrega | Definição de pronto |
|------|---------|---------------------|
| 0 | Scaffolding monorepo + tooling + containers + ADRs | `make dev`, CI verde |
| 1 | Bounded contexts vazios + interfaces + diagramas | testes de arquitetura passam |
| 2 | `shared` kernel (auth, errors, UoW, tenant) | cobertura ≥90% |
| 3 | Módulo Journal (CRUD + Markdown) | testes end-to-end verde |
| 4 | Roadmap, Projects, Studies, Library | um PR por módulo |
| 5 | `AIProvider` abstraction + OpenAI + PromptEngineer | troca de provider por config |
| 6 | Agentes (LinkedIn, GitHub, Planner, Summary, Career) | um agente por PR |
| 7 | Automation: Arq worker + pipeline diário idempotente | job re-entrante |
| 8 | RAG: ingestão + retrieval (pgvector) | QA sobre a própria base |
| 9 | Integrations: GitHub, Obsidian, LinkedIn (drafts) | ACL isolada |
| 10 | Dashboard + Next.js frontend | API pública estável |
| 11 | Observabilidade (structlog, OpenTelemetry, Sentry-ready) | tracing ponta-a-ponta |
| 12 | SaaS-ready (billing-ready, S3 storage, multi-tenant já ativo) | isolamento validado |