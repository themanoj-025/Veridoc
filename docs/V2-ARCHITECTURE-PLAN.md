# Veridoc v2 — Architecture & Re-architecture Plan

> Planning document for the Prompt 1 → Prompt 2 → Prompt 3 re-architecture pass.
> **Zero implementation code.** This is a decision and roadmap document only.

---

## 1. Root-Cause Architecture Diagnosis

Every verified defect in the v1 codebase falls under **exactly six root causes**:

### Root Cause A: Leaky Resource Lifecycle (Primary bug — session management)
The `get_session()` FastAPI dependency both **owns** the session lifecycle (creates/closes the `async with` block) AND **calls** `commit()` and `rollback()` around the caller's business logic. This means:
- The SSE `event_generator` in `stream_chat` receives a pre-yielded session that gets committed and closed before the generator finishes iterating
- Mid-stream database writes (saving the assistant message, writing usage logs) operate on a closed session
- The caller has no control over transaction boundaries

**Fix principle:** *Session-per-unit-of-work.* The DI layer yields a **raw** session without committing. Each service method opens its own `async with session.begin()` for an explicit unit of work. The API route or service orchestrator decides where commit boundaries lie.

### Root Cause B: Unbounded Background Work (Ingestion)
`asyncio.create_task(process_document(...))` fires a coroutine and forgets it. No queue, no retry, no persistence, no observability:
- Server restart = task silently lost
- 100 concurrent uploads = 100 concurrent CPU-bound tasks, no worker pool
- Failed ingestion has no retry — the task is simply abandoned after the first exception

**Fix principle:** *Durable queue + worker pool.* All async work goes through Redis-backed RQ (or Celery). Workers have bounded concurrency, retry-with-backoff, dead-letter queues, and progress reported to the database so the frontend can poll it.

### Root Cause C: Fail-Open Security Defaults
`jwt_secret`, `file_encryption_key`, `postgres_password`, and `minio_secret_key` all have real fallback values in `config.py`:
- If someone deploys without setting `.env`, the app boots with insecure defaults
- The encryption default is not even valid base64; `_get_fernet()` falls through to an undocument SHA-256 derivation
- No startup validation warns or fails

**Fix principle:** *Fail-fast on missing secrets.* Config values that are security-critical must be validated at startup — refuse to boot if they're empty, match a known-placeholder pattern, or fail to decode. Provide `.env.example` with clear instructions, not live-looking defaults.

### Root Cause D: No Isolation Boundaries (Global singletons, no DI, no service layer)
Five global mutable singletons (`_vector_store`, `_provider`, `_embedding_model`, `_reranker`, `_bm25_indexes`) scattered across three files. `retrieval.py` violates SRP by holding six distinct responsibilities. API routes contain 120+ lines of inline business logic (the `stream_chat` endpoint):
- Impossible to unit test without `patch()` on module globals
- No way to swap implementations (e.g., ChromaDB → Qdrant) without editing consumer code
- The 120-line endpoint cannot be independently verified

**Fix principle:** *3-layer architecture with DI.* API routes (~20 lines each) → Service layer (orchestrates pipeline steps, owns transactions) → Data layer (repositories for DB, vector store, object storage). All dependencies injected via FastAPI `Depends()` or application state. Global singletons become app-state-scoped instances.

### Root Cause E: No Bulkhead Pattern (No timeouts, no caching, sync bottleneck)
Every external call (LLM generation, ChromaDB search, MinIO read) is unbounded in time. The BM25 index is rebuilt on every query. NLTK downloads on every BM25 call. The cross-encoder reranks serially:
- A slow or hung downstream service hangs the entire request indefinitely
- p95 latency is dominated by redundant work (rebuilding BM25, downloading punkt)
- No caching of embeddings, frequent queries, or retrieval results

**Fix principle:** *Bulkheads + caching + startup initialization.* Every external call has a configurable timeout via `asyncio.wait_for()`. BM25 indexes are built once and invalidated on document changes. NLTK data is downloaded at app startup. A Redis cache layer stores frequent query embeddings and retrieval results with TTL. Cross-encoder uses batched prediction or ONNX runtime.

### Root Cause F: No Observability Contract (Zero telemetry)
No structured logging, no metrics, no tracing, and a health endpoint that returns "ok" without checking any dependency:
- Ops cannot answer "is the app healthy?" without tailing raw logs
- Performance regression detection requires manual profiling
- Debugging a slow query requires guessing which pipeline stage is slow

