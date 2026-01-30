---
phase: 29-c-backend-bug-fixes
verified: 2026-01-30T23:35:00Z
status: gaps_found
score: 1/5 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 1/5
  previous_verified: 2026-01-30T22:10:00Z
  gaps_closed: []
  gaps_remaining:
    - "BUG-01: Subtraction underflow"
    - "BUG-02: Comparison"
    - "BUG-03: Multiplication logic"
    - "BUG-04: QFT addition"
    - "Full verification pipeline"
  regressions:
    - item: "BUG-04 addition test results"
      before: "3+5 returned 9 (off by +1)"
      now: "3+5 returns 6 (off by -2)"
      reason: "CQ_add fix applied but results differ - possible cache issue or BUG-05 interference"
gaps:
  - truth: "qint(3) - qint(7) on 4-bit integers returns 12 (unsigned wrap), not 7"
    status: failed
    reason: "QQ_add not fixed - only CQ_add was modified in plan 29-03"
    artifacts:
      - path: "c_backend/src/IntegerAddition.c"
        issue: "QQ_add function (lines 132-206) has no bit-ordering fix applied"
    missing:
      - "Apply bit-ordering fix to QQ_add similar to CQ_add"
      - "QQ_add uses different formula - needs separate investigation and fix"
  
  - truth: "qint(5) <= qint(5) returns 1 (true), not 0"
    status: failed
    reason: "Blocked by BUG-01 - comparison depends on working subtraction"
    artifacts:
      - path: "src/quantum_language/qint.pyx"
        issue: "__le__ calls __sub__ which uses broken QQ_add"
    missing:
      - "Fix BUG-01 (QQ_add) first, then retest"
  
  - truth: "Multiplication operations complete without segfault across bit widths 1-4"
    status: partial
    reason: "Segfault fixed (ACHIEVED) but returns 0 instead of correct products"
    artifacts:
      - path: "c_backend/src/IntegerMultiplication.c"
        issue: "Bit-ordering fix attempted (line 136) but tests still return 0"
    missing:
      - "Deep QFT multiplication algorithm investigation"
      - "Fix beyond bit-ordering - formula or gate placement may be wrong"
  
  - truth: "QFT-based addition of two nonzero operands returns correct sum (e.g., 3+5=8)"
    status: failed
    reason: "CQ_add fixed but QQ_add not; results still wrong and possibly regressed"
    artifacts:
      - path: "c_backend/src/IntegerAddition.c"
        issue: "CQ_add fixed, QQ_add untouched"
    missing:
      - "Fix QQ_add bit-ordering"
      - "Investigate CQ_add regression (3+5 worse than before)"
  
  - truth: "All four fixes pass through full verification pipeline"
    status: failed
    reason: "Only 2/23 individual test cases pass"
    artifacts:
      - path: "tests/bugfix/"
        issue: "Most tests fail - only simple cases pass (7-3, 5-5)"
    missing:
      - "Complete all four bug fixes"
      - "Address BUG-05 for reliable batch testing"
---

# Phase 29: C Backend Bug Fixes Re-Verification Report

**Phase Goal:** All four known C backend bugs are fixed -- subtraction underflow, less-or-equal comparison, multiplication segfault, and QFT addition with nonzero operands all produce correct results.

**Verified:** 2026-01-30T23:35:00Z
**Status:** gaps_found  
**Re-verification:** Yes - after plans 29-03, 29-04, 29-05

## Re-Verification Summary

**Previous verification:** 2026-01-30T22:10:00Z (after plans 29-01, 29-02)
- Status: gaps_found
- Score: 1/5 must-haves verified

**Current verification:** 2026-01-30T23:35:00Z (after plans 29-03, 29-04, 29-05)
- Status: gaps_found
- Score: 1/5 must-haves verified
- **NO IMPROVEMENT** despite 3 additional plans

**Work completed since last verification:**
- Plan 29-03: Fixed CQ_add bit-ordering (classical+qint addition) - PARTIAL SUCCESS
- Plan 29-04: Investigated BUG-01 & BUG-02 - CONFIRMED BLOCKED by unfixed QQ_add
- Plan 29-05: Attempted multiplication bit-ordering fix - NO IMPROVEMENT

