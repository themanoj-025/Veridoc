# Veridoc — Case Study

## Problem

Knowledge workers spend an estimated 20% of their time searching for information across documents. When they find it, they often can't verify whether the answer is complete or accurate. Existing solutions either:
1. Require cloud subscriptions and send sensitive documents to third-party APIs
2. Hallucinate answers without grounding them in source material
3. Don't provide visible, clickable citations the user can verify

## Solution: Veridoc

Veridoc is a "chat with your documents" RAG application that:
- Runs **100% locally** with no cloud accounts
- Provides **cited, verifiable answers** from uploaded documents
- Supports **multi-document, multi-turn conversations**
- Uses **hybrid search** (BM25 + dense embeddings + cross-encoder reranking) for retrieval quality

## Technical Architecture

### Stack Choice Rationale

**Backend: FastAPI**
- Native async support for SSE streaming
- Pydantic v2 for schema validation
- Auto-generated OpenAPI docs

**Frontend: Next.js + TypeScript**
- Server-side rendering for performance
- TypeScript for type safety
- Tailwind CSS for rapid UI development

**Vector Store: ChromaDB**
- Runs locally, persists to disk
- Zero cloud accounts needed
- Simple API for embedding storage/retrieval

**LLM: Ollama (local)**
- No API keys or cloud accounts
- Open-weight models (llama3.1:8b)
- Pluggable: swap to Claude/GPT via env var

### Key Technical Decisions

1. **Hybrid Retrieval**: BM25 catches exact keyword matches that dense search might miss. Dense search captures semantic similarity. RRF merges both fairly. Cross-encoder reranks top candidates for precision.

2. **Hand-rolled Pipeline**: No LangChain abstraction. Every step (retrieval, reranking, generation, faithfulness checking) is explicit code, making the system inspectable and explainable.

3. **Instruction Boundary**: Retrieved content is separated from system instructions with clear delimiters, preventing prompt injection through document text.

4. **Faithfulness Checking**: Each answer is verified against source context using an LLM-as-judge approach, providing a quantitative faithfulness score.

---

## What Was Broken and How It Was Found and Fixed

*This section is the most honest part of this document. It documents real bugs discovered during the engineering audit and how each was fixed.*

### 1. SSE Streaming Was Corrupting the Database Session

**Bug:** `get_session()` in `database.py` used a try/finally block that committed and closed the session after every yield. This worked fine for normal request/response endpoints, but for the SSE streaming endpoint (`stream_chat`), the route handler returns BEFORE the stream finishes. By the time the assistant message needed to be persisted, the session was already closed.

**How it was found:** The SSE stream would crash with an "await on a closed session" error after streaming a few tokens. The audit traced this to the FastAPI dependency-injection lifecycle — the session generator was cleaned up when the route handler returned, not when the event generator finished.

**Fix:** `backend/app/core/database.py:get_session()` — removed the auto-close on normal exit. The caller (service method or route handler) now owns the full lifecycle. For SSE streaming, the event generator's `finally` block closes the session after all tokens have been streamed. For regular endpoints, the route handler calls `await session.close()` after committing.

**File:** `backend/app/core/database.py` — 3 lines changed.

### 2. BM25 Index Rebuilt From Scratch on Every Query

**Bug:** Every call to `bm25_search()` rebuilt the entire BM25 index from scratch — tokenizing every chunk with NLTK and training a new `BM25Okapi` instance. With documents containing hundreds of chunks, this added ~500ms of overhead to every single query.

**How it was found:** Profiling query latency showed that BM25 took 60% of the total retrieval time despite being the simpler of the two search methods.

**Fix:** `backend/app/services/retrieval/bm25.py:_bm25_indexes` — added an in-memory cache keyed by sorted document IDs. The BM25 index is now built once per unique set of documents and reused on subsequent queries. The cache is invalidated when documents are added, deleted, or re-indexed via `invalidate_bm25_index()`.

**File:** `backend/app/services/retrieval/bm25.py` — ~30 lines added for caching.

### 3. Naive Query Rewrite Was String Concatenation

**Bug:** The original query-rewrite function simply concatenated the last user message with the current query: `f"{history[-2]} {query}"`. For a follow-up like "what about section 3?", this produced a garbled query like "tell me about the contract what about section 3?" that confused the search.

**How it was found:** Manual testing with multi-turn conversations showed the second query always retrieved worse results than the first.

**Fix:** `backend/app/services/retrieval/query_rewrite.py` — replaced with an actual LLM-based rewrite call. The LLM receives the chat history and the follow-up question, and produces a standalone, well-formed query. Falls back to the original query on timeout or error (not to the old concatenation).

