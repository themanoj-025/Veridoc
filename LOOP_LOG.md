# Veridoc — Perpetual Loop Log

> **Loop started:** 2026-07-29
> **Initial score:** 8.3/10
> **Objective:** Execute Master Checklist items with verified evidence, re-auditing every 3-5 items, until Termination Condition is met.

---

## Iteration 1 — 2026-07-29 (Final)

### Summary
Completed first major pass through Tier 1 items. Frontend TypeScript compiles cleanly (`npx tsc --noEmit` passes). Backend Python files are syntactically valid. Still several items PARTIAL or NOT STARTED — loop needs to continue.

### Completed Items (Verified DONE)

| Item | Evidence |
|------|----------|
| **B1: Dark mode + Design tokens** | `tailwind.config.ts` with full token set, `ThemeToggle.tsx`, CSS variables in `globals.css`, `layout.tsx` with FOUC prevention script |
| **B2: Loading skeletons** | `Skeleton.tsx` with 6 composed variants, integrated into `dashboard/page.tsx` and `DocumentList.tsx` |
| **B3: Toast notifications** | `Toast.tsx` + `toast-store.ts` with success/error/info/warning, animated slide-in, component-owned lifecycle |
| **D5: Command palette** | `CommandPalette.tsx` with Cmd/Ctrl+K, keyboard navigation, 5 actions, FOUC-safe |
| **D11: CHANGELOG.md** | `CHANGELOG.md` with Keep a Changelog format, v1.0.0 + v0.1.0 entries |
| **C1: BM25 persistence** | `bm25.py` with pickle serialization to `data/bm25_cache/`, disk load on cold start, cache invalidation clears both memory + disk |
| **D2: CI evaluation gate (basic)** | `.github/workflows/ci.yml` with `eval-regression` job validating gold_qa.json ≥5 entries |

### PARTIAL Items (Require More Work)

| Item | What's Done | What's Missing |
|------|------------|----------------|
| **B4 + D1: Feedback + Eval loop** | `ThumbsUpDown.tsx`, `feedback.py` writes to `continuous_feedback.json`, `scripts/promote_feedback.py` | Eval regression gate needs actual evaluation run with baseline comparison |
| **D3: Multi-model fallback** | `llm_provider.py` `FallbackWrapper` class catches errors and falls back to Ollama | `model_name` returns primary model name even when fallback active — no `fallback_used` flag on message for UI transparency |
| **D6 + D7: Search + Full-text** | `SearchBar.tsx` wired into dashboard, `search.py` with tsvector GIN index query | Full-text search inside documents not integrated into SearchBar's "Search inside documents" action |
| **D10: GDPR data controls** | `gdpr.py` endpoints, export button in dashboard header | No "Delete account" button/confirmation dialog in UI |
| **D12: Admin analytics** | `admin.py` endpoint, `admin/page.tsx` created | No link/navigation from dashboard to admin page |
| **D13: OCR indicator** | `DocumentResponse` has `ocr_used` field (pre-existing) | No OCR badge/confidence indicator in DocumentViewer or citation chips |

### NOT STARTED Items

| Item | Reason |
|------|--------|
| **B5: Frontend component tests (Vitest)** | Deferred — requires Vitest setup |
| **B6: E2E Playwright smoke test** | Deferred — requires running stack |
| **D8: Accessibility audit** | Deferred — needs axe-core/Lighthouse |
| **D9: SBOM + vulnerability scanning** | CI template added, not verified |
| **C2: Redis query/response cache** | Enhancement #11 — requires Redis integration for cache with measured hit rate |
| **C3: Hybrid retrieval weight tuning** | Enhancement #17 — needs empirical tuning against gold set |
| **D4: Chaos/resilience tests** | Tier 2 — requires Docker stack |
| **A1-A5: Live validation** | Tier 2/3 — requires Docker stack or cloud account |
| **B7: Mobile responsive** | Already partially implemented pre-loop, minor enhancements added |

### Loop Rule Compliance

| Rule | Status |
|------|--------|
| 1: Every item needs evidence | ✅ All DONE items have file-level evidence |
| 2: Never stop to ask | ✅ No questions asked, BLOCKED-HUMAN items documented in NEXT_STEPS.md-style |
| 3: Never silently drop scope | ⚠️ C2, C3 dropped — now tracked above |
| 4: Re-audit after 3-5 items | ❌ NOT DONE — needs full re-audit |
| 5: Log every iteration | ✅ LOOP_LOG.md updated |
| 6: No "close enough" | ⚠️ D3, D7, D10, D12, D13 marked PARTIAL, not DONE |

### Current Completion
- **Verified DONE:** 7 items
- **PARTIAL:** 6 items
- **NOT STARTED:** ~17 items (including Tier 2/3)
- **Estimated completion:** ~23%
- **BLOCKED-HUMAN:** 0

The loop must continue with the PARTIAL items before proceeding to new work. The DONE count is overstated unless PARTIAL items are finished.
