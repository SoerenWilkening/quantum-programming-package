---
phase: 113-diffusion-redesign-move-enumeration
plan: 02
subsystem: quantum-walk
tags: [qarray, qint, diffusion, counting-circuit, walk]

requires:
  - phase: 112-numpy-qubit-sets
    provides: numpy-based qubit operations used by walk infrastructure
provides:
  - counting-based variable diffusion replacing O(2^d_max) combinatorial code
  - _counting_diffusion method on QWalkTree
affects: [113-03, chess-walk-integration]

tech-stack:
  added: []
  patterns: [counting-circuit-diffusion, qarray-sum-popcount, qint-equality-dispatch]

key-files:
  created:
    - tests/python/test_counting_diffusion.py
  modified:
    - src/quantum_language/walk.py

key-decisions:
  - "Used qarray.sum() for validity bit popcount into count register"
  - "Dispatch via qint.__eq__ comparison loop instead of itertools.combinations enumeration"
  - "Used _emit_multi_controlled_ry with explicit control qubit lists to avoid nested with qbool limitation"
  - "Count register width = ceil(log2(d_max + 1))"

patterns-established:
  - "Counting circuit pattern: sum validity bits → compare count → controlled rotations"
  - "Multi-control dispatch: pass [h_qubit, cond_qubit, validity_qubit] as ctrl_qubits list"

requirements-completed: [WALK-03]

duration: 8min
completed: 2026-03-08
---

# Plan 113-02: Counting-Based Diffusion Summary

**O(d_max) counting diffusion replaces O(2^d_max) combinatorial enumeration using qarray.sum() popcount and qint == dispatch**

## Performance

- **Duration:** ~8 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented `_counting_diffusion()` on QWalkTree with O(d_max) gate complexity
- Verified statevector equivalence with old combinatorial code on d_max=2,3
- Verified D_x^2 = I reflection property holds
- Confirmed gate count scales linearly (not exponentially) with d_max
- Removed legacy `_variable_diffusion_legacy` and `import itertools` after regression pass
- All 79 walk/chess/counting tests pass

## Task Commits

1. **Task 1: Create counting diffusion test scaffold and implement _counting_diffusion** - `9b16766` (feat)
2. **Task 2: Regression and legacy cleanup** - `1588338` (refactor)

## Files Created/Modified
- `tests/python/test_counting_diffusion.py` - 8 tests: equivalence d2/d3, d4 state modification, reflection d2/d3, norm preservation, state modification, gate count linearity
- `src/quantum_language/walk.py` - Added `_counting_diffusion()`, removed legacy `_variable_diffusion_legacy` and `import itertools`

## Decisions Made
- Used qarray.sum() with width parameter for popcount — worked directly with qbool elements
- Count register uncomputed by reversing the sum additions (subtracting validity bits in reverse)
- Explicit control qubit lists passed to _emit_multi_controlled_ry to avoid nested with qbool contexts

## Deviations from Plan
None - plan executed as written.

## Issues Encountered
- Agent hit OAuth token expiration mid-execution — Task 1 completed, Task 2 finished manually by orchestrator

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `_counting_diffusion()` in walk.py ready for chess_walk.py integration (Plan 113-03)
- All regression tests green

---
*Plan: 113-02-counting-diffusion*
*Completed: 2026-03-08*
