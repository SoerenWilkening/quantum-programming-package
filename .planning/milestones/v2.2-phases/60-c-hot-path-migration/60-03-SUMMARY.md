---
phase: 60
plan: 03
subsystem: performance-migration
tags: [hot-path, C-migration, addition, nogil, Cython-wrapper]

dependency-graph:
  requires:
    - phase: 60-01
      provides: hot-path-identification, baseline-benchmarks
    - phase: 60-02
      provides: hot_path_mul pattern, nogil wrapper template
    - phase: 57
      provides: Cython-static-typing, boundscheck-directives
    - phase: 58-59
      provides: hardcoded-sequences, IntegerAddition.c
  provides:
    - hot_path_add.c C implementation of addition_inplace
    - hot_path_add.h header with QQ and CQ entry points
    - C-level unit tests for addition hot path
    - 61% speedup for classical iadd, 42% for quantum iadd
  affects: [60-04]

tech-stack:
  added: []
  patterns: [hot-path-C-migration, thin-Cython-wrapper-with-nogil, stack-allocated-qubit-arrays]

key-files:
  created:
    - c_backend/include/hot_path_add.h
    - c_backend/src/hot_path_add.c
    - tests/c/test_hot_path_add.c
  modified:
    - setup.py
    - src/quantum_language/_core.pxd
    - src/quantum_language/qint.pyx
    - src/quantum_language/qint_arithmetic.pxi
    - tests/c/Makefile

key-decisions:
  - "MIG-08: Same two-entry-point pattern (hot_path_add_qq, hot_path_add_cq) as plan 02"
  - "MIG-09: Addition hot path passes invert parameter to run_instruction for subtraction support"
  - "MIG-10: Controlled QQ_add uses fixed position 2*result_bits for control qubit (not sequential after other qubits)"

patterns-established:
  - "Addition hot path migration pattern identical to multiplication: C builds qa[256], calls sequence generator, calls run_instruction"
  - "Invert parameter enables subtraction via same C function (no separate subtract function needed)"

metrics:
  duration: "13m 2s"
  completed: "2026-02-06"
---

# Phase 60 Plan 03: Migrate addition_inplace to C Summary

**One-liner:** addition_inplace hot path fully migrated to C with two entry points (QQ and CQ), thin Cython nogil wrapper, achieving 61% speedup for classical iadd and 42% speedup for quantum iadd.

## Performance

- **Duration:** 13m 2s
- **Started:** 2026-02-06T17:49:03Z
- **Completed:** 2026-02-06T18:02:04Z
- **Tasks:** 2/2
- **Files created:** 3 (header, implementation, C test)
- **Files modified:** 5 (setup.py, _core.pxd, qint.pyx, qint_arithmetic.pxi, tests/c/Makefile)

## What Was Migrated

**Hot path #2: `addition_inplace`** -- the highest-frequency hot path identified in Plan 01 profiling (called by iadd, isub, eq, lt, add, sub -- every comparison and arithmetic operation goes through addition_inplace).

### Architecture

```
Before: Python -> Cython addition_inplace -> qubit_array global -> CQ_add/QQ_add -> run_instruction
After:  Python -> Cython thin wrapper (nogil) -> C hot_path_add_* -> qubit_array on stack -> CQ_add/QQ_add -> run_instruction
```

The Cython wrapper now only extracts qubit indices from Python objects, then calls a pure C function that handles all qubit layout and sequence execution without returning to Python.

### C Implementation (hot_path_add.c)

Two entry points:
- `hot_path_add_qq(circ, self_qubits, self_bits, other_qubits, other_bits, invert, controlled, control_qubit, ancilla, num_ancilla)` -- quantum-quantum addition
- `hot_path_add_cq(circ, self_qubits, self_bits, classical_value, invert, controlled, control_qubit, ancilla, num_ancilla)` -- classical-quantum addition

Key difference from multiplication: the `invert` parameter is passed through to `run_instruction`, enabling subtraction (isub) to reuse the same C functions.

Each function:
1. Builds qubit layout on stack (`qa[256]`)
2. Calls appropriate sequence generator (`QQ_add`/`cQQ_add`/`CQ_add`/`cCQ_add`)
3. Calls `run_instruction(seq, qa, invert, circ)`

### Qubit Layout (Critical)

**CQ path (uncontrolled):**
- `[0..self_bits-1]` = self qubits (target)
- `[self_bits..]` = ancilla

**CQ path (controlled):**
- `[0..self_bits-1]` = self qubits (target)
- `[self_bits]` = control_qubit
- `[self_bits+1..]` = ancilla

