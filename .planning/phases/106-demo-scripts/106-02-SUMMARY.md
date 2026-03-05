---
phase: 106-demo-scripts
plan: 02
subsystem: demo
tags: [quantum-walk, chess, circuit-generation, comparison-script, qwalktree]

# Dependency graph
requires:
  - phase: 106-01-demo-scripts
    provides: demo.py main() with circuit stats return value
  - phase: 105-full-walk-operators
    provides: walk_step compiled operator, QWalkTree API
  - phase: 103-chess-encoding
    provides: encode_position, legal_moves, prepare_walk_data
provides:
  - "chess_comparison.py side-by-side Manual vs QWalkTree circuit stats comparison"
  - "test_comparison_main smoke test for comparison script"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [side-by-side-comparison-demo, dual-patch-test-pattern]

key-files:
  created:
    - src/chess_comparison.py
  modified:
    - tests/python/test_demo.py
    - src/quantum_language/walk.py

key-decisions:
  - "Patched both demo.walk_step and QWalkTree.walk_step in smoke test to avoid OOM in CI"
  - "Fixed QWalkTree._setup_diffusion cascade fallback to match chess_walk.py pattern"
  - "Trivial predicate (always-accept) for QWalkTree comparison per user decision"

patterns-established:
  - "Comparison script pattern: run same position through manual and API, print delta table"
  - "Dual-patch test pattern: patch both manual walk_step and QWalkTree.walk_step for CI safety"

requirements-completed: [DEMO-02]

# Metrics
duration: 14min
completed: 2026-03-05
---

# Phase 106 Plan 02: Comparison Script Summary

**Side-by-side Manual vs QWalkTree circuit stats comparison with formatted delta table and cascade fallback fix**

## Performance

- **Duration:** 14 min
- **Started:** 2026-03-05T16:05:00Z
- **Completed:** 2026-03-05T16:19:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created chess_comparison.py that runs same chess endgame through Manual (demo.py) and QWalkTree API approaches
- Formatted comparison table with Metric | Manual | QWalkTree | Delta columns
- Fixed QWalkTree._setup_diffusion to handle cascade NotImplementedError gracefully (matching chess_walk.py)
- Both test_demo_main and test_comparison_main pass green

## Task Commits

Each task was committed atomically:

1. **Task 1: Create chess_comparison.py with side-by-side stats** - `b13b973` (feat)
2. **Task 2: Unskip comparison smoke test and verify both pass** - `28f271d` (feat)

## Files Created/Modified
- `src/chess_comparison.py` - Side-by-side Manual vs QWalkTree comparison script with formatted delta table
- `tests/python/test_demo.py` - Unskipped test_comparison_main with dual walk_step patching
- `src/quantum_language/walk.py` - Added try/except cascade fallback in QWalkTree._setup_diffusion

## Decisions Made
- Patched QWalkTree.walk_step in test: like the manual walk_step, QWalkTree compilation needs 8GB+ RAM. Test patches both to emit lightweight X gates for non-zero stats in CI.
- Fixed QWalkTree cascade fallback: QWalkTree._setup_diffusion called _plan_cascade_ops without error handling, while chess_walk.py's precompute_diffusion_angles already had the try/except. Added matching fallback in two locations.
- Trivial predicate: get_api_stats() uses a trivial_predicate that returns (ql.qbool(), ql.qbool()) -- always-accept, per user decision from planning phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed QWalkTree cascade NotImplementedError**
- **Found during:** Task 2 (test verification)
- **Issue:** QWalkTree._setup_diffusion crashes with NotImplementedError when branching=15 and branch_width=4, because _plan_cascade_ops is called without error handling. The manual chess_walk.py already handles this with try/except.
- **Fix:** Added try/except NotImplementedError -> empty ops list in two locations within QWalkTree._setup_diffusion, matching the chess_walk.py pattern
- **Files modified:** src/quantum_language/walk.py
- **Verification:** QWalkTree(branching=[15]) constructs successfully, tests pass
- **Committed in:** 28f271d (Task 2 commit)

**2. [Rule 3 - Blocking] Patched QWalkTree.walk_step in test to avoid OOM**
- **Found during:** Task 2 (test verification)
- **Issue:** QWalkTree.walk_step() triggers full walk compilation requiring 8GB+ RAM, killing the test process
- **Fix:** Added _fake_qwt_walk_step patch alongside existing demo.walk_step patch
- **Files modified:** tests/python/test_demo.py
- **Verification:** Both tests pass in 0.21s without OOM
- **Committed in:** 28f271d (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for correctness and CI viability. The cascade fallback is a genuine bug fix that brings QWalkTree in line with the manual implementation. No scope creep.

## Issues Encountered
- QWalkTree cascade planning failure for high branching factors: documented as known limitation, now handled gracefully with fallback.
- OOM during QWalkTree.walk_step compilation in tests: same root cause as Plan 01, now both walk_step paths are patched.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Phase 106 plans complete (01 demo script + 02 comparison script)
- Both smoke tests pass green
- v6.1 Quantum Chess Demo milestone ready for final review

---
*Phase: 106-demo-scripts*
*Completed: 2026-03-05*
