# AGENTS.md — Veridoc

> Canonical project instructions. Pointers like `CLAUDE.md` or
> `.github/copilot-instructions.md` should say "See AGENTS.md".

---

## Project overview

**Veridoc** — a document verification and integrity platform. Core
components:

- **API** — FastAPI service for document verification checks.
- **Doc** — document processing + attestation logic.
- **Pipeline** — batch verification and audit jobs.
- **Web / App** — frontend for submitting and reviewing docs.

Stack: Python 3.11+ · FastAPI · Celery · Streamlit.

---

## Exact commands

```bash
# Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Lint / typecheck / test
make lint
pre-commit run --all-files
python -m mypy . --ignore-missing-imports
python -m pytest tests/ -v --cov=. --cov-fail-under=70

# Run
uvicorn api.main:app --reload
```

---

## Folder map

| Path | Purpose |
|------|---------|
| `api/` | FastAPI application (routes, services) |
| `doc/` | Document processing + attestation |
| `pipeline/` | Batch verification jobs |
| `dashboard/` | Streamlit app |
| `tests/` | pytest suite |
| `.github/workflows/` | CI (ruff, mypy, pytest, gitleaks, trivy) |

## Do / don't

- **Do** keep the verification interface stable so the attestation logic
  can be extended without breaking the API.
- **Do not** commit `.env` files.
- **Do not** commit original source documents that may contain sensitive
  or copyrighted content.

## Security rules

- No secrets in the repository; `gitleaks` CI gate gates on hits.
- Document content containing PII or copyright material must be
  anonymized before any file leaves the sandbox.

## AI-assistance convention

Commits authored by AI must carry the trailer:

```text
AI-Assisted: yes | no | partial
```

See `.gitmessage` for the template. Do not rewrite historic commits
retroactively.
