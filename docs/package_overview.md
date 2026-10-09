# Veridoc — Package & Module Inventory

## Backend: `backend/app` (FastAPI)

| Area | Modules |
|---|---|
| `api/` | `auth.py` (JWT + refresh), `documents.py` (upload/ingest/list), `chat.py`, `search.py`, `sharing.py`, `api_keys.py`, `feedback.py`, `gdpr.py`, `admin.py` |
| `core/` | `config.py` (env settings), `database.py`, `security.py`, `rate_limit.py`, `token_store.py`, `dependencies.py`, `di.py` (composition root), `logging_config.py` |
| `models/` | `user`, `document`, `chunk`, `conversation`, `message`, `api_key`, `citation_record`, `usage_log`, `admin_audit_log`, `document_share` (+ `conversation_document`) |
| `repositories/` | `base.py`, `user_repo`, `document_repo`, `chunk_repo`, `conversation_repo`, `usage_log_repo` |
| `schemas/` | `base`, `auth`, `chat`, `document`, `api_key`, `sharing` (Pydantic DTOs) |
| `services/` | `ingestion.py`, `chunking.py`, `vector_store.py`, `retrieval/bm25.py`, `retrieval/dense.py`, `retrieval/hybrid.py`, `retrieval/rrf.py`, `retrieval/query_rewrite.py`, `llm_provider.py`, `chat_service.py`, `response_cache.py`, `prompt_registry.py`, `job_queue.py`, `worker.py`, `email_sender.py`, `evaluation.py`, `ssrf_protection.py` |
| `main.py` | App factory + lifespan |

## Frontend: `frontend/src` (Next.js 14)

| Area | Modules |
|---|---|
| `app/` | `page.tsx` (landing), `dashboard/page.tsx`, `admin/page.tsx`, `login/page.tsx`, `register/page.tsx`, `layout.tsx`, `globals.css` |
| `components/` | `ChatPanel`, `DocumentList`, `DocumentViewer`, `SearchBar`, `CommandPalette`, `ConfidenceBadge`, `OCRBadge`, `ThumbsUpDown`, `Toast`, `Skeleton`, `ThemeToggle`, `ErrorBoundary`, `AuthProvider`, `QueryProvider` |
| `lib/` | `api.ts` (client), `api-types.ts`, `queries.ts`, `store.ts` + `toast-store.ts` (Zustand), `utils.ts`, `i18n.ts` |
| `middleware.ts` | Auth route guard |

## Tests

- `backend/tests/` — `test_auth`, `test_health`, `test_ingestion`,
  `test_integration`, `test_rate_limit_headers`, `test_rbac_auth_rate`,
  `test_resilience`, `test_response_cache`, `test_retrieval`,
  `test_schema`, `test_sharing_api_keys`, `test_virus_scan`,
  `test_eval_harness` + `conftest.py`
- `frontend/src/**/__tests__/` — component + lib + page Vitest suites;
  `playwright.config.ts` for E2E

## Non-package trees

| Path | Purpose |
|---|---|
| `backend/alembic/` | 5 migrations (initial → token expiry) |
| `scripts/` | `run_eval.py`, `benchmark_reranker.py`, `build_gold_qa.py`, `download_squad.py`, `fetch_eval_data.py`, `tune_hybrid_weights.py`, `run_standalone_eval.py`, `run_load_test.py` + `locustfile.py`, `run_redteam_live.py`, `chaos_test_live.py`, `ci_eval_gate.py`, `promote_feedback.py`, `restart_docker.ps1` |
| `eval/` | `gold_qa.json`, `red_team/prompt_injection.json` |
| `prompts/registry.json` | Versioned prompts |
| `data/` | Docker volume mounts (pgdata, chroma, minio, ollama) |
| `docs/` | Full documentation suite (architecture, technical/, migration/) |
