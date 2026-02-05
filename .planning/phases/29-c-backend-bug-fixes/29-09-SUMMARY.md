# Phase 29 Plan 09: QFT/IQFT Convention Fix Summary

**One-liner:** Fixed textbook QFT qubit processing order in gate.c, corrected CQ_add layer allocation and QQ_add target formula, resolving BUG-01 subtraction and maintaining CQ_add (BUG-04) correctness.

## Changes Made

### 1. gate.c QFT/IQFT qubit processing order (ROOT CAUSE)

**Problem:** The QFT in gate.c processed qubits from index 0 upward (LSB first). The textbook QFT processes from index n-1 downward (MSB first). This produced a non-standard Fourier transform that could not be corrected by any combination of target/control remapping in the adder functions.

**Fix:** Reversed the qubit processing order by introducing `int q = num_qubits - 1 - j` mapping in both QFT and QFT_inverse. The loop variable `j` still iterates 0..n-1 (preserving the layer structure), but the actual qubit operated on is `q = n-1-j`. This means:
- QFT first processes qubit n-1 (H + controlled phases), then n-2, ..., finally qubit 0
- IQFT reverses this order correctly

The controlled phase gates `cp(q, q-i-1, pi/2^(i+1))` now correctly pair the processed qubit with lower-indexed qubits, matching the textbook formulation.

### 2. IntegerAddition.c CQ_add/cCQ_add layer allocation fix

**Problem:** The old `start_layer = bits` for phase rotations assumed QFT layers could be shared with rotation layers. With the corrected QFT, the gate-to-qubit mapping at intermediate layers changed, causing conflicts (two gates on the same qubit in the same layer).

**Fix:**
- Changed `start_layer` from `bits` to `2*bits-1` (placing rotations after all QFT layers)
- Changed `num_layer` from `4*bits-1` to `5*bits-2` (QFT: 2n-1, rotations: n, IQFT: 2n-1)
- Changed `used_layer++` to `used_layer += bits` after rotations

### 3. IntegerAddition.c QQ_add target formula

**Problem:** The target formula `target = bits - i - 1 - rounds` addressed Fourier qubits in descending order, matching the old (wrong) QFT convention.

**Fix:** Changed to `target = rounds + i` (ascending order), matching the corrected QFT's Fourier-domain qubit ordering. This is exactly the fix originally proposed in plan 29-09's initial draft.

### 4. IntegerAddition.c cQQ_add target formulas

**Problem:** The controlled QQ_add (cQQ_add) had the same target reversal issue across all 3 blocks.

**Fix:** Applied consistent reversal:
- Block 1: `bit` -> `bits - 1 - bit`
- Block 2: `bit - i` -> `rounds + i`
- Block 3: `bit - i` -> `rounds + i`

### 5. Reverted plan 29-10 CQ_add workarounds

**Problem:** Plan 29-10 added qubit_array reversal in Python (qint.pyx) and rotation-to-qubit reversal in C (IntegerAddition.c) to compensate for the wrong QFT convention. With the correct QFT, these workarounds double-compensated.

**Fix:** Removed:
- Python qubit_array reversal loop in `addition_inplace()`
- C-side `rotations[bits-1-i]` mapping (restored to `rotations[i]`)
- Unused `j_rev` and `tmp_rev` variable declarations

## Test Results

### BUG-01 Subtraction (QQ_add) - ALL PASS
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| 3-7 | 12 | 12 | PASS |
| 7-3 | 4 | 4 | PASS |
| 5-5 | 0 | 0 | PASS |
| 0-1 | 15 | 15 | PASS |
| 15-0 | 15 | 15 | PASS |

### BUG-04 CQ_add (classical+quantum) - ALL PASS
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| 0+0 | 0 | 0 | PASS |
| 0+1 | 1 | 1 | PASS |
| 1+0 | 1 | 1 | PASS |
| 1+1 | 2 | 2 | PASS |
| 3+5 | 8 | 8 | PASS |
| 7+8 | 15 | 15 | PASS |
| 8+8 overflow | 0 | 0 | PASS |

### BUG-02 Comparison (uses cQQ_add) - PRE-EXISTING FAILURE
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| 5<=5 | 1 | 0 | FAIL (pre-existing) |
| 3<=7 | 1 | 0 | FAIL (pre-existing) |

Comparison failures are identical in both original and fixed code. Root cause is BUG-05 (circuit cache contamination) causing the restore step (`self += other`) to produce wrong results when QQ_add is invoked twice in the same circuit.

## Deviations from Plan

### [Rule 3 - Blocking] CQ_add/cCQ_add layer allocation fix

- **Found during:** Task 2 (testing)
- **Issue:** After fixing QFT qubit order, CQ_add tests still failed because phase rotation gates overlapped with QFT gates in the layer structure. The old `start_layer = bits` relied on layer sharing specific to the old QFT qubit-to-layer mapping.
- **Fix:** Changed `start_layer` to `2*bits-1` and `num_layer` to `5*bits-2`
- **Files modified:** c_backend/src/IntegerAddition.c

### [Rule 3 - Blocking] QQ_add target formula reversal

- **Found during:** Task 2 (testing)
- **Issue:** After fixing QFT, QQ_add's Fourier-domain targets were in reverse order
- **Fix:** Changed `target = bits - i - 1 - rounds` to `target = rounds + i`
- **Files modified:** c_backend/src/IntegerAddition.c

### [Rule 3 - Blocking] cQQ_add target formula reversal

- **Found during:** Task 2 (testing comparison tests)
- **Issue:** cQQ_add had same target ordering issue as QQ_add across all 3 blocks
- **Fix:** Applied consistent target reversal in all blocks
- **Files modified:** c_backend/src/IntegerAddition.c

### [Rule 3 - Blocking] CQ_add rotation mapping kept as direct (not reversed)

- **Found during:** Task 2 (testing)
- **Issue:** Initially tried reversing rotations[bits-1-i] for CQ_add, but Qiskit verification showed direct mapping (rotations[i]) is correct with the textbook QFT
- **Fix:** Kept direct rotation mapping, reverted 29-10's reversal
- **Files modified:** c_backend/src/IntegerAddition.c

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Remap qubit indices rather than reverse loop direction | Preserves layer structure (number of gates per layer unchanged), avoids recomputing memory allocation patterns |
| Revert 29-10 workarounds completely | With correct QFT, the qubit_array reversal and rotation reversal are unnecessary and cause double-compensation |
| Accept comparison test failures as pre-existing | Verified same failures occur with original code; root cause is BUG-05 cache contamination, not QFT convention |

## Files Modified

- `c_backend/src/gate.c` - QFT and QFT_inverse qubit processing order
- `c_backend/src/IntegerAddition.c` - CQ_add/cCQ_add layer allocation, QQ_add/cQQ_add target formulas, rotation mapping
- `src/quantum_language/qint.pyx` - Removed 29-10 qubit_array reversal workaround

## Commit

- `02fec7c`: fix(29-09): fix QFT/IQFT qubit processing order and Draper adder conventions
