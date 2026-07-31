# Veridoc — Perpetual Loop Log

Every item below is closed with **cited evidence**: a test name + pass/fail, a
real log excerpt, a measured number, or a linked artifact. Statuses: ✅ DONE /
⚠️ PARTIAL / 🔧 PREPARED / ⛔ BLOCKED-HUMAN.

---

## 2026-07-31 — Closeout pass (37-item master completion)

### Tier 1 — Code/CI-only

**F2 — DI container typed interfaces — ✅ DONE**
- `backend/app/core/di.py` defines `EmbeddingModel` and `Reranker` structural
  Protocols; `DIContainer` fields are fully typed (`VectorStore | None`,
  `LLMProvider | None`, `JobQueue | None`, `EmbeddingModel | None`,
  `Reranker | None`) — zero `Any` in the container.
- Type-check evidence: `python -m mypy app/core/di.py app/core/rate_limit.py
  app/services/prompt_registry.py app/services/chat_service.py app/api/documents.py
  app/api/chat.py app/services/ssrf_protection.py app/main.py
  --ignore-missing-imports --follow-imports=skip` → `Success: no issues found
  in 8 source files`.
- Pre-existing latent bug fixed while type-checking consumers: chat streaming
  used `asyncio.wait_for(async_generator)` (raises TypeError at runtime);
  replaced with the `asyncio.timeout` context manager in `chat_service.py`.

**F3 — Real RBAC — ✅ DONE**
- `User.role` column (`user`/`admin`), set explicitly at creation; migration
  004 backfills the first user for backward compatibility; `admin.py` checks
  `user.role != "admin"` on every admin endpoint.
- Tests: `test_rbac_auth_rate.py::TestF3_RBAC` — `test_admin_role_required`
  (403 for role=user), `test_admin_role_granted` (200 for role=admin),
  `test_non_first_user_admin_access` (non-first-registered admin works).
- **All backend tests pass: 158 passed, 8 skipped.**

**F4 (build) — Email verification + password reset — ✅ DONE**
- `POST /auth/verify-email`, `POST /auth/request-password-reset`,
  `POST /auth/reset-password` (+ `request-verification-email`) in `auth.py`;
  config-driven dev-mode sender in `email_sender.py` (logs token).
- **Token expiry completed this pass:** `verification_token_expiry` column
  added via migration `005_add_verification_token_expiry.py`; model field +
  expiry checks in `verify_email` (24h) and `reset_password` (1h); tokens are
  cleared after use — old verification links can no longer be replayed.
- Tests: `test_rbac_auth_rate.py::TestF4_EmailVerification` plus
  `test_auth.py` F4 expiry block — `test_verify_email_success`,
  `test_verify_email_expired_token_rejected` (400, user stays unverified),
  `test_verify_email_unknown_token_rejected`, `test_reset_password_success`,
  `test_reset_password_expired_token_rejected`, and
  `test_request_password_reset_always_ok` (anti-enumeration).
- Live SMTP verification is Tier 2 item 26 (🔧 PREPARED in `NEXT_STEPS.md`).

**F5 — OAuth dead schema — ✅ DONE**
- Decision documented in `DECISIONS.md` (F5): remove unused
  `google_id`/`github_id` via migration 004 (no half-state). OAuth client
  config values remain in `Settings` but are unwired by design.

**F6 — Rate limiting on upload & chat (per-user) — ✅ DONE**
- Per-user key func `get_user_identifier()` in `rate_limit.py` (parses Bearer
  JWT → `user:<id>`; falls back to IP). Applied via `key_func=` on
  `POST /documents/upload` (10/min), `POST /chat/stream` (20/min),
  `POST /chat/conversations` (30/min).
- Tests: `test_rate_limit_headers.py` — key-function unit tests
  (user/fallback/refresh-token rejection) plus end-to-end per-user bucket
  independence (`test_per_user_rate_limits_are_independent`,
  `test_per_user_same_user_shares_bucket`) and 429 + Retry-After
  (`test_429_returned_with_retry_after`).

**F7 (build) — SSRF & virus-scan hooks — ✅ DONE**
- `ssrf_protection.py`: `validate_upload_url()` blocks private/link-local
  ranges; `VirusScanner` Protocol + `NoopVirusScanner` default;
  `get_virus_scanner()` factory. Upload endpoint now invokes the hook and
  rejects (400) infected files.
- Tests: `test_virus_scan.py` — `test_upload_rejects_infected_file` (400,
  file deleted, no doc row), `test_upload_accepts_clean_file_through_noop`
  (201), no-op default accepts.
- Live EICAR verification is Tier 2 item 27 (🔧 PREPARED).

**F8 — Admin action audit log — ✅ DONE**
- `admin_audit_log` table (append-only) + `_log_admin_action()` in every
  admin endpoint (analytics, cache-stats, feedback-queue).
- Tests: `test_rbac_auth_rate.py::TestF8_AdminAuditLog` — creation,
  append-only persistence (real SQLite), multiple entries.

