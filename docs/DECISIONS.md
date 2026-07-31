# Veridoc — Architectural Decision Records

> **Last updated:** 2026-07-31
> This file documents significant architectural decisions and the rationale behind them.

---

## F5: OAuth Dead Schema Resolution

**Decision:** Remove unused `google_id`/`github_id` columns via migration.

**Rationale:**
- The columns were added as a placeholder but never wired to real OAuth routes.
- No OAuth client IDs, secrets, or callback handlers existed in the codebase.
- Keeping dead schema creates confusion and adds maintenance cost.
- If OAuth is needed in the future, it should be implemented as a proper authorization-code flow with scoped permissions, not just two nullable columns.
- The config values (`google_client_id`, `google_client_secret`, `github_client_id`, `github_client_secret`) remain in `Settings` for future use but are not wired to any endpoint.

**Implementation:** Migration 004 removes the columns. The `User` model no longer references them.

---

## F4: Email Sender Abstraction

**Decision:** Use a log-to-console sender in dev mode, with config-driven swap to real SMTP.

**Rationale:**
- No SMTP credentials should be required for local development.
- The log-to-console sender outputs the verification/reset token as a structured log line, which is sufficient for testing.
- The interface (`send_verification_email`, `send_password_reset_email`) is async and accepts the same parameters a real sender would.
- In production, replace the implementation at the import level or inject via config.

**Implementation:** `app/services/email_sender.py` — two async functions that log via structlog. The token prefix is logged for easy verification in dev.

---

## F3: RBAC — Explicit Role Column vs First-User Heuristic

**Decision:** Use an explicit `role` column (`user`/`admin`) set at registration time, not inferred from registration order.

**Rationale:**
- The original heuristic ("the first registered user is admin") was fragile and broke in test environments, concurrent registrations, and password-reset flows.
- An explicit column makes the access policy visible in the database and auditable.
- Registration does NOT automatically grant admin — admin role must be set explicitly (e.g., via a management command, DB migration, or config).
- The backfill in Migration 004 sets the first registered user as admin for backward compatibility.

**Implementation:** `User.role` column, checked in `admin.py` endpoints. `UserRepository.find_by_role()` for admin discovery.

---

## F6: Rate Limiting Strategy

**Decision:** Per-endpoint rate limits using slowapi, with per-user granularity.

**Rationale:**
- Auth endpoints: 5/min (prevent brute force)
- Document upload: 10/min (prevent storage abuse)
- Chat create: 30/min (conversation creation)
- Chat stream: 20/min (prevent API cost flooding)
- Rate limits are bypassed in test mode (`app_env == "test"`) via the `_should_rate_limit()` check.
- slowapi automatically adds `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` response headers (G6).

**Implementation:** `@limiter.limit()` decorators on individual route handlers. No global rate limit middleware.

---

## F10: Async/Batched UsageLog Writes

**Decision:** Fire-and-forget via `asyncio.ensure_future` with a separate database session.

**Rationale:**
- Synchronous usage-log writes on every query would add ~10-50ms to the critical path.
- Accuracy of the log is not critical (best-effort) — losing a few entries on a crash is acceptable.
- Fire-and-forget with a fresh session avoids coupling the usage log to the request's transaction.
- A batched buffer (periodic flush) was considered but adds complexity; fire-and-forget is simpler and removes the same latency.

**Implementation:** `chat_service.py` creates a new session and writes the log entry in a separate asyncio task.

---

## F11: SSE Reconnect Strategy

**Decision:** Client-side exponential backoff with configurable max retries (default 3).

**Rationale:**
- Backoff: 1s → 2s → 4s → 8s (capped at 16s)
- The reconnection is invisible to the user (same conversation_id and message are retried).
- Server-side SSE state is idempotent per message, so retransmission is safe.
- A "reconnecting..." UI state is shown during retries.

**Implementation:** `streamChat()` in `frontend/src/lib/api.ts` with `maxRetries` parameter.

---

## G2: Prompt Version Registry

**Decision:** Version all system/RAG prompt templates in a JSON registry, store the version on each generated message.

**Rationale:**
- Prompt changes are the most common source of regressions in LLM applications.
- Storing the prompt version on each message makes every answer traceable to the exact prompt template that produced it.
- The registry file is human-readable and lives in `prompts/registry.json`.

**Implementation:** Versioned prompt templates in `prompts/registry.json`. `prompt_version` column on `Message` model.

---

## F18: Model Name Semantics

**Decision:** Store the actual model name (e.g., `ollama/llama3.1:8b`, `claude-sonnet-4-20250514`) not just the provider name.

**Rationale:**
- Provider-only names (e.g., "ollama", "claude") lose information about which specific model was used.
- Model-specific logging is essential for cost tracking, latency analysis, and regression detection.
- The format `{provider}/{model_name}` allows easy filtering by provider or model.

**Backfill Note:** Existing rows with provider-only names should be updated when the model is identifiable from the original request. No automated migration — the model_used field was already storing full names.

---

## F7: Virus Scanning Strategy

**Decision:** Interface-first approach — `VirusScanner` protocol with no-op default.

**Rationale:**
- ClamAV is not universally available (requires installation, not Docker-friendly on Windows).
- The protocol allows swapping in a real scanner without changing any route handler code.
- The no-op default reports everything as clean, which is safe for development but obviously not for production.

**Implementation:** `VirusScanner` protocol + `NoopVirusScanner` in `app/services/ssrf_protection.py`.

---

## G9: i18n Strategy

**Decision:** Extract all user-facing strings into a translation-key structure, ship only English.

**Rationale:**
- String extraction is a prerequisite for internationalization.
- Using a key-based approach (`t("dashboard.title")`) makes future locale additions a config change, not a code rewrite.
- No runtime i18n library dependency is introduced — the `t()` function is a simple key lookup.
- When a real i18n library is needed (e.g., `next-intl`), the function signature is compatible with a drop-in replacement.

**Implementation:** `frontend/src/lib/i18n.ts` with all keys in a `Record<string, string>` map.

---

## G8: Visual Regression Testing Strategy

**Decision:** Playwright screenshot comparison with 2-3% pixel diff tolerance.

**Rationale:**
- Visual regression tests catch layout bugs that unit tests miss (e.g., the P0-2 duplicate declaration would have been caught).
- Baselines are stored in version control for CI comparison.
- Tolerance allows for OS-level font rendering differences across platforms.

**Implementation:** `frontend/e2e/visual.spec.ts` with `@visual` test tag. Baselines in `frontend/e2e/snapshots/`.
