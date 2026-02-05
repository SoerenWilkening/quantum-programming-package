---
status: complete
phase: 36-verification-regression
source: [36-01-SUMMARY.md]
started: 2026-02-01T23:50:00Z
updated: 2026-02-02T00:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Equality comparison returns correct results
expected: `qint(3) == qint(3)` returns True, `qint(3) == qint(5)` returns False (no longer inverted by BUG-CMP-01)
result: pass

### 2. Ordering comparison at MSB boundary
expected: `qint(3, width=3) < qint(4, width=3)` returns True (4 is the MSB value for 3-bit, previously failed due to BUG-CMP-02)
result: pass

### 3. Array constructor initializes correct values
expected: `ql.array([3, 5, 7], width=4)` creates elements with values 3, 5, 7 (not all initialized to width value 4 as before BUG-ARRAY-INIT fix)
result: pass

### 4. xfail markers removed from test suite
expected: No active pytest.mark.xfail markers for BUG-CMP-01/02 remain (only historical comments documenting fixes)
result: pass

### 5. Deferred bug markers preserved
expected: xfail markers for deferred bugs (division, mod, conditionals) remain in test files
result: pass

### 6. No test regressions
expected: Running `pytest tests/test_compare.py` produces 1515 passed, 0 failures. Running `pytest tests/test_uncomputation.py` produces 14 passed, 4 failed (all pre-existing), 2 xfailed.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
