---
phase: 105-full-walk-operators
plan: 01
subsystem: quantum-walk
tags: [quantum-walk, montanaro, chess, diffusion, R_A, R_B]

# Dependency graph
requires:
  - phase: 104-walk-register-scaffolding-local-diffusion
    provides: apply_diffusion(), height_qubit(), create_height_register(), create_branch_registers(), prepare_walk_data()
provides:
  - r_a() walk operator (even depths, excluding root and leaves)
  - r_b() walk operator (odd depths plus root)
affects: [105-02 walk step compilation, 106 demo scripts]

# Tech tracking
tech-stack:
  added: []
  patterns: [R_A/R_B as thin loops over apply_diffusion, Montanaro depth convention]

key-files:
  created: []
  modified:
    - src/chess_walk.py
    - tests/python/test_chess_walk.py

key-decisions:
  - "r_a skips depth 0 (leaves) since level_idx=max_depth exceeds oracle_per_level range"
  - "r_a skips depth==max_depth (root always in R_B per Montanaro convention)"
  - "r_b explicitly adds max_depth when even to ensure root inclusion"

patterns-established:
  - "Walk operator composition: thin loop calling apply_diffusion at correct depth subsets"
  - "Depth set disjointness: R_A even (no root/leaves) + R_B odd + root = full coverage minus leaves"

requirements-completed: [WALK-04, WALK-05, WALK-06]

# Metrics
duration: 7min
completed: 2026-03-05
---

# Phase 105 Plan 01: R_A/R_B Walk Operators Summary

**R_A and R_B walk operators as thin loops over apply_diffusion with Montanaro depth convention and disjointness verification**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-05T13:38:23Z
- **Completed:** 2026-03-05T13:46:10Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Implemented r_a() composing apply_diffusion at even depths (skip leaves and root)
- Implemented r_b() composing apply_diffusion at odd depths plus root (explicit root when max_depth even)
- 18 new tests covering depth coverage, disjointness, completeness, and circuit-gen smoke
- All 53 tests pass (35 existing + 18 new), zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: r_a() and r_b() functions with tests**
   - `571232f` (test) - RED: failing tests for R_A/R_B
   - `db3912c` (feat) - GREEN: implement r_a and r_b

## Files Created/Modified
- `src/chess_walk.py` - Added r_a() and r_b() functions, updated __all__
- `tests/python/test_chess_walk.py` - Added TestRA, TestRB, TestHeightControlledCascade classes

## Decisions Made
- r_a() skips depth 0 (leaves have no children; level_idx=max_depth is out of range for oracle_per_level). This matches the plan's IMPORTANT note about open question 1.
- Disjointness tested externally via TestHeightControlledCascade, not asserted inside functions (per user decision in CONTEXT.md).
- Coverage verification confirms R_A union R_B = {1..max_depth} (depth 0 excluded as leaves).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- r_a() and r_b() ready for walk step composition (105-02)
- walk_step() will use U = R_B * R_A with @ql.compile and mega-register
- All walk operator building blocks in place

---
*Phase: 105-full-walk-operators*
*Completed: 2026-03-05*