**F9 (build) — Composite indexes — ✅ DONE**
- Migration 004: `idx_documents_user_status (user_id, status)` and
  `idx_conversations_user_active (user_id, is_active)`.
- Live `EXPLAIN ANALYZE` verification is Tier 2 item 28 (🔧 PREPARED).

**F10 — Async UsageLog writes — ✅ DONE**
- `chat_service.save_assistant_message` writes usage logs via
  `asyncio.ensure_future` with a separate session — off the critical path.
- Evidence: `app/services/chat_service.py` `_log_usage()` coroutine;
  latency removed from request path (documented in `DECISIONS.md` F10).

**F17 — Font loading — ✅ DONE**
- `layout.tsx` loads `Inter`, `Source_Serif_4`, `JetBrains_Mono` via
  `next/font/google`; `globals.css` has no `@import`.
- Evidence: `npm run build` passes (✓ Compiled successfully, 8/8 pages).

**F18 — `usage_logs.model_used` semantics — ✅ DONE**
- `llm_provider.py` exposes `ollama/llama3.1:8b`, `claude/claude-sonnet-4-20250514`,
  `openai/gpt-4o-mini`; `chat_service` stores `self.llm.model_name` on every
  message and usage log row. Backfill note in `DECISIONS.md` (F18).

**F11 — SSE reconnect with backoff — ✅ DONE**
- `api.ts` `streamChat()` auto-reconnects with exponential backoff
  (1s→2s→4s→8s, max 3 retries) on network error or mid-stream drop; new
  `onReconnecting` callback; ChatPanel shows a visible "Reconnecting..." chip.
- Tests: `Regression.test.tsx` F11 block — backoff retries after repeated
  network errors, mid-flight drop recovery, no reconnect on clean completion,
  `onReconnecting` fired.

**F12 — Response compression — ✅ DONE**
- `GZipMiddleware(minimum_size=1000)` in `main.py` (F12).
- CDN-for-static-assets noted in `docs/deployment-runbook.md` (Tier 3).

**F13 — All fetches through shared API client — ✅ DONE**
- `queries.ts` admin queries now use shared `getApiBase()`/`getAuthHeaders()`
  from `api.ts` (removed duplicate `adminHeaders()`); dashboard GDPR calls
  already used `getAuthHeaders()`.
- Evidence: `frontend/src/lib/queries.ts` — no local header helper remains.

**F14 — React Query — ✅ DONE**
- `QueryProvider.tsx` + `queries.ts` hooks for documents, conversations,
  admin analytics; caching/refetch defaults (staleTime 30s, gcTime 5m).
- Evidence: `page.test.tsx` (17 tests) renders dashboard through
  QueryClientProvider and verifies data-driven UI.

**F15 — Bundle analysis — ✅ DONE**
- `@next/bundle-analyzer` wired in `next.config.js` (activates with
  `ANALYZE=true` only).
- Measured sizes recorded in `BUILD_LOG.md` (2026-07-31): dashboard
  181 kB First Load JS, shared baseline 87.4 kB, middleware 26.7 kB.
- Verdict: no oversized chunk; no action required.

**F16 — Missing tests — ✅ DONE** (verified, not re-done)
- 158 backend + 147 frontend tests green; suites: pytest (158 passed,
  8 skipped), vitest (147 passed), tsc (0 errors), mypy (0 errors).

**F19 (build) — Document preview with citation highlighting — ✅ DONE**
- `DocumentViewer.tsx` renders chunks with page info + OCR badges, listens
  for `citation-highlight` events, scrolls to and highlights the cited chunk
  (ring + tint, 3s). `dashboard/page.tsx` switches to viewer on
  `citation-navigate`.
- Real-PDF verification is Tier 2 item 29 (🔧 PREPARED).

**F20 — Document sharing + API keys — ✅ DONE**
- `document_shares` table + endpoints (list/create/update/delete, owner-only)
  in `sharing.py`; `api_keys` table + issue/revoke (`vid_`-prefixed keys,
  SHA-256 hashed at rest) in `api_keys.py`.
- Tests: `test_sharing_api_keys.py` — non-owner 404 on list/create/update
  shares, API-key 401 unauthenticated, key format/hash-once semantics,
  cross-user revoke denied.

**G1 — Per-answer confidence badge — ✅ DONE**
- `ConfidenceBadge.tsx` combines retrieval + faithfulness into
  High/Medium/Low; distinct from OCR badge.
- Tests: `ConfidenceBadge.test.tsx` (7 tests) — each tier renders correctly,
  missing scores → Low.

**G2 — Prompt-version registry — ✅ DONE**
- `prompts/registry.json` versions 3 templates with changelogs; new
  `prompt_registry.py` resolver; `chat_service` stamps `prompt_version`
  on every assistant message and loads the system prompt from the registry.
- Tests: `test_rbac_auth_rate.py::TestG2_PromptVersion` — field exists,
  persisted in real SQLite, resolver returns `1.0.0`, unknown → "unknown",
  `test_chat_service_records_prompt_version_on_message` (version recorded on
  generated message), `test_build_system_prompt_uses_registry_template`.

