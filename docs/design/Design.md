# Design — Veridoc: Design System & UX Principles

| Field | Value |
| --- | --- |
| Version | v0.1 |
| Last Updated | 2026-08-06 |
| Owner | Lead Designer |
| Status | Approved |

---

## 1. Design Principles

1. **Verifiability first** — citations are the hero element; every claim links to a highlighted passage.
2. **Local-first trust** — the UI communicates privacy (no cloud) without clutter.
3. **Calm density** — document library and chat are focused, single-purpose surfaces.
4. **Honest states** — faithfulness refusals are explained, not hidden.
5. **Keyboard-first** — power users move through docs and chat without a mouse.

## 2. Brand & Visual Identity

- **Tagline:** "Answers you can verify, not just believe."
- **Tone:** precise, trustworthy, technical.
- **Imagery:** document + magnifier motif; citation highlight as the signature interaction.

## 3. Color System

| Token | Hex | Usage | Contrast |
| --- | --- | --- | --- |
| bg-canvas | #0F172A | App background (dark slate) | — |
| bg-surface | #1E293B | Cards, panels | — |
| text-primary | #F8FAFC | Body | ≥ 7:1 |
| text-muted | #94A3B8 | Secondary | ≥ 4.5:1 |
| accent | #38BDF8 | Links, active, citations | ≥ 4.5:1 |
| success | #34D399 | Indexed/complete | ≥ 4.5:1 |
| danger | #F87171 | Errors, refusals | ≥ 4.5:1 |
| warn | #FBBF24 | Degraded health | ≥ 4.5:1 |
| border | #334155 | Dividers | — |
| citation-highlight | #FEF3C7 | Highlighted passage bg (light) | — |

## 4. Typography Scale

| Token | Font | Size | Weight | LH | Usage |
| --- | --- | --- | --- | --- | --- |
| display | Inter | 28px | 700 | 1.2 | Dashboard hero |
| title | Inter | 20px | 600 | 1.3 | Screen titles |
| body | Inter | 16px | 400 | 1.5 | Chat + lists |
| caption | Inter | 13px | 400 | 1.4 | Meta, citations |
| mono | JetBrains Mono | 14px | 400 | 1.5 | Document IDs, code |

## 5. Spacing & Grid

- Base 4px; scale 4/8/12/16/24/32/48.
- Library: 3-col cards desktop, 1-col mobile; chat full-height column.
- Max content width 1200px.

## 6. Component Library

### 6.1 Document Card

| State | Style |
| --- | --- |
| Default | Icon, name, size, status chip, updated |
| Loading | Skeleton shimmer |
| Error | Card-level retry |

### 6.2 Ingestion Progress

- Stepped indicator: parse → chunk → embed → index; each with spinner/check/fail.
- Lives inline on upload card.

### 6.3 Chat Message with Citation

| Element | Spec |
| --- | --- |
| Answer text | Body 16px |
| Citation chip | `[p.3 · ¶2]` accent chip → click scrolls + highlights |
| Refusal | Danger border panel with reason + retry |

### 6.4 Highlighted Passage

- Citation target: yellow highlight (`citation-highlight`) with page label; scroll-into-view animation.

### 6.5 Buttons / Inputs / Toasts

- Primary (accent), ghost secondary, danger destructive.
- Inputs: 1px border, accent focus ring; error + helper text.
- Toasts: success/danger/warn; 5s auto-dismiss.

## 7. Iconography & Imagery

- Lucide-style stroke icons 20px (upload, file-text, message, shield, link, check).
- No stock photography.

## 8. Accessibility

- WCAG 2.1 AA; full keyboard nav; focus visible; skip-to-content.
- aria-live on streaming chat and ingestion progress.
- prefers-reduced-motion: disable scroll animations.

## 9. Responsive Behavior

| Breakpoint | Layout |
| --- | --- |
| < 640px | Stacked; chat full-screen; citations open document panel |
| 640–1024px | Library 2-col; split chat/doc |
| > 1024px | Library 3-col; dedicated chat + doc viewer |

## 10. Motion

| Token | Value |
| --- | --- |
| Duration | 150–250 ms |
| Easing | cubic-bezier(0.2,0,0,1) |
| Animated | citation scroll-into-view, toasts, streaming caret |
| Never | faithfulness verdict flips (instant) |

## 11. Dark Mode

- Default theme is dark (bg-canvas #0F172A); light mode reserved for future with token mapping.

## 12. Related Documents

| Document | Relationship |
| --- | --- |
| [AppFlow.md](AppFlow.md) | Screens consuming components |
| [PRD.md](../product/PRD.md) | UX requirements |
| [Rules.md](../project/Rules.md) | UI conventions |
