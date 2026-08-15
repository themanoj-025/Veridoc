# Veridoc — Old Tree → New Tree

## This pass (2026-08-11)

```
Before                                After
──────                                ─────
docs/migration_summary.md      →      docs/migration/migration_summary.md
docs/architecture.md (3-line stub)    docs/architecture.md (full architecture doc)
docs/folder_structure.md (stub)       docs/folder_structure.md (annotated tree)
—                                     docs/module_dependency.md        (new)
—                                     docs/startup_flow.md             (new)
—                                     docs/package_overview.md         (new)
—                                     docs/migration/old_tree_to_new_tree.md (new)
—                                     docs/migration/file_move_ledger.md     (new)
.mypy_cache/ (48 files, tracked)  →   untracked + .gitignore rule added
```

## Prior pass (v5.0 modernization, commit `9a691e8`)

Veridoc was restructured by the v5.0 pass into the current layout:
all Python under `backend/app` (api/core/models/repositories/schemas/services),
Next.js under `frontend/`, ops under `scripts/`, evaluation under `eval/`,
prompts under `prompts/`, docs under `docs/`. The legacy v5.0 record was a
stub template; this pass replaces the stubs with real content.

## No-code-move rationale (this pass)

The layout already conforms (backend/frontend split, feature-cohesive layers,
canonical artifact dirs, root metadata only). This pass only consolidates the
migration record, completes the Phase-6 doc suite, and removes the tracked
mypy cache — zero application code changed.
