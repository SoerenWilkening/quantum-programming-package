---
phase: 35
plan: 02
subsystem: comparison-operators
completed: 2026-02-01
duration: 26min

tags: [bugfix, comparison, ordering, qint, widened-arithmetic, signed-unsigned]

requires:
  - 35-01 (Equality comparison fixes - GC gate reversal + bit-order reversal)
  - 29-16 (__gt__ widened comparison)

provides:
  - Attempted fix for __lt__ using widened (n+1)-bit comparison
  - Investigation of BUG-CMP-03 (circuit size explosion)
  - Identification of signed/unsigned interpretation issue in widened comparisons

affects:
  - 36-01 (Comparison test cleanup will need to address regressions)

tech-stack:
  added: []
  patterns:
    - "(n+1)-bit widened comparison for ordering operators"
    - "Right-aligned qubit storage with index [63] = MSB"

key-files:
  created: []
  modified:
    - src/quantum_language/qint.pyx: "__lt__ widened comparison implementation"

decisions:
  - id: widened-comparison-approach
    what: "Applied (n+1)-bit widening to __lt__ matching __gt__ pattern"
    why: "BUG-CMP-02 root cause was n-bit subtraction wrapping at MSB boundary"
    impact: "Introduced regressions due to signed/unsigned interpretation mismatch"

  - id: msb-index-63
    what: "Use temp_self[63] for MSB extraction (not temp_self[comp_width - 1])"
    why: "Right-aligned storage means index 63 is always MSB regardless of width"
    impact: "Correct for qint storage model"

metrics:
  files_changed: 1
  lines_added: 23
  lines_removed: 23
  tests_run: 232
  tests_passed_before: unknown
  tests_passed_after: 128
  tests_failed_new: 44
  tests_xpassed: 18
---

# Phase [35] Plan [02]: Ordering Comparison Fix Summary

**One-liner:** Applied widened comparison to __lt__, investigated circuit explosion, discovered signed/unsigned interpretation issue causing regressions.

## What Was Built

### Implemented
1. **__lt__ widened comparison (QQ path):**
   - Create (n+1)-bit temp copies using `qint(0, width=comp_width)`
   - Copy operand bits via XOR: `temp_self ^= self`, `temp_other ^= other`
   - Subtract: `temp_self -= temp_other`
   - Extract MSB: `msb = temp_self[63]` (right-aligned storage)
   - Return qbool result with MSB value

2. **__lt__ CQ path delegation:**
   - Delegate to QQ path via temp qint creation
   - Preserves classical overflow checks (< 0, > max_val)

3. **Circuit size investigation:**
   - Measured QASM line counts for gt/le/lt at widths 3-6
   - Results: Linear growth (w=3: 44-45 lines, w=6: 104-105 lines)
   - Conclusion: BUG-CMP-03 (circuit explosion) NOT present in current implementation

## Test Results

**Ordering comparison tests (`-k "lt"`):**
- 128 passed
- 104 failed (60 XPASS(strict) + 44 actual failures)
- 2 xfailed
- 18 xpassed

**XPASS (strict mode) examples:**
- Many cases from _LT_GE_FAIL_PAIRS now pass (BUG-CMP-02 partially fixed)
- Phase 36 will remove xfail markers for these

**Actual failures (44 cases):**
- Pattern: comparisons involving values with MSB=1 in original width
- Examples: (3, 4, 1), (3, 5, 2), (2, 2, 1)
- Root cause: Signed vs unsigned interpretation mismatch

## Deviations from Plan

### [Rule 1 - Bug] Attempted to fix MSB indexing bug (reverted)
- **Found during:** Task 1 implementation
- **Issue:** Initially used `temp_self[comp_width - 1]` for MSB extraction
- **Investigation:** Discovered right-aligned storage means index 63 is ALWAYS MSB
- **Fix:** Reverted to `temp_self[63]` matching __gt__ implementation
- **Files modified:** src/quantum_language/qint.pyx
- **Commit:** Included in main Task 1 commit (single unified change)

## Issues Discovered

### Critical Issue: Signed/Unsigned Interpretation Mismatch

