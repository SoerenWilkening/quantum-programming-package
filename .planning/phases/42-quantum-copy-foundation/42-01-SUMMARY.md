---
phase: 42-quantum-copy-foundation
plan: 01
subsystem: quantum-types
tags: [copy, cnot, qint, qbool, uncomputation]
dependency-graph:
  requires: [41-uncomputation-fix]
  provides: [qint.copy, qint.copy_onto, qbool.copy]
  affects: [43-copy-aware-binops]
tech-stack:
  added: []
  patterns: [CNOT-based state copy, Q_xor gate sequence]
key-files:
  created:
    - tests/test_copy.py
  modified:
    - src/quantum_language/qint.pyx
    - src/quantum_language/qbool.pyx
decisions:
  - id: D42-01-1
    description: "Place copy methods after __invert__ in qint.pyx, before __getitem__"
    rationale: "Grouped with bitwise operations since copy uses CNOT (XOR) gates"
  - id: D42-01-2
    description: "copy_onto does not set layer tracking or dependencies on target"
    rationale: "Raw CNOT operation; caller manages target lifecycle"
  - id: D42-01-3
    description: "qbool.copy() uses cdef cast to access qubits from qint.copy() result"
    rationale: "qubits is cdef object (not public), requires Cython-level access"
metrics:
  duration: "10 min"
  completed: "2026-02-02"
---

# Phase 42 Plan 01: Quantum Copy Foundation Summary

**CNOT-based quantum state copy for qint and qbool, verified exhaustively through Qiskit simulation.**

## What Was Done

### Task 1: Implement copy() and copy_onto() on qint
- Added `qint.copy()` method that allocates fresh |0> qubits, applies CNOT gates via Q_xor, and sets layer tracking metadata (operation_type='COPY', start/end layer, dependency)
- Added `qint.copy_onto(target)` method that XOR-copies source bits onto target qubits with width validation (raises ValueError on mismatch)
- Both methods follow the exact same CNOT pattern as the existing `__xor__` implementation (lines 1510-1519)

### Task 2: qbool.copy() override and verification tests
- Added `qbool.copy()` that calls `qint.copy()` then wraps result in qbool via `create_new=False, bit_list=...`, transferring qubit ownership and layer tracking
- Created 69 tests in `tests/test_copy.py`:
  - 30 exhaustive copy value tests (widths 1-4, all values)
  - 30 exhaustive copy_onto value tests (widths 1-4, all values)
  - 4 width preservation tests
  - 1 qubit distinctness test
  - 1 width mismatch error test
  - 1 qbool type preservation test
  - 2 qbool value tests (True/False)

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D42-01-1 | Place copy methods after __invert__ | Groups with bitwise ops (copy uses CNOT/XOR gates) |
| D42-01-2 | copy_onto has no layer tracking | Raw CNOT op; caller manages lifecycle |
| D42-01-3 | qbool.copy() uses cdef cast for qubit access | qubits attr is cdef, not public |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] qbool.copy() AttributeError on qubits access**
- **Found during:** Task 2
- **Issue:** Initial implementation accessed `result_qint.qubits` from Python level, but `qubits` is a `cdef object` attribute not visible to Python
- **Fix:** Used `cdef qint result_qint` typed variable to access qubits at Cython level
- **Files modified:** src/quantum_language/qbool.pyx

**2. [Rule 3 - Blocking] pip install -e . fails with absolute path error**
- **Found during:** Task 1
- **Issue:** Editable install fails due to absolute path in setup.py on this platform
- **Fix:** Used `python3 setup.py build_ext --inplace` directly for Cython compilation
- **Files modified:** None (build process only)

## Test Results

```
tests/test_copy.py: 69 passed, 0 failed
Existing tests (tests/python/): No regressions (1 pre-existing failure in test_qint_default_width, 1 pre-existing segfault in array tests)
```

## Next Phase Readiness

Phase 43 (copy-aware binary operations) can proceed. The `copy()` and `copy_onto()` primitives are in place and verified. Key integration points:
- `qint.copy()` returns a new qint with `operation_type='COPY'` and proper dependency tracking
- `qint.copy_onto(target)` provides raw CNOT for cases where caller manages lifecycle
- Both participate in scope-based uncomputation via layer tracking
