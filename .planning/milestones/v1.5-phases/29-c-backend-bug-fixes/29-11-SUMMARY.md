---
phase: 29-c-backend-bug-fixes
plan: 11
subsystem: c-backend-multiplication
tags: [bugfix, QFT, multiplication, CQ_mul, Draper]
depends_on: [29-09, 29-10]
provides:
  - "Fixed CQ_mul classical-quantum multiplication (100% correct)"
  - "Identified QQ_mul deeper algorithmic issues beyond simple target reversal"
affects:
  - "Phase 29-12 or future work: QQ_mul algorithm redesign needed"
tech-stack:
  patterns:
    - "Draper QFT multiplication with controlled phase rotations"
    - "Target qubit offset encodes positional weight (no separate multiplier needed)"
key-files:
  modified:
    - c_backend/src/IntegerMultiplication.c
decisions:
  - "Fix CQ_mul only; QQ_mul requires deeper algorithm redesign"
  - "Remove pow(2,bits-1-bit) from CQ_mul value formula (double-counting fix)"
metrics:
  duration: "~38 min"
  completed: "2026-01-31"
---

# Phase 29 Plan 11: Multiplication Target Qubit Fix Summary

Fixed CQ_mul (classical * quantum multiplication) by correcting target qubit mapping and removing double-counted positional weight factor. QQ_mul (quantum * quantum) changes from plan were investigated but found insufficient -- the algorithm requires deeper redesign.

## Changes Made

### CQ_mul Fix (Verified Correct)

**Target qubit mapping:** Changed `bits - i - 1 - rounds` to `rounds + i` to match the textbook QFT convention established in plan 29-09.

**Value formula fix:** Removed `pow(2, bits-1-bit)` multiplicative factor. This factor was double-counting the control qubit's positional weight: the target offset through `rounds` already encodes the positional significance, so the explicit `pow(2, bits-1-bit)` caused phase angles to exceed 2*PI and wrap around to incorrect values.

**Result:** CQ_mul passes 10/10 tests including all combinations of operands and bit widths tested (1*1, 1*2, 2*1, 1*3, 3*1, 2*2, 2*3, 3*2, 5*3, 7*2).

### CP_sequence Loop Fix (Cosmetic)

Fixed inverted path loop condition from `i < l2` to `(fac > 0 ? i < l2 : i > l2)`. The original condition would never execute the inverted path (dead code). All current callers use `inverted=false`, so this has no functional impact.

### QQ_mul Investigation (No Change Committed)

The plan prescribed applying the same target reversal from QQ_add to QQ_mul's CP_sequence and block 2. Extensive testing showed:

- **CP_sequence target fix alone:** Breaks 0*5 (was 0, becomes 11). Worse overall.
- **Block 2 target fix (`bits-i-1` to `i`):** Fixes 2*2 but breaks 1*1. Net neutral.
- **All plan changes combined:** 2/5 (0*5, 2*2) vs baseline 2/5 (0*5, 1*1). Net neutral with different tests passing.
- **Root cause analysis:** QQ_mul uses a complex CCP decomposition (controlled-controlled-phase) where block 1 (CP_sequence) and block 2 (CX + all_rot + culmination CP) must be internally consistent. The simple analogy to QQ_add's target reversal is insufficient because the multiplication decomposition involves different mathematical relationships between blocks than the simple addition pattern.

**Decision:** Keep QQ_mul at baseline rather than trade one set of passing tests for another. The QQ_mul algorithm needs a deeper redesign that goes beyond target qubit mapping.

## Test Results

### QQ_mul (qint * qint) -- 2/5 (baseline, unchanged)
| Test | Expected | Got | Status |
|------|----------|-----|--------|
| 0*5 (4bit) | 0 | 0 | PASS |
| 1*1 (2bit) | 1 | 1 | PASS |
| 2*3 (4bit) | 6 | 15 | FAIL |
| 2*2 (3bit) | 4 | 1 | FAIL |
| 3*3 (4bit) | 9 | 2 | FAIL |

### CQ_mul (int * qint) -- 10/10 (FIXED from ~50%)
| Test | Expected | Got | Status |
|------|----------|-----|--------|
| 1*1 (2bit) | 1 | 1 | PASS |
| 1*2 (3bit) | 2 | 2 | PASS |
| 2*1 (3bit) | 2 | 2 | PASS |
| 1*3 (3bit) | 3 | 3 | PASS |
| 3*1 (3bit) | 3 | 3 | PASS |
| 2*2 (3bit) | 4 | 4 | PASS |
| 2*3 (4bit) | 6 | 6 | PASS |
| 3*2 (4bit) | 6 | 6 | PASS |
| 5*3 (4bit) | 15 | 15 | PASS |
| 7*2 (4bit) | 14 | 14 | PASS |

### Regression Tests -- No regressions
- Addition (3+5=8): PASS
- Subtraction (3-7=12): PASS

## Deviations from Plan

### [Rule 1 - Bug] CQ_mul value formula had double-counted positional weight

- **Found during:** Task 1 investigation
- **Issue:** Plan specified only target reversal (`bits-i-1-rounds` to `rounds+i`). Investigation revealed that the `pow(2, bits-1-bit)` factor in CQ_mul's value computation was double-counting the control qubit's positional weight -- the rounds-based target offset already encodes this weight. This caused phase angles to wrap around 2*PI for control qubits with weight >= 2.
- **Fix:** Removed the redundant `pow(2, bits-1-bit)` factor from CQ_mul value formula.
- **Files modified:** c_backend/src/IntegerMultiplication.c
- **Commit:** 192dc47

### [Rule 1 - Bug] QQ_mul target changes were net-neutral, kept baseline

- **Found during:** Task 1 investigation
- **Issue:** Plan prescribed CP_sequence and QQ_mul block 2 target changes. Testing showed these changes trade one set of passing tests for another (2/5 either way). The QQ_mul CCP decomposition algorithm has internal consistency requirements between blocks that the simple target reversal doesn't satisfy.
- **Decision:** Keep QQ_mul at baseline. Document for future deeper algorithm redesign.
- **No change committed for QQ_mul.**

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Fix CQ_mul value formula (remove pow factor) | Double-counting caused phase wrapping; CQ_mul now 100% correct |
| Keep QQ_mul unchanged from baseline | Target reversal alone is insufficient; trades one set of failures for another |
| QQ_mul needs deeper algorithm redesign | CCP decomposition has block-to-block consistency requirements beyond target mapping |

## Next Phase Readiness

- CQ_mul is now fully correct for the textbook QFT convention
- QQ_mul remains at 2/5 baseline -- a proper fix requires understanding the full CCP decomposition mathematics and ensuring all blocks are consistent with the no-swap QFT
- BUG-05 (circuit cache contamination) continues to make QQ_mul testing unreliable when running multiple tests in same process
