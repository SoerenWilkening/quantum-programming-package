---
phase: 29-c-backend-bug-fixes
plan: 08
subsystem: c-backend
tags: [bugfix, verification, subtraction, comparison, qq-add, bug-05]

# Dependency graph
requires:
  - phase: 29-06
    provides: QQ_add control qubit bit-ordering fix
  - phase: 29-04
    provides: BUG-01/BUG-02 test infrastructure
provides:
  - BUG-01 verification results (2/5 tests pass - no improvement)
  - BUG-02 verification results (2/6 tests pass - no improvement)
  - Confirmation that QQ_add fix incomplete, additional bit-ordering issues remain
affects: [BUG-05-circuit-reset, future-qq-add-fix]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Individual test isolation pattern to avoid BUG-05 state contamination"
    - "Transitive failure analysis: comparison failures trace to subtraction root cause"

key-files:
  created: []
  modified: []

key-decisions:
  - "QQ_add 3+5=8 test passed, confirming basic addition works after plan 29-06 fix"
  - "Subtraction results (2/5 pass) unchanged from plan 29-06 baseline"
  - "Comparison failures (2/6 pass) are transitive from subtraction errors"
  - "BUG-05 interference likely corrupting test results, preventing definitive diagnosis"

patterns-established:
  - "Comparison logic (__le__) is correct: negative OR zero check via subtraction"
  - "Subtraction chain (sub -> isub -> addition_inplace(invert=True)) is correct"
  - "Test failure patterns suggest additional QQ_add bit-ordering issues beyond control qubit fix"

# Metrics
duration: 3min
completed: 2026-01-31
---

# Phase 29 Plan 08: BUG-01 & BUG-02 Verification After QQ_add Fix Summary

**Subtraction and comparison tests show no improvement — QQ_add control fix incomplete, BUG-05 blocks definitive diagnosis**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-31T00:06:36Z
- **Completed:** 2026-01-31T00:09:54Z
- **Tasks:** 3 (Task 0: QQ_add sanity check, Task 1: BUG-01, Task 2: BUG-02)
- **Files modified:** 0 (verification-only execution)

## Accomplishments

- **QQ_add basic verification passed:** qint(3) + qint(5) = 8 confirms plan 29-06 control fix works for simple addition
- **BUG-01 subtraction results documented:** 2/5 tests pass (no change from plan 29-06 baseline)
  - PASSED: 0-1=15 ✓, 15-0=15 ✓
  - FAILED: 3-7 got 10 (expected 12), 7-3 got 13 (expected 4), 5-5 got 10 (expected 0)
- **BUG-02 comparison results documented:** 2/6 tests pass (no change from plan 29-04 baseline)
  - PASSED: 7<=3 = 0 ✓, 15<=0 = 0 ✓
  - FAILED: All "True" cases (5<=5, 3<=7, 0<=0, 0<=15) return 0 instead of 1
- **Root cause analysis:** Comparison failures are transitive from subtraction errors (5-5 returns 10, not 0, so is_zero fails)

## Task Commits

No file modifications — verification-only plan. Test results documented in this summary.

## Files Created/Modified

None - all tasks were test execution and analysis only.

## Decisions Made

- **QQ_add fix is partial:** Plan 29-06 control reversal (2*bits-1-bit) is correctly applied, but test results show additional bit-ordering issues remain
- **Comparison logic verified correct:** `__le__` implementation uses `(self - other)` then checks `is_negative OR is_zero`, which is mathematically sound
- **Subtraction chain verified correct:** `__sub__` -> `__isub__` -> `addition_inplace(invert=True)` -> `QQ_add(..., invert=True)` is proper implementation
- **Failures are in QQ_add implementation:** Since subtraction and comparison logic are correct, errors must be in C backend QQ_add quantum gates
- **BUG-05 prevents definitive diagnosis:** Cannot distinguish between QQ_add bit-ordering errors vs BUG-05 cache pollution without circuit state reset fix

## Deviations from Plan

None - plan executed exactly as written. All tests run individually to avoid BUG-05 state contamination.

## Issues Encountered

### BUG-05 continues to block arithmetic verification

**Problem:** Same as documented in plan 29-06 — circuit state reset bug prevents reliable test execution.

**Evidence:** Test results show inconsistent error patterns that could be either:
1. Additional QQ_add bit-ordering bugs (target qubit mapping or phase formulas)
2. BUG-05 cache pollution corrupting quantum state between operations

**Impact:** Cannot conclusively fix remaining QQ_add issues without first resolving BUG-05.

### Subtraction error pattern analysis

**Observation:** Specific error offsets in failed tests:
- 3-7: expected 12, got 10 (off by -2)
- 7-3: expected 4, got 13 (off by +9)
- 5-5: expected 0, got 10 (off by +10)

**Hypothesis:** The errors are not random — they show systematic patterns suggesting:
1. Possible target qubit mapping issue (target = bits - i - 1 - rounds)
2. Possible phase value calculation issue (value = 2*π / 2^(i+1))
3. Possible interaction between invert flag and QFT gate sequence

**Limitation:** Without BUG-05 fix, cannot isolate whether these are true code bugs or test contamination artifacts.

## User Setup Required

None - verification-only plan with no code changes.

## Next Phase Readiness

**Progress toward arithmetic verification:**
- ✓ QQ_add basic addition verified working (3+5=8)
- ✗ QQ_add subtraction still broken (2/5 tests pass)
- ✗ Comparison transitively broken (2/6 tests pass)
- ✗ BUG-05 CRITICAL BLOCKER prevents further progress

**Critical blocker escalated:**
- **BUG-05 (circuit state reset) MUST be resolved before any further arithmetic work**
- Cannot fix remaining QQ_add bit-ordering issues without clean test environment
- Cannot verify CQ_add (plan 29-03 fix) without BUG-05 resolution
- Cannot proceed to Phase 30 (Arithmetic Verification) without BUG-05 fix

**Recommendations:**
1. **IMMEDIATE:** Prioritize BUG-05 fix as highest priority task
2. After BUG-05 fix: Re-run all plan 29-08 tests to get clean baseline
3. After BUG-05 fix: Investigate specific QQ_add target/phase issues if tests still fail
4. After BUG-05 fix: Re-verify CQ_add (plan 29-03) which is analytically correct but test-blocked
5. Consider pausing Phase 29 until BUG-05 is resolved, as no arithmetic verification is reliable

---
*Phase: 29-c-backend-bug-fixes*
*Plan: 08*
*Completed: 2026-01-31*
