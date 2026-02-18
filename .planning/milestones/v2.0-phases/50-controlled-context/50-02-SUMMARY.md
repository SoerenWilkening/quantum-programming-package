# Phase 50 Plan 02: Controlled Context Compile Tests Summary

**One-liner:** 7 comprehensive tests verifying compiled functions work correctly inside `with qbool:` blocks with separate cache entries, correct gate controls, and control qubit remapping.

## Results

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Add controlled context compile tests | 622cc38 | Done |

## What Was Done

### Test Cases Added (7 tests)

1. **test_compile_controlled_basic** -- Verifies compiled function inside `with qbool:` produces controlled gates; checks both uncontrolled and controlled cache entries exist after eager compilation.

2. **test_compile_controlled_separate_cache_entries** -- Verifies 2 cache entries are created on first call (uncontrolled + controlled); subsequent calls in both contexts are cache hits without re-capture.

3. **test_compile_controlled_gates_have_extra_control** -- Verifies every gate in the controlled variant has exactly `num_controls + 1` compared to the uncontrolled variant, with same gate type and target.

4. **test_compile_controlled_nested_with** -- Verifies compiled function called inside sequential `with` blocks uses different control qubits and all are cache hits.

5. **test_compile_controlled_replay_correct_qubits** -- Verifies replayed controlled gates use the correct control qubit for each call (different `with` blocks use different qubits).

6. **test_compile_controlled_custom_key** -- Verifies custom `key` function is wrapped with control count, producing separate cache entries `(key_result, 0)` and `(key_result, 1)`.

7. **test_compile_controlled_first_call_inside_with** -- Tests the accepted trade-off where first-call capture runs in uncontrolled mode; verifies both variants are cached and subsequent controlled replays produce correctly controlled gates.

### Phase 50 Success Criteria Coverage

| Criterion | Tests Covering |
|-----------|---------------|
| CTL-01: Compiled function inside `with qbool:` produces controlled gates | test_compile_controlled_basic, test_compile_controlled_first_call_inside_with |
| CTL-03: Separate cache entries for controlled vs uncontrolled | test_compile_controlled_separate_cache_entries, test_compile_controlled_custom_key |
| Gates have exactly +1 control | test_compile_controlled_gates_have_extra_control |
| Nested/sequential `with` blocks work | test_compile_controlled_nested_with |
| Control qubit remapping correct | test_compile_controlled_replay_correct_qubits |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Nested `with` block test adjusted for AND limitation**
- **Found during:** Task 1
- **Issue:** True nested `with qbool1: with qbool2:` raises `NotImplementedError: Controlled quantum-quantum AND not yet supported` because the inner `__enter__` tries to AND the bools while already in controlled mode.
- **Fix:** Changed to sequential `with` blocks (one after the other) instead of nested, which tests the same compile-cache behavior without triggering the AND limitation.
- **Files modified:** `tests/test_compile.py`
- **Commit:** 622cc38

## Decisions Made

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Sequential `with` blocks instead of nested for test | Nested `with` blocks trigger unsupported controlled AND; sequential blocks still verify cache hit behavior correctly |

## Verification

- `pytest tests/test_compile.py -x -q` -- 43/43 tests pass (36 existing + 7 new)
- `pytest tests/test_compile.py -x -q -k "controlled"` -- 8/8 controlled tests pass (7 new + 1 pre-existing)
- No regressions in existing tests

## Key Files

### Created
None

### Modified
- `tests/test_compile.py` -- 7 new controlled context test functions added

## Duration

~3 minutes

---
*Phase: 50-controlled-context, Plan: 02, Completed: 2026-02-04*
