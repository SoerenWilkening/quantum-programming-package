# Phase 33 Plan 03: Array Operation Verification Summary

**One-liner:** Verified ql.array reductions (sum, AND, OR) and element-wise ops through full pipeline; all blocked by BUG-ARRAY-INIT constructor bug that ignores user data and element widths.

## Results

| Metric | Value |
|--------|-------|
| Tests created | 14 |
| Passed | 5 (calibration + manual sanity) |
| xfailed | 7 (BUG-ARRAY-INIT) |
| xpassed | 2 (single-element cases where width==value accidentally) |
| Unexpected failures | 0 |
| Duration | ~6 min |
| Completed | 2026-02-01 |

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create array verification tests with calibration | 40aa3fc | tests/test_array_verify.py |
| 2 | Feature status summary | (this document) | 33-03-SUMMARY.md |

## Key Findings

### Finding 1: BUG-ARRAY-INIT Blocks All Array Value Tests

The `ql.array([values], width=w)` constructor has a confirmed bug: it creates `qint(self._width)` instead of `qint(value, width=self._width)`. This means:
- The width parameter is passed as the VALUE to qint
- All elements receive the same quantum value (= width), regardless of user data
- Element widths are auto-inferred from the width value's bit_length(), not the specified width
- Example: `ql.array([1, 2], width=3)` creates two 2-bit qints both with value 3 (instead of two 3-bit qints with values 1 and 2)

The correct fix would be `q = qint(value, width=self._width)` in `qarray.pyx` line 303, but this is outside phase 33 verification scope.

### Finding 2: ql.array Cannot Wrap Existing qint Objects

Attempting `ql.array([qint_a, qint_b])` fails with AttributeError because qint has no `.value` attribute accessible from Python. The constructor tries `q.value = value.value` which crashes. This prevents the obvious workaround of constructing elements manually then wrapping.

### Finding 3: Underlying Operations Work Correctly

Manual sanity tests confirm that addition (`qint + qint`), AND (`qint & qint`), and OR (`qint | qint`) all produce correct results through the full pipeline when qints are constructed directly. The issue is exclusively in array initialization, not in the reduction/element-wise operation logic.

### Finding 4: Single-Element Array Edge Cases Accidentally Pass

Single-element arrays where the intended value equals the width parameter accidentally pass:
- `ql.array([3], width=3)` creates `qint(3)` with quantum value 3 -- matches expected value 3
- `ql.array([2], width=2)` creates `qint(2)` with quantum value 2 -- matches expected value 2

These are marked with non-strict xfail so xpass is acceptable.

## Feature Status Table (VADV-03)

| Feature | Status | Tests | Blocking Bugs | Notes |
|---------|--------|-------|---------------|-------|
| Array sum (2-elem) | XFAIL | test_array_sum_2elem | BUG-ARRAY-INIT | Elements initialized wrong |
| Array sum (1-elem) | XPASS | test_array_sum_1elem | BUG-ARRAY-INIT | Accidentally passes (width==value) |
| Array sum (overflow) | XFAIL | test_array_sum_overflow | BUG-ARRAY-INIT | Elements initialized wrong |
| Array AND (2-elem) | XFAIL | test_array_and_2elem | BUG-ARRAY-INIT | Elements initialized wrong |
| Array AND (1-elem) | XFAIL | test_array_and_1elem | BUG-ARRAY-INIT | Width 2, value 3 mismatch |
| Array OR (2-elem) | XFAIL | test_array_or_2elem | BUG-ARRAY-INIT | Elements initialized wrong |
| Array OR (1-elem) | XPASS | test_array_or_1elem | BUG-ARRAY-INIT | Accidentally passes (width==value) |
| Element-wise add | XFAIL | test_array_add_scalar | BUG-ARRAY-INIT | Elements initialized wrong |
| Element-wise sub | XFAIL | test_array_sub_scalar | BUG-ARRAY-INIT | Elements initialized wrong |
| Manual sum | PASS | test_manual_sum | None | Pipeline works without array bug |
| Manual AND | PASS | test_manual_and | None | Pipeline works without array bug |
| Manual OR | PASS | test_manual_or | None | Pipeline works without array bug |

## Deviations from Plan

None -- plan executed as written.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Non-strict xfail for all array tests | BUG-ARRAY-INIT; some single-element cases accidentally pass |
| Added manual sanity tests | Proves reduction operations work when array init bug is absent |
| Documented both BUG-ARRAY-INIT and qint wrapping limitation | Two separate issues prevent correct array testing |

## Next Phase Readiness

Phase 33 is the final phase. All three VADV verification plans are complete:
- VADV-01 (Uncomputation): Tested in 33-01
- VADV-02 (Conditionals): 12 pass, 2 xfail (BUG-COND-MUL-01)
- VADV-03 (Arrays): 5 pass, 7 xfail, 2 xpass (BUG-ARRAY-INIT)

**Blocking bugs for array operations:** BUG-ARRAY-INIT must be fixed before array operations can be verified end-to-end. The fix is a one-line change in `qarray.pyx`.

---
*Summary created: 2026-02-01*
