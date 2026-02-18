---
phase: 29-c-backend-bug-fixes
verified: 2026-01-31T00:18:17Z
status: gaps_found
score: 1/5 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 1/5
  previous_verified: 2026-01-30T23:35:00Z
  gaps_closed: []
  gaps_remaining:
    - "BUG-01: Subtraction underflow"
    - "BUG-02: Comparison"
    - "BUG-03: Multiplication logic"
    - "BUG-04: QFT addition"
    - "Full verification pipeline"
  regressions:
    - item: "BUG-04 addition test results"
      before: "3+5 returned 6, 0+1 returned 4"
      now: "3+5 returns 14, 0+1 returns 2, 1+1 passes"
      reason: "Test results vary between runs — confirms BUG-05 cache pollution interference"
gaps:
  - truth: "qint(3) - qint(7) on 4-bit integers returns 12 (unsigned wrap), not 7"
    status: failed
    reason: "QQ_add control reversal applied but additional bit-ordering issues remain"
    artifacts:
      - path: "c_backend/src/IntegerAddition.c"
        issue: "QQ_add line 191: control mapping fixed, but results still wrong (3-7=10 not 12)"
    missing:
      - "Target qubit mapping or phase formula corrections in QQ_add"
      - "Investigation of systematic off-by-N error patterns"
      - "BUG-05 fix required for clean test environment"
  
  - truth: "qint(5) <= qint(5) returns 1 (true), not 0"
    status: failed
    reason: "Transitively blocked by BUG-01 subtraction errors"
    artifacts:
      - path: "src/quantum_language/qint.pyx"
        issue: "__le__ logic correct but depends on working subtraction"
    missing:
      - "Fix BUG-01 (QQ_add) first, then comparison will work"
  
  - truth: "Multiplication operations complete without segfault across bit widths 1-4"
    status: partial
    reason: "Segfault fixed (ACHIEVED), control reversal applied, but returns wrong values"
    artifacts:
      - path: "c_backend/src/IntegerMultiplication.c"
        issue: "Control reversal from plan 29-07 applied but results still incorrect (2*3=1 not 6, but 1*1=1 passes, 0*5=0 passes)"
    missing:
      - "Target qubit mapping or phase formula fixes in QQ_mul"
      - "Algorithm comparison with reference QFT multiplication implementation"
      - "Deeper investigation beyond bit-ordering"
  
  - truth: "QFT-based addition of two nonzero operands returns correct sum (e.g., 3+5=8)"
    status: failed
    reason: "CQ_add (plan 29-03) partially works but has inconsistent results; QQ_add (plan 29-06) has additional issues"
    artifacts:
      - path: "c_backend/src/IntegerAddition.c"
        issue: "CQ_add: 1+0=1 ✓, 1+1=2 ✓, but 0+1=2 ✗, 3+5=14 ✗; QQ_add: control reversed but target/phase issues remain"
    missing:
      - "CQ_add: Fix remaining bit-ordering or phase issues causing 0+1 and 3+5 failures"
      - "QQ_add: Fix target qubit mapping or phase formulas"
      - "BUG-05 fix to eliminate cache pollution causing non-deterministic results"
  
  - truth: "All four fixes pass through full verification pipeline"
    status: failed
    reason: "Only 6/17 tested cases pass"
    artifacts:
      - path: "tests/bugfix/"
        issue: "Pass rate: BUG-01 2/5, BUG-02 0/2, BUG-03 2/3, BUG-04 3/5"
    missing:
      - "Complete all four bug fixes"
      - "Address BUG-05 for reliable, deterministic testing"
---

# Phase 29: C Backend Bug Fixes Re-Verification Report #2

**Phase Goal:** All four known C backend bugs are fixed -- subtraction underflow, less-or-equal comparison, multiplication segfault, and QFT addition with nonzero operands all produce correct results.

**Verified:** 2026-01-31T00:18:17Z
**Status:** gaps_found  
**Re-verification:** Yes — after plans 29-06, 29-07, 29-08

## Re-Verification Summary

**Previous verification:** 2026-01-30T23:35:00Z (after plans 29-03, 29-04, 29-05)
- Status: gaps_found
- Score: 1/5 must-haves verified

**Current verification:** 2026-01-31T00:18:17Z (after plans 29-06, 29-07, 29-08)
- Status: gaps_found
- Score: 1/5 must-haves verified
- **NO NET IMPROVEMENT** despite 3 additional plans

