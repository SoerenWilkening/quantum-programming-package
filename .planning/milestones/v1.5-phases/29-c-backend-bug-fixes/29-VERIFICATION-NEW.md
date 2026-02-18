---
phase: 29-c-backend-bug-fixes
verified: 2026-01-30T23:30:00Z
status: gaps_found
score: 1/5 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 1/5
  previous_verified: 2026-01-30T22:10:00Z
  gaps_closed: []
  gaps_remaining:
    - "BUG-01: Subtraction underflow (3-7 returns 7, not 12)"
    - "BUG-02: Comparison (5<=5 returns 0, not 1)"
    - "BUG-03: Multiplication logic (2*3 returns 0, not 6)"
    - "BUG-04: QFT addition (3+5 returns 6, not 8)"
  regressions:
    - item: "BUG-04 addition results"
      before: "3+5 returned 9 (off by 1)"
      now: "3+5 returns 6 (off by 2)"
      reason: "Plan 29-03 fixed CQ_add but introduced new errors; 0+1 was claimed fixed but returns 4"
gaps:
  - truth: "qint(3) - qint(7) on 4-bit integers returns 12 (unsigned wrap), not 7"
    status: failed
    reason: "Subtraction still returns 7 - QQ_add not fixed (only CQ_add was fixed in plan 29-03)"
    artifacts:
      - path: "c_backend/src/IntegerAddition.c"
        issue: "QQ_add function (lines 132-206) was NOT modified - still has bit-ordering bug"
      - path: "src/quantum_language/qint.pyx"
        issue: "No changes made - __sub__ depends on broken QQ_add for qint operands"
    missing:
      - "Apply bit-ordering fix to QQ_add (similar to CQ_add fix in lines 56, 70)"
      - "QQ_add uses different formula (lines 183-190) - needs separate investigation"
      - "Subtraction uses QQ_add path when operand is qint (plan 29-04 finding)"
  
  - truth: "qint(5) <= qint(5) returns 1 (true), not 0"
    status: failed
    reason: "Comparison still returns 0 - blocked by BUG-01 (depends on subtraction)"
    artifacts:
      - path: "src/quantum_language/qint.pyx"
        issue: "__le__ implementation calls self -= other, which uses broken QQ_add"
    missing:
      - "Fix BUG-01 first (QQ_add), then retest BUG-02"
      - "BUG-02 blocked by dependency chain: __le__ -> __sub__ -> QQ_add"
  
  - truth: "Multiplication operations complete without segfault across bit widths 1-4"
    status: partial
    reason: "Segfault eliminated (SUCCESS) but multiplication returns 0 for all inputs"
    artifacts:
      - path: "c_backend/src/IntegerMultiplication.c"
        issue: "Memory fixed (MAXLAYERINSEQUENCE, 10*bits) but bit-ordering fix (plan 29-05) ineffective"
    missing:
      - "Deep algorithm investigation - bit-ordering fix attempted but tests still return 0"
      - "Plan 29-05 tried bin[bits-1-bit_int2] reversal but no improvement"
      - "May need QFT multiplication formula review beyond bit-ordering"
  
  - truth: "QFT-based addition of two nonzero operands returns correct sum (e.g., 3+5=8)"
    status: failed
    reason: "CQ_add fixed but results worse; QQ_add not fixed; inconsistent test results"
    artifacts:
      - path: "c_backend/src/IntegerAddition.c"
        issue: "CQ_add fixed (lines 56, 70) but QQ_add (lines 132-206) untouched"
    missing:
      - "Fix QQ_add bit-ordering (same issue as CQ_add but different formula)"
      - "Investigate why CQ_add fix made results WORSE (3+5: 9->6, 0+1: 8->4)"
      - "Plan 29-03 claimed 0+1 and 7+8 fixed but current tests show 0+1 returns 4"
      - "Possible cache invalidation issue or BUG-05 interference"
  
  - truth: "All four fixes pass through full verification pipeline (OpenQASM -> Qiskit simulate -> result check)"
    status: failed
    reason: "Zero bugs fully fixed; segfault eliminated (partial) but no correctness achieved"
    artifacts:
      - path: "tests/bugfix/test_bug01_subtraction.py"
        issue: "2/5 tests pass (7-3=4, 5-5=0), main case fails (3-7=7 not 12)"
      - path: "tests/bugfix/test_bug02_comparison.py"
        issue: "0/6 tests pass (all blocked by subtraction dependency)"
      - path: "tests/bugfix/test_bug03_multiplication.py"
        issue: "0/5 tests pass for correctness (all return 0), 5/5 no segfault"
      - path: "tests/bugfix/test_bug04_qft_addition.py"
        issue: "0/7 tests pass (3+5=6 not 8, 0+1=4 not 1)"
    missing:
      - "Complete QQ_add fix for BUG-01 and BUG-04"
      - "Fix multiplication algorithm logic (BUG-03)"
      - "Retest BUG-02 after BUG-01 fixed"
      - "Investigate CQ_add regression (results worse after fix)"
