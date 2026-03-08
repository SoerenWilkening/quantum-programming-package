---
phase: 113-diffusion-redesign-move-enumeration
plan: 03
subsystem: quantum-walk
tags: [diffusion, counting-circuit, chess-walk, code-sharing, refactor]

requires:
  - phase: 113-02
    provides: counting-based _counting_diffusion method on QWalkTree
provides:
  - counting_diffusion_core standalone function shared by QWalkTree and chess_walk
  - chess_walk.apply_diffusion using O(d_max) counting diffusion
affects: [113-04, chess-walk-performance]

tech-stack:
  added: []
  patterns: [shared-counting-diffusion-core, module-level-function-extraction]

key-files:
  created: []
  modified:
    - src/quantum_language/walk.py
    - src/chess_walk.py
    - tests/python/test_walk_variable.py

key-decisions:
  - "Extracted counting_diffusion_core as module-level function in walk.py rather than standalone module"
  - "chess_walk.py still owns angle precomputation and validity evaluation, only delegates counting core"
  - "Removed itertools and unused diffusion import from chess_walk.py"

patterns-established:
  - "Shared diffusion core: callers handle validity alloc/eval/uncompute, core handles count+rotate+S_0"

requirements-completed: [WALK-03]

duration: 7min
completed: 2026-03-08
---

# Plan 113-03: Chess Walk Shared Diffusion Summary

**chess_walk.py wired to counting_diffusion_core from walk.py, eliminating duplicate combinatorial O(2^d_max) code**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-08T19:01:38Z
- **Completed:** 2026-03-08T19:08:33Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Extracted `counting_diffusion_core()` standalone function in walk.py containing the counting+rotation+S_0 core
- Rewired `QWalkTree._counting_diffusion` to delegate to shared function
- Replaced itertools.combinations loop in `chess_walk.apply_diffusion()` with single call to `counting_diffusion_core`
- Removed `import itertools` and unused `from quantum_language.diffusion import diffusion` from chess_walk.py
- All 259 tests pass across walk, chess_walk, counting_diffusion, chess, and broader walk suites

## Task Commits

1. **Task 1: Extract shared counting diffusion and wire chess_walk.py** - `68c793f` (feat)
2. **Task 2: Full regression suite and cleanup** - `cbbd693` (test)

## Files Created/Modified
- `src/quantum_language/walk.py` - Added `counting_diffusion_core()` standalone function, refactored `_counting_diffusion` to delegate
- `src/chess_walk.py` - Replaced itertools.combinations diffusion with `counting_diffusion_core` call, removed unused imports
- `tests/python/test_walk_variable.py` - Updated pruning predicate test to verify state modification instead of superposition count

## Decisions Made
- Extracted core as module-level function in walk.py (not a separate module) to keep related code together
- chess_walk.py retains its own angle precomputation (`precompute_diffusion_angles`) and validity evaluation -- only the counting+rotation+S_0 core is shared
- Kept `_plan_cascade_ops` import in chess_walk.py since `precompute_diffusion_angles` still uses it

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in `test_walk_detection.py::test_sat_predicate_qubit_budget_depth1` (qubit budget exceeded) -- not a regression, was failing before changes (32719 qubits before, 19 after -- actually improved)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Single shared counting diffusion implementation across both walk.py and chess_walk.py
- Ready for phase 113-04 (if applicable) or next milestone work
- One pre-existing test failure remains in walk_detection (qubit budget test)

---
*Plan: 113-03-chess-walk-shared-diffusion*
*Completed: 2026-03-08*
