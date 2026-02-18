---
phase: 40
plan: 01
subsystem: qarray
tags: [optimization, qarray, classical-operands, performance]
dependency-graph:
  requires: []
  provides: ["optimized qarray classical element-wise operations"]
  affects: []
tech-stack:
  added: []
  patterns: ["pass classical int directly to qint operators via CQ_* C backend"]
key-files:
  created: []
  modified: ["src/quantum_language/qarray.pyx"]
decisions:
  - id: D-40-01
    choice: "Remove all temporary qint wrapping in _inplace_binary_op for classical operands"
    reason: "All 6 qint in-place operators (__iadd__, __isub__, __imul__, __iand__, __ior__, __ixor__) already handle int natively via CQ_* C backend calls"
metrics:
  duration: "~5 min"
  completed: "2026-02-02"
---

# Phase 40 Plan 01: Array Classical Optimization Summary

**Eliminate temporary qint allocations in qarray _inplace_binary_op by passing int directly to qint operators which handle int natively via CQ_* C backend calls.**

## What Was Done

### Task 1: Remove unnecessary qint wrapping in _inplace_binary_op

**Verified** that all 6 qint in-place operators handle `int` operands natively:
- `__iadd__` -> `addition_inplace` -> checks `type(other) == int` -> calls `CQ_add` directly
- `__isub__` -> `addition_inplace(invert=True)` -> same int handling
- `__imul__` -> `self * other` -> `multiplication_inplace` -> checks `type(other) == int` -> calls `CQ_mul` directly
- `__iand__` -> `self & other` -> int path exists in `__and__`
- `__ior__` -> `self | other` -> int path exists in `__or__`
- `__ixor__` -> checks `type(other) == int` -> applies X gates directly

**Removed** two unnecessary qint wrapping patterns:

1. **Scalar int path** (line 868): `other = qint(other, width=self._width)` -- created ONE temporary qint per operation. Removed; int now passed directly to qint operators.

2. **List-of-int path** (line 885): `val = qint(flat_values[i], width=self._width) if type(flat_values[i]) == int else flat_values[i]` -- created a temporary qint PER ELEMENT inside the loop. Removed; values now passed directly.

**Confirmed** out-of-place `_elementwise_binary_op` already passes int directly via lambdas (no changes needed).

## Verification Results

- `test_qarray_elementwise.py`: 67 passed, 5 skipped (pre-existing skips)
- All 112 qarray tests: passed (5 skipped, pre-existing)
- `qint(other, width` no longer appears in `_inplace_binary_op`
- `qint(flat_values` no longer appears anywhere in qarray.pyx
- Full test suite: 1 pre-existing failure (`test_qint_default_width`) + pre-existing segfault in large parameterized tests -- both confirmed pre-existing via git stash testing

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D-40-01 | Remove all qint wrapping in _inplace_binary_op | All 6 qint in-place operators handle int natively via CQ_* |

## Commits

| Hash | Message |
|------|---------|
| 026d981 | perf(40-01): eliminate temporary qint allocations in qarray classical operations |
