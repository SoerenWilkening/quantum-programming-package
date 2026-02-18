---
phase: 32
plan: 01
subsystem: verification
tags: [bitwise, AND, OR, XOR, NOT, QQ, CQ, exhaustive, sampled, pipeline]
dependency-graph:
  requires: [28, 30]
  provides: [VBIT-01-correctness]
  affects: [33]
tech-stack:
  added: []
  patterns: [keepalive-refs-for-gc-safety, oracle-based-parametrized-testing]
key-files:
  created: [tests/test_bitwise.py]
  modified: [tests/conftest.py]
decisions:
  - id: D-32-01-01
    description: "Add gc.collect() and keepalive ref support to verify_circuit"
    rationale: "Bitwise ops use uncomputation GC; qint destructors inject gates into new circuit after reset"
  - id: D-32-01-02
    description: "Mark CQ tests with non-strict xfail for BUG-BIT-01"
    rationale: "CQ bitwise ops have systemic result register layout bug; failure pattern too complex to predict exactly"
  - id: D-32-01-03
    description: "CQ xfail only for b != max_val"
    rationale: "CQ ops with b = 2^width - 1 (all bits set) reliably pass since full result register is allocated"
metrics:
  duration: "36 min"
  completed: "2026-02-01"
---

# Phase 32 Plan 01: Bitwise Same-Width Correctness Summary

Exhaustive and sampled bitwise verification through full pipeline (Python -> C -> OpenQASM -> Qiskit) for AND, OR, XOR (QQ+CQ) and NOT at widths 1-6.

## One-liner

2418 parametrized bitwise tests: QQ+NOT all pass; CQ 754 xfail due to BUG-BIT-01 result register layout bug.

## What Was Done

### Task 1: Create test_bitwise.py with exhaustive and sampled bitwise tests

Created `tests/test_bitwise.py` with 6 parametrized test functions:

| Test Function | Cases | Status |
|---|---|---|
| test_qq_bitwise_exhaustive | 1020 (widths 1-4, all pairs, 3 ops) | All pass |
| test_cq_bitwise_exhaustive | 1020 (widths 1-4, all pairs, 3 ops) | 661 xfail (BUG-BIT-01) |
| test_not_exhaustive | 30 (widths 1-4, all values) | All pass |
| test_qq_bitwise_sampled | 198 (widths 5-6, boundary+random, 3 ops) | All pass |
| test_cq_bitwise_sampled | 108 (widths 5-6, boundary+random, 3 ops) | 93 xfail (BUG-BIT-01) |
| test_not_sampled | 42 (widths 5-6, boundary+random values) | All pass |

**Total: 2418 tests collected. 1356 passed, 754 xfailed, 308 xpassed, 0 failures.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed qint destructor gate leakage between tests**

- **Found during:** Task 1 initial test run
- **Issue:** Bitwise operations use the C backend's garbage collection (uncomputation) feature. When qint objects go out of scope, their destructors add uncomputation gates to the active circuit. When circuit_builder returns, Python's reference counting destroys the local qint objects, injecting extra gates into the circuit BEFORE to_openqasm() is called. This corrupted every bitwise circuit after the first test.
- **Fix:** (1) Added `gc.collect()` before `ql.circuit()` in verify_circuit to clean up lingering refs from previous tests. (2) Modified verify_circuit to support `(expected, keepalive_refs)` return from circuit_builder, keeping qint objects alive until after OpenQASM export. (3) All circuit_builders in test_bitwise.py return keepalive refs.
- **Files modified:** tests/conftest.py, tests/test_bitwise.py
- **Commit:** c3e6661

## Bugs Found

### BUG-BIT-01: CQ Bitwise Result Register Layout

**Severity:** HIGH -- affects all CQ bitwise operations (AND, OR, XOR with qint op int)

**Description:** Classical-quantum bitwise operations produce incorrect result register layouts. The C backend allocates result qubits only for bits that are SET in the classical operand, rather than always allocating a full-width result register. When `popcount(classical_value) < width`, fewer result qubits are allocated, and `bitstring[:width]` extracts the wrong bits.

**Impact:**
- CQ AND: 9/16 failures at width 2 (passes only when a=0 or b=max_val)
- CQ OR: 6/16 failures at width 2
- CQ XOR: 8/16 failures at width 2
- Total across all widths: 754 xfailed tests

**Root cause:** The C backend functions `CQ_and()`, `CQ_or()`, and `CQ_xor()` (in LogicOperations.c) only apply gates for bits that are set in the classical value, and the result register size equals popcount(classical_value) rather than the full operand width.

**Workaround:** QQ variants work correctly for all cases. Use QQ bitwise operations instead of CQ.

## Decisions Made

| ID | Decision | Rationale |
|---|---|---|
| D-32-01-01 | Add gc.collect() and keepalive ref support to verify_circuit | Bitwise ops use uncomputation GC; qint destructors inject gates into new circuit after reset |
| D-32-01-02 | Mark CQ tests with non-strict xfail for BUG-BIT-01 | CQ bitwise ops have systemic result register layout bug; failure pattern too complex to predict exactly |
| D-32-01-03 | CQ xfail only for b != max_val | CQ ops with b = 2^width - 1 (all bits set) reliably pass since full result register is allocated |

## Verification Results

```
$ python3 -m pytest tests/test_bitwise.py --co -q | tail -1
2418 tests collected

$ python3 -m pytest tests/test_bitwise.py -q --tb=short | tail -1
1356 passed, 754 xfailed, 308 xpassed, 1736 warnings in 162.73s

$ python3 -m pytest tests/test_add.py tests/test_compare.py -q | tail -1
1875 passed, 488 xfailed, 40 xpassed (no regression)
```

## Commits

| Hash | Message |
|---|---|
| c3e6661 | feat(32-01): add exhaustive and sampled bitwise verification tests |

## Next Phase Readiness

- BUG-BIT-01 should be tracked for future C backend fix
- Phase 32-02 (mixed-width and preservation tests) can proceed independently
- QQ bitwise operations are fully verified and correct
- NOT operation is fully verified and correct (in-place, all widths)
