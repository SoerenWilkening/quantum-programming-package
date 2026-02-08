---
phase: 63-right-sizing-implementation
plan: 01
subsystem: codegen
tags: [c-codegen, qft, iqft, hardcoded-sequences, code-deduplication]

# Dependency graph
requires:
  - phase: 62-measurement
    provides: "Benchmark data proving 2-6x dispatch speedup for hardcoded sequences"
provides:
  - "Data-driven decision document keeping all addition widths 1-16 hardcoded"
  - "Refactored generate_seq_all.py with shared QFT/IQFT factoring"
  - "Regenerated C files with 32.9% source line reduction (79,867 -> 53,598)"
  - "Passing test suite confirming arithmetic correctness preserved"
affects: [64-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns: ["segmented optimization (QFT/middle/IQFT independently)", "composite LAYERS arrays referencing shared static const gate arrays", "shared init helpers for template-init functions"]

key-files:
  created:
    - ".planning/phases/63-right-sizing-implementation/RIGHT_SIZING_DECISION.md"
  modified:
    - "scripts/generate_seq_all.py"
    - "c_backend/src/sequences/add_seq_1.c through add_seq_16.c"
    - "c_backend/src/sequences/add_seq_dispatch.c"

key-decisions:
  - "KEEP all addition widths 1-16 hardcoded based on Phase 62 benchmark data (2-6x speedup, 192ms import)"
  - "Apply segmented optimization (QFT/middle/IQFT independently) to enable clean sharing"
  - "Use packed QFT layout from _generate_qft_layers() for shared arrays"
  - "Separate sharing categories: static const for QQ/cQQ, init helpers for CQ/cCQ"

patterns-established:
  - "Composite LAYERS pattern: reference shared arrays by pointer in variant-specific LAYERS[] arrays"
  - "Segmented optimization: optimize sections independently to preserve sharing boundaries"

# Metrics
duration: 37min
completed: 2026-02-08
---

# Phase 63 Plan 01: Right-Sizing Implementation Summary

**Shared QFT/IQFT factoring across 4 addition variants per width, reducing 79,867 lines to 53,598 (32.9%), with all 165 hardcoded sequence tests passing**

## Performance

- **Duration:** 37 min
- **Started:** 2026-02-08T17:14:11Z
- **Completed:** 2026-02-08T17:52:09Z
- **Tasks:** 3
- **Files modified:** 18 (1 script + 16 per-width C files + 1 dispatch C file + 1 decision doc)

## Accomplishments
- Created data-driven decision document (ADD-01) keeping all addition widths 1-16 hardcoded, justified by Phase 62 benchmark data
- Refactored generate_seq_all.py to factor out shared QFT/IQFT sub-sequences between all 4 addition variants per width
- Reduced total generated C source from 79,867 to 53,598 lines (32.9% reduction, 26,269 lines eliminated)
- All 165 hardcoded sequence tests pass, confirming arithmetic correctness preserved

## Task Commits

Each task was committed atomically:

1. **Task 1: Decision document and baseline measurement** - `45397c4` (docs)
2. **Task 2: Refactor generation script for shared QFT/IQFT factoring** - `28eaf18` (feat)
3. **Task 3: Regenerate C files, validate sharing, rebuild, and test** - `38bcfcb` (feat)

## Files Created/Modified
- `.planning/phases/63-right-sizing-implementation/RIGHT_SIZING_DECISION.md` - Data-driven decision to keep all addition widths 1-16 hardcoded
- `scripts/generate_seq_all.py` - Refactored with 8 new functions for shared QFT/IQFT factoring
- `c_backend/src/sequences/add_seq_1.c` through `add_seq_16.c` - Regenerated with SHARED_QFT/SHARED_IQFT arrays and init helpers
- `c_backend/src/sequences/add_seq_dispatch.c` - Regenerated (functionally identical, minor formatting changes from clang-format)

## Decisions Made
- **KEEP all addition widths 1-16:** Phase 62 data shows 2-6x dispatch speedup with acceptable 192ms import overhead
- **Segmented optimization:** QFT, middle, and IQFT segments optimized independently to prevent cross-boundary merging that would break sharing. Adds +1 layer for widths >= 2 (negligible)
- **Packed QFT from _generate_qft_layers():** Uses the pre-packed layout that places non-overlapping gates in the same layer, producing fewer layers than the sequential approach
- **Const vs mutable separation:** Static const arrays shared between QQ/cQQ (read-only), init helper functions shared between CQ/cCQ (mutable malloc'd data)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Layer count mismatch due to packed QFT layout**
- **Found during:** Task 2 (validation)
- **Issue:** The packed `_generate_qft_layers()` produces different layer counts than the sequential QFT in `generate_qq_add()`. Expected counts in `validate()` were wrong.
- **Fix:** Recomputed expected layer counts based on actual segmented optimization results. Added gate equivalence verification to confirm correctness despite different layer structure.
- **Files modified:** `scripts/generate_seq_all.py` (validate function)
- **Verification:** All validations pass including gate equivalence check
- **Committed in:** `28eaf18` (Task 2 commit)

**2. [Rule 3 - Blocking] Pre-existing segfaults in test suite**
- **Found during:** Task 3 (full test suite run)
- **Issue:** `test_phase7_arithmetic` and `test_array_creates_list_of_qint` crash with segfault, but this is pre-existing (confirmed by reverting and testing old code)
- **Fix:** No fix needed -- these are documented pre-existing bugs (32-bit multiplication segfault in STATE.md). Ran all non-crashing test files plus the comprehensive 165-test hardcoded sequence suite.
- **Files modified:** None
- **Verification:** Verified same tests crash on old code before changes

---

**Total deviations:** 2 auto-fixed (2 blocking issues)
**Impact on plan:** First deviation was necessary for correct validation. Second was a pre-existing issue not caused by our changes.

## Issues Encountered
- Build system requires `python setup.py build_ext --inplace` rather than `pip install -e .` due to `build_preprocessor` module not being found in pip's isolated build environment
- clang-format expanded some generated C code lines, increasing total line count from 41,821 (pre-format) to 53,598 (post-format). The reduction is still significant at 32.9%

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 63 plan 01 objectives (ADD-01 and ADD-02) are satisfied
- ADD-03 (removal path) is not applicable since all widths are kept
- Ready for Phase 64 (if any remaining cleanup tasks exist)
- Pre-existing test segfaults are documented but not introduced by this phase

## Self-Check: PASSED

- [x] RIGHT_SIZING_DECISION.md exists
- [x] generate_seq_all.py exists
- [x] add_seq_16.c exists with SHARED_QFT pattern
- [x] add_seq_dispatch.c exists (427 lines, unchanged)
- [x] Commit 45397c4 exists (Task 1)
- [x] Commit 28eaf18 exists (Task 2)
- [x] Commit 38bcfcb exists (Task 3)
- [x] Decision document contains "KEEP all addition widths 1-16"
- [x] Total line count 53,598 < 79,867 (measurable reduction)

---
*Phase: 63-right-sizing-implementation*
*Completed: 2026-02-08*
