# Glossary — Veridoc: Shared Vocabulary

| Field | Value |
|---|---|
| Version | v0.1 |
| Last Updated | 2026-08-06 |
| Owner | Tech Writer |
| Status | Approved |

| Term | Definition |
|---|---|
| RAG | Retrieval-Augmented Generation — retrieve passages, then generate grounded answers |
| Local-first | Runs without cloud accounts/API keys (Ollama default) |
| Chunk | Bounded passage of a document fed to embeddings |
| Embedding | Dense vector (384-dim, MiniLM) representing chunk semantics |
| BM25 | Lexical keyword ranking |
| Dense search | Vector similarity search |
| RRF | Reciprocal Rank Fusion — merges BM25 + dense rankings |
| Cross-encoder reranker | Model scoring query-passage pairs; top-20 → top-5 |
| Query rewriting | LLM converts vague follow-up into standalone query |
| SSE | Server-Sent Events — token streaming to client |
| Citation | Link from a claim to source page + paragraph |
| Faithfulness check | LLM-as-judge verifying answer is grounded before display |
| Refusal | Graceful "cannot answer" when retrieval/faithfulness fails |
| Gold set | 23 curated Q&A pairs across 4 document types for eval |
| Red-team test | Adversarial security test (8 total) |
| Prompt injection | Attack trying to override system instructions via content |
| Retrieved-context markers | `<retrieved_context>` boundaries separating content from instructions |
| Row-level isolation | user_id from JWT enforced on every user-scoped endpoint |
| Fernet | AES-128-CBC + HMAC symmetric encryption for files at rest |
| ARQ | Async Redis job queue for ingestion |
| MinIO | S3-compatible local object store for encrypted files |
| DI container | Constructor-injection wiring replacing global singletons |
| Correlation ID | Request/user/conversation id on every log line |
| Testcontainers | Real Postgres + ChromaDB spun up for CI integration tests |
| OQ-01 live eval | Full 23-question run on Docker stack (pending) |

## Related Documents

| Document | Relationship |
|---|---|
| [PRD.md](PRD.md) | Feature vocabulary |
| [TechSpec.md](TechSpec.md) | Technical terms |
| [AppFlow.md](AppFlow.md) | Screen-level terms |
| [Schema.md](Schema.md) | Data terms (TBL-*) |
| [ImplementationPlan.md](ImplementationPlan.md) | Task vocabulary |
| [Tracker.md](Tracker.md) | Status terms |
| [Rules.md](Rules.md) | Convention terms |
| [API.md](API.md) | API vocabulary |
| [SecurityAndCompliance.md](SecurityAndCompliance.md) | Security terms |
| [Testing.md](Testing.md) | Test vocabulary |
| [Deployment.md](Deployment.md) | Ops terms |
| [RiskRegister.md](RiskRegister.md) | Risk vocabulary |
