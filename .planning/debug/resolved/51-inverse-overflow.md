---
status: resolved
trigger: "Investigate a blocker bug in the quantum assembly compiler's `.inverse()` feature."
created: 2026-02-04T00:00:00Z
updated: 2026-02-04T00:15:00Z
---

## Current Focus

hypothesis: CONFIRMED - Legacy backward compat code in qint.__del__ line 568 causes underflow
test: Reproduced bug with test_inverse_bug2.py
expecting: Fix by adding guard condition to prevent negative subtraction
next_action: Implement fix in qint.pyx line 568

## Symptoms

expected: `.inverse()` should replay gates in reversed order with adjoint transformations without errors
actual: OverflowError during qint.__del__ when calling _set_smallest_allocated_qubit
errors:
```
Traceback (most recent call last):
  File "src/quantum_language/_core.pyx", line 119, in quantum_language._core._set_smallest_allocated_qubit
OverflowError: can't convert negative value to unsigned int
Exception ignored in: 'quantum_language.qint.__del__'
```
reproduction: Call .inverse() on a compiled function (@ql.compile)
started: Phase 51 added .inverse() feature to compiled functions

## Eliminated

## Evidence

- timestamp: 2026-02-04T00:05:00Z
  checked: qint.__del__ in qint.pyx lines 524-570
  found: Line 568 calls `_set_smallest_allocated_qubit(_get_smallest_allocated_qubit() - self.bits)` which performs unsigned subtraction
  implication: If _get_smallest_allocated_qubit() is 0 or small, subtracting self.bits causes integer underflow to negative, passed to unsigned int parameter

- timestamp: 2026-02-04T00:07:00Z
  checked: _set_smallest_allocated_qubit signature in _core.pyx line 119
  found: Function signature is `def _set_smallest_allocated_qubit(unsigned int value)` - expects unsigned int
  implication: Python passes negative int, Cython tries to convert to unsigned int → OverflowError

- timestamp: 2026-02-04T00:10:00Z
  checked: compile.py _InverseCompiledFunc._replay usage (line 833)
  found: Calls `self._original._replay(self._inv_cache[cache_key], quantum_args)` which uses CompiledFunc._replay
  implication: Inverse replay allocates fresh ancillas at line 709 via _allocate_qubit(), these get deallocated when qints go out of scope

- timestamp: 2026-02-04T00:12:00Z
  checked: Line 568 context in qint.__del__
  found: This is "backward compat tracking (deprecated)" that runs AFTER the proper uncomputation at line 567 check
  implication: This legacy code doesn't guard against negative results, assumes monotonic growth of _smallest_allocated_qubit

## Resolution

root_cause: |
  The bug occurs in qint.__del__ at line 568 in src/quantum_language/qint.pyx.
  This legacy "backward compat tracking" code performs unsigned integer arithmetic
  without checking for underflow:

  `_set_smallest_allocated_qubit(_get_smallest_allocated_qubit() - self.bits)`

  When _get_smallest_allocated_qubit() returns a value smaller than self.bits
  (which happens during inverse replay when fresh ancillas are allocated),
  the subtraction produces a negative integer. This negative value is then
  passed to _set_smallest_allocated_qubit() which expects `unsigned int`,
  causing Cython's OverflowError: "can't convert negative value to unsigned int".

  The inverse feature allocates fresh ancillas during replay (compile.py line 709),
  and when these qints are garbage collected, their __del__ tries to decrement
  _smallest_allocated_qubit below zero.

fix: |
  Applied two guard conditions to prevent negative integer underflow in legacy
  backward compatibility code:

  1. In src/quantum_language/qint.pyx line 568:
     Added check: if current_smallest >= self.bits before decrementing
     _set_smallest_allocated_qubit to prevent passing negative value to unsigned int.

  2. In src/quantum_language/_core.pyx line 159:
     Added check: if ancilla[0] >= amount before decrementing ancilla[0]
     to prevent numpy unsigned integer overflow warning.

  Both pieces of code are marked as "deprecated, but maintained for older code"
  and the proper uncomputation happens earlier in the flow. The guards ensure
  inverse function replay (which allocates fresh ancillas that may be deallocated
  in different order) doesn't cause underflow in the legacy tracking.

verification: |
  Created and ran three test files:
  - test_inverse_bug.py: Original minimal reproduction - now passes without error
  - test_inverse_bug2.py: Direct test with explicit del - passes without OverflowError
  - test_inverse_comprehensive.py: Comprehensive test with multiple patterns - all pass

  All tests run successfully with no OverflowError or RuntimeWarning.
  The inverse function feature now works correctly for compiled functions.

files_changed:
  - src/quantum_language/qint.pyx (lines 566-569)
  - src/quantum_language/_core.pyx (lines 156-160)
