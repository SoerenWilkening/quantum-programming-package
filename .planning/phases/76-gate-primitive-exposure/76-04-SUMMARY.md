---
phase: 76-gate-primitive-exposure
plan: 04
subsystem: quantum-compiler
tags: [optimizer, rotation-gates, branch, uncomputation, gate-inverse]

# Dependency graph
requires:
  - phase: 76-gate-primitive-exposure
    provides: "branch() method with Ry emission (plan 02), MCZ gate (plan 01)"
provides:
  - "Correct Ry/Rx/Rz inverse detection in optimizer (gates_are_inverse)"
  - "Accumulating _start_layer/_end_layer tracking for multiple branch() calls"
affects: [76-05-PLAN, 76-06-PLAN, oracle-scope, grover-iteration]

# Tech tracking
tech-stack:
  added: []
  patterns: ["negated-angle inverse check for rotation gates", "min/max layer accumulation for multi-call uncomputation"]

key-files:
  created: []
  modified:
    - c_backend/src/gate.c
    - src/quantum_language/qint.pyx

key-decisions:
  - "Task 1 gate.c fix was already applied in commit 4bae694 (plan 01) -- no redundant commit needed"
  - "Layer accumulation uses 0/0 sentinel to distinguish first call from subsequent calls"

patterns-established:
  - "Rotation gate inverse: Ry(theta)^-1 = Ry(-theta), same pattern for Rx, Rz, P"
  - "Multi-call layer tracking: min/max accumulation instead of overwrite"

requirements-completed: [PRIM-01, PRIM-02, PRIM-03]

# Metrics
duration: 2min
completed: 2026-02-20
---

# Phase 76 Plan 04: Branch Accumulation Bug Fixes Summary

**Fixed two bugs preventing branch() rotation accumulation: optimizer Ry/Rx/Rz inverse detection and _start_layer overwrite in multi-call scenarios**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-20T13:40:13Z
- **Completed:** 2026-02-20T13:42:49Z
- **Tasks:** 2
- **Files modified:** 1 (gate.c fix was pre-existing)

## Accomplishments
- Confirmed gates_are_inverse() already handles Ry/Rx/Rz with negated-angle check (applied in plan 01 commit 4bae694)
- Fixed branch() _start_layer/_end_layer overwrite bug with min/max accumulation logic
- Multiple branch() calls now correctly expand the tracked layer range for uncomputation

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix gates_are_inverse() rotation gate inverse check** - `4bae694` (already applied in plan 01, no new commit)
2. **Task 2: Fix branch() _start_layer accumulation** - `16e38f0` (fix)

## Files Created/Modified
- `c_backend/src/gate.c` - gates_are_inverse() now checks negated angle for Ry/Rx/Rz (pre-existing fix)
- `src/quantum_language/qint.pyx` - branch() accumulates _start_layer/_end_layer across multiple calls via min/max

## Decisions Made
- Task 1 fix was already present from commit 4bae694 (feat(76-01): add MCZ gate to C backend). Rather than creating a redundant no-op commit, documented the existing fix.
- Used 0/0 sentinel check (`self._start_layer == 0 and self._end_layer == 0`) to distinguish first branch() call from subsequent calls, matching the default initialization.

## Deviations from Plan

### Task 1 Already Applied

Task 1 (gates_are_inverse fix) was already implemented in commit `4bae694` during plan 01 execution. The plan was written based on an older snapshot of the code. No redundant commit was created.

---

**Total deviations:** 1 (Task 1 pre-existing fix)
**Impact on plan:** No impact -- the fix was already correct. Only Task 2 required new work.

## Issues Encountered
- Pre-commit hooks initially failed due to missing `pre_commit` Python module. Resolved by installing `pre-commit` package.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both fixes are source-level changes only; package rebuild (plan 06) is required before tests can verify at runtime
- Plan 05 (controlled branch fix) can proceed independently
- Plan 06 (rebuild + test verification) will validate both fixes end-to-end

## Self-Check: PASSED

- FOUND: c_backend/src/gate.c
- FOUND: src/quantum_language/qint.pyx
- FOUND: 76-04-SUMMARY.md
- FOUND: 4bae694 (Task 1 pre-existing commit)
- FOUND: 16e38f0 (Task 2 commit)

---
*Phase: 76-gate-primitive-exposure*
*Completed: 2026-02-20*