**Gaps closed:** 0
**Gaps remaining:** 5 (all original gaps still present)
**Regressions:** 1 (BUG-04 test results changed but not improved)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Change | Evidence |
|---|-------|--------|--------|----------|
| 1 | qint(3) - qint(7) returns 12 | ✗ FAILED | No change | Returns 7 (test_bug01_subtraction.py::test_sub_3_minus_7) |
| 2 | qint(5) <= qint(5) returns 1 | ✗ FAILED | No change | Returns 0 (test_bug02_comparison.py::test_le_5_le_5) |
| 3 | Multiplication no segfault | ⚠️ PARTIAL | No change | No segfault ✓, returns 0 ✗ (test_bug03_multiplication.py) |
| 4 | QFT addition (3+5=8) | ✗ FAILED | REGRESSED | Returns 6, was 9 before (test_bug04_qft_addition.py::test_add_3_plus_5) |
| 5 | Full pipeline verification | ✗ FAILED | No change | 2/23 test cases pass (only 7-3=4, 5-5=0) |

**Score:** 1/5 truths verified (partial success on #3: segfault eliminated)

### Test Results - Detailed Comparison

**BUG-01 Subtraction (5 tests):**
- test_sub_3_minus_7: ✗ FAILED (expected 12, got 7) - **MAIN BUG**
- test_sub_7_minus_3: ✓ PASSED (expected 4, got 4)
- test_sub_5_minus_5: ✓ PASSED (expected 0, got 0)
- test_sub_0_minus_1: Not tested (BUG-05 memory overflow)
- test_sub_15_minus_0: Not tested

**Pass rate:** 2/5 tested (40%) - unchanged from previous verification

**BUG-02 Comparison (6 tests):**
- test_le_5_le_5: ✗ FAILED (expected 1, got 0) - **MAIN BUG**
- Other 5 tests: Not tested (blocked by subtraction dependency)

**Pass rate:** 0/6 (0%) - unchanged from previous verification

**BUG-03 Multiplication (5 tests):**
- test_mul_2x3_4bit: ✗ FAILED (expected 6, got 0) - no segfault ✓
- Other 4 tests: Likely all return 0

**Pass rate:** 0/5 for correctness (0%), 5/5 for no segfault (100%) - unchanged from previous

**BUG-04 QFT Addition (7 tests):**
- test_add_3_plus_5: ✗ FAILED (expected 8, got 6) - **REGRESSED** (was 9)
- test_add_0_plus_1: ✗ FAILED (expected 1, got 4) - **STILL BROKEN** (plan 29-03 claimed fixed)
- Other tests: Not individually verified

**Pass rate:** 0/7 (0%) - WORSE than previous (some cases claimed fixed in 29-03 still fail)

### Code Changes Analysis

**What was changed:**

1. **IntegerAddition.c (commit bd8b581 - plan 29-03):**
   - ✓ CQ_add line 56: `bin[bit_idx]` → `bin[bits - 1 - bit_idx]` (reverse MSB→LSB)
   - ✓ CQ_add line 70: `rotations[bits - i - 1]` → `rotations[i]` (fix cache path)
   - ✓ cCQ_add: Similar changes applied
   - ✗ QQ_add lines 132-206: **NO CHANGES** (this is the gap!)
   
2. **IntegerMultiplication.c (commit fce4453 - plan 29-05):**
   - ✓ CQ_mul line 136: Applied bit-ordering reversal `bin[bits - 1 - bit_int2]`
   - Status: Change applied but tests still fail (deeper issue)

**What was NOT changed:**

1. **QQ_add function:** The critical path for qint+qint operations
   - Used by subtraction when operand is qint
   - Used by addition when both operands are qint
   - Still has original bit-ordering bug
   - Plan 29-04 identified this gap but no fix was applied

2. **qint.pyx:** Correctly left unchanged (root cause is C backend)

### Root Cause Analysis

**Why bugs remain unfixed:**

1. **BUG-01 & BUG-02 (Subtraction & Comparison):**
   - Root cause: QQ_add (qint+qint addition) has bit-ordering bug
   - Plan 29-03 fixed CQ_add (classical+qint addition) only
   - Subtraction path: `x - y` → `x.__sub__(y)` → `x -= y` → `QQ_add` with invert=True
   - Plan 29-04 correctly identified this but no fix was applied
   - **BLOCKED by incomplete BUG-04 fix**

2. **BUG-03 (Multiplication):**
   - Segfault: ✓ FIXED (memory allocation increased)
   - Logic bug: ✗ NOT FIXED (returns 0)
   - Plan 29-05 applied bit-ordering fix but no improvement
   - Likely issues beyond bit-ordering: formula, gate placement, or QFT timing
   - **Needs deeper algorithm investigation**

3. **BUG-04 (QFT Addition):**
   - CQ_add path: ⚠️ FIXED but results questionable (regression observed)
   - QQ_add path: ✗ NOT FIXED (unchanged code)
   - Plan 29-03 claimed 0+1 and 7+8 fixed but current test shows 0+1 returns 4
   - Possible cache invalidation issues or BUG-05 interference
   - **Partially fixed but incomplete and possibly regressed**

### Regression Analysis

**BUG-04 test result regression:**

| Test Case | Previous Result | Current Result | Expected | Change |
|-----------|----------------|----------------|----------|--------|
| 3 + 5 | 9 (off by +1) | 6 (off by -2) | 8 | WORSE |
| 0 + 1 | 8 (claimed fixed) | 4 (off by +3) | 1 | STILL BROKEN |

**Possible causes:**
1. **Cache issue:** CQ_add uses precompiled sequence cache - may need invalidation
2. **BUG-05 interference:** Circuit state accumulation affects results
3. **Incomplete fix:** CQ_add fix may have partial errors
4. **Test environment:** Non-deterministic results due to state pollution

**Evidence from plan summaries:**
- Plan 29-03 summary claims "0+1 and 7+8 now work"
- Current verification shows 0+1 returns 4 (wrong)
- Plan 29-03 summary notes BUG-05 interference with test verification
- Plan states "test results unreliable due to BUG-05"

### Dependency Chain Blocking Goal

```
BUG-02 (comparison)
  ↓ depends on
BUG-01 (subtraction)
  ↓ depends on  
BUG-04 (QFT addition - QQ_add path)
  ↓ status
✗ NOT FIXED (QQ_add unchanged)

BUG-03 (multiplication)
  ↓ status
⚠️ PARTIAL (no segfault, wrong results)

BUG-04 (QFT addition - CQ_add path)
  ↓ status
⚠️ FIXED? (code changed but results questionable)
```

### Required Artifacts Status

| Artifact | Status | Level 1: Exists | Level 2: Substantive | Level 3: Wired |
|----------|--------|----------------|---------------------|---------------|
| test_bug01_subtraction.py | ✓ VERIFIED | ✓ EXISTS (79 lines) | ✓ SUBSTANTIVE | ✓ WIRED to framework |
| test_bug02_comparison.py | ✓ VERIFIED | ✓ EXISTS (95 lines) | ✓ SUBSTANTIVE | ✓ WIRED to framework |
| test_bug03_multiplication.py | ✓ VERIFIED | ✓ EXISTS (79 lines) | ✓ SUBSTANTIVE | ✓ WIRED to framework |
| test_bug04_qft_addition.py | ✓ VERIFIED | ✓ EXISTS (96 lines) | ✓ SUBSTANTIVE | ✓ WIRED to framework |
| IntegerAddition.c CQ_add fix | ⚠️ PARTIAL | ✓ MODIFIED | ✓ SUBSTANTIVE | ⚠️ QUESTIONABLE (regression) |
| IntegerAddition.c QQ_add fix | ✗ MISSING | ✓ EXISTS | ✗ STUB (no fix) | ✗ BROKEN |
| IntegerMultiplication.c fix | ⚠️ PARTIAL | ✓ MODIFIED | ✓ SUBSTANTIVE | ✗ BROKEN (returns 0) |

**Critical gap:** QQ_add in IntegerAddition.c has no bit-ordering fix applied, blocking BUG-01, BUG-02, and part of BUG-04.

### Anti-Patterns Found

| File | Issue | Severity | Impact |
|------|-------|----------|--------|
| IntegerAddition.c | QQ_add not fixed despite plan 29-03 | 🛑 BLOCKER | Blocks BUG-01, BUG-02, partial BUG-04 |
| IntegerMultiplication.c | Bit-ordering fix ineffective | 🛑 BLOCKER | BUG-03 returns 0 despite fix attempt |
| Plan 29-03 SUMMARY | Claims fixes that tests don't verify | ⚠️ WARNING | Unreliable verification due to BUG-05 |
| Test results | Non-deterministic (BUG-05 interference) | ⚠️ WARNING | Can't trust individual test runs |

### Requirements Coverage

| Requirement | Status | Progress | Blocking Issue |
|-------------|--------|----------|----------------|
| BUG-01: Subtraction underflow | ✗ BLOCKED | 0% | QQ_add not fixed |
| BUG-02: Comparison | ✗ BLOCKED | 0% | Depends on BUG-01 |
| BUG-03: Multiplication segfault | ⚠️ PARTIAL | 50% | Segfault fixed ✓, logic broken ✗ |
| BUG-04: QFT addition | ⚠️ PARTIAL | 25% | CQ_add fixed?, QQ_add not fixed |

**Coverage:** 0/4 requirements fully satisfied, 2/4 partially addressed (same as previous verification)

## Gaps Summary

**Phase 29 goal NOT achieved.** Same score as previous verification (1/5).

**Plans 29-03, 29-04, 29-05 completed but made NO measurable progress:**
- Plan 29-03: Fixed CQ_add but not QQ_add - incomplete fix
- Plan 29-04: Investigation only, no code changes
- Plan 29-05: Attempted multiplication fix, no improvement

**Critical missing work:**

1. **Fix QQ_add bit-ordering** (highest priority - blocks 3 bugs):
   - Apply same approach as CQ_add fix (lines 56, 70)
   - QQ_add uses different formula (lines 183-190) - needs investigation
   - This will unblock BUG-01, BUG-02, and complete BUG-04

2. **Fix multiplication algorithm** (independent - can proceed in parallel):
   - Bit-ordering fix attempted but ineffective
   - Need deeper investigation: formula, QFT placement, gate construction
   - May need to compare with reference QFT multiplication implementation

3. **Investigate CQ_add regression**:
   - Test results changed but not improved
   - Possible cache invalidation issue
   - May be BUG-05 interference (non-deterministic results)

4. **Address BUG-05** (out of scope but critical for verification):
   - Circuit state reset bug prevents reliable testing
   - Plan summaries note tests are "unreliable due to BUG-05"
   - Can't verify fixes properly without this

**Dependency order for success:**
1. Fix QQ_add (unblocks BUG-01, BUG-02, completes BUG-04)
2. Verify CQ_add actually works (investigate regression)
3. Fix multiplication algorithm (BUG-03)
4. Optionally fix BUG-05 for reliable verification

## Human Verification Required

**Not needed at this stage** - all failures are programmatically verifiable through automated tests.

Human verification would be useful AFTER bugs are actually fixed:
1. Run full test suite without BUG-05 interference
2. Verify performance (QFT operations not exponentially slow)
3. Test additional bit widths (5-8 bits) for edge cases

## Recommendations

**Immediate actions:**

1. **Create plan to fix QQ_add:** Apply bit-ordering fix similar to CQ_add
   - Investigate QQ_add formula (lines 183-190 in IntegerAddition.c)
   - Apply bin[] reversal or equivalent fix
   - Test with both addition and subtraction (invert=True) cases

2. **Investigate CQ_add regression:** Understand why test results changed
   - Check cache invalidation (precompiled_CQ_add_width[bits])
   - Run tests in isolation to rule out BUG-05 interference
   - Verify formula correctness against Qiskit reference

3. **Deep dive on multiplication:** Beyond bit-ordering
   - Review QFT multiplication algorithm literature
   - Compare implementation with reference (e.g., Qiskit, Cirq)
   - Check gate construction and QFT placement

**Longer-term:**

4. **Consider BUG-05 fix:** Circuit state reset for reliable testing
   - Currently out of scope but critical for verification
   - Prevents running full test suites
   - Causes non-deterministic results

**Phase 30 readiness:** BLOCKED - cannot proceed with arithmetic verification while core operations are broken.

---

_Verified: 2026-01-30T23:35:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification after plans: 29-03, 29-04, 29-05_
_Status: No improvement - gaps remain, 1 regression observed_
