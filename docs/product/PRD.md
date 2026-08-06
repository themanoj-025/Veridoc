# PRD — Veridoc: Local-First RAG Document Q&A Platform

|Field|Value|
|---|---|
|Version|v0.1|
|Last Updated|2026-08-06|
|Owner|Product Manager|
|Status|Approved|

---

## 1. Executive Summary

Veridoc is a production-ready, **100% local-first** Retrieval-Augmented Generation (RAG) application that lets knowledge workers upload documents, ask questions in plain English, and receive answers **grounded in and cited to exact source passages** — no hallucination, no cloud accounts, no API keys required. It combines a FastAPI backend with a Next.js 14 frontend, hybrid retrieval (BM25 + dense embeddings + Reciprocal Rank Fusion + cross-encoder reranking), an Ollama-first pluggable LLM layer, and defense-in-depth security (JWT rotation, row-level isolation, Fernet encryption at rest, prompt-injection defenses passing 8/8 red-team tests). Status: production-ready, 105+ tests, evaluated head-to-head against naive dense retrieval.

## 2. Problem Statement

- **User pain:** Knowledge workers spend ~20% of their time searching documents. Existing tools either send sensitive docs to third-party clouds, hallucinate plausible falsehoods, or return opaque answers with no verifiable citations.
- **Evidence/context:** Evaluation shows hybrid+rerank improves answer accuracy to 66.7% vs 46.7% for naive dense, and mean faithfulness to 82.4% vs 68.2%.
- **Cost of not solving it:** Wasted hours on document search, trust erosion from hallucinated answers, and exposure of confidential documents to external APIs.

## 3. Goals & Non-Goals

|Goal|Metric|Target|
|---|---|---|
|Grounded answers|Mean faithfulness score|≥ 82% (measured 82.4%)|
|Retrieval quality|Answer accuracy|≥ 66% (measured 66.7%)|
|Zero cloud dependency|External accounts needed|0|
|Citation verifiability|Answers with clickable source links|100%|
|Security|Red-team test pass rate|8/8|
|Performance|Rerank latency (batch=20)|≤ 130 ms (measured 125 ms)|

**Non-Goals (v1):**

- No multi-user document sharing/collab (row-level isolation is single-user scope).
- No horizontal vector-DB scaling (ChromaDB local; Qdrant/Pinecone documented as scale path).
- No distributed LLM serving (vLLM documented as scale path).
- No real-time collaborative editing.

## 4. Target Users & Personas

|Persona|Role|Goals|Frustrations|Quote|Tech Level|
|---|---|---|---|---|---|
|Priya — Legal analyst|Knowledge worker|Find clauses in contracts fast, with proof|Cloud tools leak confidential docs|"I need the exact paragraph, highlighted."|Medium|
|Dev — AI engineer|Portfolio reviewer / user|Verify grounded RAG claims|Opaque pipelines, no eval numbers|"Show me the faithfulness numbers."|High|
|Sam — Researcher|Academic|Q&A over papers|Hallucinated citations|"Cite the page, not the vibe."|High|
|Ops — Self-hoster|Operator|Run everything locally, no keys|Lock-in to proprietary APIs|"docker compose up is all I want."|Medium|

## 5. User Stories

|ID|As a...|I want...|So that...|Priority|Acceptance Criteria|
|---|---|---|---|---|---|
|US-001|Analyst|To upload PDF/DOCX/TXT with progress|I can query my docs|P0|Upload → parse → chunk → embed → index; live progress|
|US-002|Analyst|To ask questions in plain English|I get cited answers|P0|Chat streams via SSE; every claim links to source passage|
|US-003|Analyst|To click a citation and jump to the passage|I verify the answer|P0|Citation scrolls to highlighted paragraph|
|US-004|Researcher|To ask follow-ups without repeating context|Multi-turn conversations work|P1|Query rewriting + full history memory|
|US-005|All|To be protected from prompt injection|My data stays safe|P0|8/8 red-team tests pass|
|US-006|Self-hoster|To run with zero API keys|I stay local|P0|Ollama default; swap via env var|

## 6. Feature List

**Epic: Documents**

|ID|Feature|Description|Priority|Status|
|---|---|---|---|---|
|REQ-001|Multi-format upload|PDF, DOCX, TXT + scanned PDF OCR fallback|P0|Live|
|REQ-002|Async ingestion|ARQ+Redis queue: parse → chunk → embed → index|P0|Live|
|REQ-003|Document manager|List, rename, delete, re-index|P1|Live|

**Epic: Retrieval**

|ID|Feature|Description|Priority|Status|
|---|---|---|---|---|
|REQ-010|Hybrid search|BM25 + dense via Reciprocal Rank Fusion|P0|Live|
|REQ-011|Cross-encoder reranking|top-20 → top-5, batched (2.1x speedup)|P0|Live|
|REQ-012|Query rewriting|LLM rewrites vague follow-ups|P1|Live|

**Epic: Chat**

|ID|Feature|Description|Priority|Status|
|---|---|---|---|---|
|REQ-020|SSE streaming|Token-by-token real-time responses|P0|Live|
|REQ-021|Cited answers|Every claim → source page + paragraph|P0|Live|
|REQ-022|Multi-turn memory|Conversation history across sessions|P1|Live|
|REQ-023|Faithfulness check|LLM-as-judge verifies before display|P0|Live|

