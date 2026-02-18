---
phase: 29-c-backend-bug-fixes
plan: 04
subsystem: c-backend
tags: [bugfix, investigation, blocked, subtraction, comparison, qft]

# Dependency graph
requires:
  - phase: 29-03
    provides: BUG-04 CQ_add bit-ordering fix (partial)
affects: [BUG-01-subtraction, BUG-02-comparison, 30-arithmetic-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "QQ_add (qint+qint) has different implementation than CQ_add (classical+qint)"
    - "BUG-04 fix only addressed CQ_add, not QQ_add"

key-files:
  created: []
  modified: []

key-decisions:
  - "BUG-01 and BUG-02 remain blocked - BUG-04 fix incomplete"
  - "QQ_add needs separate investigation for bit-ordering issues"
  - "Measure() is a placeholder returning init value - tests use Qiskit simulation"

patterns-established:
  - "Test failures can reveal incomplete fixes in dependencies"
  - "Different code paths (QQ_add vs CQ_add) require separate fixes"

# Metrics
duration: 26min
completed: 2026-01-30
---

# Phase 29 Plan 04: BUG-01 & BUG-02 Retest (Blocked) Summary

**Investigation confirms BUG-01 and BUG-02 remain blocked - BUG-04 fix incomplete, affecting only CQ_add path, not QQ_add path**

## Performance

- **Duration:** 26 min
- **Started:** 2026-01-30T22:43:18Z
- **Completed:** 2026-01-30T23:09:21Z
- **Tasks:** 2 (investigation only, no fixes applied)
- **Files modified:** 0

## Accomplishments

### Investigation Findings

**BUG-01: Subtraction underflow (3-7 returns 7 instead of 12)**

**Test Results:**
- ✓ `test_sub_7_minus_3`: PASSES (returns 4)
- ✓ `test_sub_5_minus_5`: PASSES (returns 0)
- ✓ `test_sub_15_minus_0`: PASSES (returns 15)
- ✗ `test_sub_3_minus_7`: FAILS (returns 7, expected 12)
- ⊘ `test_sub_0_minus_1`: SKIPPED (BUG-05 memory overflow)

**Root Cause Analysis:**
1. Subtraction uses `__sub__` which creates result qint and calls `a -= other`
2. In-place subtraction (`a -= other`) calls `addition_inplace(other, invert=True)`
3. When `other` is a qint, this uses `QQ_add` (qint+qint addition)
4. `QQ_add` is a DIFFERENT implementation than `CQ_add` (classical+qint)
5. **BUG-04 fix from plan 29-03 only fixed `CQ_add`, NOT `QQ_add`**
6. `QQ_add` likely has similar bit-ordering bug, causing incorrect subtraction

**Evidence:**
- QASM inspection shows result qubits correctly initialized to |3⟩
- QFT operations applied via QQ_add path
- Qiskit simulation produces 7 instead of 12
- Result register (qubits 8-11) = 0111 = 7 (should be 1100 = 12)

**Conclusion:** BUG-01 is NOT a Python-level bug. It's blocked by incomplete BUG-04 fix. `QQ_add` needs bit-ordering correction similar to what was applied to `CQ_add` in plan 29-03.

---

**BUG-02: Less-or-equal comparison (5<=5 returns 0 instead of 1)**

**Test Results:**
- All 6 comparison tests NOT RUN (blocked by BUG-01 dependency)

**Analysis:**
- `__le__` implementation depends on `self -= other` for comparison logic
- Since subtraction is broken (BUG-01), comparison cannot work correctly
- BUG-02 is transitively blocked by BUG-04 incomplete fix

**Conclusion:** Cannot test BUG-02 until BUG-01 is resolved.

---

**Additional Discovery: measure() is a placeholder**

During investigation, discovered that `qint.measure()` (line 673 in qint.pyx) just returns `self.value` (initialization value), not the actual quantum state. This is documented as "simulation placeholder" in comments.

**Impact:** None - test infrastructure uses OpenQASM export + Qiskit simulation, not `measure()`.

## Task Commits

No commits - investigation only, no code changes made.

## Files Created/Modified

None - investigation documented findings without requiring fixes.

## Decisions Made

**Accept blocked status for BUG-01 and BUG-02:**
Both bugs remain blocked by incomplete BUG-04 fix. The fix from plan 29-03 only addressed `CQ_add` (classical+qint addition), but subtraction and comparison use `QQ_add` (qint+qint addition), which has the same bit-ordering issue.

**QQ_add requires separate investigation:**
The QQ_add implementation (IntegerAddition.c lines 132-206) uses a different formula than CQ_add. It doesn't call `two_complement()` or use bin[] arrays. Instead, it directly generates controlled-phase gates in nested loops. The bit-ordering fix will require understanding this formula and applying appropriate corrections.

**Defer to future plan:**
A new gap closure plan is needed to:
1. Investigate QQ_add bit-ordering
2. Apply fix similar to CQ_add approach
3. Retest BUG-01 and BUG-02 after QQ_add fix

## Deviations from Plan

None - plan anticipated either automatic resolution (if BUG-04 fix was complete) or targeted Python fixes (if logic bugs remained). Investigation revealed a third scenario: BUG-04 fix incomplete, affecting only one code path.

## Issues Encountered

### BUG-04 fix scope limitation

**Problem:** Plan 29-03 claimed to fix BUG-04 (QFT addition), but only addressed `CQ_add` function. The `QQ_add` function uses a different implementation and was not fixed.

**Impact:**
- Subtraction with qint operands fails (uses QQ_add path)
- Subtraction with int operands might work (uses CQ_add path) - not tested
- Addition with qint operands likely also fails

**Code Paths:**
```python
# CQ_add path (FIXED in 29-03):
x = qint(3, width=4)
x += 5  # Classical int operand -> CQ_add

# QQ_add path (NOT FIXED):
x = qint(3, width=4)
y = qint(7, width=4)
result = x - y  # qint operand -> QQ_add with invert=True
```

### Test result pattern

**Observation:**
- `7 - 3 = 4` ✓ PASS
- `5 - 5 = 0` ✓ PASS
- `3 - 7 = 7` ✗ FAIL (expected 12)

The failing case is when subtraction would produce a negative result in standard arithmetic. In 4-bit unsigned: `3 - 7 = -4 mod 16 = 12`.

**Hypothesis:** QQ_add with `invert=True` may have issues with:
- Bit ordering in phase rotation formula
- Control/target qubit mapping
- Inverse QFT application

## User Setup Required

None - no code changes made.

## Next Phase Readiness

**BLOCKED for Phase 30 (Arithmetic Verification):**
- BUG-01 (subtraction) remains broken
- BUG-02 (comparison) transitively blocked
- BUG-04 (addition) needs QQ_add fix
- Cannot proceed with arithmetic verification until core operations work

**Blockers:**
1. **CRITICAL:** Fix QQ_add bit-ordering (similar to 29-03 CQ_add fix)
2. **CRITICAL:** Retest BUG-01 after QQ_add fix
3. **CRITICAL:** Test BUG-02 after BUG-01 resolution
4. BUG-05 (circuit state reset) still blocks exhaustive testing

**Recommendations:**
1. **Immediate:** Create plan 29-06 to fix QQ_add bit-ordering
   - Study QQ_add formula (lines 183-190 in IntegerAddition.c)
   - Apply bit-ordering reversal if needed
   - Test with both addition and subtraction cases

2. **After QQ_add fix:** Re-run plan 29-04 tests to verify BUG-01 resolution

3. **Verify fix scope:** Test both code paths:
   - `qint += int` (CQ_add - should already work from 29-03)
   - `qint += qint` (QQ_add - needs fix)

## Technical Debt Created

None - no code changes made.

## Lessons Learned

1. **Code path coverage:** When fixing a bug, identify ALL code paths that might be affected. CQ_add and QQ_add are separate implementations of the same conceptual operation.

2. **Test coverage reveals gaps:** Testing multiple operand types (int vs qint) exposes implementation differences.

3. **Measure() limitations:** The qint.measure() placeholder is fine for development, but critical for test infrastructure to use proper simulation (OpenQASM + Qiskit).

4. **Test result patterns:** When some cases pass and others fail, the pattern often reveals the root cause (here: negative results fail).

5. **Dependency chains:** BUG-02 blocked by BUG-01, BUG-01 blocked by BUG-04, BUG-04 partially fixed. Dependency chains can have unexpected gaps.

---
*Phase: 29-c-backend-bug-fixes*
*Plan: 04*
*Completed: 2026-01-30*
*Status: Investigation complete, bugs remain blocked*
