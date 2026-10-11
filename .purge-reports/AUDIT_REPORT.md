# DEAD-WEIGHT PURGE v2.0 AUDIT REPORT

**Repository**: `Veridoc`  
**Mode**: `AUDIT_ONLY` (Zero repository modifications performed)  
**Baseline Commit SHA**: `86a146d60e4a423e3de70b09d122dac11f8db51f`  
**Audit Date**: 2026-10-11  
**Verdict**: **YELLOW** (Dead weight detected; review recommended)

---

## 1. Executive Summary

- **Tracked Files in Git**: 283
- **Untracked Local Files**: 0
- **Total LOC**: 73,710
- **Analyzed Size**: 4.32 MB
- **Total Dead-Weight Candidates Identified**: 95
  - **Tier 0 (Provable Junk/Empty)**: 58
  - **Tier 1 (High Confidence)**: 0
  - **Tier 2 (Medium / Needs Verification)**: 37
  - **Tier 3 (Protected / Hard Vetoed)**: 0

## 2. Findings by Category

| Category | Description | Count |
|---|---|---|
| **A** | Empty & Near-Empty Files | 6 |
| **C** | Junk / Caches / Build Artifacts | 52 |
| **D** | Potential Orphan Modules | 37 |
| **H** | Exact Hash Duplicates | 0 |

### Top Tier-0 Items (Provable Deletion Candidates if EXECUTE_SAFE were used):
- [`A`] `backend/app/__init__.py`: 0-byte file with no content
- [`A`] `backend/app/api/__init__.py`: 0-byte file with no content
- [`A`] `backend/app/schemas/__init__.py`: 0-byte file with no content
- [`A`] `backend/app/services/__init__.py`: 0-byte file with no content
- [`A`] `backend/tests/__init__.py`: 0-byte file with no content
- [`A`] `py.typed`: 0-byte file with no content
- [`C`] `.cleanup-audit/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.cleanup-audit/.claude/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.coverage`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.env`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.hypothesis/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.hypothesis/.gitignore`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.hypothesis/unicode_data/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.mypy_cache/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.pytest_cache/`: Untracked build/dependency/cache artifact directory in workspace
_...and 43 more listed in `manifest.csv`._

## 3. Next Steps & Recommended Actions

1. Review `.purge-reports/manifest.csv` and `.purge-reports/FLAGGED.md`.
2. If safe cleanup is desired, configure `MODE: EXECUTE_SAFE` or generate an approval `PLAN.yaml`.
3. Verify that all untracked artifacts (`__pycache__`, `.venv`, `.pytest_cache`) are properly covered in `.gitignore`.
