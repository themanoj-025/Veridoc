# Veridoc — System Architecture

Veridoc is an **AI document RAG platform**: ingest documents (PDF, text,
scanned PDFs with OCR), chunk + embed them into a vector store, answer
questions with cited, grounded LLM responses over hybrid retrieval
(BM25 + dense + RRF), with RBAC, sharing, GDPR controls, and an evaluation
harness.

## High-level components

```
                 ┌───────────────────────────────────────────────┐
                 │         frontend/  (Next.js 14 app)           │
                 │  app/ pages · components/ · lib/ (api, store) │
                 └──────────────────┬────────────────────────────┘
                                    │ HTTPS (JWT auth)
                 ┌──────────────────▼────────────────────────────┐
                 │          backend/app  (FastAPI)               │
                 │  api/ (auth, documents, chat, search, admin,  │
                 │        api_keys, feedback, gdpr, sharing)     │
                 │  services/ (ingestion, chunking, vector_store,│
                 │            retrieval/{bm25,dense,hybrid,rrf}, │
                 │            llm_provider, chat_service, worker)│
                 └──┬─────────┬─────────┬──────────┬─────────────┘
                    │         │         │          │
                    ▼         ▼         ▼          ▼
              ┌──────────┐ ┌──────┐ ┌───────┐ ┌──────────┐
              │ Postgres │ │Redis │ │Chroma │ │  MinIO   │
              │ (SQLAlch)│ │cache │ │vectors│ │ documents│
              └──────────┘ └──────┘ └───────┘ └──────────┘
                    └──────────────┬─────────────────┘
                                   ▼
                       ┌──────────────────────────┐
                       │  eval/ + prompts/ +      │
                       │  scripts/ (evaluation,   │
                       │  red-team, chaos tests)  │
                       └──────────────────────────┘
```

## Component responsibilities

| Component | Responsibility |
|---|---|
| `backend/app/api/` | FastAPI routers: `auth` (JWT + RBAC), `documents` (upload/ingest), `chat`, `search`, `sharing`, `api_keys`, `feedback`, `gdpr`, `admin` |
| `backend/app/core/` | `config` (env), `database` (engine/session), `security`, `rate_limit`, `token_store`, `dependencies`/`di` (DI), `logging_config` |
| `backend/app/models/` | SQLAlchemy models: user, document, chunk, conversation, message, api_key, citation_record, usage_log, admin_audit_log, document_share |
| `backend/app/repositories/` | Data-access layer (user, document, chunk, conversation, usage_log) |
| `backend/app/services/` | `ingestion` (parse + OCR + virus scan), `chunking`, `vector_store` (Chroma), `retrieval/` (bm25, dense, hybrid, rrf, query_rewrite), `llm_provider`, `chat_service`, `response_cache`, `prompt_registry`, `job_queue`, `worker` (background jobs), `email_sender`, `evaluation`, `ssrf_protection` |
| `backend/app/main.py` | FastAPI app factory + lifespan wiring |
| `backend/alembic/` | 5 migrations (initial, array normalization, chunk OCR flag, RBAC/indexes/sharing, token expiry) |
| `frontend/` | Next.js 14 App Router UI (dashboard, admin, login/register), TanStack Query, Zustand, i18n, middleware auth |
| `eval/` | Gold QA set (`gold_qa.json`) + red-team prompts |
| `prompts/registry.json` | Versioned prompt registry |
| `scripts/` | Evaluation, benchmark, load/chaos/red-team tests, SQuAD fetch, hybrid-weight tuning |

## Key architectural decisions

- **Hybrid retrieval with RRF** — `retrieval/hybrid.py` fuses BM25 (SQLite FTS)
  and dense (Chroma) results via Reciprocal Rank Fusion; `query_rewrite` for
  multi-hop questions.
- **Grounded, cited answers** — `chat_service` requires citations
  (`citation_record`) and refuses to answer without retrieved evidence.
- **Async ingestion pipeline** — upload → virus scan → parse/OCR → chunk →
  embed → store, driven by `services/worker.py` + `job_queue` (Redis).
- **RBAC + audit** — role-based auth (`core/security`, `models/admin_audit_log`),
  API keys, document sharing, GDPR data-export/delete endpoints.
- **Offline evaluation gate** — `scripts/run_eval.py` + `eval/gold_qa.json`
  gate CI quality; red-team + chaos tests in `scripts/`.
- **Defense in depth** — SSRF protection on URL ingestion, rate limiting,
  token expiry (migration 005), virus scanning, prompt-registry versioning.
