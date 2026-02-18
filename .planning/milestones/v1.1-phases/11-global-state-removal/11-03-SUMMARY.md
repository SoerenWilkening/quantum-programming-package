---
phase: 11-global-state-removal
plan: 03
subsystem: backend
tags: [c, quantum-backend, refactoring, global-state, parameterization]

# Dependency graph
requires:
  - phase: 11-01
    provides: Removed classical-only functions
  - phase: 11-02
    provides: Parameterized P_add and cP_add functions
provides:
  - Parameterized legacy logic functions (q_and_seq, cq_and_seq, cqq_and_seq, etc.)
  - Explicit width/value parameters instead of QPU_state->Q0/R0 reads
  - Updated header declarations for refactored functions
affects:
  - 11-04: Comparison function refactoring benefits from fewer global state dependencies
  - 12: Future refactoring work has cleaner codebase with minimal global state usage

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Legacy function parameterization: Add explicit bits/classical_value parameters instead of reading global state"
    - "DEPRECATED comments direct users to modern Q_and/Q_xor/Q_or functions from bitwise_ops.h"

key-files:
  created: []
  modified:
    - Backend/src/LogicOperations.c
    - Backend/include/LogicOperations.h

key-decisions:
  - "Parameterized legacy semi-classical functions while keeping qq_* functions (pure quantum) unchanged where they don't read QPU_state"
  - "Added DEPRECATED comments to guide users toward modern width-parameterized functions"

patterns-established:
  - "Legacy refactoring pattern: Keep function names, add explicit parameters, update callers separately"
  - "Header documentation: Mark deprecated functions and point to modern alternatives"

# Metrics
duration: 3min
completed: 2026-01-27
---

# Phase 11 Plan 03: Legacy Logic Function Parameterization Summary

**Refactored 10 legacy semi-classical logic functions to take explicit width/value parameters instead of reading QPU_state->Q0->MSB and QPU_state->R0**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-27T14:15:51Z
- **Completed:** 2026-01-27T14:18:58Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Parameterized 3 legacy AND functions (q_and_seq, cq_and_seq, cqq_and_seq)
- Parameterized 4 legacy XOR functions (q_xor_seq, cq_xor_seq, qq_xor_seq, cqq_xor_seq)
- Parameterized 3 legacy OR functions (q_or_seq, cq_or_seq, cqq_or_seq)
- Updated header declarations with new signatures and DEPRECATED comments
- Verified code compiles without errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor legacy AND sequence functions** - `7436321` (refactor)
2. **Task 2: Refactor legacy XOR and OR sequence functions** - `ea579a0` (refactor)
3. **Task 3: Update header declarations** - `be75d23` (refactor)

## Files Created/Modified
- `Backend/src/LogicOperations.c` - Refactored 10 legacy logic functions with explicit parameters
- `Backend/include/LogicOperations.h` - Updated declarations with new signatures and deprecation notices

## Decisions Made

**Selective parameterization:** Only modified functions that actually read QPU_state. Functions with commented-out QPU_state reads (qq_and_seq, qq_or_seq) were left unchanged as they don't have the global state dependency.

**No backward compatibility wrappers:** Since these are legacy functions and modern alternatives exist (Q_and, Q_xor, Q_or from bitwise_ops.h), we didn't create deprecated wrappers. Future work will update callers to use explicit parameters or migrate to modern functions.

## Deviations from Plan

None - plan executed exactly as written.

All functions identified in the plan were refactored with explicit parameters:
- AND: q_and_seq, cq_and_seq, cqq_and_seq (3 functions)
- XOR: q_xor_seq, cq_xor_seq, qq_xor_seq, cqq_xor_seq (4 functions)
- OR: q_or_seq, cq_or_seq, cqq_or_seq (3 functions)

Functions that don't read QPU_state (qq_and_seq, qq_or_seq) were correctly left unchanged.

## Issues Encountered
None. All functions were parameterized cleanly. Compilation verification passed after each task.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

**Ready for Plan 11-04 (Comparison Function Refactoring):**
- Legacy logic functions now take explicit parameters
- QPU_state->Q0 and QPU_state->R0 references eliminated from logic operations
- Only 4 commented-out QPU_state->Q0 references remain (in functions that don't actually use them)
- Codebase has significantly fewer global state dependencies

**No blockers or concerns.**

**Status:** Phase 11 (Global State Removal) continues with comparison function refactoring to eliminate remaining QPU_state dependencies.

---
*Phase: 11-global-state-removal*
*Completed: 2026-01-27*
