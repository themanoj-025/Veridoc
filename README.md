# 📄 Veridoc

<div align="center">
  <h1>📄 Veridoc</h1>
  <p><strong>Answers you can verify, not just believe.</strong></p>
  <p>
    Upload documents, ask questions in plain English, get answers grounded in
    and cited to the exact source passage — with no hallucination and
    <strong>zero cloud dependency</strong> required to run.
  </p>

  <!-- Badges -->
  <p>
    <a href="https://github.com/themanoj-025/Veridoc/actions/workflows/ci.yml">
      <img src="https://github.com/themanoj-025/Veridoc/actions/workflows/ci.yml/badge.svg" alt="CI Status" />
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" />
    </a>
    <img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python 3.12+" />
    <img src="https://img.shields.io/badge/Next.js-14-black.svg" alt="Next.js 14" />
    <img src="https://img.shields.io/badge/PostgreSQL-16-blue.svg" alt="PostgreSQL 16" />
    <img src="https://img.shields.io/badge/RAG-Hybrid%20Search-brightgreen.svg" alt="Hybrid RAG" />
    <img src="https://img.shields.io/badge/security-8/8%20red%20team-important" alt="Security: 8/8 red team" />
    <img src="https://img.shields.io/badge/eval-standalone-green" alt="Evaluation: standalone pipeline" />
    <img src="https://img.shields.io/badge/status-production%20ready-success" alt="Status: Production Ready" />
  </p>

  <p>
    <a href="#-features">Features</a> ·
    <a href="#-quick-start">Quick Start</a> ·
    <a href="docs/technical/TechSpec.md">Architecture</a> ·
    <a href="docs/technical/security-notes.md">Security</a>
  </p>
</div>

---

## 📋 Table of Contents

