# Contributing to Veridoc

Thank you for considering contributing to Veridoc! This document outlines the process for contributing code, documentation, or bug reports.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone. Harassment, discriminatory language, and personal attacks are not tolerated.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/veridoc.git`
3. **Create a branch**: `git checkout -b feature/my-feature`
4. **Make your changes**
5. **Run tests**: ensure all existing tests pass
6. **Submit a PR** against the `main` branch

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker Desktop (for full stack testing)
- Git

### One-Command Setup

```bash
cp .env.example .env
# Edit .env — generate secrets as instructed in the file
docker compose up --build -d
```

### Manual Setup (without Docker)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev

# Required services: PostgreSQL 16, Redis, ChromaDB, MinIO
# These can run via Docker: docker compose up postgres redis chroma minio -d
```

## Code Style

### Python

- **PEP 8** with a 100-character line limit
- **Type hints** required for all function signatures and public methods
- **Docstrings** (Google-style) for all public modules, classes, and functions
- **Imports** organized: standard library → third-party → local (alphabetical within groups)

### TypeScript / React

- **Strict TypeScript** mode — no `any` types unless absolutely necessary
- **Function components** with hooks — no class components
- **Props interfaces** defined alongside the component, exported if reused
- **Tailwind CSS** for styling — no CSS modules
- **Prettier** formatting (default config)

### Commit Messages

Use conventional commits:

```
feat: add hybrid search with cross-encoder reranking
fix: resolve SSE streaming session lifecycle bug
docs: add evaluation report with accuracy metrics
test: add negative security tests for JWT tampering
refactor: extract ChatService from stream_chat route
```

## Testing

### Backend Tests

```bash
cd backend
python -m pytest tests/ -v --timeout=30
```

- **Unit tests** run without external services (mocked PostgreSQL/ChromaDB)
- **Integration tests** require Docker services:
  ```bash
  docker compose up postgres chroma -d
  python -m pytest tests/ -k "integration" -v --timeout=120
  ```
- **Security tests** verify JWT validation, rate limiting, and prompt injection defense
- **Regression tests** ensure fixed bugs stay fixed

### Frontend Tests

```bash
cd frontend
npm run lint  # TypeScript type checking + ESLint
npm run build # Full build verification
```

### Running the Evaluation Harness

```bash
# Requires full Docker stack
docker compose up -d
python scripts/run_eval.py --compare
```

## Pull Request Process

1. **Ensure all tests pass** before submitting
2. **Update documentation** if adding or changing features
   - API changes → update `README.md` API table
   - Architecture changes → update `docs/architecture.md`
   - New features → add to `README.md` Features table
3. **Add evaluation data** if modifying the retrieval pipeline
   - Add questions to `eval/gold_qa.json`
   - Run evaluation and update `docs/evaluation-report.md`
4. **Write a clear PR description** explaining:
   - What the change does
   - Why it's needed
   - How it was tested
   - Any breaking changes
5. **Link related issues** if the PR addresses an existing issue
6. **Await review** — maintainers will review within 3-5 business days

### PR Checklist

- [ ] All backend tests pass (unit + integration)
- [ ] Frontend builds without errors
- [ ] Documentation updated (if applicable)
- [ ] Evaluation data updated (if retrieval pipeline changed)
- [ ] No new lint warnings or errors
- [ ] Commit messages follow conventional commits

## Reporting Bugs

When reporting a bug, please include:

1. **Description**: What happened vs. what was expected
2. **Steps to reproduce**: Exact steps, including any input data
3. **Environment**:
   - OS and version
   - Docker version (`docker --version`)
   - Python version (if running outside Docker)
   - Browser (if frontend issue)
4. **Logs**: Relevant backend logs (use `docker logs veridoc-backend`)
5. **Screenshots**: If applicable

## Feature Requests

Feature requests are welcome! Please:

1. **Check existing issues** to avoid duplicates
2. **Describe the problem** the feature would solve, not just the feature itself
3. **Explain why** it fits Veridoc's architecture (local-first, zero cloud accounts)
4. **Tag** the issue with `enhancement`

---

*Thank you for contributing to Veridoc — answers you can verify, not just believe.*
