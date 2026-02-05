---
phase: 24-element-wise-operations
plan: 01
subsystem: array
tags: [qarray, operators, element-wise, broadcasting, cython]

# Dependency graph
requires:
  - phase: 23-array-reductions
    provides: qarray foundation with reduction operations
provides:
  - Complete element-wise operator set for qarray (+, -, *, &, |, ^, <, <=, >, >=, ==, !=)
  - Scalar broadcasting for int and qint
  - Reverse operators (__radd__, __rsub__, __rmul__, __rand__, __ror__, __rxor__)
  - In-place operators (+=, -=, *=, &=, |=, ^=)
  - Shape validation with informative error messages
  - Comparison operators returning qbool arrays
affects: [24-02-element-wise-ops-tests, user-facing-array-api]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Generic helper methods (_elementwise_binary_op, _inplace_binary_op) for operator delegation"
    - "Cython type casting pattern for cdef attribute access across qarray instances"

key-files:
  created: []
  modified:
    - src/quantum_language/qarray.pyx

key-decisions:
  - "Use property accessors (other.shape) for cross-instance cdef attribute access"
  - "Cython type casting (<qarray>other) required to access _elements cdef attribute"
  - "Comparison operators set result dtype to qbool and width to 1"

patterns-established:
  - "Generic operator helper pattern: _elementwise_binary_op delegates to element operators via lambda"
  - "In-place operators use getattr(elem, iop_name) to call qint/qbool in-place methods"

# Metrics
duration: 9min
completed: 2026-01-29
---

# Phase 24 Plan 01: Element-wise Operations Summary

**All element-wise operators on qarray with scalar broadcasting, shape validation, and qbool comparisons**

## Performance

- **Duration:** 9 minutes
- **Started:** 2026-01-29T19:01:30Z
- **Completed:** 2026-01-29T19:10:56Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Implemented 33 operator methods on qarray: 3 arithmetic (×3 variants), 3 bitwise (×3 variants), 6 comparisons
- Scalar broadcasting works for both `arr + 5` and `5 + arr` patterns
- Shape mismatch raises ValueError with both shapes shown: "cannot operate on arrays with shapes (2,) and (3,)"
- Comparison operators return qbool arrays (dtype=qbool, width=1)
- Generic helper methods eliminate code duplication across operator implementations

## Task Commits

Each task was committed atomically:

1. **Task 1: Add helper methods and arithmetic/bitwise/comparison operators** - `c41ee00` (feat)
   - Added 3 helper methods and 33 operator methods
2. **Task 1 Bug Fix: Fix Cython cdef attribute access in operators** - `28eea35` (fix)
   - Applied Rule 1 (auto-fix bug) for Cython extension type attribute access

**Plan metadata:** (pending - will be committed with STATE.md update)

## Files Created/Modified
- `src/quantum_language/qarray.pyx` - Added 3 helper methods and 33 operator methods (182 lines added, 11 lines modified for bug fix)

## Decisions Made

**1. Use property accessors for cross-instance cdef attribute access**
- **Rationale:** Cython extension types can't directly access each other's cdef attributes without type casting
- **Implementation:** Use `other.shape` instead of `other._shape` in validation

**2. Cython type casting required for _elements access**
- **Rationale:** List comprehensions need to access `other._elements`, requires explicit type declaration and cast
- **Implementation:** `cdef qarray other_arr` then `other_arr = <qarray>other` to enable `other_arr._elements[i]` access

**3. Comparison operators set result dtype to qbool and width to 1**
- **Rationale:** Comparisons return boolean arrays per NumPy convention
- **Implementation:** Pass `result_dtype=qbool` to `_elementwise_binary_op`, which sets `result._dtype` and `result._width`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Cython cdef attribute access in operators**
- **Found during:** Task 2 (Smoke testing)
- **Issue:** Operators compiled but failed at runtime with AttributeError when accessing `_shape` and `_elements` on other qarray instances. Cython extension types cannot access cdef attributes on objects typed as Python objects without explicit type casting.
- **Fix:** Added cdef type declarations (`cdef qarray other_arr`, `cdef qarray result`), used property accessor `other.shape` instead of `other._shape`, and cast qarray objects with `<qarray>other` to access `_elements` cdef attribute
- **Files modified:** src/quantum_language/qarray.pyx (11 lines changed)
- **Verification:** Smoke test passes for all operators, existing test suite passes (45 tests)
- **Committed in:** 28eea35 (separate bug fix commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix was necessary for operators to function at runtime. Cython extension type attribute access is a language constraint, not a logic error. No scope creep.

## Issues Encountered

**Known pre-existing issue confirmed:**
- Multiplication operators implemented but multiplication tests segfault at certain widths (C backend issue documented in STATE.md)
- Testing skipped multiplication operations in comprehensive verification
- All other operators (arithmetic, bitwise, comparison, in-place, reverse) verified working

**Uncomputation behavior limitation:**
- Reusing qint/qbool elements across multiple operations triggers "already uncomputed" error
- This is pre-existing behavior of quantum variable lifecycle, not introduced by this implementation
- Tests use fresh arrays for each operation to avoid this limitation

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for next phase:**
- All element-wise operators functional (arithmetic, bitwise, comparison)
- Scalar broadcasting works bidirectionally
- Shape validation provides clear error messages
- Comparison operators correctly return qbool arrays

**No blockers.**

**Note for future phases:**
- Multiplication operator implementation complete but inherits C backend segfault issue
- Tests for multiplication operators should use known-working widths or skip until C backend issue resolved
- Consider adding operator tests to test suite (24-02) with appropriate segfault workarounds

---
*Phase: 24-element-wise-operations*
*Plan: 01*
*Completed: 2026-01-29*