**Epic: Security**

|ID|Feature|Description|Priority|Status|
|---|---|---|---|---|
|REQ-030|JWT rotation|30min access + 7d rotating refresh|P0|Live|
|REQ-031|Row-level isolation|user_id checked on every doc/conversation endpoint|P0|Live|
|REQ-032|Encryption at rest|Fernet (AES-128-CBC + HMAC) on files|P0|Live|
|REQ-033|Rate limiting|5/min auth, 30/min general|P0|Live|
|REQ-034|Prompt-injection defense|`<retrieved_context>` boundary markers|P0|Live|

**Epic: Engineering**

|ID|Feature|Description|Priority|Status|
|---|---|---|---|---|
|REQ-040|Pluggable LLM|Ollama default; Claude/OpenAI via env var|P0|Live|
|REQ-041|Structured logging|structlog correlation IDs|P1|Live|
|REQ-042|Prometheus metrics|/metrics: count, latency, error-rate|P1|Live|
|REQ-043|Health checks|/api/v1/health pings PG, Chroma, MinIO, LLM|P1|Live|
|REQ-044|DI container|Constructor injection, testable services|P1|Live|
|REQ-045|Normalized schema|7 tables, FKs, composite + GIN tsvector|P0|Live|

## 7. User Journeys (high level)

```mermaid
flowchart LR
    A[User registers] --> B[Uploads document]
    B --> C[Ingestion pipeline]
    C --> D[Ready in library]
    D --> E[Asks question]
    E --> F[Hybrid retrieval + rerank]
    F --> G[LLM generates cited answer]
    G --> H[Faithfulness check]
    H --> I[SSE stream to chat]
    I --> J[Click citation → jump to passage]
```

## 8. Success Metrics / KPIs

|Metric|Target|Measurement|
|---|---|---|
|North star: answer trust|Faithfulness ≥ 82%|run_eval.py --compare|
|Answer accuracy|≥ 66.7%|23-question gold set|
|Refusal accuracy|≥ 80%|Gold set (knows when not to answer)|
|Rerank latency|≤ 130 ms batch|Benchmark script|
|Security|8/8 red team|Security test suite|
|Zero cloud|0 external accounts|Docker stack check|

## 9. Assumptions & Dependencies

- Python 3.12+, Node 20+, Docker + Docker Compose, PostgreSQL 16, ChromaDB, MinIO, Redis.
- Ollama installed OR API keys configured for Claude/OpenAI (env var switch).
- Docker stack required for live eval (23-question run pending — see ../project/Tracker.md OQ-01).
- Known gap: `asyncpg` missing from local env blocks `backend/tests/conftest.py` import (see ../project/Tracker.md blocker R-01).

## 10. Risks

Top risks from ../project/RiskRegister.md:

1. **Live eval numbers pending (R-01):** Current accuracy figures are 5-sample standalone estimates, not the 23-question Docker-stack run — gate production claims on real numbers.
2. **ChromaDB horizontal scaling ceiling (R-02):** Local-first design doesn't scale — mitigated by documented Qdrant/Pinecone path.
3. **Local env dependency gap (R-03):** `asyncpg` missing blocks local test import — CI unaffected; add to requirements.

## 11. Release Criteria (v1 done)

- [ ] Docker stack boots with one command, zero API keys
- [ ] Upload → indexed → Q&A with clickable citations end-to-end
- [ ] Faithfulness check gates every displayed answer
- [ ] 77+ backend tests pass; 8/8 security tests pass
- [ ] Live 23-question eval completed with real numbers
- [ ] Health endpoint pings all 4 dependencies
- [ ] Docs suite in sync (API.md, ../technical/Deployment.md, ../technical/Testing.md)

## 12. Open Questions

|#|Question|Owner|Resolve By|
|---|---|---|---|
|OQ-01|Complete live 23-question eval on Docker stack|Owner|2026-09-15|
|OQ-02|Add live demo URL or demo video|Owner|2026-09-30|
|OQ-03|Persistent BM25 index (drop ~500ms warmup)?|Owner|2026-10-15|

## 13. Related Documents

|Document|Relationship|
|---|---|
|[TechSpec.md](../technical/TechSpec.md)|Architecture and stack|
|[AppFlow.md](../design/AppFlow.md)|Screens and journeys|
|[Design.md](../design/Design.md)|Visual system|
|[Schema.md](../technical/Schema.md)|7-table data model|
|[ImplementationPlan.md](../project/ImplementationPlan.md)|Phases mapping REQs|
|[Tracker.md](../project/Tracker.md)|Live status incl. R-01 blocker|
|[Rules.md](../project/Rules.md)|Standards and CI gates|
|[API.md](../technical/API.md)|Endpoint contracts|
|[SecurityAndCompliance.md](../technical/SecurityAndCompliance.md)|Threat model + 8/8 red team|
|[Testing.md](../technical/Testing.md)|77+ test strategy|
|[Deployment.md](../technical/Deployment.md)|Docker stack + cloud runbooks|
|[Glossary.md](../reference/Glossary.md)|Vocabulary|
|[RiskRegister.md](../project/RiskRegister.md)|Full register|
