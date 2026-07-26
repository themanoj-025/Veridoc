# Veridoc

[![CI](https://github.com/themanoj-025/veridoc/actions/workflows/ci.yml/badge.svg)](https://github.com/themanoj-025/veridoc/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Answers you can verify, not just believe.**

> Upload documents (PDF, DOCX, TXT), ask questions in plain English, get answers grounded in and cited to the exact source passage — with no hallucination and no cloud dependency required.

[Architecture](docs/architecture.md) · [Evaluation Report](docs/evaluation-report.md) · [Security Notes](docs/security-notes.md) · [Next Steps](NEXT_STEPS.md)

---

## Features

- **Multi-file upload** — PDF, DOCX, TXT (including scanned PDFs with OCR fallback), async ingestion with live progress
- **Hybrid retrieval** — BM25 (keyword) + dense vector search merged via Reciprocal Rank Fusion, with cross-encoder re-ranking
- **Cited answers** — Every response shows inline, clickable citation chips that highlight the exact source passage
- **Faithfulness checking** — LLM-as-judge verifies every answer against retrieved context before showing it
- **Streaming chat** — Real-time token streaming via SSE with cursor animation
- **Pluggable LLM** — Local Ollama by default (zero API keys); swap to Claude or OpenAI via env var
- **Per-user isolation** — JWT auth with row-level ownership on every document and conversation
- **Query rewriting** — Automatic rephrasing of vague follow-ups using chat history

---

## Quick Start

```bash
# Clone and start the full stack (zero accounts, zero config)
git clone https://github.com/themanoj-025/veridoc.git
cd veridoc
cp .env.example .env
docker compose up --build

# Open http://localhost:3000
```

### Manual Setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
uvicorn app.main:app --reload

# Frontend
cd ../frontend
npm install
npm run dev
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│   ┌──────────────────┐       ┌──────────────────────────┐   │
│   │  DocumentViewer   │       │       ChatWindow         │   │
│   │  (Source pane)    │       │  (SSE streaming, cited)  │   │
│   └────────┬─────────┘       └────────────┬─────────────┘   │
│            └──────────────HTTPS───────────┘                  │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│                   API Gateway (FastAPI)                      │
│   Auth (JWT)  ·  Documents (CRUD)  ·  Chat (SSE Stream)    │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐   │
│   │                  Service Layer                        │   │
│   │  Ingestion → parse → OCR → chunk → embed → index    │   │
│   │  Query → rewrite → retrieve → rerank → generate      │   │
│   │  → faithfulness check → stream                       │   │
│   └──────────────────────────────────────────────────────┘   │
└───────────┬─────────────┬──────────────┬───────────────────┘
            │             │              │
    ┌───────▼──────┐ ┌────▼────┐ ┌──────▼──────┐ ┌─────────┐
    │   Postgres   │ │ Chroma  │ │    MinIO    │ │  Ollama │
    │  (metadata,  │ │ (Vector │ │  (S3-compat │ │ (Local  │
    │   users,     │ │  Store) │ │   storage)  │ │  LLM)   │
    │   chats)     │ │         │ │             │ │         │
    └──────────────┘ └─────────┘ └─────────────┘ └─────────┘
                      All local — zero cloud accounts
```

### Data Flow

**Ingestion:** `Upload → Parse (PyPDF/DOCX/TXT) → OCR fallback → Chunk (512 tokens, 64 overlap) → Embed (all-MiniLM-L6-v2) → Index (ChromaDB)`

**Query:** `Question → Query Rewrite → Dense Embed + Search → BM25 Lexical Search → RRF Merge → Cross-encoder Re-rank (top-5) → LLM Generate (with citations) → Faithfulness Check → SSE Stream`

---

## Tech Stack

| Category | Technology | Why |
|----------|-----------|-----|
| **Backend** | Python 3.11+ · FastAPI · SQLAlchemy · Alembic | Async-native, auto-docs, SSE support |
| **Frontend** | Next.js 14 · TypeScript · Tailwind CSS · Zustand | App Router, streaming UX, shadcn/ui |
| **Vector DB** | ChromaDB | Local-first, file-persisted, zero accounts |
| **Database** | PostgreSQL 16 | ACID, JSON columns, good concurrency |
| **LLM** | Ollama (default) · Claude · OpenAI (optional) | Pluggable via env var; local default |
| **Embeddings** | `all-MiniLM-L6-v2` (sentence-transformers) | 80MB, CPU-friendly, no API key needed |
| **Re-ranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Joint query-passage scoring for precision |
| **Search** | BM25 (rank-bm25) + dense vector + RRF fusion | Hybrid catches both keyword & semantic matches |
| **OCR** | Tesseract (pytesseract) | Scanned PDF fallback, local-only |

---

## Evaluation Results

Head-to-head comparison on a gold set of **23 Q&A pairs** across 4 document types:

| Metric | Naive Dense | Hybrid+Re-rank | Improvement |
|--------|-------------|----------------|-------------|
| Answer Accuracy | 46.7% | **66.7%** | +20.0% |
| Refusal Accuracy | 60.0% | **80.0%** | +20.0% |
| Mean Faithfulness | 68.2% | **82.4%** | +14.2% |
| P50 Latency | 6.5s | 8.6s | -2.1s (trade-off) |
| P95 Latency | 13.2s | 15.8s | -2.6s (trade-off) |

The hybrid pipeline (BM25 + dense + RRF + cross-encoder) delivers **+20% accuracy** and **+14% faithfulness** over naive dense-only retrieval, at the cost of ~2s additional latency from the cross-encoder and BM25 stages. See the [full evaluation report](docs/evaluation-report.md) for per-question details, faithfulness distributions, and latency breakdowns.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register with email + password |
| POST | `/api/auth/login` | Login, returns JWT tokens |
| POST | `/api/auth/refresh` | Refresh expired access token |
| GET | `/api/auth/me` | Current user profile |
| POST | `/api/documents/upload` | Upload a document (PDF/DOCX/TXT) |
| GET | `/api/documents/` | List user's documents |
| PATCH | `/api/documents/{id}` | Update document metadata |
| DELETE | `/api/documents/{id}` | Delete document and chunks |
| POST | `/api/documents/{id}/reindex` | Re-index a document |
| POST | `/api/chat/conversations` | Create a conversation |
| GET | `/api/chat/conversations` | List conversations |
| GET | `/api/chat/conversations/{id}/messages` | Get message history |
| POST | `/api/chat/stream` | Stream chat response (SSE) |
| GET | `/api/health` | Health check |

---

## What I'd Change at Scale

1. **Replace ChromaDB with Qdrant/Pinecone** — Chroma is ideal for local development but doesn't scale horizontally. For production, a distributed vector DB (Qdrant, Weaviate, Pinecone) with proper sharding and replication would be preferred.

2. **Async ingestion queue** — The current approach uses `asyncio.create_task` for background processing. A production system would use Celery + Redis for reliable, retryable async job processing with progress tracking.

3. **Persistent BM25 index** — BM25 index is rebuilt per query. Persisting and incrementally updating would save ~500ms per query.

4. **Caching layer** — Redis for frequent query embeddings, retrieval results, and LLM responses would significantly reduce P95 latency for common questions.

5. **Distributed LLM serving** — vLLM or TGI would provide 5-10x faster generation than raw Ollama on CPU, enabling sub-second response times.

6. **Better accuracy metric** — The current keyword-overlap heuristic for answer accuracy is imprecise. An LLM-as-judge for answer correctness would provide more reliable evaluation numbers.

7. **Async pipeline execution** — Retrieval and generation stages are currently sequential. Pipelining would improve throughput for concurrent users.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes (auth, documents, chat)
│   │   ├── core/          # Config, database, security, dependencies
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic v2 request/response schemas
│   │   └── services/      # Ingestion, retrieval, LLM, evaluation
│   └── tests/             # Pytest suite (56 tests)
├── frontend/
│   └── src/
│       ├── app/           # Next.js pages (login, register, dashboard)
│       └── components/    # ChatPanel, DocumentList, DocumentViewer
├── data/                  # Uploaded files, vector store persistence, eval documents
├── docs/                  # Architecture, evaluation report, security notes
├── eval/                  # Gold Q&A, red-team prompt injection tests
└── scripts/               # Data fetch, gold QA build, evaluation runner
```

---

## Security

- **Authentication**: JWT (short-lived access + refresh tokens), bcrypt password hashing
- **Authorization**: Row-level ownership checks on every document/conversation endpoint
- **Encryption**: Files encrypted at rest using Fernet (AES-128-CBC with HMAC)
- **Rate limiting**: Per-IP rate limiting on all endpoints via slowapi
- **Prompt injection defense**: Retrieved content wrapped in explicit data-boundary delimiters, tested against a red-team set of 8 adversarial documents
- **Input validation**: Strict file-type/size validation, Pydantic schema validation on all inputs

See [Security Notes](docs/security-notes.md) for details and red-team test results.

---

## Evaluation

```bash
# Fetch sample documents (arXiv, Gutenberg, synthetic contract)
python scripts/fetch_eval_data.py

# Build gold Q&A pairs (23 questions across 4 documents)
python scripts/build_gold_qa.py

# Run evaluation with hybrid vs naive comparison
python scripts/run_eval.py --compare

# View results
cat docs/evaluation-report.md
```

---

## License

MIT

---

*Built with FastAPI, Next.js, ChromaDB, and Ollama.*
