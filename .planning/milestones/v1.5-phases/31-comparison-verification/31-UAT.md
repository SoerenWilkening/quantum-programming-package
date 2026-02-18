---
status: complete
phase: 31-comparison-verification
source: 31-01-SUMMARY.md, 31-02-SUMMARY.md
started: 2026-01-31T12:00:00Z
updated: 2026-01-31T12:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Comparison test suite collects expected tests
expected: `python3 -m pytest tests/test_compare.py --co -q` collects ~1515 tests covering all 6 operators (eq, ne, lt, gt, le, ge) in both QQ and CQ variants.
result: pass

### 2. Comparison tests pass (zero failures)
expected: `python3 -m pytest tests/test_compare.py -q --tb=line` completes with 0 FAILED. Expect ~987 passed, ~488 xfailed, ~40 xpassed. All known bugs documented as xfail.
result: pass

### 3. BUG-02 regression sub-cases pass
expected: `python3 -m pytest tests/test_compare.py -k "TestBug02Regression" -v` shows 3 tests (MSB index, GC gate reversal, unsigned overflow) all PASSED.
result: pass

### 4. Operand preservation tests pass
expected: `python3 -m pytest tests/test_compare_preservation.py -v --tb=short` shows 108 tests all PASSED. Covers all 6 operators in QQ and CQ variants plus calibration sanity tests.
result: pass

### 5. No regressions in prior test suites
expected: `python3 -m pytest tests/test_add.py tests/test_mul.py -q --tb=line` runs prior phase tests with 0 failures (existing xfails remain xfailed).
result: pass

### 6. BUG-CMP-01 and BUG-CMP-02 documented in test file
expected: `tests/test_compare.py` module docstring describes BUG-CMP-01 (equality inversion) and BUG-CMP-02 (ordering errors). Failure sets are recorded as Python sets in the file.
result: pass

### 7. Calibration-based operand extraction works
expected: `tests/test_compare_preservation.py` contains `_calibrate_extraction` function that empirically detects operand positions per operator. Different operators (especially gt with widened temporaries) have different qubit layouts.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
