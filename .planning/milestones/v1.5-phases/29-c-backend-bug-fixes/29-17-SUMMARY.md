---
phase: 29-c-backend-bug-fixes
plan: 17
subsystem: integer-multiplication
tags: [QQ_mul, CCP-decomposition, BUG-03, qubit-mapping, Draper-QFT]
dependency_graph:
  requires: [29-15]
  provides: [correct-QQ_mul, multiplication-all-cases]
  affects: [29-18]
tech_stack:
  added: []
  patterns: [CCP-decomposition-for-quantum-quantum-operations]
key_files:
  created: []
  modified:
    - c_backend/src/IntegerMultiplication.c
decisions:
  - id: D29-17-1
    decision: "Rewrite QQ_mul with explicit CCP decomposition instead of fixing CP_sequence/all_rot"
    rationale: "The helper functions had two independent bugs (inverted target formula AND inverted b-qubit mapping). Clean rewrite with documented qubit layout is more maintainable and verifiable."
  - id: D29-17-2
    decision: "Use b_ctrl = 2*bits+j (weight 2^j at index 2*bits+j) instead of 3*bits-1-j"
    rationale: "Right-aligned qubit storage means index 0=LSB. The b register starts at 2*bits with LSB first, so weight 2^j is at index 2*bits+j, not 3*bits-1-j."
metrics:
  duration: "~18 min"
  completed: "2026-01-31"
---

# Phase 29 Plan 17: QQ_mul Multiplication Fix Summary

**One-liner:** Rewrote QQ_mul with correct CCP decomposition and fixed b-operand qubit index mapping (2*bits+j not 3*bits-1-j), fixing all non-trivial quantum-quantum multiplication.

## What Was Done

### Task 1: Analytical investigation and fix of QQ_mul algorithm

**Root cause analysis:**

The original QQ_mul had two independent bugs:

1. **Inverted target qubit formula in CP_sequence**: The helper function used `target = bits - i - 1 - rounds` instead of `target = rounds + i`. This applied phases to the wrong Fourier-domain qubits (MSB got LSB's phase and vice versa).

2. **Inverted b-operand qubit mapping**: The code used `b_ctrl = 3*bits - 1 - j` for b bit at weight 2^j, but the correct index is `b_ctrl = 2*bits + j`. The qubit_array uses right-aligned storage where `qubits[64-width+k]` stores bit k (weight 2^k). So in the sequence, b's LSB (weight 2^0) is at index 2*bits+0, not 3*bits-1.

**Fix approach:**

Rather than patching the CP_sequence and all_rot helpers (which are also used by cQQ_mul), rewrote QQ_mul with an explicit CCP decomposition:

For each a control bit (weight 2^k at seq index bits+k):
- Step 1: CP(sum_theta/2, target, a_ctrl) for each Fourier target -- sum over all b bits
- Step 2: For each b bit j: CX(a_ctrl, b_ctrl) + CP(-theta_j/2, target, a_ctrl) + CX restore
- Step 3: For each b bit j: CP(theta_j/2, target, b_ctrl_j)

This correctly decomposes the doubly-controlled phase CCP(theta, a_i, b_j, result_k) required for Draper QFT multiplication.

**Key insight:** The qubit layout is:
- Result register: seq 0..bits-1 (0=LSB, bits-1=MSB)
- Operand a: seq bits..2*bits-1 (bits=a_LSB, 2*bits-1=a_MSB)
- Operand b: seq 2*bits..3*bits-1 (2*bits=b_LSB, 3*bits-1=b_MSB)

Commit: `541fed4`

### Task 2: Full BUG-03 test suite and regression check

- BUG-03: 5/5 multiplication tests pass (2*3=6, 1*1=1, 3*3=9, 0*5=0, 2*2=4)
- BUG-01: 5/5 subtraction tests pass (no regression)
- BUG-04: 7/7 QFT addition tests pass (no regression)
- Combined: 17/17 tests pass in single pytest run

## Verification Results

| Criterion | Result |
|-----------|--------|
| 2*3=6 (4-bit) | PASS |
| 1*1=1 (2-bit) | PASS |
| 3*3=9 (4-bit) | PASS |
| 0*5=0 (4-bit) | PASS |
| 2*2=4 (3-bit) | PASS |
| BUG-01 subtraction (5/5) | PASS |
| BUG-04 QFT addition (7/7) | PASS |
| Combined pytest (17/17) | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two independent bugs in QQ_mul, not one**

- **Found during:** Task 1 analytical investigation
- **Issue:** Plan assumed a single bug (wrong phase formula or target qubit mapping). Analysis revealed two bugs: (a) CP_sequence target formula was `bits-i-1-rounds` instead of `rounds+i`, and (b) b qubit index was `3*bits-1-j` instead of `2*bits+j`.
- **Fix:** Rewrote QQ_mul entirely rather than patching helpers, since the helpers had compounding errors.
- **Files modified:** `c_backend/src/IntegerMultiplication.c`
- **Commit:** `541fed4`

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D29-17-1 | Rewrite QQ_mul with explicit CCP decomposition | Helper functions had two independent bugs; clean rewrite is more maintainable |
| D29-17-2 | Use `2*bits+j` for b qubit at weight 2^j | Right-aligned storage: LSB at lowest index in each register |

## Next Phase Readiness

BUG-03 is now FULLY FIXED. Combined with BUG-01 (fixed), BUG-04 (fixed), and BUG-05 (fixed), only BUG-02 (comparison) remains.

Note: The helper functions CP_sequence, all_rot, CX_sequence are still used by cQQ_mul (controlled quantum-quantum multiplication). cQQ_mul likely has the same qubit mapping bugs. If cQQ_mul is needed, it should be rewritten using the same approach as this fix.
