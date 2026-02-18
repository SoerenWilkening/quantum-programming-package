---
phase: 32
plan: 03
subsystem: bug-fix
tags: [bitwise, CQ, mixed-width, BUG-BIT-01, bit-ordering, qubit-allocation, gap-closure]
dependency-graph:
  requires: [32-01, 32-02]
  provides: [BUG-BIT-01-fix]
  affects: [32-04, 33]
tech-stack:
  added: []
  patterns: [padding-before-result-allocation, used_qubits-tracking]
key-files:
  created: []
  modified: [c_backend/src/LogicOperations.c, src/quantum_language/qint.pyx, src/quantum_language/qint_bitwise.pxi, src/quantum_language/_core.pxd, tests/test_bitwise.py, tests/test_bitwise_mixed.py]
decisions:
  - id: D-32-03-01
    description: "Fix CQ bit ordering by reversing two_complement index in C backend"
    rationale: "two_complement returns MSB-first (bin[0]=MSB) but qubit_array is LSB-first; bin[bits-1-i] corrects this"
  - id: D-32-03-02
    description: "Track used_qubits in circuit struct from qint constructor"
    rationale: "QASM export only includes qubits up to circ->used_qubits; CQ ops that skip some bits left qubits invisible"
  - id: D-32-03-03
    description: "Allocate padding ancilla BEFORE result for mixed-width ops"
    rationale: "Result must get highest qubit indices since bitstring[:width] extracts highest-index qubits first"
  - id: D-32-03-04
    description: "CQ mixed-width xfail kept for b.bit_length() < intended_width cases"
    rationale: "Plain int has no width metadata; result width = max(qa.bits, b.bit_length()), not max(qa.bits, intended_width)"
metrics:
  duration: "~45 min"
  completed: "2026-02-01"
---

# Phase 32 Plan 03: BUG-BIT-01 Gap Closure Summary

Fixed CQ bitwise bit ordering, CQ XOR qubit addressing, QASM qubit visibility, and QQ mixed-width padding allocation.

## One-liner

BUG-BIT-01 fixed: CQ bit ordering reversed (MSB/LSB mismatch), mixed-width padding-before-result allocation, 3684 bitwise tests pass.

## What Was Done

### Task 1: CQ Bitwise Operations Fix (commit aa882e4)

Three sub-bugs diagnosed and fixed:

1. **CQ AND/OR bit ordering mismatch**: `two_complement()` in Integer.c returns MSB-first (`bin[0]`=MSB, `bin[bits-1]`=LSB), but `qubit_array` is populated MSB-first from `qubits[64-width:64]`. The C functions used `bin[i]` to decide which bits get gates, but `i` in the loop iterates LSB-first (qubit_array index 0 = MSB qubit). Fixed by changing `bin[i]` to `bin[bits - 1 - i]` in both `CQ_and()` and `CQ_or()` in LogicOperations.c.

2. **CQ XOR qubit addressing**: The `__xor__` method's classical path used `result.qubits[64 - result_bits + (result_bits - 1 - i)]` which reversed the bit ordering. Fixed to `result.qubits[64 - result_bits + i]` to match the LSB-first iteration.

3. **Missing qubit visibility in QASM export**: When CQ operations don't touch certain result qubits (classical bit = 0), those qubits never get gates, so `circ->used_qubits` is never updated by `add_gate()`. The QASM export then declares fewer qubits than allocated. Fixed by updating `circ->used_qubits` in the qint constructor after allocation.

### Task 2: Mixed-Width Bitwise Fix (commit 2b98b24)

Four issues diagnosed and fixed:

1. **AND/OR padding allocation order**: When operand widths differ, ancilla padding qubits for the narrower operand were allocated AFTER the result qubits. Since Qiskit bitstrings are highest-index-first and `bitstring[:width]` extracts the first `width` characters, the result must have the highest qubit indices. Fixed by allocating padding BEFORE result in both AND and OR methods.

2. **AND/OR padding in qubit_array**: After allocating padding qubits, they must be placed in the qubit_array at the correct positions (MSB end of the operand's section). Added proper population of padding qubits using temporary qint objects.

3. **XOR copy step layout**: When `result_bits > self.bits`, the copy step used `Q_xor(result_bits)` but only `self.bits` source qubits exist. Fixed to use `Q_xor(self.bits)` with properly sized qubit_array sections.

4. **XOR QQ-other step layout**: Same issue for the other operand's XOR step. Fixed to use `Q_xor(other.bits)` with correct qubit_array mapping.

### Test Updates

- **test_bitwise.py**: Removed all BUG-BIT-01 xfail markers. All 2418 same-width tests (QQ + CQ + NOT) now pass without xfail.
- **test_bitwise_mixed.py**: Removed xfail from QQ mixed-width tests (all pass). Updated CQ mixed-width xfail to document design limitation (plain int has no width metadata).

## Test Results

| Test Suite | Passed | XFailed | XPassed | Total |
|------------|--------|---------|---------|-------|
| test_bitwise.py (same-width) | 2418 | 0 | 0 | 2418 |
| test_bitwise_mixed.py | 1266 | 292 | 50 | 1608 |

The 292 xfailed CQ mixed-width tests are a design limitation, not a bug: when `b.bit_length() < intended_width`, the code cannot determine the intended result width from a plain int.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] qint.pyx is the actual compiled file, not qint_bitwise.pxi**

- **Found during:** Task 1
- **Issue:** The plan assumed qint_bitwise.pxi is included by qint.pyx, but it is not. Bitwise methods are duplicated in both files but only qint.pyx is compiled.
- **Fix:** Applied all fixes to qint.pyx (the compiled file) and qint_bitwise.pxi (for consistency).
- **Files modified:** src/quantum_language/qint.pyx, src/quantum_language/qint_bitwise.pxi

**2. [Rule 2 - Missing Critical] used_qubits not tracked for allocated-but-ungated qubits**

- **Found during:** Task 1
- **Issue:** Qubits allocated by the allocator but never receiving gates were invisible in QASM export, causing incorrect simulation results.
- **Fix:** Added `used_qubits` tracking in qint constructor and added field to `circuit_s` struct in _core.pxd.
- **Files modified:** src/quantum_language/qint.pyx, src/quantum_language/_core.pxd

**3. [Rule 3 - Blocking] XOR ixor classical path had same bit ordering bug**

- **Found during:** Task 1
- **Issue:** The `__ixor__` classical path had the same reversed index formula as `__xor__`.
- **Fix:** Applied same index fix to ixor path.
- **Files modified:** src/quantum_language/qint.pyx

## Key Decisions

1. **Reversed index in C backend** (D-32-03-01): Using `bin[bits-1-i]` instead of `bin[i]` aligns two_complement's MSB-first output with the LSB-first qubit_array iteration.

2. **Padding-before-result allocation** (D-32-03-03): Critical ordering constraint -- result must be last allocated to get highest qubit indices for correct bitstring extraction.

3. **CQ mixed-width as design limitation** (D-32-03-04): Plain int has no width metadata. Future work could add an explicit `width` parameter to CQ operations.

## Next Phase Readiness

- BUG-BIT-01 is resolved for same-width CQ and QQ mixed-width operations
- Plan 32-04 can proceed to close any remaining gaps
- The CQ mixed-width limitation is documented and could be addressed in a future phase by adding width-annotated classical operands
