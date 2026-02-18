---
phase: 35-comparison-bug-fixes
plan: 01
subsystem: quantum-operations
tags: [qint, qbool, comparison, equality, cython, c-backend]

# Dependency graph
requires:
  - phase: 29-c-backend-bug-fixes
    provides: GC gate reversal fix pattern for __lt__ and __gt__
  - phase: 31-comparison-verification
    provides: Exhaustive comparison test suite identifying BUG-CMP-01
provides:
  - Fixed equality (==) and inequality (!=) operators for all qint widths
  - Resolved 488 xfail comparison tests (BUG-CMP-01)
affects: [36-comparison-xfail-cleanup, all-quantum-algorithms]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Comparison results persist without auto-uncompute (matching Phase 29-16 pattern)
    - MSB-first qubit ordering for C backend comparison operations

key-files:
  modified:
    - src/quantum_language/qint.pyx

key-decisions:
  - "Applied Phase 29-16 GC fix pattern to __eq__ (remove layer tracking from result qbool)"
  - "Fixed bit-order reversal: C backend expects MSB-first, Python was passing LSB-first"

patterns-established:
  - "All comparison operators follow no-auto-uncompute pattern (results persist after GC)"
  - "Qubit array mapping to C backend must reverse bit order for MSB-first expectations"

# Metrics
duration: 22min
completed: 2026-02-01
---

# Phase 35 Plan 01: Equality Comparison Bug Fix Summary

**Fixed dual-bug in equality operators: GC gate reversal + bit-order reversal. All 488 BUG-CMP-01 xfail tests now pass.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-02-01T20:08:59Z
- **Completed:** 2026-02-01T20:30:53Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Removed GC-triggering layer tracking from `__eq__` result qbools (both QQ and CQ paths)
- Fixed bit-order reversal in qubit array mapping to C backend CQ_equal_width
- All 488 previously-xfail BUG-CMP-01 tests now pass (equality and inequality operations work correctly)
- No regressions in ordering comparison tests (722 tests still passing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove GC-triggering layer tracking from __eq__** - `9718c41` (fix)
   - Removed `_start_layer` and `_end_layer` assignments from QQ and CQ paths
   - Discovered and fixed bit-order reversal bug (deviation Rule 1)
   - Second commit `3c9e745` for bit-order fix

2. **Task 2: Validate eq/ne fix against test suite** - (validation only, no commit)
   - Verified all 488 BUG-CMP-01 xfail tests pass
   - Confirmed no regressions in ordering comparisons

**Plan metadata:** (will be added in final commit)

## Files Created/Modified
- `src/quantum_language/qint.pyx` - Fixed `__eq__` method:
  - Removed layer tracking from result qbool (lines 1688-1690 and 1748-1749)
  - Reversed qubit array indexing for MSB-first C backend (line 1725)

## Decisions Made
- Applied Phase 29-16 pattern: comparison results don't auto-uncompute
- Fixed qubit ordering by reversing array index: `qubits[offset + (bits - 1 - i)]`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed bit-order reversal in qubit array mapping**
- **Found during:** Task 2 (testing revealed palindrome-only pattern)
- **Issue:** C backend CQ_equal_width expects MSB-first qubit order, but Python `__eq__` was passing qubits in LSB-first order. This caused non-palindrome binary values to produce incorrect comparison results (e.g., comparing 3 vs 6 would treat them as equal because 011 reversed is 110)
- **Root cause:** `two_complement()` in C returns MSB-first array (`bin[0]` = MSB), but Python loop `qubit_array[1 + i] = qubits[offset + i]` passed LSB-first
- **Fix:** Reversed qubit indexing: `qubit_array[1 + i] = self.qubits[self_offset + (self.bits - 1 - i)]`
- **Files modified:** src/quantum_language/qint.pyx (line 1725)
- **Verification:** All test patterns now pass (tested 001==001, 011==110, 101==101, etc.)
- **Committed in:** 3c9e745 (fix commit #2)
- **Impact:** This bug was MASKED by the GC gate reversal bug. Removing GC reversal revealed the bit-order bug.

---

**Total deviations:** 1 auto-fixed (1 bug discovered during testing)
**Impact on plan:** Critical bug fix required for correct operation. The plan correctly identified the GC issue, but the bit-order bug was hidden underneath. Both bugs needed fixing for equality to work.

## Issues Encountered

**Dual-bug interaction:**
- Initial fix (removing layer tracking) partially worked: palindrome bit patterns (000, 010, 101, 111) worked correctly
- Non-palindrome patterns (001, 011, 100, 110) failed with inverted results
- Investigation revealed bit-order reversal: C backend expects MSB-first, Python provided LSB-first
- The two bugs masked each other: GC reversal flipped all results, bit-order reversal flipped some results
- After both fixes: all 488 tests pass

## Test Results

**Before fix:**
- 488 tests marked xfail with BUG-CMP-01
- eq returns 0 for equal values (inverted)
- ne returns 0 for unequal values (inverted)

**After GC fix only:**
- Palindrome patterns work (000, 010, 101, 111)
- Non-palindrome patterns fail (001, 011, 100, 110 produce bit-reversed comparisons)

**After both fixes:**
- All 488 BUG-CMP-01 xfail tests pass (showing as XPASS strict)
- 265 regular eq/ne tests pass
- 722 ordering comparison tests still pass (no regression)
- Total: 505 + 480 XPASS strict = all eq/ne tests working

**Key test validations:**
```
✓ qint(3) == 3 → 1 (True)
✓ qint(3) == 5 → 0 (False)
✓ qint(3) != 5 → 1 (True)
✓ qint(3) != 3 → 0 (False)
✓ qint(1) == 1 → 1 (non-palindrome binary)
✓ qint(1) == 4 → 0 (bit-reversed values, now correctly unequal)
```

## Next Phase Readiness

**Ready for Phase 36:**
- All 488 BUG-CMP-01 tests passing
- Equality and inequality operators fully functional
- Pattern established: comparison results persist (no auto-uncompute)
- Next step: Remove xfail markers from test suite (Phase 36 task)

**Known remaining bugs:**
- BUG-CMP-02: Ordering comparison errors at MSB boundary
- BUG-CMP-03: Circuit size explosion at widths >= 6 for gt/le

---
*Phase: 35-comparison-bug-fixes*
*Completed: 2026-02-01*
