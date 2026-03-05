---
phase: 105-full-walk-operators
plan: 02
subsystem: quantum-walk
tags: [quantum-walk, compile, chess, mega-register, walk-step]

# Dependency graph
requires:
  - phase: 105-full-walk-operators
    provides: r_a(), r_b() walk operators
provides:
  - all_walk_qubits() mega-register constructor (height + branch qubits)
  - walk_step() compiled walk operator U = R_B * R_A
affects: [106 demo scripts]

# Tech tracking
tech-stack:
  added: [numpy]
  patterns: [mega-register via qint(create_new=False), compiled walk step with multi-arg pattern]

key-files:
  created: []
  modified:
    - src/chess_walk.py
    - tests/python/test_chess_walk.py

key-decisions:
  - "Board qarrays passed as separate compile args (total qubit count exceeds 64-qubit qint limit)"
  - "all_walk_qubits wraps height + branch only; board arrays handled by compile multi-arg support"
  - "Module-level CompiledFunc with mutable context dict for closure updates across calls"
  - "Cache key = total qubit count (height + branch + board elements)"

patterns-established:
  - "Multi-arg compile pattern: mega-register qint + separate qarray args for large qubit sets"
  - "Mutable context dict in closure for functional walk_step without class state"

requirements-completed: [WALK-07]

# Metrics
duration: 25min
completed: 2026-03-05
---

# Phase 105 Plan 02: Walk Step Compilation Summary

**Compiled walk step U = R_B * R_A with multi-arg compile pattern passing height+branch qint and board qarrays separately**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-05T13:48:30Z
- **Completed:** 2026-03-05T14:13:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented all_walk_qubits() wrapping height + branch register qubits into a single qint
- Implemented walk_step() composing R_A then R_B via @ql.compile with automatic caching
- 6 new tests (3 per task), 59 total tests pass, zero regressions
- Adapted plan's single mega-register approach to multi-arg compile pattern due to 64-qubit qint limit

## Task Commits

Each task was committed atomically:

1. **Task 1: all_walk_qubits() mega-register constructor with tests**
   - `783874a` (test) - RED: failing tests for all_walk_qubits
   - `da290c5` (feat) - GREEN: implement all_walk_qubits

2. **Task 2: walk_step() compiled walk operator with tests**
   - `0723e8e` (test) - RED: failing tests for walk_step
   - `90f40dc` (feat) - GREEN: implement walk_step

## Files Created/Modified
- `src/chess_walk.py` - Added all_walk_qubits(), walk_step(), _walk_compiled_fn, numpy import, updated __all__
- `tests/python/test_chess_walk.py` - Added TestAllWalkQubits (3 tests), TestWalkStep (3 tests)

## Decisions Made
- Board qarrays (wk, bk, wn) cannot be included in a single mega-register qint because the total qubit count (height + branch + 3*64 board = ~199) exceeds the framework's 64-qubit qint width limit. Instead, all_walk_qubits() wraps only height + branch qubits, and walk_step() passes board qarrays as separate arguments to the compiled function. The compile infrastructure's multi-arg support handles qubit tracking correctly.
- Used mutable context dict pattern for the compiled function closure so walk args can be updated across calls without recreating the CompiledFunc object.
- Replay test uses mock-based verification (r_a/r_b composition check) instead of double-call gate counting to avoid ~2min test runtime.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Board qubits exceed 64-qubit qint limit**
- **Found during:** Task 1 (all_walk_qubits implementation)
- **Issue:** Plan specified wrapping height + branch + board (192 qubits) in a single qint, but qint max width is 64
- **Fix:** all_walk_qubits() wraps height + branch only; walk_step() passes board qarrays as separate compile args
- **Files modified:** src/chess_walk.py, tests/python/test_chess_walk.py
- **Verification:** 59 tests pass, walk_step smoke test succeeds with real chess position
- **Committed in:** da290c5, 90f40dc

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary adaptation to framework constraint. Multi-arg compile pattern is equivalent to mega-register pattern -- all walk qubits are tracked as parameters, not ancillas.

## Issues Encountered
- walk_step compile + optimize takes ~50s for chess position (wk=4, bk=60, wn=[10], max_depth=1) due to large gate count. Replay test restructured to use mock verification instead of double-call timing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- walk_step() is the culminating function of Phase 105, ready for Phase 106 demo scripts
- all_walk_qubits() is public and reusable for circuit statistics in demo
- Inverse available automatically via compiled function's .inverse property

## Self-Check: PASSED

All files and commits verified.

---
*Phase: 105-full-walk-operators*
*Completed: 2026-03-05*
