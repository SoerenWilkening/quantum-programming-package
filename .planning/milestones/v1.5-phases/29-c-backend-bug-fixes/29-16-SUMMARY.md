---
phase: 29-c-backend-bug-fixes
plan: 16
subsystem: comparison-operators
tags: [BUG-02, comparison, __le__, __gt__, __lt__, MSB, unsigned, qbool, uncomputation]
dependency_graph:
  requires: [29-15]
  provides: [comparison-fix, le-operator, gt-operator, lt-operator]
  affects: [29-17, 29-18]
tech_stack:
  added: []
  patterns: [widened-comparison-for-unsigned-safety, delegation-based-le]
key_files:
  created: []
  modified:
    - src/quantum_language/qint.pyx
decisions:
  - id: D29-16-1
    decision: "Use (n+1)-bit widened temporaries in __gt__ for unsigned-safe comparison"
    rationale: "n-bit modular subtraction wraps around for differences >= 2^(n-1), corrupting the sign bit. Adding 1 extra bit ensures the full unsigned range is correctly compared."
  - id: D29-16-2
    decision: "Remove _start_layer/_end_layer from comparison result qbools"
    rationale: "Layer tracking caused GC-induced gate reversal: when result qbool went out of scope, __del__ reversed the comparison circuit. Arithmetic results already skip this."
  - id: D29-16-3
    decision: "Simplify __le__ to delegate to ~(self > other)"
    rationale: "Eliminates fragile OR-combination of is_negative and is_zero qbools; correctness follows from __gt__ correctness"
metrics:
  duration: "~18 min"
  completed: "2026-01-31"
---

# Phase 29 Plan 16: Comparison Fix Summary

**One-liner:** Fixed BUG-02 by correcting MSB index (63 not 64-width), removing GC-triggered gate reversal from comparison results, and using (n+1)-bit widened subtraction for unsigned-safe comparison.

## What Was Done

### Task 1: Diagnose comparison failures
- Ran all comparison operators (__lt__, __gt__, __le__) through simulation
- Found ALL operators returning 0 for true cases (not just __le__)
- Identified three distinct root causes through systematic testing:
  1. MSB index pointed to LSB (index 64-width) instead of MSB (index 63) in right-aligned qubit storage
  2. Comparison result qbools had layer tracking that triggered GC uncomputation, reversing the circuit
  3. n-bit modular subtraction wraps around for large unsigned differences (e.g., 0-15 in 4-bit = 1, not -15)

### Task 2: Fix comparisons
- **MSB index fix:** Changed `self[64 - self.bits]` to `self[63]` and `other[64 - (<qint>other).bits]` to `other[63]` in __lt__ and __gt__ (5 occurrences across qint-qint and qint-int paths)
- **GC uncomputation fix:** Removed `_start_layer`/`_end_layer` assignment from __lt__ and __gt__ result qbools. Without layer tracking, `_do_uncompute` skips gate reversal (the `_end_layer > _start_layer` check fails), matching arithmetic result behavior.
- **Unsigned overflow fix:** Rewrote __gt__ qint-qint path to create (n+1)-bit widened temporaries, copy operand bits via XOR, subtract on the wider register, then extract the true sign bit from index 63. The extra bit ensures unsigned values that fill the full n-bit range don't pollute the sign bit.
- **__le__ simplification:** Replaced the OR-combination logic (is_negative | is_zero) with `~(self > other)` delegation.
- **Circular dependency fix:** Changed __gt__ int path from `~(self <= other)` to creating a temp qint and using the qint-qint path.
- Commit: `d8341cc`

## Verification Results

| Criterion | Result |
|-----------|--------|
| qint(5) <= qint(5) returns 1 | PASS |
| qint(3) <= qint(7) returns 1 | PASS |
| qint(7) <= qint(3) returns 0 | PASS |
| qint(0) <= qint(0) returns 1 | PASS |
| qint(0) <= qint(15) returns 1 | PASS |
| qint(15) <= qint(0) returns 0 | PASS |
| BUG-02: 6/6 comparison tests | PASS |
| BUG-01: 5/5 subtraction tests | PASS |
| BUG-04: 7/7 QFT addition tests | PASS |
| Combined 18/18 tests | PASS |
| No circular recursion | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] GC-induced gate reversal on comparison result qbools**
- **Found during:** Task 1 diagnostics
- **Issue:** Comparison result qbools had `_start_layer`/`_end_layer` layer tracking. When Python garbage-collected the result (e.g., local variable going out of scope in circuit_builder function), `__del__` triggered `_do_uncompute` which reversed all comparison gates via `reverse_circuit_range`. This caused the circuit to produce 0 even when the comparison was correct.
- **Fix:** Removed layer boundary assignment from __lt__ and __gt__ results. The default 0/0 values cause `_end_layer > _start_layer` to fail, skipping gate reversal.
- **Files modified:** src/quantum_language/qint.pyx
- **Commit:** d8341cc

**2. [Rule 1 - Bug] Unsigned overflow in n-bit modular subtraction**
- **Found during:** Task 2 verification (test_le_0_le_15 failed)
- **Issue:** For 4-bit unsigned values, `0 - 15 = 1 (mod 16)`, which has MSB=0 (looks positive). The sign-bit approach fails when the unsigned difference exceeds half the range (2^(n-1)). This is a fundamental limitation of n-bit subtraction-based comparison for unsigned integers.
- **Fix:** Used (n+1)-bit widened temporaries in __gt__. Both operands are zero-extended by 1 bit, ensuring the sign bit is never polluted by data bits. The subtraction then correctly represents the full unsigned range.
- **Files modified:** src/quantum_language/qint.pyx
- **Commit:** d8341cc

**3. [Rule 3 - Blocking] Circular dependency between __gt__ and __le__ for int operands**
- **Found during:** Task 2 implementation
- **Issue:** __gt__ int path called `~(self <= other)`, and the new __le__ calls `~(self > other)`, creating infinite recursion for int operands.
- **Fix:** Changed __gt__ int path to create a temp qint and use the qint-qint comparison path instead.
- **Files modified:** src/quantum_language/qint.pyx
- **Commit:** d8341cc

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D29-16-1 | Use (n+1)-bit widened temporaries in __gt__ | n-bit modular subtraction wraps for differences >= 2^(n-1) |
| D29-16-2 | Remove layer tracking from comparison results | GC triggers gate reversal via __del__ -> _do_uncompute |
| D29-16-3 | Simplify __le__ to ~(self > other) delegation | Eliminates fragile OR logic; correctness follows from __gt__ |

## Next Phase Readiness

BUG-02 is now fixed. Combined with BUG-01 (fixed plan 29-07), BUG-04 (fixed plan 29-09), and BUG-05 (fixed plan 29-15), the remaining unfixed bug is:
- BUG-03 (QQ_mul): Non-trivial quantum-quantum multiplication still produces wrong results. Plan 29-17 targets this.

All 18 existing tests pass in a single combined pytest run, confirming no regressions.
