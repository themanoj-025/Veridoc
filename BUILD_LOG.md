# Veridoc — Frontend Build Log

> F15: Bundle analysis — measured from real `npm run build` output.
> Generated: 2026-07-31 (Next.js 14.2.35, production build)

## Measured Bundle Sizes (2026-07-31)

```
Route (app)                              Size     First Load JS
┌ ○ /                                    1.29 kB        88.7 kB
├ ○ /_not-found                          873 B          88.3 kB
├ ○ /admin                               6.35 kB         135 kB
├ ○ /dashboard                           48.6 kB         181 kB
├ ○ /login                               1.4 kB          133 kB
└ ○ /register                            1.5 kB          133 kB
+ First Load JS shared by all            87.4 kB
  ├ chunks/117-31f7da99ff591dc2.js       31.7 kB
  ├ chunks/fd9d1056-00a4318969832c33.js  53.6 kB
  └ other shared chunks (total)          2.01 kB

ƒ Middleware                             26.7 kB
```

## Analysis

- **Largest route**: `/dashboard` at 181 kB First Load JS (48.6 kB route chunk).
  This is expected — it renders the document list, viewer, chat panel, search
  bar, command palette, and React Query provider, and pulls in `react-markdown`
  + `rehype-sanitize` for chat rendering.
- **Shared baseline**: 87.4 kB shared across all routes (React + React Query
  + axios). No unexpectedly large third-party chunk was introduced.
- **No `react-markdown` bloat warning**: the chat sanitization stack is scoped
  to the dashboard route; no eager global import.
- **Middleware**: 26.7 kB — standard for Next.js middleware (auth token checks).

## Bundle Analyzer

Run `ANALYZE=true npm run build` (requires `@next/bundle-analyzer`, installed)
to open the interactive treemap showing each chunk's composition. The analyzer
is wired in `next.config.js` and activates only when `ANALYZE=true`, so it has
zero impact on normal builds.

## Verdict

No action required: no single dependency dominates the bundle. If dashboard
First Load JS grows past ~250 kB, re-check for accidental eager imports of
`react-markdown` or the LLM/client SDKs.
