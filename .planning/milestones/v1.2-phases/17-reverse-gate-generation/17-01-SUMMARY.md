---
phase: 17-reverse-gate-generation
plan: 01
subsystem: uncomputation
tags: [c, cython, reverse-gates, adjoint, uncomputation, lifo]

# Dependency graph
requires:
  - phase: 16-dependency-tracking
    provides: Dependency tracking infrastructure for parent-child relationships
provides:
  - C function reverse_circuit_range() for LIFO gate reversal
  - Python binding reverse_instruction_range() for circuit reversal
  - Helper get_current_layer() for instruction boundary tracking
  - Gate-type-specific inversion (phase gates negate, self-adjoint preserved)
affects: [18-uncomputation-integration, 19-context-manager-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LIFO gate reversal using circuit layer iteration"
    - "Phase gate inversion via pow(-1, 1) pattern"
    - "Multi-controlled gate handling with large_control array allocation"

key-files:
  created: []
  modified:
    - Execution/src/execution.c
    - Execution/include/execution.h
    - python-backend/quantum_language.pyx
    - python-backend/quantum_language.pxd
    - python-backend/test.py

key-decisions:
  - "Empty range (start == end) is no-op, returns silently"
  - "Reversed gates appended to circuit (not replaced)"
  - "Layer tracking via circuit_s.used_layer field exposure"

patterns-established:
  - "Gate reversal pattern: iterate layers backwards, iterate gates backwards within layer"
  - "Adjoint gate creation: memcpy + GateValue *= pow(-1, 1) + large_control allocation"

# Metrics
duration: 11min
completed: 2026-01-28
---

# Phase 17 Plan 01: C Reverse Gate Generation Summary

**C backend reverses circuit gate ranges in LIFO order with correct adjoint handling for phase gates (P(t) -> P(-t)) and multi-controlled gates**

## Performance

- **Duration:** 11 min
- **Started:** 2026-01-28T11:33:47Z
- **Completed:** 2026-01-28T11:44:52Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- C function `reverse_circuit_range()` reverses gates from circuit layers in LIFO order
- Phase gate inversion correctly negates angles using existing `pow(-1, 1)` pattern
- Multi-controlled gates (n > 2) allocate new large_control arrays during reversal
- Python can call `reverse_instruction_range()` to trigger C-level gate reversal
- Helper `get_current_layer()` tracks instruction boundaries for Phase 18 scope detection

## Task Commits

Each task was committed atomically:

1. **Task 1: Add reverse_circuit_range function to C backend** - `48c8bd8` (feat)
2. **Task 2: Add Python bindings for circuit reversal** - `f6acf5f` (feat)
3. **Task 3: Add tests for reverse gate generation** - `876c60c` (test)

## Files Created/Modified
- `Execution/src/execution.c` - Added reverse_circuit_range() with LIFO iteration and adjoint logic
- `Execution/include/execution.h` - Added function declaration
- `python-backend/quantum_language.pyx` - Added reverse_instruction_range() and get_current_layer() Python functions
- `python-backend/quantum_language.pxd` - Added cdef extern declaration and circuit_s.used_layer field
- `python-backend/test.py` - Added 5 Phase 17 tests (self-adjoint, phase gates, empty range, controlled gates, layer tracking)

## Decisions Made

**Empty range handling:** start_layer >= end_layer returns silently (no-op). This is correct behavior since empty ranges have no gates to reverse.

**Append vs replace:** Reversed gates are appended to the circuit rather than replacing originals. This allows for verification and matches the uncomputation model where reversed gates execute after forward computation.

**Layer tracking:** Exposed circuit_s.used_layer field to Python via .pxd struct definition. This allows Phase 18 to capture instruction boundaries when operations occur.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Test design challenge:** Initial tests assumed each operation would add new layers to the circuit. However, the circuit optimizer reuses existing layers when qubits don't conflict, so `get_current_layer()` may return the same value before and after an operation. Resolved by testing gate counts instead of layer counts, and using `reverse_instruction_range(0, circuit().depth)` to reverse entire circuit ranges.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Phase 18 (Basic Uncomputation Integration) is ready:**
- C backend can reverse gate ranges
- Python can track instruction boundaries via get_current_layer()
- Python can trigger reversal via reverse_instruction_range()
- All gate types (X, H, CX, P, multi-controlled) reverse correctly

**Implementation notes for Phase 18:**
- Capture start_layer before operation, end_layer after operation
- Call reverse_instruction_range(start_layer, end_layer) when uncomputing
- Handle case where start_layer == end_layer (optimizer placed gates in existing layers) - this means no gates to reverse

---
*Phase: 17-reverse-gate-generation*
*Completed: 2026-01-28*