---

# Phase 29: C Backend Bug Fixes Re-Verification Report

**Phase Goal:** All four known C backend bugs are fixed -- subtraction underflow, less-or-equal comparison, multiplication segfault, and QFT addition with nonzero operands all produce correct results.

**Verified:** 2026-01-30T23:30:00Z
**Status:** gaps_found
**Re-verification:** Yes - after plans 29-03, 29-04, 29-05 (gap closure attempts)

## Re-Verification Summary

**Previous verification (2026-01-30T22:10:00Z):** 1/5 must-haves verified (gaps_found)
**Current verification (2026-01-30T23:30:00Z):** 1/5 must-haves verified (gaps_found)

**Progress:** NO IMPROVEMENT
- Gaps closed: 0
- Gaps remaining: 5
- Regressions: 1 (BUG-04 addition results worse)

**Plans executed since last verification:**
- 29-03: Fix BUG-04 QFT addition (CQ_add bit-ordering) - PARTIAL, introduced regression
- 29-04: Retest BUG-01 & BUG-02 - INVESTIGATION only, confirmed blocked by unfixed QQ_add
- 29-05: Fix BUG-03 multiplication logic - ATTEMPTED, no improvement

## Goal Achievement

### Observable Truths

| # | Truth | Status | Previous | Evidence |
|---|-------|--------|----------|----------|
| 1 | qint(3) - qint(7) returns 12, not 7 | ✗ FAILED | ✗ FAILED | Returns 7 (test_bug01_subtraction.py::test_sub_3_minus_7) |
| 2 | qint(5) <= qint(5) returns 1, not 0 | ✗ FAILED | ✗ FAILED | Returns 0 (test_bug02_comparison.py::test_le_5_le_5) |
| 3 | Multiplication no segfault (1-4 bits) | ⚠️ PARTIAL | ⚠️ PARTIAL | No segfault ✓, returns 0 ✗ (test_bug03_multiplication.py::test_mul_2x3_4bit) |
| 4 | QFT addition correct (3+5=8) | ✗ REGRESSED | ✗ FAILED | Returns 6, was 9 (test_bug04_qft_addition.py::test_add_3_plus_5) |
| 5 | Full verification pipeline works | ✗ FAILED | ✗ FAILED | 2/23 individual test cases pass (7-3=4, 5-5=0 only) |

**Score:** 1/5 truths verified (no change from previous)

**Regression details:**
- BUG-04 (3+5): Previous result 9 (off by 1) → Current result 6 (off by 2, WORSE)
- BUG-04 (0+1): Plan 29-03 claimed fixed → Current result 4 (still broken)

### Required Artifacts - Re-verification Focus

**Artifacts with changes since previous verification:**

| Artifact | Change | Status | Details |
|----------|--------|--------|---------|
| `c_backend/src/IntegerAddition.c` | ✓ MODIFIED | ⚠️ PARTIAL | Lines 56, 70 fixed in CQ_add (commit bd8b581), but QQ_add (lines 132-206) UNTOUCHED |
| `c_backend/src/IntegerMultiplication.c` | ✓ MODIFIED | ⚠️ PARTIAL | Bit-ordering fix attempted (commit fce4453), tests still fail |

**Artifacts unchanged (as expected):**

| Artifact | Status | Reason |
|----------|--------|--------|
| `tests/bugfix/test_bug01_subtraction.py` | ✓ EXISTS | Created in 29-01, no changes needed |
| `tests/bugfix/test_bug02_comparison.py` | ✓ EXISTS | Created in 29-01, no changes needed |
| `tests/bugfix/test_bug03_multiplication.py` | ✓ EXISTS | Created in 29-02, no changes needed |
| `tests/bugfix/test_bug04_qft_addition.py` | ✓ EXISTS | Created in 29-02, no changes needed |
| `src/quantum_language/qint.pyx` | ✗ NOT MODIFIED | Correctly deferred - root cause is C backend |

### Code Changes Verification

**Plan 29-03 changes to IntegerAddition.c (commit bd8b581):**

✓ VERIFIED in CQ_add:
- Line 56: Changed `bin[bit_idx]` → `bin[bits - 1 - bit_idx]` (reverses MSB-first to LSB-first)
- Line 70: Changed `rotations[bits - i - 1]` → `rotations[i]` (fixes cache update path)
- Comments updated to document bit ordering

✓ VERIFIED in cCQ_add:
- Similar changes applied (lines ~238, ~252)

✗ NOT APPLIED to QQ_add:
- Lines 132-206 show NO changes
- QQ_add still uses original formula (lines 183-190)
- This is why BUG-01 and part of BUG-04 remain broken

**Plan 29-05 changes to IntegerMultiplication.c (commit fce4453):**

Attempted bit-ordering reversal - inspection needed:

