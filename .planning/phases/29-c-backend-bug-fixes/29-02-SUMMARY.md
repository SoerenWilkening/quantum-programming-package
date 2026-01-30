---
phase: 29-c-backend-bug-fixes
plan: 02
subsystem: c-backend
tags: [bugfix, c, memory-allocation, qft, addition, multiplication]

# Dependency graph
requires:
  - phase: 28-verification-framework-init
    provides: Verification test framework and fixtures
provides:
  - BUG-03 segfault fix: increased memory allocation in multiplication functions
  - BUG-04 partial fix: corrected QFT addition phase rotation formula
affects: [30-arithmetic-verification, future-multiplication-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Conservative memory allocation: use MAXLAYERINSEQUENCE instead of formula-based calculations for complex circuits"
    - "QFT addition formula: each qubit receives phases from all lower-indexed bits"

key-files:
  created:
    - tests/bugfix/test_bug03_multiplication.py
    - tests/bugfix/test_bug04_qft_addition.py
  modified:
    - c_backend/src/IntegerMultiplication.c
    - c_backend/src/IntegerAddition.c

key-decisions:
  - "Used MAXLAYERINSEQUENCE for num_layer allocation in multiplication functions (conservative but safe)"
  - "Increased per-layer gate allocation from 2*bits to 10*bits"
  - "Fixed QFT addition to apply phases to all qubits (not just subset)"
  - "Accepted partial fixes per context: segfault fixed, logic bugs remain"

patterns-established:
  - "Bugfix testing pattern: create tests/bugfix/test_bugXX_name.py with targeted test cases"
  - "Memory allocation strategy: when formula unclear, use MAXLAYERINSEQUENCE"

# Metrics
duration: 28min
completed: 2026-01-30
---

# Phase 29 Plan 02: C Backend Bug Fixes (BUG-03, BUG-04) Summary

**Fixed multiplication segfault (BUG-03) via conservative memory allocation; partially fixed QFT addition (BUG-04) with corrected phase rotation formula**

## Performance

- **Duration:** 28 min
- **Started:** 2026-01-30T21:30:21Z
- **Completed:** 2026-01-30T21:58:01Z
- **Tasks:** 2
- **Files modified:** 4 (2 C files, 2 test files)

## Accomplishments

- **BUG-03 FIXED:** Multiplication no longer segfaults across bit widths 1-4
  - Changed num_layer allocation from formula-based to MAXLAYERINSEQUENCE
  - Increased per-layer gate allocation from 2*bits to 10*bits
  - All 4 multiplication functions updated: CQ_mul, QQ_mul, cCQ_mul, cQQ_mul

- **BUG-04 PARTIALLY FIXED:** QFT addition corrected for some cases
  - Fixed phase rotation loop to iterate over all qubits (not just bits-i)
  - Corrected rotation application indexing (direct instead of reversed)
  - Added constraint: higher bits don't affect lower qubits
  - Results: 0+1 and 7+8 now work (were failing), but 1+1, 3+5, 8+8 still fail

- Created targeted verification tests for both bugs in tests/bugfix/ directory

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix BUG-03 multiplication segfault** - `4d2db15` (fix)
2. **Task 2: Fix BUG-04 QFT addition** - `4e5496a` (fix, partial)

## Files Created/Modified

- `c_backend/src/IntegerMultiplication.c` - Memory allocation fixes for all mul functions
- `c_backend/src/IntegerAddition.c` - QFT phase rotation formula corrections
- `tests/bugfix/test_bug03_multiplication.py` - 5 multiplication test cases
- `tests/bugfix/test_bug04_qft_addition.py` - 7 addition test cases

## Decisions Made

- **Conservative allocation strategy:** When exact requirements unclear, use MAXLAYERINSEQUENCE (10000 layers) instead of formula-based calculations. Trades memory for reliability.

- **Partial fix acceptance:** Per context decisions, accepted partial fixes for both bugs:
  - BUG-03: Segfault eliminated (primary goal achieved), logic bugs remain
  - BUG-04: Some cases fixed (0+1, 7+8), others still failing (1+1, 3+5, 8+8)

- **Separate commits per bug:** Even though both in same files, maintained atomic commits for independent revertability

- **Test organization:** Created tests/bugfix/ subdirectory for bug-specific tests, separate from verification test suites

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Increased per-layer allocation beyond minimum**
- **Found during:** Task 1 (multiplication fix)
- **Issue:** Original formula `2*bits` gates per layer insufficient for complex multiplication circuits
- **Fix:** Increased to `10*bits` after testing showed `3*bits` and `4*bits` still segfaulted
- **Files modified:** c_backend/src/IntegerMultiplication.c
- **Rationale:** Critical for preventing segfaults - better to over-allocate than crash

**2. [Rule 3 - Blocking] Changed num_layer allocation strategy**
- **Found during:** Task 1 (multiplication fix)
- **Issue:** Formula `bits * (2 * bits + 6) - 1` insufficient for actual layer count
- **Fix:** Used MAXLAYERINSEQUENCE (10000) like cQQ_mul already does
- **Files modified:** c_backend/src/IntegerMultiplication.c (CQ_mul, QQ_mul, cCQ_mul)
- **Rationale:** Blocking issue - couldn't proceed without fixing layer allocation

**3. [Rule 1 - Bug] Fixed QFT rotation loop bounds**
- **Found during:** Task 2 (addition fix)
- **Issue:** Inner loop `j < bits - i` only applied phases to subset of qubits
- **Fix:** Changed to `j < bits` with constraint `j >= bit_idx` (higher bits don't affect lower qubits)
- **Files modified:** c_backend/src/IntegerAddition.c (CQ_add, cCQ_add)
- **Rationale:** Core bug in QFT formula - must apply phases to all affected qubits

**4. [Rule 1 - Bug] Fixed rotation application indexing**
- **Found during:** Task 2 (addition fix)
- **Issue:** Rotations applied with reversed indexing `rotations[bits-i-1]` instead of `rotations[i]`
- **Fix:** Changed application to direct indexing `rotations[i]`
- **Files modified:** c_backend/src/IntegerAddition.c (CQ_add, cCQ_add)
- **Rationale:** Mismatch between how rotations computed vs applied

---

**Total deviations:** 4 auto-fixed (all critical/blocking bugs discovered during implementation)

## Issues Encountered

### BUG-03: Multiplication segfault

**Problem:** Initial allocations of `3*bits` and `4*bits` per layer still caused segfaults.

**Resolution:** Increased to `10*bits` and adopted MAXLAYERINSEQUENCE pattern. Segfault eliminated, though multiplication logic itself still returns incorrect results (returns 0 for most cases).

**Remaining:** Multiplication produces wrong results - this is a separate logic bug beyond the memory allocation fix scope.

### BUG-04: QFT addition

**Problem:** After initial fix, addition still failed for some cases (1+1, 3+5, 8+8).

**Resolution:** Partially fixed - 2 of 7 test cases now pass that were failing before. Remaining failures suggest deeper issues with bit ordering or two's complement conversion.

**Remaining:** 3 test cases still fail with off-by-2 or off-by-4 errors. Further investigation needed into:
- two_complement() bit indexing
- Qubit layout mapping
- Possible sign handling issues

### BUG-05 encountered (out of scope)

**Problem:** After fixes, running multiple tests in sequence triggers massive memory allocation (requesting 18 exabytes).

**Analysis:** This is BUG-05 (circuit state reset bug) discovered in Phase 28 and explicitly excluded from Phase 29 scope per context decisions.

**Impact:** Cannot run full test suite without hitting memory limits. Individual tests work when run in isolation.

## User Setup Required

None - all changes are C backend fixes requiring only rebuild via `python3 setup.py build_ext --inplace`.

## Next Phase Readiness

**Partially ready for Phase 30 (Arithmetic Verification):**
- Multiplication and addition tests can be written, but will hit memory issues when run in batches
- Individual operation verification works
- BUG-05 (circuit reset) must be addressed before exhaustive testing

**Blockers for Phase 30:**
- BUG-05: Circuit state accumulation causes memory explosion
- Multiplication logic: Returns 0 instead of correct products
- QFT addition logic: 3 of 7 cases still failing

**Recommendations:**
- Address BUG-05 before Phase 30 (or run tests in isolation)
- Further investigation needed on multiplication implementation
- QFT addition needs bit-ordering analysis for remaining cases

---
*Phase: 29-c-backend-bug-fixes*
*Plan: 02*
*Completed: 2026-01-30*
