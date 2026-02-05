---
phase: 29-c-backend-bug-fixes
plan: 10
subsystem: c-backend
tags: [qft, draper-adder, cq-add, qubit-convention, bit-ordering]

# Dependency graph
requires:
  - phase: 29-03
    provides: "CQ_add rotation formula fix (bin[bits-1-bit_idx] reversal)"
provides:
  - "CQ_add and cCQ_add produce correct addition results for all tested inputs"
  - "Qubit convention fix: qubit_array reversal + rotation reversal compensates for QFT-no-swaps"
affects: [29-subtraction-fixes, 29-comparison-fixes, 30-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "QFT-no-swaps compensation: reverse qubit_array in Python + reverse rotation mapping in C"

key-files:
  created:
    - "tests/bugfix/test_cq_add_isolated.py"
  modified:
    - "c_backend/src/IntegerAddition.c"
    - "src/quantum_language/qint.pyx"

key-decisions:
  - "Two-part fix: qubit_array reversal in Python + rotation reversal in C (not single-layer fix)"
  - "Path taken: convention fix, not BUG-05 cache — isolation test confirmed 0+1 fails in fresh process"
  - "Fix applied to both CQ_add and cCQ_add (4 code locations total)"

patterns-established:
  - "QFT-no-swaps convention: always reverse qubit_array before CQ_add/cCQ_add to compensate for missing swap gates"

# Metrics
duration: 45min
completed: 2026-01-31
---

# Phase 29 Plan 10: CQ_add Convention Fix Summary

**Fixed CQ_add qubit convention mismatch: two-part fix (qubit_array reversal + rotation reversal) compensates for QFT-no-swaps bit ordering, producing correct Draper addition for all tested inputs**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-01-31T10:15:00Z
- **Completed:** 2026-01-31T11:02:52Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- Diagnosed root cause: QFT without swap gates treats qubit 0 as MSB in Fourier domain, but qubits stored LSB-first
- Implemented two-part fix: Python qubit_array reversal + C rotation reversal together implement the missing QFT swaps
- All 7 QFT addition tests pass individually AND in combined multi-test run (0+1=1, 3+5=8, 8+8=0 overflow)
- Created isolation test confirming this is a genuine convention bug, not BUG-05 cache pollution

## Task Commits

Each task was committed atomically:

1. **Task 1: Create isolated diagnostic test and fix CQ_add convention** - `0f5ff3a` (fix)

## Files Created/Modified
- `tests/bugfix/test_cq_add_isolated.py` - Isolation test for 0+1 in fresh process (diagnosis tool)
- `c_backend/src/IntegerAddition.c` - Reversed rotation-to-qubit mapping in CQ_add and cCQ_add (4 locations: 2 cache paths + 2 build paths)
- `src/quantum_language/qint.pyx` - Added qubit_array reversal before CQ_add/cCQ_add calls in addition_inplace()

## Decisions Made
- **Two-part fix approach:** The QFT-no-swaps convention requires compensating at both the qubit mapping level (Python) and the rotation assignment level (C). Neither fix alone produces correct results — both are necessary.
- **Path taken: convention fix (not BUG-05 cache).** The isolation test (`test_cq_add_isolated.py`) showed 0+1 fails even in a fresh process with no prior quantum operations, definitively ruling out cache pollution as the cause.
- **Fix applied to CQ_add and cCQ_add only.** QQ_add (quantum-quantum addition) has a separate implementation with different qubit mapping and was not modified (separate bug, separate plan).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] qint_arithmetic.pxi is unused — actual code is in qint.pyx**
- **Found during:** Task 1 (initial implementation attempt)
- **Issue:** The plan referenced `src/quantum_language/qint_arithmetic.pxi` as the Python file to modify, but the arithmetic methods are actually defined directly in `qint.pyx`. The .pxi file is an unused duplicate.
- **Fix:** Applied the qubit_array reversal to `qint.pyx` instead of the .pxi file
- **Files modified:** `src/quantum_language/qint.pyx`
- **Verification:** Confirmed the .pxi file has no `include` reference in qint.pyx
- **Committed in:** `0f5ff3a`

**2. [Rule 1 - Bug] Cython cdef placement restriction**
- **Found during:** Task 1 (Cython compilation)
- **Issue:** Initial implementation placed `cdef int j_rev` and `cdef unsigned int tmp_rev` inside an if block, which Cython disallows
- **Fix:** Moved cdef declarations to the top of the `addition_inplace()` function
- **Files modified:** `src/quantum_language/qint.pyx`
- **Committed in:** `0f5ff3a`

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correct implementation. No scope creep.

## Issues Encountered
- **Linter auto-reverting IntegerAddition.c:** The clang-format pre-commit hook reformatted the C file. This was handled by re-staging after formatting and committing.
- **Build cache stale after .pxi changes:** Cython doesn't detect changes to .pxi include files. Required `rm -f src/quantum_language/qint.c` to force recompilation. Ultimately moot since the code was in qint.pyx directly.
- **Extensive investigation required:** The plan's two execution paths (BUG-05 cache vs convention fix) were both partially correct conceptually, but the actual fix required a combination approach (qubit reversal + rotation reversal) not fully described in either path. Verified correct approach via exhaustive Qiskit simulation of all 4-bit addition pairs.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CQ_add (qint += int) now produces correct results for all tested cases
- Subtraction (qint -= int) uses the same code path with `invert=True` and should benefit from this fix
- QQ_add (qint += qint) is NOT fixed by this plan — it has a separate qubit convention issue
- BUG-05 (circuit() reset) remains unresolved and causes memory explosion in multi-operation tests

---
*Phase: 29-c-backend-bug-fixes*
*Completed: 2026-01-31*