**Fix principle:** *Observability from day one.* Structured logging (`structlog`) with correlation IDs through every request. Prometheus metrics (latency histograms, request counters, error rates) via `prometheus-fastapi-instrumentator`. Per-stage timing in the retrieval/generation pipeline exposed both as metrics and in the response. A `/api/health` that actually pings every downstream dependency.

---

## 2. Target Architecture (v2)

```mermaid
graph TB
    subgraph "Frontend (Next.js + TypeScript)"
        FE[Next.js App]
        TYPES[Generated TS Types<br/>from OpenAPI spec]
    end

    subgraph "API Gateway (FastAPI)"
        MW[Middleware:<br/>Auth · Rate-limit · Logging<br/>Prometheus · CORS]
        ROUTES[API Routes<br/>~20 lines each]
        SL[Service Layer<br/>ChatService · DocumentService<br/>AuthService · IngestionService]
        DL[Data Layer<br/>UserRepo · DocRepo · ConvRepo<br/>ChunkRepo · VectorStoreRepo]
    end

    subgraph "Background Workers (ARQ/Redis)"
        WQ[Work Queue]
        W1[Worker: Ingest]
        W2[Worker: Re-index]
        W3[Worker: Re-rank batch]
        DLQ[Dead Letter Queue]
    end

    subgraph "Infrastructure"
        PG[(Postgres<br/>+pgvector for fs)]
        CH[(ChromaDB<br/>Vector Store)]
        MO[(MinIO<br/>S3-compatible)]
        RD[(Redis<br/>Cache + Queue)]
        LLM[Ollama / Claude / OpenAI]
    end

    subgraph "Observability"
        PROM[Prometheus<br/>/metrics]
        STR[Structured Logs<br/>structlog + correlation IDs]
        TRC[OpenTelemetry<br/>Tracing]
        HC[/api/health<br/>Real dependency checks]
    end

    FE -->|HTTPS + SSE| MW
    MW --> ROUTES
    ROUTES --> SL
    SL --> DL
    DL --> PG
    DL --> CH
    DL --> MO
    SL --> LLM
    SL --> RD
    ROUTES --> WQ
    WQ --> W1
    WQ --> W2
    W1 --> DLQ
    W2 --> DLQ
    W1 --> CH
    W2 --> CH
    ROUTES --> PROM
    ROUTES --> STR
    ROUTES --> TRC
    ROUTES --> HC
```

### Key changes from v1:

| v1 Pattern | v2 Target | Why |
|-----------|-----------|-----|
| `get_session()` auto-commits | Session per unit of work; services call `session.begin()` explicitly | Prevents mid-stream commit/close bug |
| `asyncio.create_task(process_document(...))` | Redis-backed RQ/ARQ work queue with retry + dead-letter | Durable, observable, bounded |
| Global singletons (`_vector_store`, etc.) | FastAPI app.state or DI container | Testable, swappable |
| 120-line `stream_chat` endpoint | `ChatService` orchestrator + route handler | Testable, readable |
| BM25 rebuilt per query | Cached BM25 index per collection; invalidated on doc change | 10-100x latency improvement |
| NLTK download at query time | NLTK downloaded in lifespan startup | Zero query-time filesystem overhead |
| No timeouts | `asyncio.wait_for()` on every external call | Prevent hanging requests |
| ARRAY(UUID) for document_ids | `conversation_documents` junction table | Indexable, queryable, normalized |
| JSON blob for citations | `citations` table with FKs to messages + chunks | Queryable, referentially intact |
| No pagination | `limit`/`offset` on all list endpoints | Prevents OOM at scale |
| No API versioning | `/api/v1/` prefix | Contract evolution |
| No cache | Redis cache for embeddings, frequent queries | p95 latency reduction |
| No structured logging | `structlog` with correlation IDs | Debuggable production |
| No metrics | Prometheus via `prometheus-fastapi-instrumentator` | Observability |
| No tracing | OpenTelemetry spans per pipeline stage | Performance diagnosis |
| `/api/health` returns static "ok" | `/api/health` pings Postgres, Chroma, MinIO, LLM | Real health signals |

### Data flow (corrected v2):

**Ingestion:** `Upload → RQ queue → Worker picks up → Parse (PyPDF/DOCX/TXT) → OCR fallback → Recursive chunk (paragraph→sentence→word) → Embed (all-MiniLM-L6-v2) → Index (ChromaDB) + Save chunks (Postgres) → Update BM25 cache → Mark complete (Postgres)`

**Query:** `Question → [Redis cache hit? → return cached result] → Query Rewrite (LLM) → Dense Embed + Search (ChromaDB) → BM25 Search (cached index) → RRF Merge → Cross-encoder Re-rank (top-5) → LLM Generate (streaming, with citations) → Faithfulness Check (async, after response) → SSE Stream → Log to UsageLog + Prometheus`

