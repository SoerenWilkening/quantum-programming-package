---
phase: 06-bit-operations
plan: 03
subsystem: frontend
tags: [python, cython, bitwise, operator-overloading, qint]

# Dependency graph
requires:
  - phase: 06-01
    provides: Q_not, cQ_not, Q_xor, cQ_xor C implementations
  - phase: 06-02
    provides: Q_and, CQ_and, Q_or, CQ_or C implementations
provides:
  - "qint.__and__(other) for bitwise AND"
  - "qint.__or__(other) for bitwise OR"
  - "qint.__xor__(other) for bitwise XOR"
  - "qint.__invert__() for bitwise NOT"
  - "Augmented assignment operators (&=, |=, ^=)"
affects: [06-04 test suite, future phases using bitwise ops]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bitwise ops return qint with max(width_a, width_b)"
    - "In-place ops use qubit reference swap pattern"
    - "Classical-quantum ops use CQ_ functions with value parameter"

key-files:
  created: []
  modified:
    - python-backend/quantum_language.pxd
    - python-backend/quantum_language.pyx
    - tests/python/test_qbool_operations.py

key-decisions:
  - "Bitwise ops return qint (not qbool) with max width of operands"
  - "In-place ops swap qubit references rather than copy"
  - "Classical XOR implemented via individual X gates (no CQ_xor)"

patterns-established:
  - "Operator methods check for qint, qbool, or int type"
  - "Right-aligned qubit extraction for variable-width"
  - "NotImplementedError for unsupported controlled variants"

# Metrics
duration: 7min
completed: 2026-01-26
---

# Phase 6 Plan 03: Python Bitwise Operations Summary

**Python operator overloading for bitwise ops (&, |, ^, ~) with variable-width qint support**

## Performance

- **Duration:** 7 min
- **Started:** 2026-01-26T16:41:03Z
- **Completed:** 2026-01-26T16:48:26Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added Cython declarations for all 8 width-parameterized bitwise C functions
- Implemented `__and__`, `__iand__`, `__rand__` for qint-qint and qint-int AND
- Implemented `__or__`, `__ior__`, `__ror__` for qint-qint and qint-int OR
- Implemented `__xor__`, `__ixor__`, `__rxor__` for qint-qint and qint-int XOR
- Updated `__invert__` to use width-parameterized Q_not/cQ_not
- All operations support variable-width (1-64 bits)
- Mixed-width operations return result with max(width_a, width_b)

## Task Commits

Each task was committed atomically:

1. **Task 1: Cython declarations** - `f921d58`
2. **Task 2: AND operators** - `dba45e3`
3. **Task 3: OR, XOR, NOT operators** - `f2b87de`
4. **Test updates** - `2e1b97b`

## Files Created/Modified

- `python-backend/quantum_language.pxd` - Added int64_t import and 8 function declarations
- `python-backend/quantum_language.pyx` - Implemented all bitwise operator methods
- `tests/python/test_qbool_operations.py` - Updated for new return type semantics

## Decisions Made

1. **Return qint, not qbool**: Bitwise operations now return qint with width = max(operand widths). This is the correct semantics for multi-bit integers (was previously returning qbool which only captured single-bit result).

2. **In-place swap pattern**: `__iand__`, `__ior__` allocate new result then swap qubit references with self, maintaining Python variable binding semantics.

3. **Classical XOR via X gates**: Since CQ_xor is not exposed, classical XOR is implemented by applying individual X gates for each 1 bit in the classical value. This works but is less efficient than a dedicated CQ_xor.

4. **NotImplementedError for controlled ops**: Controlled variants (using `with ctrl:` context manager) raise NotImplementedError for now since controlled bitwise ops are not yet implemented in C layer.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertions expecting qbool return type**
- **Found during:** Verification phase
- **Issue:** Old tests expected `qint & qint` to return `qbool`, but this was incorrect behavior
- **Fix:** Updated tests to expect `qint` with correct width property
- **Files modified:** tests/python/test_qbool_operations.py
- **Commit:** 2e1b97b

## Issues Encountered

- Large-width operations (8+ bits) can be slow due to circuit complexity
- This is expected behavior, not a bug - the circuits grow exponentially with width

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All Python bitwise operators implemented and tested
- Ready for 06-04 (Bitwise operations test suite)
- 125 tests pass including updated behavioral tests

---
*Phase: 06-bit-operations*
*Completed: 2026-01-26*
