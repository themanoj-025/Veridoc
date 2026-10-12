<p align="center">
  <img src="https://img.shields.io/badge/Veridoc-Verifiable%20Document%20RAG-blue?style=for-the-badge" alt="Veridoc Logo" />
</p>

<h1 align="center">Veridoc</h1>

<p align="center">
  <strong>Grounded document intelligence and hybrid RAG search with passage-level attribution and zero cloud dependencies.</strong>
</p>

<p align="center">
  <a href="https://github.com/themanoj-025/Veridoc/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/Veridoc/ci.yml?style=flat-square&label=CI" alt="CI Status" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License MIT" /></a>
  <a href="https://github.com/themanoj-025/Veridoc/stargazers"><img src="https://img.shields.io/github/stars/themanoj-025/Veridoc?style=social" alt="GitHub Stars" /></a>
  <a href="https://github.com/themanoj-025/Veridoc/issues"><img src="https://img.shields.io/github/issues/themanoj-025/Veridoc?style=flat-square" alt="GitHub Issues" /></a>
  <a href="https://github.com/themanoj-025/Veridoc/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs Welcome" /></a>
</p>

---

## Overview

Most document question-answering systems promise citations but silently hallucinate answers when retrieval context is weak. Veridoc is engineered for strict verifiability: every response is grounded in retrieved chunks, and claims are accompanied by traceable source passage citations.

The hybrid RAG architecture combines BM25 keyword matching with dense vector retrieval using PostgreSQL `pgvector`, operating completely on-premises with zero mandatory third-party cloud API dependencies.

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Quick Start](#installation--quick-start)
- [REST API Reference](#rest-api-reference)
- [Evaluation & Red-Team Audit](#evaluation--red-team-audit)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Support](#support)

---

## Key Features

- **Grounded Source Citations**: Strictly bounds generated responses to retrieved context; outputs highlight exact source passages to enable reader verification.
- **Hybrid RAG Pipeline**: Merges sparse BM25 keyword search with dense embedding vector similarity in `pgvector` to maximize retrieval recall.
- **Zero Cloud Requirement**: Runs completely locally using local embedding models or self-hosted LLM endpoints.
- **Multi-Format Ingestion**: Ingests, parses, chunks, and indexes PDFs, DOCX documents, Markdown, and plain text files.
- **Dual Surface Deployment**: Ships with an intuitive Next.js 14 web chat interface and a high-performance FastAPI backend.

---

## Architecture

```text
               User Document Upload / Question
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
    Next.js 14 Frontend             FastAPI Ingestion / Chat
      (frontend/, Port 3000)         (backend/main.py, Port 8000)
               │                             │
               └──────────────┬──────────────┘
                              │
                              ▼
                   Document Ingestion Engine
            (Chunking, Tokenization, Text Normalization)
                              │
                              ▼
                     Hybrid Retrieval
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
     Sparse BM25 Search                      Dense Vector Search
     (Keyword Precision)                     (PostgreSQL pgvector)
          │                                       │
          └───────────────────┬───────────────────┘
                              │
                              ▼
                     Reciprocal Rank Fusion
                              │
                              ▼
                   Verifiable Generation
            (Passage Grounding & Citation Synthesis)
```

---

## Tech Stack

| Domain | Technologies |
| :--- | :--- |
| **Backend & API** | FastAPI, SQLAlchemy 2.x, Alembic, Uvicorn |
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS |
| **Database & Vector Store** | PostgreSQL 16 with `pgvector` extension |
| **Retrieval Engine** | Hybrid BM25 + dense vector embeddings |
| **Evaluation Suite** | Standalone benchmark harness (`eval/`) |
| **Infrastructure** | Docker Compose, GitHub Actions CI |

---

## Project Structure

```text
Veridoc/
├── backend/                # FastAPI application, database, and RAG logic
│   ├── api/                # API routers and endpoints
│   ├── db/                 # SQLAlchemy ORM models and database session
│   ├── rag/                # Ingestion, chunking, embeddings, and search
│   └── main.py             # Backend application entry point
├── frontend/               # Next.js 14 web chat application
├── eval/                   # Standalone RAG evaluation harness
├── tests/                  # Pytest automated test suites
├── Dockerfile              # Multi-stage container build
├── docker-compose.yml      # Local development container orchestration
├── docker-compose.prod.yml # Production multi-service orchestration
├── pyproject.toml          # Build backend and quality configuration
├── requirements.txt        # Backend dependencies
└── README.md               # Project documentation
```

---

## Prerequisites

- **Python**: `>= 3.12`
- **Node.js**: `>= 18.0` (for frontend development)
- **Docker & Docker Compose**: Recommended for local orchestration with `pgvector`

---

## Installation & Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/themanoj-025/Veridoc.git
cd Veridoc

# Start all services (PostgreSQL + pgvector, Backend, Frontend)
docker compose up --build -d
```

*Frontend: http://localhost:3000*  
*Backend API docs: http://localhost:8000/docs*

### Option 2: Local Development Setup

```bash
# 1. Backend Setup
cd backend
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp ../.env.example .env

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend Setup (in separate terminal)
cd ../frontend
npm install
npm run dev
```

---

## REST API Reference

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service liveness probe |
| `POST` | `/api/v1/upload` | Upload and index document files |
| `POST` | `/api/v1/chat` | Submit question and receive grounded answer with citations |

### Example Request (`POST /api/v1/chat`)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the specific termination notice periods outlined in the agreement?"
  }'
```

---

## Evaluation & Red-Team Audit

- **Red-Team Security**: Passed 8/8 automated adversarial tests evaluating prompt injection resilience, authentication boundaries, and secret isolation.
- **Standalone Evaluation Suite**: The `eval/` pipeline evaluates answer groundedness independently of the user interface:
```bash
cd eval
python run_eval.py --config config/eval.yaml
```

---

## Testing

```bash
# Execute backend test suite
pytest tests/ -v
```

---

## Roadmap

- [x] Grounded hybrid search with citation extraction
- [x] Local `pgvector` integration
- [x] Next.js 14 interactive chat dashboard
- [x] Standalone offline evaluation suite
- [ ] Adaptive sliding-window chunking <!-- TODO: Track via GitHub issue -->
- [ ] Temporal metadata filtering for historical documents <!-- TODO: Track via GitHub issue -->

---

## Contributing

Contributions are welcomed! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for pull request guidelines.

---

## Security

Please report vulnerabilities following the instructions in [SECURITY.md](SECURITY.md).

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Support

- 🐛 **Issue Tracker**: [GitHub Issues](https://github.com/themanoj-025/Veridoc/issues)
- 💡 **Discussions & Feedback**: [GitHub Pull Requests](https://github.com/themanoj-025/Veridoc/pulls)
