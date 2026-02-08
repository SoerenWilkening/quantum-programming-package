---
phase: 59
plan: 03
subsystem: c-backend-sequences
tags: [hardcoded-sequences, routing, IntegerAddition, CQ_add, cCQ_add, QQ_add, cQQ_add]
dependency-graph:
  requires: ["59-02"]
  provides: ["IntegerAddition.c routing for all 4 hardcoded addition variants"]
  affects: ["59-04"]
tech-stack:
  added: []
  patterns: ["template-init cache population pattern for CQ/cCQ"]
key-files:
  created: []
  modified:
    - c_backend/src/IntegerAddition.c
    - c_backend/src/sequences/add_seq_1.c through add_seq_16.c
    - scripts/generate_seq_all.py
key-decisions:
  - id: SEQ-10
    decision: "CQ/cCQ template-init populates existing precompiled cache array before cache check"
    rationale: "Reuses existing angle injection path without duplication"
metrics:
  duration: "48 min"
  completed: "2026-02-06"
---

# Phase 59 Plan 03: IntegerAddition.c Routing Summary

**One-liner:** Route all 4 addition variants through hardcoded sequences for widths 1-16, fixing critical include-order bug in per-width C files.

## Performance

- Build: Compiles without errors (only pre-existing sign-compare warning)
- All 888 addition tests pass
- All 61 hardcoded sequence tests pass

## Accomplishments

### Task 1: Update QQ_add and cQQ_add routing comments
- Updated QQ_add comment from "widths 1-8" to "widths 1-16"
- Updated cQQ_add comment from "widths 1-8" to "widths 1-16"
- Updated dynamic fallback comments to reference HARDCODED_MAX_WIDTH
- No logic change needed (existing code already uses HARDCODED_MAX_WIDTH constant)

### Task 2: Add CQ_add and cCQ_add routing + fix include order bug
- Added hardcoded template-init block to CQ_add() for widths 1-16
- Added hardcoded template-init block to cCQ_add() for widths 1-16
- Template-init populates `precompiled_CQ_add_width[bits]` cache on first call
- Existing cache path handles angle injection on subsequent calls
- Fixed critical include-order bug in all 16 per-width C files (see deviations)
- Fixed generation script to produce correct include order on regeneration

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Update QQ_add/cQQ_add routing comments | 62bc745 | IntegerAddition.c |
| 2 | Add CQ_add/cCQ_add routing + fix include order | 08c9606 | IntegerAddition.c, add_seq_1-16.c, generate_seq_all.py |

## Files Modified

| File | Change |
|------|--------|
| c_backend/src/IntegerAddition.c | Added CQ/cCQ template-init, updated QQ/cQQ comments |
| c_backend/src/sequences/add_seq_1.c - add_seq_16.c | Fixed #include ordering (sequences.h before #ifdef guard) |
| scripts/generate_seq_all.py | Fixed include order in template generation |

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| SEQ-10 | Template-init populates existing precompiled cache before cache check | Reuses existing angle-injection path, zero code duplication |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed #include ordering in all 16 per-width C files**
- **Found during:** Task 2 (build verification)
- **Issue:** Per-width files (add_seq_N.c) wrapped all code inside `#ifdef SEQ_WIDTH_N` BEFORE `#include "sequences.h"`, but sequences.h is what defines `SEQ_WIDTH_N`. This circular dependency caused all per-width files to compile to empty object files (0 symbols). The hardcoded sequences were never actually compiled or linked, though the build "succeeded" because the dispatch file also guarded its calls with the same ifdefs.
- **Fix:** Moved `#include "sequences.h"` before the `#ifdef SEQ_WIDTH_N` guard in all 16 files. Also fixed scripts/generate_seq_all.py to produce correct order on regeneration.
- **Files modified:** add_seq_1.c through add_seq_16.c, scripts/generate_seq_all.py
- **Commit:** 08c9606
- **Impact:** This was a latent bug from Plan 59-02 that prevented ALL hardcoded sequences from being compiled. Without this fix, the dispatch functions returned NULL for all widths, and the system silently fell back to dynamic generation for every width.

## Issues and Concerns

**Retroactive impact on Phase 58:** The include-order bug was introduced in Plan 59-02 when per-width files replaced the original add_seq_1_4.c and add_seq_5_8.c. This means hardcoded sequences for widths 1-8 (from Phase 58) were also not being compiled since Plan 59-02. The fix in this plan restores ALL widths 1-16.

## Next Phase Readiness

- All 4 addition variants route through hardcoded sequences for widths 1-16
- Width 17+ falls back to dynamic generation
- Ready for Plan 59-04 (validation and verification)