**QQ path (uncontrolled):**
- `[0..self_bits-1]` = self qubits (target)
- `[self_bits..self_bits+other_bits-1]` = other qubits
- `[start..]` = ancilla (start = self_bits + other_bits)

**QQ path (controlled):**
- `[0..self_bits-1]` = self qubits (target)
- `[self_bits..self_bits+other_bits-1]` = other qubits
- `[2*result_bits]` = control_qubit (fixed position, NOT sequential!)
- `[2*result_bits+1..]` = ancilla

### Cython Wrapper (qint_arithmetic.pxi)

The `addition_inplace` method was reduced from ~82 lines of Cython logic to ~57 lines of pure data extraction + two `with nogil:` C calls. The wrapper:
1. Extracts qubit arrays from Python `qint` objects into stack-allocated C arrays
2. Gets circuit pointer, control flags, and ancilla from Python accessors
3. Calls `hot_path_add_cq` or `hot_path_add_qq` inside `with nogil:` block
4. Returns self

## Benchmark Results

### Addition-specific benchmarks (hot path #2)

| Operation | Baseline (Plan 01) | After Migration | Change |
|-----------|-------------------|-----------------|--------|
| iadd_8bit (classical) | 37.2 us | 14.4 us | **-61.3% faster** |
| isub_8bit (classical) | 31.2 us | 17.1 us | **-45.2% faster** |
| iadd_quantum_8bit | 62.4 us | 36.0 us | **-42.3% faster** |
| isub_quantum_8bit | 61.7 us | 58.5 us | -5.2% |
| iadd_16bit (classical) | 48.3 us | 36.2 us | **-25.1% faster** |
| iadd_quantum_16bit | 413.7 us | 268.1 us | **-35.2% faster** |

The classical iadd path shows a dramatic 61% improvement -- this is because the 7 Python accessor roundtrips eliminated by the migration were a proportionally large fraction of the ~37us total call time.

### Cumulative improvements (Plan 02 + Plan 03)

| Operation | Phase 60 Baseline | After Plan 02 | After Plan 03 | Total Change |
|-----------|------------------|---------------|---------------|-------------|
| iadd_8bit | 37.2 us | 37.2 us | 14.4 us | **-61.3%** |
| isub_8bit | 31.2 us | 31.2 us | 17.1 us | **-45.2%** |
| iadd_quantum_8bit | 62.4 us | 62.4 us | 36.0 us | **-42.3%** |
| mul_8bit | 236.2 us | 223.3 us | 237.0 us | ~0% (noise) |
| eq_8bit | 103.1 us | -- | 60.0 us | **-41.8%** |
| lt_8bit | 115.3 us | -- | 78.5 us | **-31.9%** |
| add_8bit | 59.6 us | -- | 39.2 us | **-34.2%** |

Equality and less-than operations also improved significantly because they internally call addition_inplace.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | C implementation and unit test | 9a11ed6 | c_backend/include/hot_path_add.h, c_backend/src/hot_path_add.c, tests/c/test_hot_path_add.c, tests/c/Makefile |
| 2 | Cython integration and build | dff3592 | setup.py, _core.pxd, qint.pyx, qint_arithmetic.pxi |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

### Must-Haves Verification

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Hot path #2 executes entirely in C with single Cython entry point | PASS - addition_inplace calls hot_path_add_qq/hot_path_add_cq via nogil |
| 2 | All existing tests pass after migration | PASS - 293 core tests + 165 hardcoded sequence tests pass; only pre-existing failures (width-32 segfault, qint_mod) |
| 3 | Benchmark shows measurable change for migrated path | PASS - iadd_8bit: 37.2us -> 14.4us (-61.3%), iadd_quantum_8bit: 62.4us -> 36.0us (-42.3%) |

### Test Results

- **C unit tests (hot_path_add):** 9/9 passed
- **Addition tests (hardcoded sequences):** 165/165 passed
- **Core functionality tests:** 293/293 passed
- **Benchmarks:** 24/24 passed
- **Pre-existing failures (not related to changes):** width-32 segfault (in original code), qint_mod * qint_mod NotImplementedError, qbool uncomputed ValueError

## Next Phase Readiness

Plan 04 (ixor/xor migration) can proceed using the same pattern:
1. Create `hot_path_xor.h` / `hot_path_xor.c` with stack-based qubit layout
2. Add extern declaration to `_core.pxd`
3. Add import to `qint.pyx`
4. Replace `__ixor__` and `__xor__` bodies in `qint_bitwise.pxi` with thin nogil wrappers
5. Build and verify

## Self-Check: PASSED
