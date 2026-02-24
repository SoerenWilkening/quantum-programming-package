---
phase: 86-qft-bug-fixes
plan: 02
subsystem: cqq-addition
tags: [qft, controlled-addition, qubit-mapping, bug-fix]

requires:
  - phase: 86-01
    provides: Fixed mixed-width QFT addition
provides:
  - Correct cQQ_add source qubit mapping matching QQ_add convention
  - cQQ_add tests passing at widths 2-4
affects: [tests/test_cqq_add.py]

tech-stack:
  added: []
  patterns: [source-qubit-offset-correction]

key-files:
  created: []
  modified:
    - c_backend/src/hot_path_add.c

key-decisions:
  - "Source qubit mapping in cQQ_add corrected to match QQ_add convention"
  - "Fix applied only to hot_path_cadd_qqq (controlled QQ add) -- QQ_add was already correct"

patterns-established: []

requirements-completed: [BUG-05]

duration: ~15min
completed: 2026-02-24
---

# Plan 86-02: Fix cQQ_add rotation errors (BUG-05) Summary

**Correct cQQ_add source qubit mapping to match QQ_add convention**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-24
- **Completed:** 2026-02-24
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Fixed source qubit offset in cQQ_add (hot_path_cadd_qqq) to match QQ_add convention
- cQQ_add tests pass at widths 2-4 (exhaustive verification via Qiskit simulation)
- No regressions in QQ_add or CQ_add tests

## Task Commits

1. **Task 1 + Task 2: Fix + verification** - `ec95526` (fix)

## Files Created/Modified
- `c_backend/src/hot_path_add.c` - Source qubit mapping fix in cQQ_add

## Decisions Made
- Only hot_path_cadd_qqq needed fixing; QQ_add already had correct qubit layout
- Verified fix against all cQQ_add test cases including previously-failing ones

## Deviations from Plan
None.

## Issues Encountered
None.

## User Setup Required
None.

---
*Phase: 86-qft-bug-fixes*
*Completed: 2026-02-24*
