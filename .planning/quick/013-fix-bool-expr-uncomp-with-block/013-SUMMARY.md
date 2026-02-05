---
phase: quick-013
plan: 01
subsystem: uncomputation
tags: [circuit-optimizer, min_layer_used, start_layer, reverse_circuit_range]
requires: []
provides: [min_layer_used tracking, correct start_layer for all operations]
affects: []
tech-stack:
  added: []
  patterns: [reset-before-read-after for min_layer_used tracking]
key-files:
  created:
    - tests/bugfix/test_bug_uncomp_optimizer_layer.py
  modified:
    - c_backend/include/circuit.h
    - c_backend/src/circuit_allocations.c
    - c_backend/src/optimizer.c
    - src/quantum_language/_core.pxd
    - src/quantum_language/qint_comparison.pxi
    - src/quantum_language/qint_bitwise.pxi
    - src/quantum_language/qint_arithmetic.pxi
    - src/quantum_language/qint_division.pxi
decisions: []
metrics:
  duration: ~22min
  completed: 2026-02-04
---

# Quick Task 013: Fix Bool Expression Uncomputation with Block Summary

**One-liner:** min_layer_used field in circuit_t tracks optimizer early gate placement so reverse_circuit_range covers all gates during uncomputation

## What Was Done

### Task 1: Add min_layer_used tracking to C backend
- Added `num_t min_layer_used` field to `circuit_t` struct in `circuit.h`
- Initialized to `UINT32_MAX` in `init_circuit()` in `circuit_allocations.c`
- Updated `add_gate()` in `optimizer.c` to track the minimum layer any gate was placed into after `append_gate`

### Task 2: Expose min_layer_used to Python and fix all start_layer captures
- Added `min_layer_used` to `circuit_s` forward declaration in `_core.pxd`
- For **simple operations** (single `run_instruction`): reset `min_layer_used` to `0xFFFFFFFF` before, read after, adjust `start_layer` if optimizer placed gates earlier
  - `__eq__` int path, `__and__`, `__or__`, `__xor__`, `copy()`
- For **compound operations** (delegate to Python operators): track `actual_start` across all sub-operations by resetting/reading `min_layer_used` around each sub-op and taking minimum
  - `__eq__` qint path, `__lt__`, `__gt__`, `__add__`, `__radd__`, `__sub__`, `__neg__`, `__rsub__`, `__lshift__`, `__rshift__`, `__mul__`, `__rmul__`, `__floordiv__`, `__mod__`, `__divmod__`

### Task 3: Regression test
- Created `tests/bugfix/test_bug_uncomp_optimizer_layer.py` with 5 tests
- Tests verify `_start_layer` is 0 when optimizer places gates at layer 0
- Tests verify the original bug scenario (`with (cr == 1) | (cr == 3)`) works correctly
- Tests verify comparison result via Qiskit simulation

## The Bug

When `add_gate()` places a gate (e.g., X gates from `CQ_equal_width`), it calls `minimum_layer()` which can return layer 0 if the target qubits have no prior gates. But the Python code captured `start_layer = circuit.used_layer` before calling `run_instruction`, and `used_layer` only grows monotonically. So if `used_layer` was 5 but the optimizer placed X gates at layer 0, `reverse_circuit_range(5, end)` would miss those gates during uncomputation.

## The Fix

`min_layer_used` on `circuit_t` tracks the lowest layer touched by any `add_gate` call. Python code resets it to `UINT32_MAX` before operations and reads it after, using `min(start_layer, min_layer_used)` as the actual start layer. This ensures `reverse_circuit_range` covers all gates placed by the operation, regardless of optimizer placement.

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 3e3f9df | feat | Add min_layer_used tracking to C backend |
| eb49719 | feat | Use min_layer_used to fix start_layer in all operations |
| f4d23fa | test | Add regression test for uncomputation optimizer layer bug |