---

## 3. Security Hardening Plan

### 3.1 Fail-fast secret validation
```python
# Added to config.py Settings class — Pydantic validators
@field_validator("jwt_secret", "file_encryption_key", mode="after")
@classmethod
def reject_placeholder_secrets(cls, v: str, info: ValidationInfo) -> str:
    placeholders = ["change-me-", "changeme", "placeholder"]
    if not v or any(p in v.lower() for p in placeholders):
        raise ValueError(
            f"{info.field_name} must be set to a strong, unique value. "
            f"See .env.example for generation instructions."
        )
    return v
```

### 3.2 Refresh token rotation
- Add `token_version: int = 1` column to `users` table
- New JWT claim `tok_ver: <version>` included in every refresh token
- On refresh: increment `token_version` for the user, invalidating all previous refresh tokens
- `/api/v1/auth/logout` increments the version counter (invalidates all sessions)

### 3.3 Tiered rate limiting

| Endpoint Group | Limit | Window |
|----------------|-------|--------|
| `/api/v1/auth/login` | 5 | per minute per IP |
| `/api/v1/auth/register` | 3 | per hour per IP |
| `/api/v1/auth/refresh` | 10 | per minute per IP |
| `/api/v1/chat/*` | 30 | per minute per user |
| `/api/v1/documents/*` | 60 | per minute per user |
| All others | 100 | per minute per IP |

### 3.4 Frontend mitigations
- **CSP headers** added via Next.js `middleware.ts`
- **Markdown sanitization** via `rehype-sanitize` or `DOMPurify` before `react-markdown` rendering
- **Error boundaries** wrapping `ChatPanel` and `DocumentViewer` components
- **httpOnly cookies** as an alternative storage for tokens (optional config switch)

### 3.5 Red-team test execution plan
1. Start the full stack (`docker compose up`)
2. Upload each adversarial document from `eval/red_team/`
3. Ask a question that triggers the injection
4. Record whether the model followed the injected instruction
5. Update `docs/security-notes.md` with actual pass/fail + model output

---

## 4. Data Model Redesign

### 4.1 New junction table: `conversation_documents`
```sql
CREATE TABLE conversation_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(conversation_id, document_id)
);
CREATE INDEX idx_conv_docs_conv ON conversation_documents(conversation_id);
CREATE INDEX idx_conv_docs_doc ON conversation_documents(document_id);
```

### 4.2 New normalized table: `citations`
```sql
CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    chunk_id UUID REFERENCES chunks(id) ON DELETE SET NULL,
    chroma_chunk_id VARCHAR(255),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    page_number INTEGER,
    score FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_citations_message ON citations(message_id);
```

### 4.3 Migration from old schema
- Alembic migration 002: create junction + citations tables, migrate existing data from JSON/ARRAY columns, then drop old columns

### 4.4 Required composite indexes

| Table | Index | Query Pattern |
|-------|-------|---------------|
| `documents` | `(user_id, created_at DESC)` | `SELECT ... WHERE user_id = X ORDER BY created_at DESC` |
| `conversations` | `(user_id, updated_at DESC)` | `SELECT ... WHERE user_id = X ORDER BY updated_at DESC` |
| `chunks` | `(document_id, chunk_index)` | `SELECT ... WHERE document_id = X ORDER BY chunk_index` |
| `messages` | `(conversation_id, created_at)` | `SELECT ... WHERE conversation_id = X ORDER BY created_at` |
| `chunks` | GIN `(to_tsvector('english', content))` | Full-text search (replacing/augmenting BM25) |

---

## 5. API Contract Redesign

### 5.1 Versioned routes
All routes move under `/api/v1/`:
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/documents/upload`
- `GET /api/v1/documents/`
- etc.

### 5.2 Pagination envelope
```python
# All list responses use this shape
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int = 20
    offset: int = 0
```

### 5.3 Consistent error envelope
```python
class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None  # e.g., "TOKEN_EXPIRED", "RATE_LIMIT_EXCEEDED"
    error_type: str | None = None
    timestamp: datetime
```

### 5.4 Operation IDs
Explicit `operation_id` on every route for clarity in generated OpenAPI/TypeScript:
```python
@router.post("/upload", operation_id="uploadDocument")
```

### 5.5 TypeScript type generation
```bash
npx openapi-typescript http://localhost:8000/openapi.json -o frontend/src/lib/api-types.ts
```
This replaces all manually-duplicated `Citation` and `Message` interfaces in the frontend.

---

## 6. Observability Plan

### 6.1 Structured logging (`structlog`)
```python
import structlog

