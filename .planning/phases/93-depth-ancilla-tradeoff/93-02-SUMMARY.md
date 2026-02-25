---
phase: 93-depth-ancilla-tradeoff
plan: 02
subsystem: api
tags: [cython, c-backend, CLA, subtraction, twos-complement, tradeoff]

# Dependency graph
requires:
  - phase: 93-01
    provides: Tradeoff option API, C-level tradeoff_min_depth field, runtime CLA dispatch
provides:
  - Two's complement CLA subtraction in min_depth mode (QQ and CQ, uncontrolled and controlled)
  - Documented CLA subtraction limitation and approach in code comments and docstrings
  - Comprehensive test coverage for all tradeoff modes with addition and subtraction
affects: [phase-94]

# Tech tracking
tech-stack:
  added: []
  patterns: [twos-complement-cla-subtraction]

key-files:
  created: []
  modified:
    - c_backend/src/hot_path_add_toffoli.c
    - tests/python/test_tradeoff.py
    - src/quantum_language/_core.pyx

key-decisions:
  - "QQ two's complement: X(b) + CLA_add(a += ~b) + CQ_add(a += 1) + X(b) -- 3 steps with O(log n) depth"
  - "CQ two's complement: classical negation (2^width - value) + forward CLA add -- no X gates needed"
  - "Controlled paths use CX gates for bit flipping and controlled CQ/CLA sequences"
  - "Clifford+T hardcoded paths not modified -- they fall through to non-decomposed two's complement paths"

patterns-established:
  - "Two's complement subtraction via forward CLA: negate + add + correct"
  - "Classical negation for CQ paths avoids quantum X-gate overhead"

requirements-completed: [TRD-04, TRD-01, TRD-02]

# Metrics
duration: ~25min
completed: 2026-02-25
---

# Phase 93 Plan 02: CLA Subtraction Summary

**Two's complement CLA subtraction in min_depth mode for O(log n) depth subtraction, verified across all tradeoff modes**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 completed
- **Files modified:** 3

## Accomplishments
- Implemented two's complement CLA subtraction for QQ uncontrolled, QQ controlled, CQ uncontrolled, and CQ controlled paths
- Documented CLA subtraction limitation and two's complement approach in file header and option() docstring
- 27 total tests (6 new) covering CLA subtraction correctness, cross-mode equivalence, and comprehensive add/sub regression

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement two's complement CLA subtraction** - `3dd8074` (feat)
2. **Task 2: Add CLA subtraction tests and docstring documentation** - `a522178` (test)

## Files Created/Modified
- `c_backend/src/hot_path_add_toffoli.c` - Added 4 two's complement CLA subtraction blocks + file header documentation
- `tests/python/test_tradeoff.py` - Added TestCLASubtraction (3 tests) and TestTradeoffRegression (3 tests) classes
- `src/quantum_language/_core.pyx` - Extended option() docstring with tradeoff documentation

## Decisions Made
- Clifford+T hardcoded paths left unchanged -- they fall through to the non-decomposed two's complement paths (acceptable since Clifford+T is an optimization layer)
- Used classical negation for CQ paths to avoid quantum overhead of X gates
- Controlled QQ subtraction uses CX gates (controlled by control qubit) for bit flipping

## Deviations from Plan
None - plan executed as specified.

## Issues Encountered
- Initial build had stale .so import error (undefined symbol) -- fixed with `rm -rf build/` clean build

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 93 complete: all requirements (TRD-01 through TRD-04) satisfied
- Ready for Phase 94 or milestone completion

---
*Phase: 93-depth-ancilla-tradeoff*
*Plan: 02*
*Completed: 2026-02-25*