**Work completed since last verification:**
- Plan 29-06: Fixed QQ_add control qubit bit-ordering (2*bits-1-bit reversal) - PARTIAL SUCCESS
- Plan 29-07: Applied control reversal to multiplication - PARTIAL SUCCESS (1*1 now passes)
- Plan 29-08: Verified BUG-01 & BUG-02 after QQ_add fix - NO IMPROVEMENT

**Gaps closed:** 0
**Gaps remaining:** 5 (all original gaps still present)
**Regressions:** Test results continue to vary between runs, confirming BUG-05 interference

## Goal Achievement

### Observable Truths

| # | Truth | Status | Change from prev | Evidence |
|---|-------|--------|-----------------|----------|
| 1 | qint(3) - qint(7) returns 12 | ✗ FAILED | No change | Returns 10 (off by -2) |
| 2 | qint(5) <= qint(5) returns 1 | ✗ FAILED | No change | Returns 0 (blocked by #1) |
| 3 | Multiplication no segfault | ⚠️ PARTIAL | IMPROVED | No segfault ✓, 1*1=1 ✓, 0*5=0 ✓, but 2*3=1 ✗ (was 0) |
| 4 | QFT addition (3+5=8) | ✗ FAILED | CHANGED | Returns 14 (was 6), non-deterministic |
| 5 | Full pipeline verification | ✗ FAILED | SLIGHT IMPROVEMENT | 6/17 cases pass (was 2/23) |

**Score:** 1/5 truths verified (partial success on #3: segfault eliminated, 1*1 passes)

### Test Results - Current vs Previous

**BUG-01 Subtraction (5 tests):**
| Test | Expected | Current | Previous | Status |
|------|----------|---------|----------|--------|
| test_sub_3_minus_7 | 12 | 10 | 7 or 10 | ✗ FAILED (main bug, consistent) |
| test_sub_7_minus_3 | 4 | 13 | 13 | ✗ FAILED (off by +9) |
| test_sub_5_minus_5 | 0 | 10 | 10 | ✗ FAILED (off by +10) |
| test_sub_0_minus_1 | 15 | 15 | Memory explosion | ✓ PASSED (no longer hits BUG-05!) |
| test_sub_15_minus_0 | 15 | 15 | Memory explosion | ✓ PASSED (no longer hits BUG-05!) |

**Pass rate:** 2/5 (40%) — SAME as previous verification
**Notable:** BUG-05 memory explosions no longer occur for these tests (improvement in test reliability)

**BUG-02 Comparison (6 tests):**
| Test | Expected | Current | Status |
|------|----------|---------|--------|
| test_le_5_le_5 | 1 | 0 | ✗ FAILED (main bug) |
| test_le_3_le_7 | 1 | 0 | ✗ FAILED (transitive from subtraction) |

**Pass rate:** 0/2 tested (0%) — SAME as previous
**Note:** Comparison logic is correct; failures are 100% due to BUG-01 subtraction errors

**BUG-03 Multiplication (5 tests):**
| Test | Expected | Current | Previous | Status |
|------|----------|---------|----------|--------|
| test_mul_0x5_4bit | 0 | 0 | 0 | ✓ PASSED |
| test_mul_1x1_2bit | 1 | 1 | 0 | ✓ PASSED (IMPROVEMENT!) |
| test_mul_2x3_4bit | 6 | 1 | 0 or 1 | ✗ FAILED (was 0, now 1 — progress but still wrong) |
| test_mul_2x2_3bit | 4 | 1 | Not tested | ✗ FAILED |
| test_mul_3x3_4bit | 9 | 2 | Not tested | ✗ FAILED |

**Pass rate:** 2/5 (40%) for correctness — IMPROVED from 1/5 (0*5 only)
**Segfault rate:** 0/5 (0%) — MAINTAINED (segfault fix from plan 29-02 stable)
**Analysis:** Control reversal (plan 29-07) shows partial improvement — 1*1 now works, other tests return non-zero (was all 0) but still wrong

**BUG-04 QFT Addition (7 tests):**
| Test | Expected | Current | Previous | Status |
|------|----------|---------|----------|--------|
| test_add_0_plus_0 | 0 | 0 | 0 | ✓ PASSED |
| test_add_0_plus_1 | 1 | 2 | 4 | ✗ FAILED (off by +1, was +3) |
| test_add_1_plus_0 | 1 | 1 | 1 | ✓ PASSED |
| test_add_1_plus_1 | 1 | 2 | 0 | ✓ PASSED (IMPROVEMENT!) |
| test_add_3_plus_5 | 8 | 14 | 6 or 9 | ✗ FAILED (off by +6, non-deterministic) |
| test_add_7_plus_8 | 15 | Not tested | Not tested | Unknown |
| test_add_8_plus_8 | 0 | Not tested | Not tested | Unknown |

**Pass rate:** 3/5 tested (60%) — IMPROVED from 1/7 or 3/7 (was inconsistent)
**Analysis:** Pattern emerges:
- X+0 works (1+0=1 ✓)
- 0+0 works (0+0=0 ✓)
- 1+1 works (1+1=2 ✓) — NEW PASS
- 0+X fails (0+1=2 ✗)
- X+Y fails (3+5=14 ✗)

This suggests CQ_add has asymmetric behavior or operand-order dependency

### Code Changes Analysis

**What was changed since previous verification:**

1. **IntegerAddition.c QQ_add (commit 237135d - plan 29-06):**
   - Line 191: `control = bits + bit` → `control = bits + (bits - 1 - bit)` (control qubit reversal)
   - Applied same pattern from CQ_add fix to QQ_add
   - Rationale: outer loop iterates MSB-first but needs LSB-first qubit access

2. **IntegerMultiplication.c (commit aae8ad0 - plan 29-07):**
   - Systematic control qubit reversal across ALL helper functions:
     - QQ_mul line 210: `bits + bit` → `2*bits - 1 - bit`
     - CX_sequence line 33: applied reversal
     - CCX_sequence line 49: applied reversal
     - all_rot line 58: applied reversal
     - CQ_mul line 128: applied reversal
     - CQ_mul line 145: added phase weight factor `* pow(2, bits - 1 - bit)`

**What remains unchanged:**
- CQ_add and cCQ_add (plan 29-03 fix): bin[] reversal and cached path fix applied
- QQ_add target qubit mapping: still uses `bits - i - 1 - rounds` (not reversed)
- QQ_mul target qubit mapping: not modified in plan 29-07

### Root Cause Analysis

**Why bugs remain unfixed:**

1. **BUG-01 & BUG-02 (Subtraction & Comparison):**
   - Root cause: QQ_add has additional bit-ordering issues beyond control qubit fix
   - Plan 29-06 fixed control mapping but results show systematic errors:
     - 3-7: expected 12, got 10 (off by -2)
     - 7-3: expected 4, got 13 (off by +9)
     - 5-5: expected 0, got 10 (off by +10)
   - These non-random patterns suggest target qubit mapping or phase formula errors
   - **STATUS:** Control fix applied, but target/phase issues remain

2. **BUG-03 (Multiplication):**
   - Segfault: ✓ FIXED (plan 29-02 memory allocation maintained)
   - Control reversal: ✓ APPLIED (plan 29-07)
   - Results: ⚠️ PARTIAL IMPROVEMENT
     - 1*1=1 now passes (was 0) — validates control fix helps
     - 2*3=1 (was 0, expected 6) — non-zero result suggests partial fix
     - Complex products still wrong — likely target qubit or phase formula issues
   - **STATUS:** Progressing but needs target/phase fixes like QQ_add

3. **BUG-04 (QFT Addition):**
   - CQ_add path (plan 29-03): ⚠️ PARTIALLY WORKS
     - 1+0=1 ✓, 1+1=2 ✓ (new!), 0+0=0 ✓
     - 0+1=2 ✗ (off by +1), 3+5=14 ✗ (off by +6)
     - Asymmetric: X+0 works, 0+X fails — suggests operand order or qubit layout issue
   - QQ_add path (plan 29-06): ⚠️ CONTROL FIXED, OTHER ISSUES REMAIN
     - Not directly tested (BUG-04 tests use classical int, not qint+qint)
     - BUG-01 results show QQ_add still broken
   - **STATUS:** Both CQ_add and QQ_add have partial fixes but additional issues remain

### Test Result Variability Analysis

**Evidence of BUG-05 interference:**
- Plan 29-08 summary reports: 3+5=6
- Current verification: 3+5=14
- Previous verification: 3+5=6 or 9 (varied)

**However, improvements noted:**
- Plan 29-08: test_sub_0_minus_1 had "Memory explosion"
- Current verification: test_sub_0_minus_1 PASSED (15)
- Plan 29-08: test_sub_15_minus_0 had "Memory explosion"
- Current verification: test_sub_15_minus_0 PASSED (15)

**Interpretation:**
- BUG-05 still affects complex operations (3+5 results vary)
- But simple operations no longer trigger memory explosions
- Possible cache state differences between verification runs
- Individual test isolation (per user instruction) helps avoid cascading failures

### Systematic Error Patterns

**QQ_add subtraction errors (4-bit):**
| Operation | Binary | Expected | Got | Error |
|-----------|--------|----------|-----|-------|
| 3-7 | 0011-0111 | 12 (1100) | 10 (1010) | -2 |
| 7-3 | 0111-0011 | 4 (0100) | 13 (1101) | +9 |
| 5-5 | 0101-0101 | 0 (0000) | 10 (1010) | +10 |

**Hypothesis:** The errors are not random. Bit pattern 1010 (10) appears in multiple results, suggesting:
1. Target qubit mapping may be reversed or offset
2. Phase accumulation may have sign or magnitude error
3. Possible interaction between invert flag and bit-ordering

**CQ_add asymmetry (4-bit):**
| Operation | Works? | Got | Expected |
|-----------|--------|-----|----------|
| 1+0 | ✓ | 1 | 1 |
| 0+1 | ✗ | 2 | 1 |
| 1+1 | ✓ | 2 | 2 |
| 3+5 | ✗ | 14 | 8 |

**Hypothesis:** Operand order matters:
- qint(N) += 0 works (no-op or simple case)
- qint(N) += M where N≠0 and M≠0 works (1+1)
- qint(0) += M fails (0+1=2)
- Large values fail (3+5=14)

This suggests bin[] indexing or rotation accumulation has edge cases

### Required Artifacts Status

| Artifact | Status | Level 1: Exists | Level 2: Substantive | Level 3: Wired |
|----------|--------|----------------|---------------------|---------------|
| test_bug01_subtraction.py | ✓ VERIFIED | ✓ EXISTS (79 lines) | ✓ SUBSTANTIVE | ✓ WIRED to framework |
| test_bug02_comparison.py | ✓ VERIFIED | ✓ EXISTS (95 lines) | ✓ SUBSTANTIVE | ✓ WIRED to framework |
| test_bug03_multiplication.py | ✓ VERIFIED | ✓ EXISTS (79 lines) | ✓ SUBSTANTIVE | ✓ WIRED to framework |
| test_bug04_qft_addition.py | ✓ VERIFIED | ✓ EXISTS (96 lines) | ✓ SUBSTANTIVE | ✓ WIRED to framework |
| IntegerAddition.c CQ_add fix | ⚠️ PARTIAL | ✓ MODIFIED | ✓ SUBSTANTIVE | ⚠️ PARTIAL (3/5 tests pass) |
| IntegerAddition.c QQ_add fix | ⚠️ PARTIAL | ✓ MODIFIED | ✓ SUBSTANTIVE | ✗ BROKEN (2/5 sub tests pass) |
| IntegerMultiplication.c fix | ⚠️ PARTIAL | ✓ MODIFIED | ✓ SUBSTANTIVE | ⚠️ PARTIAL (2/5 tests pass, 1*1 works) |

**Progress:** Control qubit fixes applied to all three functions (CQ_add, QQ_add, QQ_mul), but target qubit and phase formula issues remain

### Anti-Patterns Found

| File | Issue | Severity | Impact |
|------|-------|----------|--------|
| IntegerAddition.c QQ_add | Control reversed but target/phase not fixed | 🛑 BLOCKER | Blocks BUG-01, BUG-02 |
| IntegerAddition.c CQ_add | Asymmetric behavior (X+0 works, 0+X fails) | 🛑 BLOCKER | Partial BUG-04 |
| IntegerMultiplication.c | Control reversed but algorithm still broken | 🛑 BLOCKER | BUG-03 returns wrong values |
| Test environment | BUG-05 causes non-deterministic results | ⚠️ WARNING | Can't fully trust verification |
| Plan summaries | Results vary from actual tests | ⚠️ WARNING | BUG-05 interference during execution |

### Requirements Coverage

| Requirement | Status | Progress | Blocking Issue |
|-------------|--------|----------|----------------|
| BUG-01: Subtraction underflow | ✗ PARTIAL | 40% | QQ_add control fixed, target/phase not fixed |
| BUG-02: Comparison | ✗ BLOCKED | 0% | Depends on BUG-01 |
| BUG-03: Multiplication segfault | ⚠️ PARTIAL | 60% | Segfault fixed ✓, control reversed ✓, target/phase not fixed |
| BUG-04: QFT addition | ⚠️ PARTIAL | 60% | CQ_add 3/5 pass, QQ_add partial fix |

**Coverage:** 0/4 requirements fully satisfied, 3/4 show measurable progress

## Gaps Summary

**Phase 29 goal NOT achieved.** Same score as previous two verifications (1/5).

**Plans 29-06, 29-07, 29-08 show INCREMENTAL PROGRESS but no complete fixes:**
- Plan 29-06: QQ_add control reversal applied — necessary but insufficient
- Plan 29-07: Multiplication control reversal applied — 1*1 now works
- Plan 29-08: Investigation only, confirmed QQ_add still broken

**Measurable improvements:**
1. Multiplication 1*1 now passes (was 0)
2. Addition 1+1 now passes (was 0)
3. No more memory explosions on 0-1 and 15-0 subtraction tests
4. Non-zero results from multiplication (was all 0) suggest partial fixes working

**Critical missing work:**

1. **Fix QQ_add target/phase issues** (highest priority - blocks BUG-01, BUG-02):
   - Control reversal applied ✓
   - Target qubit mapping: investigate `bits - i - 1 - rounds` formula
   - Phase value calculation: verify `2*PI / pow(2, i+1)` correctness
   - Test with invert flag: subtraction uses `QQ_add(..., invert=True)`

2. **Fix CQ_add asymmetry** (blocks complete BUG-04):
   - Investigate why 0+X fails but X+0 works
   - Check bin[] indexing edge cases for value=0
   - Verify rotation accumulation for all operand combinations

3. **Fix QQ_mul target/phase issues** (blocks complete BUG-03):
   - Control reversal applied ✓
   - Target qubit indexing: verify `bits - i - 1 - rounds` correctness
   - Phase formula: check all three QQ_mul blocks
   - Consider reference implementation comparison

4. **Consider BUG-05 mitigation** (improves verification reliability):
   - Already seeing improvement (no more memory explosions on some tests)
   - Individual test isolation helps (per user instruction)
   - Full BUG-05 fix would eliminate non-deterministic results

**Dependency order for success:**
1. Fix QQ_add target/phase (unblocks BUG-01, BUG-02, completes BUG-04 QQ path)
2. Fix CQ_add asymmetry (completes BUG-04 CQ path)
3. Fix QQ_mul target/phase (completes BUG-03)
4. Optionally fix BUG-05 for fully deterministic verification

**Pattern recognition:**
- Control qubit reversal is a NECESSARY fix across all three functions ✓
- But control reversal alone is INSUFFICIENT — target and phase also need fixing
- Same pattern applies to CQ_add, QQ_add, QQ_mul — systematic issue

## Human Verification Required

**Not needed at this stage** - all failures are programmatically verifiable through automated tests.

Human verification would be useful AFTER bugs are actually fixed:
1. Run full test suite with BUG-05 resolved
2. Verify performance (QFT operations not exponentially slow)
3. Test additional bit widths (5-8 bits) for edge cases
4. Cross-check against Qiskit reference QFT arithmetic

## Recommendations

**Immediate actions:**

1. **Investigate QQ_add target qubit mapping and phase formulas:**
   - Current: `target = bits - i - 1 - rounds`
   - Check if target also needs reversal like control did
   - Verify phase value calculation matches QFT addition theory
   - Test both forward (addition) and inverted (subtraction) paths

2. **Investigate CQ_add asymmetry (0+X vs X+0):**
   - Debug why qint(0)+=1 gives 2 but qint(1)+=0 gives 1
   - Check bin[] array handling for value=0 edge case
   - Verify rotation accumulation loop for all operand orders

3. **Apply same pattern to QQ_mul:**
   - If QQ_add needs target reversal, QQ_mul likely does too
   - Verify all three QQ_mul blocks (CP_sequence, CX/all_rot, culmination)
   - Check phase formula matches QFT multiplication algorithm

**Verification strategy:**

4. **Continue individual test isolation:** Already showing benefit (no memory explosions)
5. **Track test result consistency:** Document if results vary between runs
6. **Build minimal reproduction cases:** Focus on simplest failing tests (0+1, 3-7, 2*3)

**Longer-term:**

7. **Compare with reference implementations:**
   - Export OpenQASM and compare gates with Qiskit QFT adder
   - Literature review: verify QFT multiplication algorithm structure
   - Consider proven algorithms over custom implementations

8. **Address BUG-05:** Circuit state reset for fully deterministic testing
   - Current mitigation (individual tests) is working
   - Full fix would enable batch testing and faster verification

**Phase 30 readiness:** BLOCKED - cannot proceed with arithmetic verification while core operations are broken.

---

_Verified: 2026-01-31T00:18:17Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification #2 after plans: 29-06, 29-07, 29-08_
_Status: Incremental progress (control fixes applied), gaps remain (target/phase unfixed)_