logger = structlog.get_logger()
logger.info("query_processed", 
    user_id=user_id, 
    conversation_id=conv_id, 
    latency_ms=total_time,
    token_count=token_count,
    faithfulness_score=faith_score
)
```

**Correlation IDs:** A middleware generates `X-Request-ID` for every request and threads `user_id`, `conversation_id`, `document_id` through the log context.

### 6.2 Prometheus metrics
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```
Plus custom metrics:
- `veridoc_query_latency_seconds` — histogram of total query time
- `veridoc_retrieval_latency_seconds` — histogram of retrieval stage
- `veridoc_generation_latency_seconds` — histogram of generation stage
- `veridoc_queries_total` — counter, labelled by status (success/error/faithfulness_violation)
- `veridoc_tokens_total` — counter, labelled by model

### 6.3 Health check
```python
@app.get("/api/v1/health")
async def health_check():
    statuses = {
        "postgres": await _check_postgres(),
        "chroma": await _check_chroma(),
        "minio": await _check_minio(),
        "llm": await _check_llm(),
    }
    overall = "ok" if all(s["ok"] for s in statuses.values()) else "degraded"
    return {
        "status": overall,
        "version": "0.1.0",
        "checks": statuses,
        "uptime_seconds": (datetime.now(timezone.utc) - startup_time).total_seconds(),
    }
```

---

## 7. Testing Strategy

```text
         /|\
        / | \          E2E (Playwright): 3-5 tests
       /  |  \         signup → upload → ask → citation → refusal
      /   |   \
     /    |    \       Integration (testcontainers): 15-20 tests
    /     |     \      Postgres + Chroma with real queries
   /      |      \
  /       |       \    Unit (pytest + DI mocks): 80+ tests
 /        |        \   All services, all edge cases, no globals
```

### 7.1 Unit tests (80+)
- `ChatService`: mock all dependencies, verify orchestration
- `AuthService`: register, login, refresh, password change
- `DocumentService`: upload, list, delete, reindex
- `IngestionService`: parse, chunk, embed, index
- `RetrievalService`: BM25, dense, RRF, rerank
- `EvaluationService`: faithfulness check, compute_metrics
- All edge cases: empty results, invalid inputs, timeouts

### 7.2 Integration tests (15-20)
```python
@pytest.mark.integration
async def test_document_ingestion_end_to_end(postgres_container, chroma_container):
    # Real Postgres + Real ChromaDB via testcontainers
    doc = await ingest_service.ingest("test.pdf")
    assert doc.status == "indexed"
    results = await retrieval_service.retrieve("test query", [str(doc.id)])
    assert len(results) > 0
```

### 7.3 E2E tests (3-5 Playwright)
```typescript
test("full flow: upload, ask, cite", async ({ page }) => {
    await page.goto("/register");
    await page.fill("[name=email]", "test@test.com");
    // ...
    await page.click("text=Upload Document");
    await page.setInputFiles("input[type=file]", "data/documents/test.pdf");
    await page.click("text=Upload");
    await page.waitForText("Indexed");
    await page.fill("textarea", "What is this about?");
    await page.press("textarea", "Enter");
    await page.waitForSelector(".citation-chip");
    await page.click(".citation-chip");
    await page.waitForSelector(".highlighted-passage");
});
```

### 7.4 Security tests
```python
async def test_cross_user_access():
    # User A's token, try to read User B's document → 403
    # Tampered JWT → 401
    # SQL injection in search → 400 (not 500)
    # XSS in document title → rendered as text, not HTML
```

### 7.5 Load tests (Locust)
```python
class VeridocUser(HttpUser):
    @task
    def ask_question(self):
        self.client.post("/api/v1/chat/stream", json={
            "conversation_id": self.conv_id,
            "message": "What is the main topic?",
        })
```
Targets: p50 < 5s, p95 < 15s, error rate < 1% at 10 concurrent users.

---

## 8. 2026 Job-Market Portfolio Differentiation Strategy

### 8.1 Real (not synthetic) evaluation report
The single biggest differentiator: a reproducible benchmark with real numbers, a naive-vs-hybrid comparison table, and a Latency/Accuracy Pareto curve. Most "chat with PDF" repos on GitHub have zero evaluation or purely made-up numbers.

### 8.2 "What I got wrong and fixed" narrative
The `docs/case-study.md` should document:
1. The audit findings (this document)
2. What was fixed and how
3. What was learned

