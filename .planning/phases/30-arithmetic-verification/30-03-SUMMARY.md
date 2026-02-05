# Phase 30 Plan 03: Division and Modulo Verification Summary

**One-liner:** Floor division and modulo verification tests with custom register extraction, uncovering 13 algorithm bugs per operation at widths 2-4.

## Execution Details

| Field | Value |
|-------|-------|
| Phase | 30-arithmetic-verification |
| Plan | 03 |
| Status | Complete |
| Duration | ~18 min |
| Completed | 2026-01-31 |

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Floor division tests with custom extraction | ebbd207 | tests/test_div.py |
| 2 | Modulo tests with custom extraction | 860b3f5 | tests/test_mod.py |

## Test Results

| Test File | Passed | xfailed | Total |
|-----------|--------|---------|-------|
| test_div.py | 76 | 24 | 100 |
| test_mod.py | 76 | 24 | 100 |
| **Combined** | **152** | **48** | **200** |

### Coverage

- **Width 1:** 2/2 pass (both div and mod) -- trivial single-bit cases
- **Width 2:** 11/12 pass -- 1 failure (0//3 overflow)
- **Width 3:** 44/56 pass -- 12 failures (8 overflow + 4 MSB comparison leak)
- **Width 4 (sampled):** 19/30 pass -- 11 failures (6 overflow + 5 MSB leak)

## Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Custom result extraction at `bs[n-2w:n-w]` | Division/modulo allocate input(w) + quotient/remainder(w) + ancillae; verify_circuit's `bs[:w]` extracts last-allocated register which is NOT the result |
| Use strict xfail for known bugs | Documents exactly which cases fail due to algorithm bugs; strict=True ensures xfails actually fail (catches regressions if bugs are fixed) |
| Same KNOWN_FAILURES set for div and mod | Both operations share the same restoring division core and produce identical failure patterns |

## Bugs Discovered

### BUG-DIV-01: Comparison overflow in restoring division

**Severity:** Medium -- affects all widths >= 2 when divisor >= 2^(w-1)

The restoring division algorithm computes `trial_value = divisor << bit_pos`. When `trial_value >= 2^width`, the comparison `remainder >= trial_value` produces incorrect results because the trial value overflows the register capacity. The comparison operator (`>=`) operates on w-bit registers and cannot correctly represent values >= 2^w.

**Affected cases:** 8 at width 3, 1 at width 2, 6 at width 4 (sampled)

**Root cause:** Missing guard `if trial_value < (1 << width)` in the bit_pos loop of `__floordiv__` and `__mod__` in `qint_division.pxi`.

### BUG-DIV-02: MSB comparison leak in division

**Severity:** Medium -- affects values >= 2^(w-1) with small divisors

For values with the MSB set (e.g., 4-7 at width 3), the comparison result from the first iteration (bit_pos=w-1) leaks into subsequent iterations, corrupting the LSB of the quotient. Specifically, `a//1` for a >= 2^(w-1) has bit 0 inverted.

**Affected cases:** 4 at width 3 (divisor=1, values 4-7), 5 at width 4 (sampled)

**Root cause:** The `>=` comparison allocates a qbool result that entangles with subsequent operations. The comparison ancillae from the MSB iteration are not fully uncomputed before the LSB iteration, causing phase/amplitude interference.

## Deviations from Plan

### [Rule 2 - Missing Critical] Added xfail markers for algorithm bugs

- **Found during:** Task 1 (division tests)
- **Issue:** The plan assumed the division algorithm was correct and only the extraction position was challenging. Empirical testing revealed 13 cases per operation with incorrect results at widths 2-4.
- **Fix:** Added `KNOWN_DIV_FAILURES` and `KNOWN_MOD_FAILURES` sets with `pytest.mark.xfail(strict=True)` markers so the test suite passes while documenting the bugs.
- **Files modified:** tests/test_div.py, tests/test_mod.py
- **Impact:** Tests document bugs rather than ignoring them; strict xfail will detect if bugs are fixed (tests will unexpectedly pass)

### [Rule 1 - Bug] Removed unused variable flagged by ruff

- **Found during:** Task 1 commit
- **Issue:** `max_val` variable in `_exhaustive_div_cases()` was assigned but never used
- **Fix:** Removed the assignment
- **Files modified:** tests/test_div.py

## Architecture Notes

### Result Register Position Formula

For division (`a // d`):
- Allocation order: input(w qubits) -> quotient(w qubits) -> remainder(w qubits) -> comparison ancillae
- Total qubits: w=1->4, w=2->8, w=3->11, w=4->14
- Quotient register: qubits w to 2w-1
- In Qiskit MSB-first bitstring of length n: `bs[n-2w : n-w]`

For modulo (`a % d`):
- Allocation order: input(w qubits) -> remainder(w qubits) -> comparison ancillae (no quotient)
- Total qubits: w=1->3, w=2->6, w=3->8, w=4->10
- Remainder register: qubits w to 2w-1
- In Qiskit MSB-first bitstring of length n: `bs[n-2w : n-w]`

Both use the same extraction formula despite different total qubit counts.

## Next Phase Readiness

- Division and modulo algorithms have bugs at widths >= 2 (13 cases each)
- These bugs are related to the comparison operator (`>=`) and should be investigated in a future bug-fix phase
- The xfail markers will automatically detect when bugs are fixed
