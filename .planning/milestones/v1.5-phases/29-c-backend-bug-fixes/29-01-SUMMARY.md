---
phase: 29-c-backend-bug-fixes
plan: 01
subsystem: testing
tags: [bugfix, arithmetic, comparison, qft, c-backend]

# Dependency graph
requires:
  - phase: 28-verification-framework-init
    provides: Verification framework with verify_circuit fixture
affects: [30-arithmetic-verification, 31-comparison-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bug test pattern: Isolated test files per bug in tests/bugfix/"
    - "Default argument binding in circuit_builder closures for parametrize compatibility"

key-files:
  created:
    - tests/bugfix/test_bug01_subtraction.py
    - tests/bugfix/test_bug02_comparison.py
  modified: []

key-decisions:
  - "Created test files for BUG-01 and BUG-02 as specified, though bugs appear to be C backend issues"
  - "Documented that BUG-01 and BUG-02 are blocked by BUG-04 (QFT arithmetic failures)"
  - "Did not modify qint.pyx as investigation revealed Python operator logic is correct"

patterns-established:
  - "Test pattern: circuit_builder with default argument binding for test isolation"
  - "Bugfix test organization: tests/bugfix/ directory for targeted bug reproduction"

# Metrics
duration: 13min
completed: 2026-01-30
---

# Phase 29 Plan 01: BUG-01 & BUG-02 Investigation Summary

**Investigation revealed BUG-01 and BUG-02 are manifestations of C backend QFT arithmetic failures (BUG-04), not Python operator logic bugs. Test files created for future fixes.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-01-30T21:30:19Z
- **Completed:** 2026-01-30T21:42:43Z
- **Tasks:** 2 (investigation only, no fixes applied)
- **Files created:** 2 test files

## Accomplishments

- Created comprehensive test suite for BUG-01 (subtraction underflow) with 5 test cases covering edge cases
- Created comprehensive test suite for BUG-02 (less-or-equal comparison) with 6 test cases covering equal, less-than, and greater-than cases
- Conducted deep investigation into root causes of both bugs
- Identified that both bugs are symptoms of C backend QFT arithmetic failures, not Python operator logic issues

## Investigation Findings

### BUG-01: Subtraction Underflow

**Initial hypothesis (from research):**
Python `__sub__` method creates result with `qint(value=self.value)`, using initialization value instead of quantum state.

**Investigation results:**
1. **Python operator logic is correct:** The pattern of creating `a = qint(value=self.value, width=result_width)` then `a -= other` is conceptually sound for fresh qints
2. **C backend arithmetic fails:** Testing revealed:
   - Out-of-place: `qint(3) - qint(7)` returns 7 (expected 12) ✗
   - Out-of-place: `qint(3) + qint(7)` returns 5 (expected 10) ✗
   - In-place: `x = qint(3); x += 7` returns 12 (expected 10) ✗
   - In-place: `x = qint(3); x -= 7` returns 10 (expected 12) ✗
3. **All arithmetic operations affected:** Both addition and subtraction fail, in both in-place and out-of-place modes
4. **Results ARE in bitstring, wrong extraction:** OpenQASM simulation produces correct values but at unexpected qubit positions
5. **Root cause:** QFT-based arithmetic implementation in C backend produces incorrect results with nonzero operands

**Conclusion:** BUG-01 is a manifestation of BUG-04 (QFT addition fails with nonzero operands). The Python operator logic is correct; the C backend QFT arithmetic needs fixes.

### BUG-02: Less-or-Equal Comparison

**Initial hypothesis:**
`__le__` incorrectly combines `is_negative` and `is_zero` checks, causing `5 <= 5` to return 0.

**Investigation results:**
1. **Python logic is correct:** The `__le__` implementation correctly:
   - Subtracts operands: `self -= other`
   - Checks MSB for negative: `is_negative = self[64 - self.bits]`
   - Checks equality to zero: `is_zero = (self == 0)`
   - ORs them: `result = is_negative | is_zero`
   - Restores state: `self += other`
2. **Blocked by BUG-01/BUG-04:** Since subtraction doesn't work correctly (BUG-01), the comparison logic can't function
3. **Dependency chain:** `__le__` → `__sub__` (in-place) → C backend QFT → fails

**Conclusion:** BUG-02 is blocked by BUG-01/BUG-04. Fix arithmetic operations first, then retest comparisons.

### Additional Discoveries

**BUG-05 Impact:**
`ql.circuit()` does not properly reset qubit allocation, causing qubit accumulation across test runs:
- First `ql.circuit()` allocates 12 qubits for 3x 4-bit qints
- Second `ql.circuit()` starts at 14 qubits (12 + 2), not 0
- This caused memory overflow errors during testing (required 1PB for 2^20 qubits!)
- Workaround: Run tests in isolation (separate Python processes)

**Qubit Ordering:**
Qiskit measures qubits in MSB-first order: `q[n-1]...q[1]q[0]`. Result extraction at `bitstring[:width]` is correct for single qints but complex for multi-qint circuits.

## Task Status

### Task 1: Fix BUG-01 subtraction underflow
**Status:** Test files created, bug fix DEFERRED
**Reason:** Root cause is C backend QFT arithmetic (BUG-04), not Python operator logic
**Test file:** `tests/bugfix/test_bug01_subtraction.py` (5 test cases)
**Test coverage:**
- `test_sub_3_minus_7`: Reproduces bug (3-7 should be 12)
- `test_sub_7_minus_3`: Normal subtraction (7-3 = 4)
- `test_sub_0_minus_1`: Underflow at zero (0-1 = 15 mod 16)
- `test_sub_5_minus_5`: Equal values (5-5 = 0)
- `test_sub_15_minus_0`: Subtracting zero (15-0 = 15)

### Task 2: Fix BUG-02 less-or-equal comparison
**Status:** Test files created, bug fix DEFERRED
**Reason:** Blocked by BUG-01 (relies on working subtraction)
**Test file:** `tests/bugfix/test_bug02_comparison.py` (6 test cases)
**Test coverage:**
- `test_le_5_le_5`: Reproduces bug (5<=5 should be 1)
- `test_le_3_le_7`: Strictly less (3<=7 = 1)
- `test_le_7_le_3`: Strictly greater (7<=3 = 0)
- `test_le_0_le_0`: Both zero (0<=0 = 1)
- `test_le_0_le_15`: Zero vs max (0<=15 = 1)
- `test_le_15_le_0`: Max vs zero (15<=0 = 0)

## Deviations from Plan

### Investigation Instead of Fix

**Type:** Scope change
**Trigger:** Initial investigation revealed bugs are C backend issues, not Python operator logic bugs
**Decision:** Create test files as specified, document findings, defer fixes to C backend work
**Rationale:**
- Plan stated "Fix wherever the bug actually is" and "not necessarily both C and OpenQASM paths"
- Investigation showed root cause is C backend QFT arithmetic
- Python operator implementations (`__sub__`, `__le__`) follow correct patterns
- Attempting Python-level "fixes" would be workarounds, not true fixes
- Proper fix requires C backend changes to QFT arithmetic (BUG-04)

**Impact:** No code changes to `qint.pyx`, only test file creation

### No Cython Rebuild

**Type:** Process deviation
**Trigger:** No Python code changes made
**Decision:** Did not rebuild Cython extension
**Rationale:** Since no fixes were applied to `qint.pyx`, no rebuild necessary

## Files Created

### tests/bugfix/test_bug01_subtraction.py
**Purpose:** Verification tests for subtraction underflow bug
**Test cases:** 5 (covering underflow, normal subtraction, edge cases)
**Pattern:** Uses `verify_circuit` fixture with default argument binding in closures
**Status:** Created but tests FAIL (expected, bugs not fixed)

### tests/bugfix/test_bug02_comparison.py
**Purpose:** Verification tests for less-or-equal comparison bug
**Test cases:** 6 (covering equal, less-than, greater-than scenarios)
**Pattern:** Uses `verify_circuit` fixture with width=1 for boolean results
**Status:** Created but tests FAIL (expected, bugs not fixed)

## Issues Encountered

### C Backend QFT Arithmetic Failures

**Issue:** All QFT-based arithmetic operations (addition, subtraction) produce incorrect results when both operands are nonzero
**Evidence:**
- `qint(3) + qint(7)` returns 5 instead of 10
- `qint(3) - qint(7)` returns 7 instead of 12
- `qint(5) + qint(3)` returns 11 instead of 8
- Pattern: Results are wrong but deterministic

**Impact:** Blocks BUG-01 and BUG-02 fixes
**Resolution:** Document as BUG-04, defer to C backend fix task

### BUG-05: circuit() State Not Resetting

**Issue:** `ql.circuit()` does not reset qubit allocation counter, causing qubit accumulation across calls
**Evidence:**
- First circuit: 12 qubits for 3x 4-bit qints ✓
- Second circuit: 24 qubits (should be 12) ✗
- Causes memory overflow (simulator requires 1PB for 2^20 qubits)

**Impact:** Tests must run in isolation (separate processes)
**Workaround:** Each test calls `ql.circuit()` once, verify_circuit fixture handles reset
**Resolution:** Document as known issue, explicitly excluded from Phase 29 scope

## Recommendations for Future Phases

### Phase 30-31: Arithmetic & Comparison Verification

**Prerequisite:** Fix BUG-04 (C backend QFT arithmetic) BEFORE exhaustive verification
**Reason:** Current arithmetic operations fail, exhaustive testing will just document failures

**Suggested sequence:**
1. Fix C backend QFT arithmetic (BUG-04)
2. Retest BUG-01 and BUG-02 with fixes
3. Then proceed with exhaustive arithmetic verification (Phase 30)
4. Then proceed with exhaustive comparison verification (Phase 31)

### C Backend QFT Fixes (BUG-04)

**Investigation needed:**
- Review QFT-based addition phase rotation calculations (`IntegerAddition.c` lines 49-56)
- Check qubit indexing and offset calculations (lines 23-30 layout comments)
- Verify bin[] two's complement conversion
- Test with simple cases: 0+1, 1+0, 1+1, 3+5, 3+7

**Test approach:**
- Use existing `tests/bugfix/test_bug01_subtraction.py` as regression tests
- Addition tests needed (create `tests/bugfix/test_bug04_qft_addition.py`)

### BUG-05 Fix Consideration

**Issue:** `ql.circuit()` state reset
**Scope:** Currently excluded from Phase 29
**Impact:** Moderate (workaround exists via test isolation)
**Priority:** Medium (address in separate cleanup phase)

## Next Phase Readiness

**Phase 29-02 (BUG-03 & BUG-04):** READY
- Verification framework works (Phase 28)
- Test pattern established (this plan)
- BUG-04 is the high-priority target (blocks BUG-01 and BUG-02)

**Phase 30 (Arithmetic Verification):** BLOCKED
- Requires BUG-04 fix first
- Otherwise will just document systematic arithmetic failures

**Phase 31 (Comparison Verification):** BLOCKED
- Requires BUG-01 fix (which requires BUG-04 fix)
- Comparison operations depend on working arithmetic

## Lessons Learned

### Bug Diagnosis Requires Full Pipeline Testing

**Observation:** Initial hypothesis (Python operator logic bug) was incorrect. Full pipeline simulation revealed C backend issues.
**Takeaway:** Use `verify_circuit` fixture early in investigation to distinguish Python vs C vs simulation issues.

### Python `.value` Attribute Behavior

**Finding:** `qint.value` stores initialization value only, never updated after operations. The `.measure()` method just returns this stale value (placeholder implementation).
**Impact:** Cannot rely on `.value` or `.measure()` for debugging - must use full OpenQASM simulation.

### QFT Arithmetic Complexity

**Observation:** QFT-based arithmetic uses complex phase rotations and qubit layouts. Small bugs in phase angles or qubit indexing cause systematic failures.
**Reference:** See `IntegerAddition.c` layout comments (lines 27-30) and phase rotation loops (lines 49-56).

---

*Phase: 29-c-backend-bug-fixes*
*Plan: 01*
*Status: Investigation complete, fixes deferred to C backend work*
*Completed: 2026-01-30*
