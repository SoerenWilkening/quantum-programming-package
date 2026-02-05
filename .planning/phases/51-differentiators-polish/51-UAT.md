---
status: diagnosed
phase: 51-differentiators-polish
source: 51-01-SUMMARY.md, 51-02-SUMMARY.md
started: 2026-02-04T12:00:00Z
updated: 2026-02-04T12:02:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Inverse Generation via .inverse()
expected: Calling `.inverse()` on a compiled function returns an inverse wrapper that replays gates in reversed order with adjoint transformations (negated rotation angles). `.inverse().inverse()` returns the original compiled function (round-trip).
result: issue
reported: "Traceback (most recent call last): File 'src/quantum_language/_core.pyx', line 119, in quantum_language._core._set_smallest_allocated_qubit OverflowError: can't convert negative value to unsigned int -- Exception ignored in qint.__del__"
severity: blocker

### 2. Eager Inverse via @ql.compile(inverse=True)
expected: Decorating with `@ql.compile(inverse=True)` eagerly creates the inverse wrapper at decoration time. The compiled function object has a `.inverse()` method available immediately.
result: skipped
reason: User ended testing early

### 3. Inverse Rejects Measurement Gates
expected: Attempting to invert a compiled function that contains measurement gates raises a `ValueError` (measurements are non-reversible).
result: skipped
reason: User ended testing early

### 4. Debug Mode Stderr Output
expected: `@ql.compile(debug=True)` causes each call to print to stderr: `[ql.compile] func_name: HIT/MISS | original=N -> optimized=M gates | cache_entries=K`. First call shows MISS, subsequent calls with same args show HIT.
result: skipped
reason: User ended testing early

### 5. Debug Mode .stats Property
expected: When `debug=True`, the `.stats` property returns a dict with keys `cache_hit`, `original_gate_count`, `optimized_gate_count`, `cache_size`, `total_hits`, `total_misses`. When `debug=False`, `.stats` returns `None`.
result: skipped
reason: User ended testing early

### 6. Nesting Depth Limit
expected: A compiled function calling another compiled function works correctly (inner function's replayed gates become part of outer capture). Exceeding 16 levels of nesting raises `RecursionError`.
result: skipped
reason: User ended testing early

### 7. Comprehensive Test Suite Passes
expected: Running `pytest tests/test_compile.py` shows 62 tests passing (43 existing + 19 new for inverse, debug, nesting, and composition). No regressions.
result: skipped
reason: User ended testing early

## Summary

total: 7
passed: 0
issues: 1
pending: 0
skipped: 6

## Gaps

- truth: "Calling .inverse() on a compiled function returns an inverse wrapper that replays gates in reversed order with adjoint transformations"
  status: fixed
  reason: "User reported: OverflowError: can't convert negative value to unsigned int in _set_smallest_allocated_qubit during qint.__del__ when using .inverse()"
  severity: blocker
  test: 1
  root_cause: "Legacy backward-compatibility tracking in qint.__del__ and _decrement_ancilla performed unsigned int arithmetic without underflow guards. Inverse replay deallocates ancillas in different order, causing negative values passed to unsigned int parameters."
  artifacts:
    - path: "src/quantum_language/qint.pyx"
      issue: "Line 568: _set_smallest_allocated_qubit called without checking for negative result"
    - path: "src/quantum_language/_core.pyx"
      issue: "Line 159: ancilla decrement without underflow guard"
  missing:
    - "Guard condition before _set_smallest_allocated_qubit in qint.__del__"
    - "Guard condition before ancilla decrement in _decrement_ancilla"
  debug_session: ".planning/debug/resolved/51-inverse-overflow.md"
  fix_commit: "f4786c3"
