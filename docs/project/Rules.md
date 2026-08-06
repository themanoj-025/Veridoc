# Rules — Veridoc: Coding Standards & AI-Agent Operating Rules

|Field|Value|
|---|---|
|Version|v0.1|
|Last Updated|2026-08-06|
|Owner|Staff Engineer|
|Status|Approved|

---

## 1. Guiding Principles

1. **Grounded over fluent** — never display an answer that failed the faithfulness gate.
2. **Local-first** — default path requires zero cloud accounts; provider swaps via env only.
3. **No silent failures** — every error logged with correlation IDs; no bare excepts.
4. **Defense in depth** — isolation, encryption, rate limits, injection defense each independent.
5. **Prove with numbers** — claims require measured results (eval, benchmarks).
6. **DI over singletons** — services constructed via container; testable by design.
7. **Small PRs** ≤ 400 lines; CI must pass.

## 2. Code Style

- **Languages:** Python 3.12 (backend), TypeScript/Next.js 14 (frontend).
- **Lint/format:** ruff + black-compatible; ESLint/Prettier + Tailwind.
- **Naming:** snake_case (py), camelCase (TS), descriptive.
- **Structure:**

```
Veridoc/
├── backend/
│   ├── app/
│   │   ├── api/          # 4 route modules (auth, documents, chat, health)
│   │   ├── core/         # config, DI, database, auth, logging, rate limiting
│   │   ├── models/       # 7 SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic v2
│   │   └── services/     # ingestion, retrieval(5), LLM, evaluation
│   └── tests/            # 77 tests / 8 files
├── frontend/src/         # app pages + 5 components
├── docs/                 # architecture, security-notes, runbooks
├── eval/                 # gold QA (23), red-team (8)
├── scripts/              # 7 automation scripts
└── data/                 # uploads, vector store, eval docs
```

## 3. Git Workflow

- Branches: `feat/<slug>`, `fix/<slug>`, `security/<slug>`, `docs/<slug>`.
- Commits: Conventional Commits.
- PRs: ≥ 1 reviewer, CI green (Postgres + Chroma services), squash merge.
- Never commit secrets; `.env` gitignored (startup fail-fast validates placeholders).

## 4. Testing Requirements

- Coverage gate on backend core paths (auth, ingestion, retrieval, chat).
- MUST have: security suite (8/8), faithfulness-gate tests, row-isolation tests, ingestion lifecycle tests, migration round-trips.
- Frontend: component tests for 5 components (AuthProvider, ChatPanel, DocumentList, DocumentViewer, ErrorBoundary).

## 5. AI Agent Operating Rules

- Read Tracker.md and ImplementationPlan.md before starting a task.
- Never mark a task 🟢 Done without tests passing.
- Never invent requirements not in ../product/PRD.md/../technical/TechSpec.md — flag ambiguity instead.
- Any schema change → same-PR update to ../technical/Schema.md + Alembic migration.
- Any API change → same-PR update to ../technical/API.md.
- Never commit secrets; env vars per ../technical/SecurityAndCompliance.md.
- Never weaken security tests; fix the code instead.
- Keep retrieval prompt-boundaries intact (`<retrieved_context>` markers).
- When a rule conflicts with a request, state the conflict rather than silently picking one.

## 6. Security Baseline Rules

- Row-level isolation: verify `user_id` from JWT on every document/conversation endpoint.
- Files encrypted at rest (Fernet); keys from env; fail-fast on missing/placeholder secrets.
- Rate limits: 5/min auth, 30/min general (slowapi).
- LLM output sanitized (rehype-sanitize) + CSP headers.
- Prompt-injection: retrieved content wrapped in boundary markers; red-team suite in CI.
- Parameterized queries only; Pydantic v2 validation everywhere.

## 7. Documentation Rules

- Migration → ../technical/Schema.md same PR.
- API contract change → ../technical/API.md same PR.
- New security control → ../technical/SecurityAndCompliance.md + docs/../technical/security-notes.md.
- Eval numbers → update ../product/PRD.md metrics + docs (never let stale numbers linger).

## 8. Prohibited Patterns

|Pattern|Why|
|---|---|
|Displaying unfaithful answers|Trust violation|
|Global mutable singletons|Untestable|
|Raw string-concat query rewriting|Weakness (fixed in audit)|
|Committing .env / secrets|Leak — startup fail-fast guards|
|Unbound LLM output in HTML|XSS — must sanitize|
|Bare except / swallowed errors|Silent failures|

## 9. Escalation Rules

**Ask a human:**
- Changing the faithfulness-gate policy.
- Weakening security controls.
- Deleting migrations or user data.
- Adding new LLM providers beyond the env-switch contract.

**Decide autonomously:**
- Refactors with tests green.
- Adding metrics/logging.
- Bug fixes within defined contracts.

## 10. Related Documents

|Document|Relationship|
|---|---|
|[Testing.md](../technical/Testing.md)|Enforcement|
|[SecurityAndCompliance.md](../technical/SecurityAndCompliance.md)|Full baseline|
|[API.md](../technical/API.md)|Contract triggers|
|[Schema.md](../technical/Schema.md)|Migration triggers|