**G3 — Dependabot auto-merge — ✅ DONE**
- `.github/dependabot.yml` (pip/npm/github-actions/docker, weekly/monthly) +
  new `.github/workflows/dependabot-auto-merge.yml` — auto-merges
  patch/minor dependabot PRs once CI passes; policy documented in
  `docs/CONTRIBUTING.md` (major updates require manual review; torch pinned).

**G4 — Secret rotation reminder — ✅ DONE**
- `secret_rotated_at` + `secret_rotation_warning_days` config; startup check
  in `main.py` warns (never fails) on never-recorded/stale/malformed and logs
  info on fresh.
- Tests: `test_rbac_auth_rate.py::TestG4_SecretRotation` — fires on
  never-recorded, stale (>window), malformed; no warning when fresh.

**G6 — Rate-limit response headers — ✅ DONE**
- Custom header injection: middleware + 429 handler emit
  `X-RateLimit-Limit/Remaining/Reset` + `Retry-After` on every limited
  response (slowapi 0.1.9's built-in injection crashes on dict-returning
  FastAPI endpoints, so the app implements it itself via
  `request.state.view_rate_limit`).
- Tests: `test_rate_limit_headers.py` — Limit/Remaining/Reset values on
  success, headers + Retry-After on 429.

**G8 — Visual regression testing — 🔧 PREPARED**
- `playwright.config.ts` + `e2e/visual.spec.ts` (5 screenshots: login,
  register, dashboard, admin, dark-mode dashboard) with 2-3% tolerance.
- Playwright + Chromium installed; **baselines not yet generated** — requires
  the running stack (backend + frontend) which needs Docker (daemon not
  running in this environment). Exact commands in `NEXT_STEPS.md` item 25.

**G9 — i18n scaffold — ✅ DONE**
- `i18n.ts` key structure (English-only) now wired into **all** user-facing
  surfaces: login, register, dashboard, ChatPanel, DocumentList, SearchBar,
  CommandPalette, DocumentViewer, ThumbsUpDown — every visible string routes
  through `t()`/`tpl()` with identical English output (no visual regression).
- New keys added this pass: `documents.*`, `command.*`, `search.fullText`,
  `document.*`, `feedback.helpful/notHelpful` (~30 keys; 120+ total).
- Evidence: pages render same strings (vitest suite + tsc + build pass);
  `src/lib/i18n.ts` 120+ keys; no raw user-facing literals remain in the 9
  wired components.

### Tier 2 — Requires Docker stack (daemon not running → PREPARED)

All Tier 2 items are fully scripted and logged in `docs/NEXT_STEPS.md`
(items 26-32): live email via MailHog, EICAR virus scan, EXPLAIN ANALYZE
index checks, preview against real PDFs, DEMO_MODE, public status page, and
cost-budget alerting. Status: 🔧 PREPARED (BLOCKED-HUMAN until Docker runs).

### Tier 3 — Human/cloud action (⛔ BLOCKED-HUMAN)

A1 eval harness, A2 red-team, A3 load test, A4 public deploy, A5 demo video —
exact commands in `docs/NEXT_STEPS.md` (items 33-37). ⛔ BLOCKED-HUMAN.

**A1 prep bugs found & fixed (2026-07-31):**
1. `scripts/run_eval.py` passed gold-set `document_id` slugs (`gutenberg_132`,
   `arxiv_*`) verbatim to the retriever, which filters Chroma metadata by real
   DB document UUIDs — every filtered question would have silently returned
   zero chunks, corrupting the report. Added `resolve_document_ids()`
   (slug→UUID fuzzy match, wildcard + DB-error fallback to search-all) in
   `app/services/evaluation.py`.
2. `use_hybrid=False` was a no-op — the `--compare` naive run used the
   identical hybrid pipeline, making the head-to-head table meaningless.
   Wired: naive path now runs dense-only retrieval (no BM25/RRF/rerank).
3. Tests: `backend/tests/test_eval_harness.py` — 15 tests (slug matching,
   wildcards, DB resolution, fallbacks, `run_evaluation()` resolver wiring,
   naive-path wiring with HybridRetriever-instantiation guard).

---

## Summary counts (per the 37-item master list)

| Status | Count |
|--------|-------|
| ✅ DONE (with cited evidence) | 24 (Tier 1 items 1-23, 25) |
| ⚠️ PARTIAL (env-blocked remainder) | 1 (item 24 / G8 baselines) |
| ⛔ BLOCKED-HUMAN (exact steps provided) | 12 (Tier 2 items 26-32 + Tier 3 items 33-37) |
| **Total** | **37** |

**Validation snapshot (2026-07-31, final):** pytest **164 passed / 8 skipped** ·
vitest **147 passed** · `tsc --noEmit` **0 errors** · mypy **0 errors**
(9 source files) · `npm run build` ✓ Compiled successfully.

**Latent runtime bug found & fixed during closeout:** `request_password_reset`
used `datetime.now()` without importing `datetime` (NameError on the
user-exists branch; hidden by tests that mock user=None). Fixed in `auth.py`;
mypy now covers `auth.py`.
