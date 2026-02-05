---
phase: 49-optimization-uncomputation
plan: 01
subsystem: compiler
tags: [gate-optimization, compile-decorator, adjacent-cancellation, rotation-merge]

# Dependency graph
requires:
  - phase: 48-core-capture-replay
    provides: "@ql.compile decorator with capture, cache, replay"
provides:
  - "_optimize_gate_list multi-pass adjacent cancellation and rotation merge"
  - "optimize parameter on @ql.compile decorator"
  - "CompiledFunc stats: original_gates, optimized_gates, reduction_percent"
affects: [49-02-uncomputation, 50-controlled-context, 51-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-pass peephole optimiser with configurable enable/disable"
    - "Silent fallback on optimiser error (no circuit corruption)"

key-files:
  created: []
  modified:
    - "src/quantum_language/compile.py"
    - "tests/test_compile.py"

key-decisions:
  - "Gate type constants mirror C enum values (X=0..M=9) for compatibility"
  - "Optimiser uses simple adjacent-pair scanning, not commutation analysis"
  - "Silent fallback on optimiser error to preserve correctness"
  - "Stats are summed across all cache entries (not per-entry)"

patterns-established:
  - "Peephole gate optimiser: cancel self-adjoint pairs, merge rotation angles"
  - "optimize=True default, opt-out with optimize=False"

# Metrics
duration: 6min
completed: 2026-02-04
---

# Phase 49 Plan 01: Gate List Optimization Summary

**Multi-pass peephole gate optimiser cancelling adjacent inverse gates and merging consecutive rotations, wired into @ql.compile capture flow with optimize parameter and stats API**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-04T14:54:16Z
- **Completed:** 2026-02-04T14:59:49Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented _optimize_gate_list with multi-pass adjacent cancellation and rotation merge
- Added optimize parameter to @ql.compile decorator (True by default, opt-out with False)
- Added stats properties: original_gates, optimized_gates, reduction_percent on CompiledFunc
- 9 new tests covering cancellation, merge, stats, opt-out, replay correctness, and edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement gate list optimizer and wire into capture flow** - `f7662fe` (feat)
2. **Task 2: Add optimization tests** - `d54974c` (test)

## Files Created/Modified
- `src/quantum_language/compile.py` - Added _gates_cancel, _gates_merge, _merged_gate, _optimize_gate_list functions; optimize parameter; stats properties
- `tests/test_compile.py` - 9 new optimization tests (31 total, all passing)

## Decisions Made
- Gate type constants (X=0 through M=9) defined as module-level ints matching the C enum Standardgate_t for zero-cost comparison
- Optimiser uses simple adjacent-pair scanning rather than commutation-aware rewriting -- sufficient for the peephole patterns and avoids complexity
- Silent fallback on optimiser error (try/except pass) per CONTEXT.md guidance to never corrupt circuits
- Stats properties sum across all cache entries so multi-key functions report aggregate reduction

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Real QFT addition sequences (e.g., `x += 1; x += 1`) produce no adjacent cancellable gates because the C backend already handles QFT/iQFT pairing -- this means the optimiser primarily benefits user-constructed sequences or future gate patterns. Tests use both synthetic gate lists and integration tests to cover the optimiser thoroughly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Gate optimiser is ready; 49-02 (uncomputation integration) can proceed
- All 31 compile tests pass with no regressions
- optimize=False provides escape hatch if optimiser causes issues in future patterns

---
*Phase: 49-optimization-uncomputation*
*Completed: 2026-02-04*
