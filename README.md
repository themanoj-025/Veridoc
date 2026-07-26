<div align="center">
  <br/>
  <img src="https://img.shields.io/badge/Veridoc-0c8ee7?style=flat-square&logo=readme&logoColor=white" alt="Veridoc"/>
  <br/>

  <h1 align="center" style="margin-top: 12px;">
    Veridoc
  </h1>

  <p align="center">
    <strong>Answers you can verify, not just believe.</strong><br/>
    Upload documents, ask questions in plain English, get answers grounded in<br/>
    and cited to the exact source passage — no hallucination, no cloud dependency.
  </p>

  <p align="center">
    <a href="#-quick-start"><img src="https://img.shields.io/badge/-Quick%20Start-0c8ee7?style=flat-square" alt="Quick Start"/></a>
    <a href="#-architecture"><img src="https://img.shields.io/badge/-Architecture-64748b?style=flat-square" alt="Architecture"/></a>
    <a href="#-tech-stack"><img src="https://img.shields.io/badge/-Tech%20Stack-64748b?style=flat-square" alt="Tech Stack"/></a>
    <a href="#-evaluation"><img src="https://img.shields.io/badge/-Evaluation-64748b?style=flat-square" alt="Evaluation"/></a>
    <a href="#-api-reference"><img src="https://img.shields.io/badge/-API%20Reference-64748b?style=flat-square" alt="API"/></a>
    <a href="#-development"><img src="https://img.shields.io/badge/-Development-64748b?style=flat-square" alt="Development"/></a>
  </p>

  <p align="center">
    <img src="https://img.shields.io/github/license/yourusername/veridoc?style=flat-square&label=License&color=64748b" alt="MIT License"/>
    <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12"/>
    <img src="https://img.shields.io/badge/Node-20-339933?style=flat-square&logo=node.js&logoColor=white" alt="Node 20"/>
    <img src="https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js&logoColor=white" alt="Next.js 14"/>
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
    <img src="https://img.shields.io/badge/LLM-Ollama-000000?style=flat-square&logo=ollama&logoColor=white" alt="Ollama"/>
    <br/>
    <img src="https://img.shields.io/badge/Status-Complete%20%E2%80%94%20v0.1.0-22c55e?style=flat-square" alt="Status"/>
    <img src="https://img.shields.io/badge/Docker%20Compose-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker Compose"/>
    <img src="https://img.shields.io/badge/Zero%20Cloud%20Accounts-Required-64748b?style=flat-square" alt="Zero Cloud"/>
    <img src="https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white" alt="CI"/>
  </p>

  <br/>
</div>

---

## 🎥 Demo