**Problem:**
- qint uses two's complement representation with signed range docstring: `[-2^(w-1), 2^(w-1)-1]`
- Test oracle uses Python native comparison (unsigned for positive integers)
- When values exceed signed range (e.g., 5 in 3-bit), they wrap (5 → -3 in signed)
- Widened MSB-check comparison performs SIGNED comparison
- Tests expect UNSIGNED comparison

**Examples:**
- `qint(5, width=3) < 2`: signed interpretation gives -3 < 2 = True (1)
- Test oracle `int(5 < 2)`: unsigned gives 5 < 2 = False (0)
- Circuit returns 1, test expects 0 → FAIL

**Impact:**
- 44 new test failures for MSB-boundary cases
- Regression from Phase 29-16 widened comparison approach

**Root cause uncertainty:**
1. Widened comparison logic might be incorrect for unsigned
2. XOR bit-copy might not zero-extend properly
3. C backend subtraction might use signed arithmetic
4. Test oracle might be wrong (should use signed comparison?)

**Needs investigation:**
- Verify qint design intent (signed vs unsigned)
- Trace through XOR bit-copy for mixed widths
- Examine C backend IntegerAddition.c subtraction implementation
- Consider alternative unsigned comparison techniques

## Next Phase Readiness

**Blockers for Phase 36 (Comparison Test Cleanup):**
- Must resolve signed/unsigned interpretation issue before removing xfail markers
- Current implementation introduces regressions that will cause Phase 36 tests to fail
- Recommend Phase 35-03 to fix interpretation issue before proceeding

**Deferred:**
- BUG-CMP-02 partially addressed (18 xpassed) but 44 new failures introduced
- BUG-CMP-03 (circuit explosion) confirmed as non-issue (linear growth observed)

## Technical Decisions

**Right-aligned storage model:**
- For n-bit qint, qubits stored at indices [64-n, ..., 63]
- Index 63 ALWAYS holds MSB qubit, regardless of width
- `self[i]` accesses `self.qubits[i]` directly (not bit position i)
- Critical for MSB extraction in widened comparisons

**Widened comparison pattern:**
- `comp_width = max(self.bits, other.bits) + 1`
- Zero-extend both operands to comp_width bits
- Perform arithmetic in widened space
- MSB of result indicates sign (for signed) or borrow (for unsigned)

## Performance Notes

- No performance regressions observed
- Circuit sizes remain manageable (w=6: 104 QASM lines)
- Widened temps cleaned up by GC (no memory leak)

## Files Modified

### src/quantum_language/qint.pyx

**Lines 1807-1850: __lt__ method**
- Added `cdef int comp_width` variable declaration
- Replaced n-bit in-place subtraction with (n+1)-bit widened comparison
- QQ path: Create temp copies, subtract, extract MSB[63]
- Removed operand restoration (temps used, not originals)
- Updated comments to explain widened arithmetic

**Lines 1852-1864: __lt__ CQ path**
- Simplified to delegate to QQ path via `temp = qint(other, width=self.bits)`
- Preserves classical overflow checks before delegation
- Matches __gt__ CQ pattern

## Lessons Learned

1. **Storage model matters:** Right-aligned storage with index 63 = MSB is non-intuitive but critical
2. **Signed vs unsigned is fundamental:** Can't apply signed comparison technique to unsigned values
3. **Test patterns reveal design intent:** Exhaustive tests at MSB boundary expose interpretation assumptions
4. **Widened arithmetic is not a silver bullet:** Works for signed, fails for unsigned without adaptation
5. **Phase 29-16 incomplete:** __gt__ has same issue (_GT_LE_FAIL_PAIRS exists), just not caught by tests

## Recommendations

1. **Phase 35-03 (new):** Fix signed/unsigned interpretation
   - Option A: Implement true unsigned comparison (carry/borrow detection)
   - Option B: Change test oracle to expect signed comparison
   - Option C: Make qint explicitly unsigned (change docstring + behavior)

2. **Phase 36 adjustment:** Block until 35-03 completes
   - Cannot remove xfail markers with 44 regressions present
   - Need clean test suite for v1.6 release

3. **Investigation tasks:**
   - Trace XOR bit-copy for qints of different widths
   - Review C backend IntegerAddition.c for signed/unsigned handling
   - Clarify qint design intent (consult original design docs or author)
