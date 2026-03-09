---
phase: 116-walk-integration-demo
plan: 02
subsystem: quantum-walk
tags: [demo, chess-walk, circuit-build, build-move-table, walk-step, testing]

# Dependency graph
requires:
  - phase: 116-walk-integration-demo
    plan: 01
    provides: chess_walk.py with quantum predicates, offset-based oracle, walk_step
provides:
  - Rewritten demo.py as KNK depth-2 walk showcase
  - Circuit-build-only test suite for demo
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Demo as framework showcase: code readability matters as much as correctness"

key-files:
  created: []
  modified:
    - src/demo.py
    - tests/python/test_demo.py

key-decisions:
  - "MAX_DEPTH=2 for depth-2 walk (white move + black response)"
  - "Removed all references to legal_moves, print_moves (classical pre-filtering artifacts)"
  - "test_demo_circuit_builds marked @pytest.mark.slow for CI flexibility"

patterns-established: []

requirements-completed: [WALK-05]

# Metrics
duration: 2min
completed: 2026-03-09
---

# Phase 116 Plan 02: Demo Rewrite Summary

**KNK depth-2 walk demo with build_move_table enumeration, circuit-build-only tests, and framework showcase**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-09T13:30:41Z
- **Completed:** 2026-03-09T13:33:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Rewrote demo.py as clean KNK depth-2 walk showcase with build_move_table, prepare_walk_data, walk_step
- Upgraded from depth-1 to depth-2 walk (white move + black response)
- Replaced old patched tests with circuit-build-only tests verifying data structures and circuit construction
- Removed all references to classical pre-filtering (legal_moves, print_moves, _walk_compiled_fn)

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite demo.py for KNK depth-2 walk** - `b117484` (feat)
2. **Task 2: Rewrite test_demo.py with circuit-build-only tests** - `0f555ad` (feat)

## Files Created/Modified
- `src/demo.py` - KNK depth-2 walk demo using build_move_table and walk_step, returns stats with build_time
- `tests/python/test_demo.py` - Circuit-build-only tests: move tables, walk data structure, full build (slow)

## Decisions Made
- MAX_DEPTH changed from 1 to 2 for depth-2 walk per plan specification
- Removed unused `math` import (ruff auto-removed) and `all_walk_qubits` import (not needed in demo)
- test_demo_circuit_builds marked with @pytest.mark.slow for optional skipping in CI

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 116 (Walk Integration & Demo) is fully complete
- demo.py demonstrates full framework expressiveness with quantum predicates
- All fast tests pass; slow circuit build test available for full verification

---
*Phase: 116-walk-integration-demo*
*Completed: 2026-03-09*