**File:** `backend/app/services/retrieval/query_rewrite.py` — complete rewrite (~80 lines).

### 4. Global Mutable Singletons Prevented Testability

**Bug:** Five module-level global variables (`_vector_store`, `_provider`, `_embedding_model`, `_reranker`, `_job_queue`) were scattered across different files. Every test that needed any of these services had to use `unittest.mock.patch()` at module-import time, making tests fragile and tightly coupled to import order.

**How it was found:** Tests would pass or fail depending on the order of imports in the test file. Adding a new import could break existing tests.

**Fix:** `backend/app/core/di.py` — created a `DIContainer` class with ContextVar-based dependency injection. All getter functions check the container first and fall back to uncached instances only when no container is active. Tests now inject fakes via `set_di_container(container_with_mocks)` instead of `patch()`.

**File:** `backend/app/core/di.py` — new file, ~170 lines.

### 5. Default JWT Secret Was Committed as a Fallback Value

**Bug:** The config had a default JWT secret: `jwt_secret: str = "change-me-in-production-this-is-not-secure"`. Because the default was a valid-looking string (not empty), developers could forget to set it in `.env` and the app would silently use an insecure secret.

**How it was found:** Code review during the security audit flagged the committed default.

**Fix:** `backend/app/core/config.py` — changed to `jwt_secret: str = ""` (empty). Added `validate_config()` that runs at startup and refuses to boot if JWT_SECRET or FILE_ENCRYPTION_KEY is empty or matches a known-placeholder pattern.

**File:** `backend/app/core/config.py` — ~30 lines added for `validate_config()` + `_validate_secret()`.

### 6. ARRAY(UUID) and JSON Blob in the Database Schema

**Bug:** The `conversations` table used `document_ids ARRAY(UUID)` to link conversations to documents, and the `messages` table used a JSON `citations` column to store citation metadata. This violated first normal form — you couldn't query "which conversations reference document X" or "which citations point to chunk Y" with standard SQL joins.

**How it was found:** The database review flagged these as anti-patterns that would prevent proper reporting and analytics queries.

**Fix:** Replaced `ARRAY(UUID)` with a `conversation_documents` junction table. Replaced JSON `citations` with a normalized `citations` table with foreign keys to `messages` and `chunks`. Added composite indexes on `(user_id, created_at)` for documents and conversations, and a `tsvector` GIN index on chunks.content for full-text search.

**File:** Alembic migration `002` — new junction and citations tables, composite and GIN indexes.

---

## Evaluation Results

See [Evaluation Report](evaluation-report.md) for detailed metrics comparing naive dense-only retrieval vs. the full hybrid+rerank pipeline.

*Note: The evaluation numbers in the report are from the standalone pipeline logic test. Full end-to-end numbers against a live Ollama model require the Docker stack to be running.*

---

## What I'd Change at Scale

1. **Replace ChromaDB with Qdrant/Pinecone**: Chroma works well locally but doesn't scale horizontally. For production, use a distributed vector DB with proper sharding and replication.

2. **Async Ingestion Queue**: The current approach uses a Redis-backed ARQ queue (sync fallback when Redis is unavailable). For production at scale, use Celery with proper monitoring and dead-letter management.

3. **BM25 Index Persistence**: The BM25 index is cached in memory but rebuilt on app restart. For production, persist the index to disk and update incrementally.

4. **Caching Layer**: Redis for frequent query embeddings, retrieval results, and LLM responses would significantly reduce P95 latency for common questions.

5. **Distributed LLM Serving**: vLLM or TGI would provide 5-10x faster generation than raw Ollama on CPU, enabling sub-second response times.

6. **Better accuracy metric**: The current keyword-overlap heuristic for answer accuracy is imprecise. An LLM-as-judge for answer correctness would provide more reliable evaluation numbers.

7. **Async pipeline execution**: Retrieval and generation stages are currently sequential. Pipelining would improve throughput for concurrent users.

---

## Conclusion

Veridoc demonstrates that a production-quality RAG system can be built entirely with open-source, locally-run components. The hybrid retrieval pipeline significantly outperforms naive dense-only retrieval, and the citation system provides verifiable answers that users can trust.

The engineering audit caught 6 significant issues that were all fixed — from session lifecycle bugs that broke SSE streaming, to committed secrets that jeopardized security, to database schema anti-patterns that would prevent analytics. This process proved the value of a systematic audit: the codebase went from a working prototype to a production-ready application with proper error handling, observability, and testability.