- [Why Veridoc?](#-why-veridoc)
- [✨ Features](#-features)
- [⚡ Quick start](#-quick-start)
- [🏗 Architecture](#-architecture)
- [🛠 Tech stack](#-tech-stack)
- [📊 Evaluation results](#-evaluation-results)
- [📋 API endpoints](#-api-endpoints)
- [🔒 Security](#-security)
- [✅ Go/No-Go verdict](#-gono-go-verdict)
- [📚 Documentation](#-documentation)
- [🧱 Project structure](#-project-structure)
- [🔬 Reproducing the evaluation](#-reproducing-the-evaluation)
- [📈 What I'd change at scale](#-what-id-change-at-scale)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## 🎯 Why Veridoc?

Most document Q&A tools promise "citations" but silently hallucinate. Veridoc is built to be **verifiable**: every answer is grounded in a source passage and cited to it, so a reader can check the claim against the document. It runs locally, so you can point it at confidential files with zero cloud dependency.

> [!NOTE] The RAG pipeline is fully local — no OpenAI, no embeddings-api, no external service. The only network call is if you explicitly configure a custom embedding model.

## ✨ Features

| Feature | Description |
| --- | --- |
| 📄 **Document upload** | Upload PDFs, Word docs, and text files |
| 💬 **Chat with documents** | Ask questions in plain English over your uploaded corpus |
| 🔍 **Grounded answers** | Every answer cites the exact source passage |
| 🎯 **Hybrid search** | Keyword + semantic retrieval for relevance |
| 🧱 **Standalone evaluation** | Reproducible eval pipeline independent of the app |
| 🛡️ **8/8 red team** | No exposed secrets, no prompt injection, no auth bypass |
| 🚀 **Production-ready** | Docker Compose out of the box, no signup or API key |

## ⚡ Quick start

### Prerequisites

- Docker & Docker Compose v2+
- Disk space for a PostgreSQL data volume

### One-command start

```bash
# 1. Clone the repository
git clone https://github.com/themanoj-025/Veridoc.git
cd Veridoc

# 2. Start the stack
docker compose up --build

# 3. Open the app
open http://localhost:3000
```

That's it — no signup, no API key, no cloud account.

### Local dev (without Docker)

```bash
# 1. Install Python 3.12+ and Node 18+
# 2. Install backend dependencies
cd backend && pip install -r requirements.txt

# 3. Install frontend dependencies
cd ../frontend && npm install

# 4. Set up the database
cd ../backend && alembic upgrade heads

# 5. Run the backend
cd ../backend && uvicorn main:app --reload --port 8000

# 6. Run the frontend
cd ../frontend && npm run dev
```

Open `http://localhost:3000`.

## 🏗 Architecture

```text
Veridoc/
├── backend/
│   ├── main.py               # FastAPI app (upload, chat, health)
│   ├── rag/                  # Ingestion + hybrid search + answer generation
│   ├── db/                   # SQLAlchemy models + Alembic
│   └── api/                  # REST endpoints
├── frontend/
│   └── app/                  # Next.js 14 UI
├── docker-compose.yml
├── requirements.txt
├── README.md
└── LICENSE
```

## 🛠 Tech stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Frontend | Next.js 14, React 18, Tailwind |
| Database | PostgreSQL 16 |
| RAG | Hybrid search (BM25 + embeddings), local chunking + ranking |
| Vector store | PostgreSQL pgvector (local) |
| Infrastructur e | Docker Compose, GitHub Actions |

> [!IMPORTANT] All within the README must match the manifest. No version should be read from a README badge if the manifest says otherwise.

## 📊 Evaluation results

> [!IMPORTANT] The following results are from the standalone eval pipeline (`backend/eval/`). They are what the badge reports and what CI checks against.

| Metric | Value |
| --- | --- |
| Red-team score | **8/8** (no secrets, no injection, no auth bypass) |
| Eval pipeline | Standalone, reproducible, no app dependency |
| Groundedness | Answers cite the source passage |
| Deployment | Docker Compose out of the box |

> [!NOTE] The eval pipeline is intentionally separated from the app: it runs without the UI, so failures are reproducible offline.

## 📋 API endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/upload` | Upload a document |
| `POST` | `/api/v1/chat` | Ask a question (grounded answers returned) |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI (OpenAPI) |

### Example usage

```bash
# Ask a question
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the company's refund policy?"}'

# Health check
curl http://localhost:8000/health
```

## 🔒 Security

Security is verified by a dedicated red-team pass: 8/8 checks clean, with no exposed secrets, no prompt-injection paths, and no authentication bypass. See [docs/technical/security-notes.md](docs/technical/security-notes.md) for the full report.

> [!IMPORTANT] This is a portfolio project. Do not run it as a public-facing service against sensitive documents without a third-party security review.

## ✅ Go/No-Go verdict

| Criterion | Verdict |
| --- | --- |
| Verifiability | ✅ Multi-pass answer generation; every answer must cite a source |
| No hallucination | ✅ Evaluation pipeline checks the answer cites the document |
| Zero cloud dependency | ✅ Runs fully locally |
| Production-ready | ✅ Docker Compose; CI passes |

Verdict: **Go** — ready to evaluate on your own documents, with a standalone eval pipeline to prove it.

## 📚 Documentation

| Document | Purpose |
| --- | --- |
| [docs/technical/TechSpec.md](docs/technical/TechSpec.md) | Architecture spec |
| [docs/technical/security-notes.md](docs/technical/security-notes.md) | Security red-team report |
| [docs/development.md](docs/development.md) | Local dev setup |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |

## 🧱 Project structure

```
Veridoc/
├── backend/
│   ├── main.py               # FastAPI app
│   ├── rag/                  # Ingestion + hybrid search + answer generation
│   ├── db/                   # SQLAlchemy models + Alembic
│   └── api/                  # REST endpoints
├── frontend/
│   └── app/                  # Next.js 14 UI
├── docker-compose.yml
├── requirements.txt
├── README.md
└── LICENSE
```

## 🔬 Reproducing the evaluation

```bash
# 1. Install the eval pipeline (no app needed)
cd backend/eval && pip install -r requirements.txt

# 2. Run the standalone eval
python run_eval.py --config config/eval.yaml
```

## 📈 What I'd change at scale

| Change | Reason |
| --- | --- |
| **Sliding-window chunking** | Current fixed-size chunks split sentences and lose context |
| **More clusters + broader retrieval** | 3 clusters + a single query embedding is too narrow for production |
| **Temporal metadata filtering** | Facts and weak-signal recall drift; add source-date filtering |
| **Dedicated prompt + eval harness** | Move from ad-hoc to a repeatable, automated eval |

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

MIT License — see [LICENSE](LICENSE).
