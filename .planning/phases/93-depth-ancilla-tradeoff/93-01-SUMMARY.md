---
phase: 93-depth-ancilla-tradeoff
plan: 01
subsystem: api
tags: [cython, c-backend, circuit-options, CLA, CDKM, tradeoff]

# Dependency graph
requires:
  - phase: 71-cla-adder
    provides: CLA adder implementation and CLA_THRESHOLD dispatch in hot_path_add_toffoli.c
  - phase: 92-modular-arithmetic
    provides: Modular arithmetic with RCA-only constraint
provides:
  - ql.option('tradeoff', ...) API with auto/min_depth/min_qubits modes
  - Runtime CLA threshold dispatch replacing compile-time CLA_THRESHOLD
  - Set-once enforcement for tradeoff option after arithmetic operations
  - Modular arithmetic RCA forcing verified independent of tradeoff
affects: [93-02-PLAN, phase-94]

# Tech tracking
tech-stack:
  added: []
  patterns: [option-set-once-enforcement, runtime-c-field-dispatch]

key-files:
  created:
    - tests/python/test_tradeoff.py
  modified:
    - c_backend/include/circuit.h
    - c_backend/src/circuit_allocations.c
    - c_backend/src/hot_path_add_toffoli.c
    - src/quantum_language/_core.pxd
    - src/quantum_language/_core.pyx
    - src/quantum_language/qint_arithmetic.pxi
    - src/quantum_language/qint.pyx
    - src/quantum_language/qint_preprocessed.pyx

key-decisions:
  - "Auto-mode threshold set to 4 (CLA for width >= 4) based on Phase 71 empirical data"
  - "Set-once enforcement via _arithmetic_ops_performed flag in _core.pyx, frozen after any addition_inplace call"
  - "min_qubits uses cla_override=1 to force RCA; min_depth sets threshold=2 for CLA at all widths"
  - "Replaced compile-time CLA_THRESHOLD with runtime circ->tradeoff_auto_threshold in all 8 dispatch locations"

patterns-established:
  - "Option set-once pattern: module-level flag (_arithmetic_ops_performed) checked in option setter, set in arithmetic entry point"
  - "C-struct field dispatch: Python option() maps to circuit_t fields read by C hot path"

requirements-completed: [TRD-01, TRD-02, TRD-03]

# Metrics
duration: ~45min
completed: 2026-02-25
---

# Phase 93 Plan 01: Tradeoff Option API Summary

**Runtime CLA/CDKM dispatch via ql.option('tradeoff') with auto/min_depth/min_qubits modes, set-once enforcement, and modular RCA forcing verification**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3 completed
- **Files modified:** 8 (+ 1 created)

## Accomplishments
- Added `tradeoff_auto_threshold` and `tradeoff_min_depth` fields to circuit_t C struct with runtime dispatch replacing compile-time CLA_THRESHOLD
- Implemented `ql.option('tradeoff', ...)` API supporting auto, min_depth, min_qubits modes with validation and set-once enforcement
- Verified modular arithmetic always uses RCA path regardless of tradeoff setting (identical QASM and qubit counts across all modes)
- 21 tests covering option API, frozen state, dispatch modes, correctness via simulation, and modular RCA forcing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add tradeoff fields to C struct and runtime CLA dispatch** - `8cf542e` (feat)
2. **Task 2: Implement tradeoff option API with set-once enforcement** - `93d2224` (feat)
3. **Task 3: Write tradeoff tests** - `a0f3ccb` (test)

## Files Created/Modified
- `c_backend/include/circuit.h` - Added tradeoff_auto_threshold and tradeoff_min_depth fields to circuit_t
- `c_backend/src/circuit_allocations.c` - Initialize new fields (threshold=4, min_depth=0)
- `c_backend/src/hot_path_add_toffoli.c` - All 8 CLA dispatch locations use circ->tradeoff_auto_threshold
- `src/quantum_language/_core.pxd` - Cython declarations for new circuit_t fields
- `src/quantum_language/_core.pyx` - Tradeoff option handler, state variables, circuit reset logic
- `src/quantum_language/qint_arithmetic.pxi` - _mark_arithmetic_performed() call in addition_inplace
- `src/quantum_language/qint.pyx` - Import _mark_arithmetic_performed from _core
- `src/quantum_language/qint_preprocessed.pyx` - Synced from qint.pyx + .pxi includes
- `tests/python/test_tradeoff.py` - 21 tests for TRD-01, TRD-02, TRD-03

## Decisions Made
- Auto-mode threshold of 4 based on Phase 71 research (CLA depth benefit minimal below width 4)
- Used inline cast expressions in option() instead of cdef variables (Cython constraint: cdef not allowed after Python statements in same scope)
- Set-once enforcement at Python level via global flag rather than C level (simpler, circuit reset handles cleanup)
- Modular arithmetic test uses peak_allocated comparison rather than simulation (avoids complex qint_mod register layout extraction)

## Deviations from Plan

### Auto-fixed Issues

**1. qint_preprocessed.pyx is generated, not source-of-truth**
- **Found during:** Task 2 (implementing _mark_arithmetic_performed call)
- **Issue:** Direct edits to qint_preprocessed.pyx were overwritten by pre-commit sync hook
- **Fix:** Edited source files (qint_arithmetic.pxi + qint.pyx), then ran build_preprocessor.py --sync-and-stage
- **Verification:** _mark_arithmetic_performed() correctly called after sync

**2. Cython cdef constraint in option() function**
- **Found during:** Task 2 (adding tradeoff case to option())
- **Issue:** `cdef circuit_s *circ = ...` not allowed after global/if/raise Python statements
- **Fix:** Used inline cast expressions on each line instead of declaring a cdef variable
- **Verification:** Build succeeds, option() correctly sets C-level fields

---

**Total deviations:** 2 auto-fixed (both blocking issues)
**Impact on plan:** Both fixes necessary for correct compilation and code generation pipeline. No scope creep.

## Issues Encountered
- OOM kills during full test suite run (1163 tests) due to memory constraints; verified regressions via targeted test subsets (CLA, Clifford+T, arithmetic, qint operations all pass)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Tradeoff API foundation complete; Plan 93-02 can proceed with CLA subtraction via two's complement
- `tradeoff_min_depth` field already in place for Plan 93-02 to use
- Test infrastructure established in test_tradeoff.py for extending with subtraction tests

---
*Phase: 93-depth-ancilla-tradeoff*
*Plan: 01*
*Completed: 2026-02-25*
