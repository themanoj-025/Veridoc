# Veridoc — File Move Ledger

## This pass (2026-08-11)

| Old path | New path | Category | Reason | Risk | Verified |
|---|---|---|---|---|---|
| `docs/migration_summary.md` | `docs/migration/migration_summary.md` | Meta/docs | Consolidate migration records under `docs/migration/` per enterprise standard | Low (docs only) | ✅ `git mv` preserved history; no inbound refs found |
| `docs/architecture.md` (3-line stub) | `docs/architecture.md` (rewritten) | Meta/docs | Stub replaced with real architecture doc | Low | ✅ |
| `docs/folder_structure.md` (stub) | `docs/folder_structure.md` (rewritten) | Meta/docs | Stub replaced with real annotated tree | Low | ✅ |
| `.mypy_cache/3.14/*` (48 files) | removed from index | Hygiene | mypy cache committed by accident; regenerable; violates root-declutter rule; `.mypy_cache/` added to `.gitignore` | Low (cache only — no source) | ✅ `git rm -r --cached` kept local files; gitignore rule verified |

## Prior pass (v5.0 modernization, commit `9a691e8`)

The v5.0 pass moved application code into the current layout
(`backend/app` layers, `frontend/`, `scripts/`, `eval/`, `prompts/`, `docs/`).
Its detailed record was a stub template (replaced by this pass).

## Non-moves (documented decisions)

| Path | Decision | Reason |
|---|---|---|
| `backend/**` | keep | Launch contract: `uvicorn app.main:app`, `cd backend && …` in Makefile/CI/compose |
| `frontend/**` | keep | Next.js build contract (package.json, playwright, vitest) |
| `scripts/`, `eval/`, `prompts/`, `data/`, `docs/` | keep | Canonical locations |
| `frontend/.next/`, `frontend/node_modules/`, `backend/.mypy_cache/`, `.pytest_cache/`, `*.egg-info/` | leave (untracked) | Build/cache artifacts, correctly gitignored |
| `.env`, `data/*` volumes | leave (untracked) | Secrets + runtime volumes |
