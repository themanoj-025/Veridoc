# Veridoc — Folder Structure

```
Veridoc/
├── backend/                       # FastAPI service (all backend code)
│   ├── app/
│   │   ├── main.py                #   App factory + lifespan
│   │   ├── api/                   #   Routers: auth, documents, chat, search,
│   │   │                          #   sharing, api_keys, feedback, gdpr, admin
│   │   ├── core/                  #   config, database, security, rate_limit,
│   │   │                          #   token_store, dependencies, di, logging_config
│   │   ├── models/                #   SQLAlchemy ORM (11 models)
│   │   ├── repositories/          #   Data-access layer
│   │   ├── schemas/               #   Pydantic DTOs (auth, chat, document, sharing)
│   │   └── services/              #   ingestion, chunking, vector_store,
│   │                              #   retrieval/{bm25,dense,hybrid,rrf,query_rewrite},
│   │                              #   llm_provider, chat_service, worker, …
│   ├── alembic/                   #   DB migrations (001–005)
│   ├── tests/                     #   14 pytest modules (auth, ingestion, retrieval, …)
│   ├── Dockerfile, requirements.txt
│   └── alembic.ini
├── frontend/                      # Next.js 14 App Router UI
│   ├── src/
│   │   ├── app/                   #   Pages (dashboard, admin, login, register)
│   │   ├── components/            #   ChatPanel, DocumentViewer, CommandPalette, …
│   │   ├── lib/                   #   api client, stores (Zustand), queries, i18n
│   │   └── middleware.ts          #   Auth middleware
│   ├── src/**/__tests__/          #   Vitest suites (components, lib, pages)
│   ├── playwright.config.ts       #   E2E config
│   └── tailwind.config.ts, vitest.config.ts, tsconfig.json
├── scripts/                       # eval, benchmark, load/chaos/red-team, SQuAD, tuning
├── eval/                          # gold_qa.json + red_team/ prompt injections
├── prompts/registry.json          # Versioned prompt registry
├── data/                          # Docker volumes (pgdata, chroma, minio, ollama)
├── docs/                          # Full suite (architecture, technical, migration/…)
├── .github/workflows/ci.yml       # CI pipeline
├── docker-compose.yml             # postgres + minio + chroma + redis + backend
├── docker-compose.prod.yml
├── Makefile                       # test / lint / run / migrate targets
├── pyproject.toml
├── .trivyignore                   # Container-scan suppressions
└── README.md · LICENSE · AGENTS.md · BUILD_LOG.md · LOOP_LOG.md · .env.example(s)
```

## Layout rules

- **`backend/` and `frontend/` are sibling monorepo halves** — all Python under
  `backend/`, all TypeScript under `frontend/`; each has its own tooling.
- **Feature-cohesive FastAPI layering** — `api/` (thin routers) → `services/`
  (business logic) → `repositories/` (data access) → `models/`; `core/` holds
  cross-cutting infrastructure.
- **Artifacts never in source** — caches (`.mypy_cache/`, `.pytest_cache/`),
  build output (`frontend/.next/`), and `node_modules/` are gitignored.
- **Secrets never tracked** — `.env` gitignored; `.env.example` +
  `.env.production.example` committed.
