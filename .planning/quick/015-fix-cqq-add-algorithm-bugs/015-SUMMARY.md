---
phase: quick-015
plan: 01
subsystem: arithmetic
tags: [cQQ_add, controlled-addition, QFT, CCP-decomposition, hardcoded-sequences]

# Dependency graph
requires:
  - phase: 58-hardcoded-sequences-1-8
    provides: "Hardcoded QQ_add and cQQ_add gate sequences for widths 1-8"
  - phase: quick-014
    provides: "Identified BUG-CQQ-ARITH: Python qubit layout mismatch"
provides:
  - "Fixed cQQ_add algorithm producing correct arithmetic for widths 1-8"
  - "Python qubit layout matches C backend for controlled addition"
  - "Regenerated hardcoded sequences with corrected Block 2 CP decomposition"
affects: [59-hardcoded-sequences-9-16, controlled-multiplication, division]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - "src/quantum_language/qint_arithmetic.pxi"
    - "c_backend/src/IntegerAddition.c"
    - "scripts/generate_seq_1_4.py"
    - "scripts/generate_seq_5_8.py"
    - "c_backend/src/sequences/add_seq_1_4.c"
    - "c_backend/src/sequences/add_seq_5_8.c"

key-decisions:
  - "BUG-CQQ-015-01: Control qubit at 2*bits (matching C's `int control = 2 * bits`), not 3*bits-1"
  - "BUG-CQQ-015-02: Block 2 negative CP uses b-register qubit (bits+bit) as control per CCP decomposition theory"

patterns-established: []

# Metrics
duration: 5min
completed: 2026-02-06
---

# Quick Task 015: Fix cQQ_add Algorithm Bugs Summary

**Fixed two cQQ_add bugs: Python control qubit placement (2*bits not 3*bits-1) and Block 2 CCP decomposition using b-register control for negative rotations**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-06T09:59:24Z
- **Completed:** 2026-02-06T10:04:01Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Fixed Python qubit layout to place control at position 2*bits, matching C backend's `int control = 2 * bits`
- Fixed Block 2 CP gates in CCP decomposition: negative rotations now controlled by b-register qubit (bits+bit), not external control
- Applied fix consistently across C backend, both generation scripts, and Python frontend
- Regenerated all hardcoded sequences for widths 1-8 from fixed algorithm
- All 61 hardcoded sequence tests pass
- All 31 Python addition tests pass (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix cQQ_add algorithm bugs in all 4 source files** - `5eb1be3` (fix)
2. **Task 2: Regenerate hardcoded sequences and validate** - `c891a32` (feat)

## Files Created/Modified
- `src/quantum_language/qint_arithmetic.pxi` - Fixed control qubit at 2*result_bits, ancillas at 2*result_bits+1+i
- `c_backend/src/IntegerAddition.c` - Fixed Block 2 CP: `cp(g, target_q, bits + bit, -value)`
- `scripts/generate_seq_1_4.py` - Fixed Block 2 CP: `Gate("P", target_q, bits + bit, -value)`
- `scripts/generate_seq_5_8.py` - Fixed Block 2 CP: `Gate("P", target_q, bits + bit, -value)`
- `c_backend/src/sequences/add_seq_1_4.c` - Regenerated (1512 lines) with corrected gate indices
- `c_backend/src/sequences/add_seq_5_8.c` - Regenerated (6355 lines) with corrected gate indices

## Decisions Made
- **BUG-CQQ-015-01:** Python side must use `qubit_array[2 * result_bits]` for control, matching C's `int control = 2 * bits`. The previous `3 * result_bits - 1` left a gap that misaligned all qubit positions.
- **BUG-CQQ-015-02:** In the CCP(theta) decomposition `CP(t/2)_{c,t} . CNOT_{c,b} . CP(-t/2)_{b,t} . CNOT_{c,b} . CP(t/2)_{b,t}`, the negative rotation (step 3) must use the b-register qubit as control. The CNOT flips `bits+bit` conditioned on `control`, so `bits+bit` is the active control for the negative half-rotation.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Build required `python3 setup.py build_ext --inplace` instead of `pip install -e .` due to build isolation not finding `build_preprocessor` module. This is a known project setup characteristic.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- BUG-CQQ-ARITH is now FIXED: cQQ_add produces correct arithmetic for all widths 1-8
- Controlled addition is now reliable for dependent operations (controlled multiplication, division)
- Phase 59 (hardcoded sequences 9-16) can proceed with confidence in the algorithm correctness

---
*Quick Task: 015-fix-cqq-add-algorithm-bugs*
*Completed: 2026-02-06*
