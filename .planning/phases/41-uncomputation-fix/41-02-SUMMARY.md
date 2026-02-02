# Phase 41 Plan 02: Gap Closure - Layer Tracking on lt/gt Results

**One-liner:** Added _start_layer/_end_layer to __lt__/__gt__ results in qint.pyx, reversing decision D41-01-3; no regressions across 5711 tests.

## Metadata

- **Phase:** 41-uncomputation-fix
- **Plan:** 02 (gap closure)
- **Subsystem:** uncomputation / comparison
- **Duration:** ~31 minutes
- **Completed:** 2026-02-02

## What Was Done

### Task 1: Add layer tracking to __lt__ and __gt__ results

Added `start_layer` capture and `_start_layer`/`_end_layer` assignment to the qint-vs-qint comparison paths in both `__lt__` and `__gt__` methods in `qint.pyx`. This matches the pattern already present in `qint_comparison.pxi` (lines 265-267 for lt, 376-378 for gt).

**Changes:**
- `__lt__` (line ~1878): Added `start_layer = (<circuit_s*>_circuit).used_layer` capture
- `__lt__` (line ~1931): Set `result._start_layer = start_layer` and `result._end_layer`
- `__gt__` (line ~1987): Added `start_layer` capture
- `__gt__` (line ~2033): Set `result._start_layer = start_layer` and `result._end_layer`
- Removed old D41-01-3 comments ("NOT setting _start_layer/_end_layer")

### Task 2: Verify test markers and full suite

No xfail markers needed adding or removing. The 4 pre-existing failures remain unchanged. The 2 existing xfail markers (gt_3v1_w3, le_1v2_w3) are still correct.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing start_layer variable declaration in __lt__/__gt__**

- **Found during:** Task 1 (Cython compilation failed)
- **Issue:** Plan stated "Both methods already have `start_layer` captured at the top" but this was incorrect. The `start_layer` variable was NOT declared or captured in either `__lt__` or `__gt__` in qint.pyx.
- **Fix:** Added `start_layer = (<circuit_s*>_circuit).used_layer if _circuit_initialized else 0` after the use-after-uncompute checks in both methods, matching the .pxi pattern.
- **Files modified:** src/quantum_language/qint.pyx
- **Commit:** 9f407d4

## Key Finding: Layer Tracking Limitation

The 4 pre-existing test failures were NOT resolved by this change. Investigation revealed a deeper architectural issue:

**Root cause:** The circuit optimizer places gates as early as possible (parallelization). When two independent operations target different qubits, their gates share the same layers. The `used_layer` counter only tracks the maximum layer ever used, NOT a monotonically increasing instruction counter. This means:

1. **First comparison:** `start_layer=1`, `end_layer=19` (correct, 18 layers of gates)
2. **Second comparison:** `start_layer=19`, `end_layer=19` (broken -- new gates placed into existing layers 1-18, so used_layer stays at 19)

**Impact:** `_do_uncompute` only reverses gates when `end_layer > start_layer`. For the second comparison, no gates are reversed.

**Remaining failures:**
- `test_uncomp_comparison_ancilla[lt_1v3_w3]`: Ancilla dirty (widened temp gates not reversed before QASM export)
- `test_uncomp_comparison_ancilla[ge_2v2_w3]`: Same root cause (ge delegates to lt)
- `test_uncomp_compound_and`: 31 qubits (OOM) -- both comparisons' widened temps unreversed
- `test_uncomp_compound_or`: 31 qubits (OOM) -- same

**Future fix needed:** Replace layer-based tracking with instruction-counter-based tracking, or add explicit gate-reversal logic within `__lt__`/`__gt__` for widened temps before returning the result.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D41-02-1 | Revise D41-01-3: Layer tracking IS set on lt/gt results | Widened temps have no layer tracking, so no double-reversal risk. Required for correct uncomputation when result is eventually uncomputed. |
| D41-02-2 | Keep 4 pre-existing failures as-is | Root cause is architectural (layer counter vs instruction counter), not fixable by layer tracking alone. |

## Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| Comparison (test_compare.py) | 1515 | All pass |
| Addition (test_add.py) | 888 | All pass |
| Subtraction (test_sub.py) | 888 | All pass |
| Bitwise (test_bitwise.py) | 2418 | All pass |
| Uncomputation (test_uncomputation.py) | 20 | 14 pass, 2 xfail, 4 fail (unchanged) |
| **Total** | **5729** | **5711 pass, 2 xfail, 4 fail (0 regressions)** |

## Files Modified

| File | Change |
|------|--------|
| src/quantum_language/qint.pyx | Added start_layer capture and _start_layer/_end_layer on __lt__/__gt__ results |

## Commits

| Hash | Message |
|------|---------|
| 9f407d4 | feat(41-02): add layer tracking to __lt__ and __gt__ results in qint.pyx |

## Next Phase Readiness

The layer tracking infrastructure is now complete (all operations in qint.pyx set _start_layer/_end_layer). However, the layer-based uncomputation mechanism has a fundamental limitation with the circuit optimizer's gate parallelization. A future phase should investigate instruction-counter-based tracking if the 4 remaining uncomputation failures need to be resolved.
