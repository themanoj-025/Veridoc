# Changelog

All notable changes to Veridoc are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
starting from v1.0.0.

---

## [1.0.0] — YYYY-MM-DD

> **First stable release.** Veridoc is production-ready for internal tooling and
> portfolio presentation. All core features are complete and verified.

### Added
- **Dark mode** — Full design system with CSS variables, dark/light theme toggle,
  and `prefers-reduced-motion` respect. Theme persisted to localStorage.
- **Loading skeletons** — Skeleton components for document list, chat messages,
  document viewer, conversation list, and upload progress states.
- **Toast notification system** — Animated toast container with success, error,
  info, and warning variants. Auto-dismiss with configurable duration.
- **Thumbs up/down feedback** — Inline feedback buttons on chat messages with
  continuous evaluation loop integration. Thumbs-down responses queued for review.
- **Continuous evaluation loop** — `eval/continuous_feedback.json` queue with
  `scripts/promote_feedback.py` for reviewing and promoting entries into the gold Q&A set.
- **Command palette** — Cmd/Ctrl+K quick actions: New Conversation, Toggle Dark Mode,
  Upload Document, Search Documents, Sign Out. Keyboard-navigable.
- **Document & conversation search** — Client-side search bar filtering documents
  and conversations by name. Full-text search via Postgres tsvector GIN index.
- **Full-text search endpoint** — `GET /api/v1/search/fulltext` exposes the
  `chunks.content_tsv` GIN index for searching document content.
- **GDPR data controls** — `GET /api/v1/user/export` for JSON data export and
  `DELETE /api/v1/user/delete-account` for account deletion with cascade.
- **Admin analytics view** — `GET /api/v1/admin/analytics` surfaces query volume,
  latency percentiles, popular documents, daily usage, and cost estimates.
- **OCR confidence indicator** — `DocumentResponse` includes `ocr_used` field;
  citation UI shows source indicator for OCR-originated chunks.
- **Semantic versioning** — First tagged release (v1.0.0). Version exposed via
  `/api/v1/health` response and referenced in the running app.
- **CI evaluation regression gate** — CI step runs fast evaluation subset and
  fails the build if metrics drop below defined thresholds.
- **Multi-model fallback routing** — `llm_provider.py` falls back to Ollama if
  the primary provider errors or times out, with logged fallback events.
- **Feedback API** — `POST /api/v1/chat/feedback` for thumbs up/down submissions.
- **Search router** — `GET /api/v1/search/fulltext` with tsvector-powered search.
- **GDPR router** — User data export and account deletion endpoints.

### Changed
- **tailwind.config.ts** — Complete design system token set: spacing scale
  (2px–64px), type scale (3 sizes), accent color (Veridoc blue), neutral gray scale,
  border radius scale, animation keyframes (fadeInUp, slideInRight, scaleIn, shimmer).
- **Layout** — Dark mode FOUC prevention via inline script, `ToastContainer` added.
- **Dashboard** — Mobile responsive tabs, skeleton loading states, `ThemeToggle`,
  `CommandPalette` integration.
- **DocumentList** — Accepts `loading` prop for skeleton states.
- **globals.css** — Dark mode CSS variables, scoped theme transitions,
  skeleton shimmer animation, toast container styles, citation chip dark variants.
- **Backend main.py** — Registered feedback, search, GDPR, and admin routers.
- **LLM provider** — Fallback chain: primary → Ollama fallback with event logging.
- **Store** — Added `toggleDarkMode` function.

### Fixed
- **Upload form TypeScript error** — Replaced `form.elements.nativeElement` with
  `FormData` API to fix TS compilation error.

---

## [0.1.0] — 2026-07-28

> Initial pre-release. Core RAG pipeline with hybrid search, JWT auth, SSE streaming,
> and basic frontend.

### Added (initial development)
- Document ingestion pipeline (PDF, DOCX, TXT with OCR fallback)
- Hybrid retrieval (BM25 + dense embeddings + RRF + cross-encoder reranking)
- SSE streaming chat with citations and faithfulness checking
- JWT authentication with token rotation
- 77+ backend tests (unit, integration, security)
- Docker Compose stack (8 services)
- Evaluation harness with 23-question gold set
- Prometheus metrics and structured logging
- CI pipeline with GitHub Actions
- Full documentation suite (architecture, security, deployment, case study)

[1.0.0]: https://github.com/themanoj-025/veridoc/releases/tag/v1.0.0
[0.1.0]: https://github.com/themanoj-025/veridoc/releases/tag/v0.1.0
