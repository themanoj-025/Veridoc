# Veridoc — Startup Flow

Veridoc runs as a Docker Compose stack (postgres, minio, chroma, redis,
backend) with a Next.js frontend. Backend commands run from `backend/`.

## Docker stack startup (`docker-compose.yml`)

1. **postgres** — `pg_isready` health check (db/user `veridoc`).
2. **minio** — S3-compatible object storage for uploaded documents
   (`curl /minio/health/live`).
3. **chroma** — vector database for dense retrieval.
4. **redis** — cache + job queue backend.
5. **backend** — `uvicorn app.main:app` (or gunicorn). Import chain:
   a. `app.core.config` loads env (DATABASE_URL, REDIS_URL, CHROMA_URL,
      MINIO_*, JWT secrets, LLM keys).
   b. `app.core.database` creates the engine; `app.core.di` builds the
      dependency graph (repositories, services).
   c. FastAPI app assembly: middleware (CORS, rate-limit, auth),
      router registration (auth, documents, chat, search, sharing,
      api_keys, feedback, gdpr, admin).
   d. Lifespan: pending Alembic migrations applied; background worker
      (ingestion queue) started.
   e. Ready: `/health`, `/docs`, business endpoints.

## Document ingestion flow

1. Upload via `api/documents` → virus scan → object stored in MinIO.
2. `services/worker.py` picks the job → `ingestion.py` parses (PDF/text;
   OCR for scanned) → `chunking.py` splits → `vector_store.py` embeds into
   Chroma → chunk rows in Postgres.
3. Status tracked per document; UI polls via the documents API.

## Chat flow (RAG)

1. `api/chat` → `chat_service` → `retrieval/hybrid` (BM25 ⊕ dense, RRF
   fusion, optional query rewrite) → top-k chunks.
2. `prompt_registry` builds the grounded prompt → `llm_provider` generates →
   answers must cite `citation_record` rows; ungrounded claims refused.
3. `response_cache` short-circuits identical queries.

## Operational entry points

| Entry | Command |
|---|---|
| Backend | `uvicorn app.main:app --reload` (from `backend/`) |
| Frontend | `npm run dev` (from `frontend/`) |
| Migrate | `cd backend && alembic upgrade head` |
| Tests (back) | `cd backend && python -m pytest tests/ -v` |
| Tests (front) | `cd frontend && npx vitest run` + `npx playwright test` |
| Eval gate | `python scripts/run_eval.py` (CI gate) |
| Red-team / chaos | `python scripts/run_redteam_live.py`, `scripts/chaos_test_live.py` |

## What must exist at startup

- Env keys from `.env.example` (DB/Redis/Chroma/MinIO URLs, JWT secrets, LLM keys)
- Postgres reachable; migrations applied
- Chroma + MinIO reachable (backend degrades gracefully to local modes)
- `prompts/registry.json` present
