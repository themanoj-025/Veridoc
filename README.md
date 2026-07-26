# Veridoc

[![CI](https://github.com/themanoj-025/veridoc/actions/workflows/ci.yml/badge.svg)](https://github.com/themanoj-025/veridoc/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An open-source question-answering system over your own documents. Upload PDFs, markdown, or text files, and ask natural-language questions with grounded, citation-backed answers.

---

## Features

- **Document ingestion** — PDF, markdown, and text file upload with auto-chunking
- **Hybrid retrieval** — Dense (embeddings) + BM25 lexical search with cross-encoder re-ranking (RRF fusion)
- **Faithfulness checking** — LLM-as-judge verifies every answer against source context
- **Pluggable LLM** — Ollama by default, switch to Claude or OpenAI via env var
- **SSE streaming** — Real-time answer streaming to the UI
- **REST API** — Full API for programmatic Q&A and document management
- **Structured evaluation** — Gold-standard Q&A pairs with faithfulness metrics

---

## Quick Start

```bash
# Clone and start
git clone https://github.com/themanoj-025/veridoc.git
cd veridoc
docker compose up --build

# Open http://localhost:3000
```

### Manual Setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure Ollama URL
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Architecture

```
User Query
    ↓
┌────────────────────────────────────────────────┐
│            Hybrid Retrieval                     │
│  Dense Search (embeddings) + BM25 Lexical      │
│  → Cross-Encoder Re-ranking (RRF)              │
└────────────────────────────────────────────────┘
    ↓
LLM Generation (grounded in retrieved context)
    ↓
Faithfulness Check (LLM-as-judge)
    ↓
SSE Stream → UI
```

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| **Backend** | Python, FastAPI, SQLAlchemy, ChromaDB |
| **Frontend** | Next.js, Tailwind CSS, TypeScript |
| **Embeddings** | all-MiniLM-L6-v2 (sentence-transformers) |
| **Re-ranker** | ms-marco-MiniLM-L6-v2 |
| **LLM** | Ollama (default), Claude, OpenAI (optional) |
| **Search** | BM25 (rank-bm25) + dense vector search |
| **Database** | PostgreSQL + ChromaDB (vector store) |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat` | Ask a question (streaming) |
| POST | `/api/v1/documents/upload` | Upload a document |
| GET | `/api/v1/documents` | List documents |
| DELETE | `/api/v1/documents/{id}` | Delete a document |
| GET | `/api/v1/health` | Service health |

---

## Evaluation

Run the evaluation harness to measure answer accuracy, refusal accuracy, and faithfulness:

```bash
# Download sample documents
python scripts/fetch_eval_data.py

# Build gold Q&A pairs
python scripts/build_gold_qa.py

# Run evaluation
python scripts/run_eval.py

# View results
cat docs/eval/report.md
```

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── core/          # Config, database
│   │   ├── models/        # SQLAlchemy models
│   │   └── services/      # Ingestion, retrieval, LLM, evaluation
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   └── components/    # UI components
│   └── public/
├── data/                  # Documents, vector store
├── docs/                  # Architecture, decisions, eval report
├── eval/                  # Gold QA, red team tests
└── scripts/               # Utility scripts
```

---

## License

MIT