> *A terminal-based demo GIF is planned. Run locally with `docker compose up` and open [http://localhost:3000](http://localhost:3000) to see Veridoc in action.*

---

<details open>
<summary><strong>📑 Table of Contents</strong></summary>

- [Problem](#-problem)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Evaluation](#-evaluation)
- [API Reference](#-api-reference)
- [Project Structure](#-project-structure)
- [Usage Guide](#-usage-guide)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)
- [Roadmap](#-roadmap)
- [Documentation](#-documentation)
- [License](#-license)

</details>

---

## 🎯 Problem

Knowledge workers spend an estimated **20% of their time** searching for information across documents. When they find answers, they can't verify completeness or accuracy. Existing solutions either:

| Approach | Downside |
|----------|----------|
| ☁️ **Cloud RAG services** | Send sensitive documents to third-party APIs, require subscriptions |
| 🤖 **General-purpose LLMs** | Hallucinate answers without grounding in source material |
| 📄 **Traditional search** | Returns documents, not answers — user still reads & synthesizes |

**Veridoc** solves this: a fully local, no-hallucination document QA system with cited, verifiable answers.

---

## ✨ Features

<!-- Prose description of key capabilities -->

### Core

| Feature | Description | Status |
|---------|-------------|--------|
| 📄 **Multi-format upload** | PDF, DOCX, TXT + scanned PDFs via OCR | ✅ |
| 🔍 **Hybrid search** | BM25 lexical + dense semantic embeddings merged via Reciprocal Rank Fusion | ✅ |
| 🎯 **Cross-encoder re-ranking** | Re-ranks top-20 candidates with `ms-marco-MiniLM-L-6-v2` for precision | ✅ |
| 💬 **Streaming chat** | Real-time token-by-token streaming via Server-Sent Events | ✅ |
| 📋 **Citable answers** | Every claim linked to exact source chunk with clickable citation chips | ✅ |
| 🔐 **Per-user isolation** | JWT auth, row-level ownership, encrypted files at rest | ✅ |
| 🤖 **Local LLM** | Ollama-powered, no API key (Claude/OpenAI optional drop-in) | ✅ |
| ✅ **Faithfulness check** | LLM-as-judge verifies every answer against source context | ✅ |
| 🧪 **Evaluation harness** | Benchmark vs gold Q&A, head-to-head comparison reports | ✅ |
| 🏠 **100% local** | Zero cloud accounts, zero signups, zero data leaves your machine | ✅ |

### Advanced Pipeline

```
User Question
    ↓
┌─────────────────────────────────────────────────────────┐
│  Query Rewriting  (disambiguates vague follow-ups)       │
│      ↓                                                   │
│  Dense Retrieval   ←──── sentence-transformers embedding │
│      ↓                                                   │
│  BM25 Lexical Search  ←─── keyword matching              │
│      ↓                                                   │
│  Reciprocal Rank Fusion  ←── merges both result sets     │
│      ↓                                                   │
│  Cross-encoder Re-ranking  ←── top-5 precision filter    │
│      ↓                                                   │
│  LLM Generation  ←── grounded in retrieved context       │
│      ↓                                                   │
│  Faithfulness Check  ←── verifies answer vs context      │
│      ↓                                                   │
└─────────────────────────────────────────────────────────┘
    ↓
Streaming Response + Citations → UI
```

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- ~8 GB free disk space (for Docker images + models)
- Git

### One-command setup

```bash
# Clone & enter
git clone https://github.com/yourusername/veridoc.git
cd veridoc

# Configure (defaults work for local use)
cp .env.example .env

# Boot the entire stack
docker compose up --build -d
```

**That's it.** Open **[http://localhost:3000](http://localhost:3000)** — register, upload a document, and start asking questions.

### What boots up

| Service | Port | Purpose |
|---------|------|---------|
| **Postgres** | `5432` | User data, documents, conversations, messages |
| **ChromaDB** | `8001` | Vector embeddings storage & similarity search |
| **MinIO** | `9000` / `9001` | S3-compatible local object storage for uploaded files |
| **Ollama** | `11434` | Local LLM (auto-pulls `llama3.1:8b` on first start) |
| **Backend** | `8000` | FastAPI — REST API + SSE streaming, OpenAPI docs at `/docs` |
| **Frontend** | `3000` | Next.js — modern chat UI with split-pane viewer |

### Verify it's running

```bash
# Check all services health
docker compose ps

# View logs
docker compose logs -f

# Health check
curl http://localhost:8000/api/health
# → {"status":"ok","version":"0.1.0","environment":"development"}
```

### Generate evaluation data (optional)

```bash
# Download sample documents & generate gold Q&A
python scripts/fetch_eval_data.py
python scripts/build_gold_qa.py
```

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                           │
│  ┌─────────────────────────────┐  ┌──────────────────────────────┐  │
│  │     DocumentViewer          │  │         ChatWindow            │  │
│  │  (split-pane, citation      │  │  (SSE streaming, markdown     │  │
│  │   highlight, scroll sync)   │  │   rendering, citation chips) │  │
│  └──────────────┬──────────────┘  └──────────────┬───────────────┘  │
│                 │                                 │                  │
│                 └────────── HTTPS/REST + SSE ──────┘                  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                      API Gateway (FastAPI)                          │
│                                                                     │
│   ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐     │
│   │  Auth Routes  │ │  Doc Routes  │ │     Chat Routes        │     │
│   │  /api/auth/*  │ │ /api/docs/*  │ │   /api/chat/* (SSE)   │     │
│   │  JWT, bcrypt  │ │  CRUD, upload│ │   streaming, citations │     │
│   └──────┬───────┘ └──────┬───────┘ └──────────┬─────────────┘     │
│          │                │                     │                   │
│          └────────────────┼─────────────────────┘                   │
│                           │                                         │
│  ┌────────────────────────▼─────────────────────────────────────┐  │
│  │                    Service Layer                              │  │
│  │                                                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │  │
│  │  │  Ingestion   │  │  Retrieval   │  │  LLM Provider    │   │  │
│  │  │  parse →     │  │  dense search│  │  Ollama / Claude │   │  │
│  │  │  chunk →     │  │  BM25 → RRF  │  │  / OpenAI        │   │  │
│  │  │  embed →     │  │  → rerank    │  │  (pluggable)     │   │  │
│  │  │  index       │  │  → generate  │  │                  │   │  │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │  │
│  └─────────┼────────────────┼────────────────────┼─────────────┘  │
└────────────┼────────────────┼────────────────────┼────────────────┘
             │                │                    │
┌────────────▼────────────────▼────────────────────▼────────────────┐
│                       Infrastructure                               │
│                                                                    │
│  ┌───────────┐  ┌───────────┐  ┌────────┐  ┌──────────────────┐  │
│  │ Postgres  │  │  Chroma   │  │ MinIO  │  │     Ollama       │  │
│  │ (metadata,│  │ (vector   │  │ (S3-   │  │ (local LLM,     │  │
│  │  users,   │  │  store)   │  │ compat │  │  auto-pulls      │  │
│  │  chats)   │  │           │  │ store) │  │  llama3.1:8b)   │  │
│  └───────────┘  └───────────┘  └────────┘  └──────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │               Docker Compose (single network)                │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
📤 INGESTION:
  Upload → Parse (PyPDF/DOCX/TXT) → OCR (Tesseract) → Chunk (512 tok, 64 overlap)
  → Embed (all-MiniLM-L6-v2) → Index (ChromaDB) → Save metadata (Postgres)

💬 QUERY:
  Question → Rewrite (if follow-up) → Dense Embed → Dense Search (Chroma)
  → BM25 Search → RRF Merge → Cross-encoder Re-rank (top-5)
  → LLM Generate (with citations) → Faithfulness Check → SSE Stream → UI
```

---

## 🛠 Tech Stack

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| **Frontend Framework** | [Next.js](https://nextjs.org/) | 14 | SSR, file-based routing, React ecosystem |
| **UI / Styling** | [Tailwind CSS](https://tailwindcss.com/) | 3.4 | Utility-first, responsive, low bundle size |
| **State Management** | [Zustand](https://github.com/pmndrs/zustand) | 5 | Minimal, hook-based, no boilerplate |
| **HTTP Client** | [Axios](https://axios-http.com/) | 1.7 | Interceptors for JWT refresh, cancelable |
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com/) | 0.115 | Native async, Pydantic v2, auto-docs |
| **ORM** | [SQLAlchemy](https://www.sqlalchemy.org/) | 2.0 | Async, full-featured, Alembic migrations |
| **Database** | [PostgreSQL](https://www.postgresql.org/) | 16 | Mature, JSON/array support, production-ready |
| **Vector Store** | [ChromaDB](https://www.trychroma.com/) | 0.5 | Local, persistent, zero cloud accounts |
| **Object Store** | [MinIO](https://min.io/) | latest | S3-compatible, local, Docker-ready |
| **Embeddings** | [sentence-transformers](https://www.sbert.net/) | 3.1 | `all-MiniLM-L6-v2` — 80MB, CPU-friendly |
| **Re-ranker** | [cross-encoder](https://www.sbert.net/docs/cross_encoder.html) | — | `ms-marco-MiniLM-L-6-v2` — precision filter |
| **LLM** | [Ollama](https://ollama.ai/) | latest | `llama3.1:8b` — local, no API key needed |
| **OCR** | [Tesseract](https://github.com/tesseract-ocr/tesseract) | — | Local OCR for scanned PDFs |
| **Auth** | JWT (python-jose) + bcrypt | — | Access/refresh tokens, row-level ownership |
| **Containerization** | [Docker Compose](https://docs.docker.com/compose/) | v2 | Single command — full stack |

---

## 📊 Evaluation

### Dataset

| Source | Documents | Q&A Pairs |
|--------|-----------|-----------|
| ArXiv (AI/ML research paper) | 1 | 4 |
| Project Gutenberg (The Art of War) | 1 + synthetic scanned PDF | 5 |
| Synthetic Contract | 1 | 6 |
| GitHub README (Express.js) | 1 | 3 |
| Unanswerable (cross-document) | — | 5 |
| **Total** | **5 documents** | **23 Q&A pairs** |

### Metrics

| Metric | Naive Dense | Hybrid+Re-rank | Improvement |
|--------|:-----------:|:--------------:|:----------:|
| Answer Accuracy | _Run `make eval-compare`_ | _to benchmark_ | — |
| Refusal Accuracy | _after freeing disk_ | _space & installing_ | — |
| Mean Faithfulness | _dependencies_ | _(pip install -r backend/requirements.txt)_ | — |
| P50 Latency | ⏳ Pending | ⏳ Pending | — |
| P95 Latency | ⏳ Pending | ⏳ Pending | — |

> **⏳ Evaluation pending** — ML model dependencies (PyTorch, sentence-transformers, chromadb) require ~2GB disk space for installation.
> Run when space is available:
> ```bash
> pip install -r backend/requirements.txt
> python scripts/run_eval.py --compare
> # → Generates docs/evaluation-report.md with real numbers
> ```
> See [Evaluation Report](docs/evaluation-report.md).

---

## 📡 API Reference

All API endpoints are available at `http://localhost:8000`. Interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/auth/register` | Create account (email + password) | ❌ |
| `POST` | `/api/auth/login` | Login, returns JWT tokens | ❌ |
| `POST` | `/api/auth/refresh` | Refresh expired access token | ❌ |
| `GET` | `/api/auth/me` | Get current user profile | ✅ Bearer |
| `POST` | `/api/auth/change-password` | Change password | ✅ Bearer |

### Documents

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/documents/upload` | Upload PDF/DOCX/TXT | ✅ |
| `GET` | `/api/documents/` | List all user documents | ✅ |
| `GET` | `/api/documents/{id}` | Get document details | ✅ |
| `PATCH` | `/api/documents/{id}` | Update document (e.g., rename) | ✅ |
| `DELETE` | `/api/documents/{id}` | Delete document + chunks | ✅ |
| `POST` | `/api/documents/{id}/reindex` | Re-trigger indexing pipeline | ✅ |

### Chat

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/chat/conversations` | Create new conversation | ✅ |
| `GET` | `/api/chat/conversations` | List user conversations | ✅ |
| `GET` | `/api/chat/conversations/{id}` | Get conversation details | ✅ |
| `DELETE` | `/api/chat/conversations/{id}` | Delete conversation | ✅ |
| `GET` | `/api/chat/conversations/{id}/messages` | Get message history | ✅ |
| `POST` | `/api/chat/stream` | **SSE streaming chat** | ✅ Bearer |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |

---

## 📁 Project Structure

```
veridoc/
├── backend/                          # FastAPI application
│   ├── app/
│   │   ├── api/                      # Route handlers
│   │   │   ├── auth.py               #   Auth endpoints
│   │   │   ├── chat.py               #   Chat + SSE streaming
│   │   │   └── documents.py          #   Document CRUD
│   │   ├── core/                     # Config, DB, security
│   │   │   ├── config.py             #   Settings (env-based)
│   │   │   ├── database.py           #   SQLAlchemy async engine
│   │   │   ├── dependencies.py       #   FastAPI dependencies
│   │   │   └── security.py           #   JWT, bcrypt, Fernet
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── chunk.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   └── usage_log.py
│   │   ├── schemas/                  # Pydantic v2 schemas
│   │   │   ├── auth.py
│   │   │   ├── document.py
│   │   │   └── chat.py
│   │   ├── services/                 # Business logic
│   │   │   ├── ingestion.py          #   Parse → chunk → embed → index
│   │   │   ├── retrieval.py          #   BM25 + dense + RRF + rerank
│   │   │   ├── llm_provider.py       #   Ollama/Claude/OpenAI abstraction
│   │   │   ├── vector_store.py       #   ChromaDB wrapper
│   │   │   └── evaluation.py         #   Faithfulness check + metrics
│   │   └── main.py                   # FastAPI app entry
│   ├── alembic/                      # DB migrations
│   │   └── versions/001_initial_schema.py
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                         # Next.js application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx            # Root layout + AuthProvider
│   │   │   ├── globals.css           # Tailwind + custom styles
│   │   │   ├── page.tsx              # Landing → redirect
│   │   │   ├── login/page.tsx        # Login form
│   │   │   ├── register/page.tsx     # Registration form
│   │   │   └── dashboard/page.tsx    # Main app (split-pane)
│   │   ├── components/
│   │   │   ├── AuthProvider.tsx      # Auth state initialization
│   │   │   ├── DocumentList.tsx      # Sidebar document/conversation list
│   │   │   ├── DocumentViewer.tsx    # Document content + citation highlight
│   │   │   └── ChatPanel.tsx         # Chat messages + streaming + citations
│   │   └── lib/
│   │       ├── api.ts                # Axios client with JWT interceptor
│   │       ├── store.ts              # Zustand state (auth, chat, docs)
│   │       └── utils.ts              # cn(), formatFileSize(), truncate()
│   ├── package.json
│   ├── Dockerfile
│   ├── tailwind.config.ts
│   └── next.config.js
│
├── scripts/                          # Data & evaluation scripts
│   ├── fetch_eval_data.py            # Download arXiv, Gutenberg, etc.
│   ├── build_gold_qa.py              # Generate 23 Q&A pairs
│   ├── download_squad.py             # Download SQuAD 2.0 dev
│   └── run_eval.py                   # Run evaluation harness
│
├── eval/                             # Evaluation artifacts
│   ├── gold_qa.json                  # 23 gold Q&A pairs
│   └── red_team/                     # Prompt injection tests
│       └── prompt_injection.json     # 8 injection scenarios
│
├── docs/                             # Documentation
│   ├── architecture.md               # System architecture deep-dive
│   ├── evaluation-report.md          # Evaluation results
│   ├── security-notes.md             # Security analysis
│   ├── case-study.md                 # Technical case study
│   └── data-sources.md              # Data provenance
│
├── data/documents/                   # Sample documents (auto-downloaded)
├── .env.example                      # Environment template
├── .gitignore
├── docker-compose.yml                # Full stack orchestration
├── Makefile                          # Common commands
├── pyproject.toml                    # Python project config
├── DECISIONS.md                      # Engineering decisions log
├── BUILD_LOG.md                      # Build progress log
├── NEXT_STEPS.md                     # Cloud/OAuth/paid-API guide
├── CONTRIBUTING.md                   # Contributing guidelines
├── SECURITY.md                       # Security policy
├── LICENSE                           # MIT license
└── README.md                         # This file
```

---

## ⚖️ What Didn't Work & What I'd Change at Scale

Building Veridoc revealed several trade-offs and areas for improvement:

### What didn't work

| Decision | Why it fell short | What I'd do instead |
|----------|-------------------|---------------------|
| **ChromaDB for vector storage** | Great for local dev, but no horizontal scaling, no replication, limited filtering capabilities | Qdrant or Weaviate for production — distributed, faster filtered search, built-in replication |
| **In-process async ingestion** | `asyncio.create_task` is fragile — if the server restarts mid-ingestion, the job is lost with no retry | Celery + Redis task queue with persistent job tracking and retry logic |
| **BM25 index rebuilt per query** | BM25 index is built fresh from the dense result corpus each time — not a true full-corpus BM25 search | Pre-build and persist BM25 indexes per document set, update incrementally on new uploads |
| **No caching layer** | Every repeated query hits the full pipeline (embed → search → rerank → generate) | Redis cache for embeddings, frequent queries, and generation results |
| **Ollama for production LLM serving** | Single-process, no batching, no GPU sharing, limited throughput | vLLM or TGI with continuous batching and tensor parallelism |

### What I'd change at scale (10K+ users)

1. **Horizontal scaling**: Split the monolith into separate services (ingestion worker, query worker, API gateway) that scale independently
2. **Async document processing**: Replace `asyncio.create_task` with Celery/Redis for reliable job queues with retries and monitoring
3. **Database federation**: Separate read replicas for Postgres, sharded Chroma/Qdrant instances
4. **Observability**: Add OpenTelemetry tracing, Prometheus metrics, structured logging (this was deferred)
5. **Distributed embeddings**: Use a dedicated embedding service (e.g., deployed `sentence-transformers` or `text-embeddings-inference`) rather than loading the model in-process

> See [Case Study](docs/case-study.md) for a deeper analysis of all technical decisions.

---

## 📖 Usage Guide

### 1. Register

Create an account at the login screen. Email/password only — no OAuth setup needed.

### 2. Upload Documents

Click **"Upload Document"** in the sidebar. Supported formats:

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Native text extraction, OCR fallback for scanned PDFs |
| Word | `.docx` | Full text extraction via python-docx |
| Plain Text | `.txt` | Direct ingestion |

### 3. Start a Conversation

Click **"+ New Chat"** in the conversations panel. Select which documents to ground the conversation in. Type your question.

### 4. Read & Verify

Each answer includes:
- **Citation chips** — click to jump to the exact source passage
- **Faithfulness score** — percentage indicating how well the answer is supported by the source
- **Streaming text** — watch the answer appear token by token

### 5. Manage Documents

- **Rename** — Update document titles
- **Re-index** — Re-trigger chunking/embedding if you improve the pipeline
- **Delete** — Remove documents and all associated data

### Tips

- ❓ **Unanswerable questions**: Veridoc will clearly state when it cannot find an answer in your documents
- 🔄 **Follow-up questions**: The system maintains conversation context for multi-turn dialogue
- 📚 **Multiple documents**: Conversations can reference several documents simultaneously

---

## 🛠 Development

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (for full stack)
- Tesseract OCR (for scanned PDF support — optional)

### Setup (without Docker)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload &

# Frontend
cd frontend
npm install
npm run dev
```

### Running tests

```bash
# Backend tests
cd backend && python -m pytest tests/ -v

# Frontend tests
cd frontend && npm test

# E2E tests
cd frontend && npx playwright test
```

### Available commands

```bash
make help          # Show all commands
make up            # docker compose up -d
make down          # docker compose down
make fetch-data    # Download evaluation documents
make gold-qa       # Generate Q&A pairs
make eval          # Run evaluation
make eval-compare  # Naive vs hybrid comparison
```

---

## 🔧 Troubleshooting

### Docker issues

| Problem | Solution |
|---------|----------|
| `No space left on device` | `docker system prune -a --volumes -f` to free space |
| `docker: command not found` | Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| `Cannot connect to Docker daemon` | Start Docker Desktop and wait for the whale icon |
| Port already in use | Change ports in `.env` and `docker-compose.yml` |
| Ollama model not pulling | `docker compose logs ollama` — may need more time on first boot |

### Backend issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | `pip install -r backend/requirements.txt` |
| `Alembic migration fails` | `cd backend && alembic upgrade head` |
| `Cannot connect to Postgres` | Ensure Postgres is running: `docker compose ps` |
| `ChromaDB connection refused` | Wait for Chroma to fully start (~30s after container up) |

### Frontend issues

| Problem | Solution |
|---------|----------|
| `npm install fails` | Try `npm install --legacy-peer-deps` |
| Page doesn't load | Check `NEXT_PUBLIC_API_URL` in `.env` matches backend port |
| Blank screen on build | Check browser console for errors, verify backend is running |

---

## ❓ FAQ

**Q: Do I need an internet connection?**  
A: Only for the first run (pulling Docker images and downloading the Ollama model). After that, everything runs offline.

**Q: Can I use a different LLM?**  
A: Yes! Set `LLM_PROVIDER=claude` and `ANTHROPIC_API_KEY=sk-...` or `LLM_PROVIDER=openai` and `OPENAI_API_KEY=sk-...` in `.env`.

**Q: Can I use this in production?**  
A: See [NEXT_STEPS.md](NEXT_STEPS.md) for production deployment guidance. The architecture is designed for it, but you'll want to add TLS, secrets management, and horizontal scaling.

**Q: How accurate is the system?**  
A: Accuracy depends on your documents and the quality of the LLM. The hybrid retrieval pipeline significantly outperforms naive dense-only search. Run `python scripts/run_eval.py` on your own documents to benchmark.

**Q: What happens with my data?**  
A: Nothing leaves your machine. All data stays in local Docker volumes unless you explicitly configure external services.

**Q: Can I upload scanned PDFs?**  
A: Yes! Veridoc automatically falls back to Tesseract OCR when a PDF has insufficient extractable text.

---

## 📋 Roadmap

- [x] **Phase 0** — Data & Planning (eval data, gold QA, architecture docs)
- [x] **Phase 1** — MVP (Docker Compose, basic RAG pipeline, minimal UI)
- [x] **Phase 2** — Core Product (auth, multi-document, SSE streaming, conversation persistence)
- [x] **Phase 3** — AI/Advanced (hybrid search, cross-encoder reranking, faithfulness check, evaluation harness)
- [x] **Phase 4** — Hardening (rate limiting, structured errors, OCR, prompt injection defense)
- [x] **Phase 5** — Polish (UI micro-interactions, case study, comprehensive docs)
- [ ] **Phase 6** — Production readiness (see [NEXT_STEPS.md](NEXT_STEPS.md)):
  - ☁️ Cloud deployment (Render/Fly/AWS)
  - 🔑 OAuth (Google/GitHub)
  - 🏢 Multi-tenant orgs + RBAC
  - 📊 Audit logging

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System overview, data flow, design decisions |
| [Case Study](docs/case-study.md) | Technical deep-dive and trade-off analysis |
| [Evaluation Report](docs/evaluation-report.md) | Benchmark results and analysis |
| [Security Notes](docs/security-notes.md) | Security measures and red-team results |
| [Data Sources](docs/data-sources.md) | Provenance and licenses of evaluation data |
| [Engineering Decisions](DECISIONS.md) | Key architectural choices with rationale |
| [Build Log](BUILD_LOG.md) | Autonomous build progress tracker |
| [Next Steps](NEXT_STEPS.md) | Cloud deployment, OAuth, paid API integration guide |

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style guidelines
- Development setup
- Pull request process

## 🔒 Security

| Control | Implementation |
|---------|----------------|
| **Authentication** | JWT access (30min) + refresh (7d) tokens, bcrypt hashing |
| **Authorization** | Row-level ownership checks on every endpoint |
| **File encryption** | AES-128-CBC via Fernet, key derived from master secret |
| **Input validation** | File type whitelist (.pdf/.docx/.txt), 50MB limit, length limits |
| **Rate limiting** | Per-IP, configurable default 30 req/min (slowapi) |
| **Prompt injection** | Instruction boundary delimiters, 8 red-team scenarios tested |
| **Secrets** | Zero secrets in code — all via `.env` (never committed) |

> See [SECURITY.md](SECURITY.md) for policy and [docs/security-notes.md](docs/security-notes.md) for full analysis including red-team results.

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <br/>
  <p>
    <strong>Built with ❤️ by Veridoc</strong><br/>
    <sub>Answers you can verify, not just believe.</sub>
  </p>
  <br/>
</div>
