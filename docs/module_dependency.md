# Veridoc — Module Dependency Map

## Backend layers (backend/app)

Dependencies flow **downward**: `api/` → `services/` → `repositories/` →
`models/`; `core/` is cross-cutting and imported by all layers.

```
core/config.py            ← imported by every module (env settings)
core/database.py          ← used by repositories, alembic env, services
core/di.py / dependencies.py ← wires routers → services → repositories (composition root)
core/security.py          ← used by api/auth, api/api_keys, dependencies (RBAC)
core/rate_limit.py        ← used by api routers
core/token_store.py       ← used by api/auth (refresh tokens)

api/*.py                  → core (DI, security, rate_limit), services.*,
                            repositories.*, models.*, schemas.*
services/chat_service.py  → services/retrieval.hybrid, llm_provider,
                            response_cache, prompt_registry, repositories, models
services/ingestion.py     → services/chunking, vector_store, ssrf_protection,
                            repositories, models
services/vector_store.py  → core.config (Chroma client)
services/retrieval/hybrid.py → retrieval/bm25, retrieval/dense, retrieval/rrf
services/retrieval/query_rewrite.py → llm_provider
services/llm_provider.py  → core.config, services/response_cache (leaf-ish)
services/worker.py        → services/job_queue, services/ingestion (background tasks)
services/evaluation.py    → services/retrieval, llm_provider (offline harness)
repositories/*.py         → core.database, models
```

## Rules

- **No upward imports** — `services`, `repositories`, `models` never import
  `api`; `models` never imports repositories/services.
- **`services` is the only layer that mixes concerns deliberately** — it owns
  retrieval fusion, LLM calls, and ingestion; `api` stays thin.
- **No circular imports** — verified by CI (flake8 F401/imports) and the
  existing test suite; `core/di.py` centralizes wiring so routers never
  construct services inline.
- **Alembic env.py** imports `app.core.database` + models for autogenerate.

## Frontend

```
frontend/src/lib/api.ts        → backend REST /api/* (JWT bearer)
frontend/src/lib/queries.ts    → TanStack Query wrappers over api.ts
frontend/src/lib/store.ts      → Zustand client state (auth, toasts)
frontend/src/components/*      → consume lib (no direct fetch)
frontend/src/app/*             → pages composed from components
frontend/src/middleware.ts     → route guard (redirects to /login)
```

## External dependencies

FastAPI + uvicorn · SQLAlchemy + Alembic + Postgres · Redis · Chroma
(vector DB) · MinIO (object storage) · SQLite FTS (BM25) · an LLM provider ·
PyMuPDF/OCR (ingestion) · Next.js 14 + React · TanStack Query · Zustand ·
Vitest + Playwright · Prometheus-style metrics/logging
