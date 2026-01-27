---
phase: 13-equality-comparison
plan: 01
subsystem: python-binding
tags: [cython, comparison, qbool, equality, CQ_equal_width]

# Dependency graph
requires:
  - phase: 12-comparison-function-refactoring
    provides: CQ_equal_width and cCQ_equal_width C functions with MCX support
provides:
  - qint == int comparison using C-level CQ_equal_width
  - qint == qint comparison using subtract-add-back pattern
  - Self-comparison optimization (a == a returns True directly)
  - Overflow handling for out-of-range classical values
affects: [13-inequality-comparison, 13-comparison-operators]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - n-controlled gate support via large_control array
    - get_control() helper pattern for accessing control qubits

key-files:
  created: []
  modified:
    - python-backend/quantum_language.pyx
    - python-backend/quantum_language.pxd
    - Backend/src/gate.c
    - Backend/src/optimizer.c
    - Execution/src/execution.c

key-decisions:
  - "Use subtract-add-back pattern for qint == qint to preserve operands"
  - "Return qbool(False) for overflow cases (value outside range)"
  - "Optimize self-comparison (a == a) to return True directly"

patterns-established:
  - "get_control() helper: Access control qubits via large_control when NumControls > 2"
  - "Overflow detection: Check seq.num_layer == 0 for C-layer overflow indication"

# Metrics
duration: 12min
completed: 2026-01-27
---

# Phase 13 Plan 01: Refactor qint.__eq__ Summary

**qint equality comparison refactored to use C-level CQ_equal_width for qint == int, subtract-add-back pattern for qint == qint, with n-controlled gate support across C backend**

## Performance

- **Duration:** 12 min
- **Started:** 2026-01-27T20:11:44Z
- **Completed:** 2026-01-27T20:23:44Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Refactored qint == int to use optimized C-level CQ_equal_width circuit
- Implemented qint == qint using subtract-add-back pattern (preserves both operands)
- Fixed n-controlled gate support across run_instruction, optimizer.c, and gate.c
- Self-comparison (a == a) optimized to return True directly

## Task Commits

All tasks completed in single commit (closely related changes):

1. **Task 1-3: Refactor __eq__ and fix n-controlled gates** - `e256996` (feat)

## Files Created/Modified

- `python-backend/quantum_language.pyx` - Refactored __eq__ method using CQ_equal_width
- `python-backend/quantum_language.pxd` - Added CQ_equal_width and cCQ_equal_width declarations, exposed sequence_t.num_layer
- `Backend/src/gate.c` - Added gate_get_control() helper for n-controlled gate support
- `Backend/src/optimizer.c` - Added get_control() helper, updated all functions to handle large_control
- `Execution/src/execution.c` - Updated run_instruction to map large_control arrays for MCX gates

## Decisions Made

- **DEC-13-01-01:** Use subtract-add-back pattern for qint == qint - preserves operands after comparison by subtracting, checking equality to zero, then adding back
- **DEC-13-01-02:** Return qbool(False) for overflow - when classical value doesn't fit in qint's bit width, result is definitely not equal
- **DEC-13-01-03:** Self-comparison optimization - `a == a` returns True directly without generating gates (identity)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] n-controlled gate support in run_instruction**
- **Found during:** Task 1 (Testing CQ_equal_width)
- **Issue:** run_instruction didn't handle large_control arrays for MCX gates with >2 controls, causing segfault
- **Fix:** Added large_control mapping in run_instruction - allocates new array and maps qubit indices
- **Files modified:** Execution/src/execution.c
- **Verification:** 3+ bit comparisons now work without segfault
- **Committed in:** e256996 (combined task commit)

**2. [Rule 1 - Bug] n-controlled gate support in optimizer.c**
- **Found during:** Task 1 (Testing CQ_equal_width)
- **Issue:** optimizer.c functions accessed Control[i] for i > 2, causing out-of-bounds access
- **Fix:** Added get_control() helper function, updated minimum_layer, merge_gates, apply_layer, append_gate, colliding_gates
- **Files modified:** Backend/src/optimizer.c
- **Verification:** All bit widths work correctly
- **Committed in:** e256996 (combined task commit)

**3. [Rule 1 - Bug] n-controlled gate support in gate.c (min_qubit/max_qubit)**
- **Found during:** Task 1 (Testing CQ_equal_width)
- **Issue:** min_qubit() and max_qubit() accessed Control[i] for i > 2, causing out-of-bounds access
- **Fix:** Added gate_get_control() helper function to handle large_control arrays
- **Files modified:** Backend/src/gate.c
- **Verification:** allocate_more_qubits now correctly tracks qubit usage for n-controlled gates
- **Committed in:** e256996 (combined task commit)

---

**Total deviations:** 3 auto-fixed (3 bugs - all related to n-controlled gate support)
**Impact on plan:** Auto-fixes were essential for n-controlled gates from Phase 12 to work correctly. This was a gap in Phase 12 that became apparent when Python bindings exercised the MCX gate path.

## Issues Encountered

- **Pre-existing multiplication segfault:** Multiplication tests (`test_qint_multiplication_qint_qint`, `test_qint_self_operations`) segfault at certain widths. This is documented in STATE.md as a known pre-existing issue unrelated to this phase.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Equality comparison (==) now uses optimized C-level circuits
- Inequality (!=) works correctly via ~(a == b) inversion
- Ready for further comparison operators if needed in future phases
- n-controlled gate support is now complete across the C backend

---
*Phase: 13-equality-comparison*
*Completed: 2026-01-27*