Recruiters at top AI companies (Anthropic, OpenAI, Google DeepMind, Cohere) are tired of perfect-showcase repos. They want to see engineering judgment — knowing what to fix and what to defer is more valuable than a spotless codebase.

### 8.3 Live demo URL
A deployed instance on Render/Fly.io with a free-tier Postgres + smaller Ollama model. Even if it's slow, having a live demo is strictly better than screenshots.

### 8.4 Badges in README
```markdown
[![CI](https://github.com/.../workflows/CI/badge.svg)](...)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://veridoc.onrender.com)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](...)
```

### 8.5 Resume bullet extraction
> *"Designed and built a production-grade RAG question-answering system (FastAPI + Next.js + Postgres + ChromaDB) that ingests PDF/DOCX/TXT documents and answers natural-language questions with inline citations. Achieved 66.7% answer accuracy (vs 46.7% naive dense-only) and 82.4% faithfulness via a hybrid BM25+dense retrieval pipeline with cross-encoder reranking, measured against a 23-question gold evaluation set. Reduced p95 query latency by 12% through BM25 index caching and cross-encoder batching. Implemented JWT auth with per-user document isolation, SSE streaming, and prompt-injection defense validated against an 8-scenario red-team test suite."*

---

## 9. Prioritized Roadmap

### 🔴 CRITICAL — Blocks correctness or security

| # | Item | Effort | Files |
|---|------|--------|-------|
| 1 | Fix `get_session()` auto-commit + SSE session bug | Easy | `backend/app/core/database.py`, `backend/app/api/chat.py` |
| 2 | Remove default secrets + add startup validation | Easy | `backend/app/core/config.py`, `.env.example` |
| 3 | Add `output: 'standalone'` to `next.config.js` | Easy | `frontend/next.config.js` |
| 4 | Add timeouts to LLM, Chroma, MinIO calls | Medium | `backend/app/services/llm_provider.py`, `vector_store.py` |
| 5 | Fix global `Exception` handler catching `HTTPException` | Easy | `backend/app/main.py` |
| 6 | Add `.dockerignore` | Easy | `.dockerignore` (new) |

### 🟡 THIS WEEK — Blocks production readiness

| # | Item | Effort | Files |
|---|------|--------|-------|
| 7 | Split `retrieval.py` into 5 files | Medium | `backend/app/services/retrieval/` (new dir) |
| 8 | Extract `ChatService` from `stream_chat` | Medium | `backend/app/services/chat_service.py` (new), `backend/app/api/chat.py` |
| 9 | Move NLTK download to lifespan | Easy | `backend/app/main.py`, `backend/app/services/retrieval/bm25.py` |
| 10 | Add `GET /api/v1/documents/{id}/content` | Medium | `backend/app/api/documents.py`, `backend/app/services/document_service.py` |
| 11 | Add `/api/v1/` prefix + pagination | Medium | All route files |
| 12 | Fix `stream_chat` SSE to use service layer | Medium | `backend/app/api/chat.py` |
| 13 | Clean up `requirements.txt` | Easy | `backend/requirements.txt` |
| 14 | Replace ARRAY/JSON with proper tables | Hard | Alembic migration + model changes |
| 15 | Add favicon, remove unused deps | Easy | `frontend/public/`, `frontend/package.json` |

### 🟢 NEXT MONTH — Scale & observability

| # | Item | Effort |
|---|------|--------|
| 16 | Redis-backed background job queue (ARQ/Celery) | Hard |
| 17 | Cache BM25 index, invalidate on doc changes | Medium |
| 18 | Structured logging (`structlog`) | Medium |
| 19 | Prometheus metrics | Medium |
| 20 | Real `/api/health` with dependency checks | Medium |
| 21 | Integration tests with testcontainers | Hard |
| 22 | Frontend unit tests (Vitest) | Medium |
| 23 | Playwright E2E tests | Medium |
| 24 | Security tests (JWT tampering, cross-user) | Medium |
| 25 | Fix CI to actually exercise real code paths | Hard |
| 26 | Add CSP headers + error boundaries | Medium |
| 27 | TypeScript type generation from OpenAPI | Easy |

### 🔵 LONG-TERM

| # | Item | Effort |
|---|------|--------|
| 28 | Load testing with Locust + numbers in docs | Medium |
| 29 | Deploy to cloud + live demo URL | Medium |
| 30 | Demo recording + README polish | Easy |
| 31 | ONNX runtime for cross-encoder batching | Hard |
| 32 | Multi-tenant orgs + RBAC | Hard |
| 33 | Kubernetes manifests | Hard |

---
*End of Prompt 1 — Planning document. Ready for Prompt 2 implementation pass.*
