---
phase: 66-cdkm-ripple-carry-adder
plan: 03
subsystem: arithmetic
tags: [toffoli, cdkm, cq-addition, ripple-carry, fault-tolerant]

# Dependency graph
requires:
  - phase: 66-01
    provides: "CDKM QQ adder with MAJ/UMA chain, emit_MAJ/emit_UMA helpers"
  - phase: 66-02
    provides: "Python integration, hot_path_add dispatch, exhaustive test framework"
provides:
  - "Correct CQ Toffoli addition using temp-register QQ approach"
  - "CQ Toffoli subtraction via inversion"
  - "All 42 Toffoli tests passing (0 xfail)"
  - "BUG-CQ-TOFFOLI resolved"
affects: [67-controlled-toffoli, toffoli-cq-operations]

# Tech tracking
tech-stack:
  added: []
  patterns: ["temp-register approach for CQ: init temp via X, run QQ adder, X-cleanup"]

key-files:
  modified:
    - "c_backend/src/ToffoliAddition.c"
    - "c_backend/src/hot_path_add.c"
    - "c_backend/include/toffoli_arithmetic_ops.h"
    - "tests/test_toffoli_addition.py"

key-decisions:
  - "Temp-register approach for CQ: allocate N temp qubits, X-init to classical value, run proven QQ CDKM adder, X-cleanup"
  - "CQ now uses 2*N+1 qubits (N temp + N self + 1 carry) instead of N+1"
  - "CQ tests use dedicated _verify_toffoli_cq() for correct result extraction from qubit position 0"

patterns-established:
  - "Temp-register CQ pattern: reuse QQ adder for CQ by X-initializing a temp register to classical value"

# Metrics
duration: 18min
completed: 2026-02-14
---

# Phase 66 Plan 03: CQ Toffoli Gap Closure Summary

**Fixed CQ Toffoli addition by replacing buggy MAJ/UMA CQ simplification with temp-register QQ approach using X-init, proven CDKM adder, and X-cleanup**

## Performance

- **Duration:** 18 min
- **Started:** 2026-02-14T21:04:52Z
- **Completed:** 2026-02-14T21:22:42Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- CQ Toffoli addition produces correct results for all input pairs at widths 1-4 (exhaustive verification)
- CQ Toffoli subtraction (via inverted adder) produces correct results for all input pairs at widths 1-4
- All 42 Toffoli tests pass with 0 failures and 0 xfail markers
- BUG-CQ-TOFFOLI (documented in 66-02) fully resolved
- No regressions in QFT test suite

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite toffoli_CQ_add to use temp-register QQ approach** - `911e442` (fix)
2. **Task 2: Update CQ hot path dispatch and enable CQ tests** - `c313bbe` (feat)

## Files Created/Modified
- `c_backend/src/ToffoliAddition.c` - Deleted 4 buggy CQ MAJ/UMA helpers, rewrote toffoli_CQ_add general case with temp-register + QQ CDKM approach
- `c_backend/src/hot_path_add.c` - Updated hot_path_add_cq to allocate self_bits+1 ancilla and build tqa[] with new layout
- `c_backend/include/toffoli_arithmetic_ops.h` - Updated toffoli_CQ_add documentation with new qubit layout
- `tests/test_toffoli_addition.py` - Added _verify_toffoli_cq() helper, removed xfail markers, updated CQ test class docstring

## Decisions Made
- **Temp-register approach over fixing CQ simplification:** The 2-qubit MAJ/UMA CQ simplification was fundamentally flawed (MAJ with a classical bit cannot be correctly simplified to a 2-qubit unitary). Rather than attempting to fix the simplification, we reuse the proven QQ CDKM adder by allocating a temp register initialized to the classical value via X gates. This is correct by construction since the QQ adder is already exhaustively verified.
- **2*N+1 qubits for CQ:** The temp-register approach uses more qubits (2*N+1 vs N+1) but guarantees correctness. The extra qubits are ancilla that are freed after each operation.
- **Dedicated CQ test verification:** Created `_verify_toffoli_cq()` helper that extracts results from qubit position 0 (where the self register lives), since the generic `verify_circuit` fixture reads from the top qubits which are now ancilla.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CQ test result extraction from wrong qubit position**
- **Found during:** Task 2 (enabling CQ tests)
- **Issue:** The CQ tests used the `verify_circuit` fixture which extracts results from the highest-indexed qubits (bitstring[:width]). With the new layout, the ancilla qubits are at the highest indices (all |0>), so all test results were 0.
- **Fix:** Created `_verify_toffoli_cq()` helper that uses `_simulate_and_extract()` with result_start=0, matching the self register position. Changed CQ tests to use this helper instead of the verify_circuit fixture.
- **Files modified:** tests/test_toffoli_addition.py
- **Verification:** All 42 tests pass
- **Committed in:** c313bbe (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential fix for correct test validation. The test extraction was never validated for CQ since those tests were xfailed. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 success criteria for Phase 66 CDKM Ripple-Carry Adder are now fully satisfied
- QQ addition: exhaustive pass at widths 1-4
- CQ addition: exhaustive pass at widths 1-4
- QQ/CQ subtraction: exhaustive pass at widths 1-4
- Mixed-width: representative test pass
- Ancilla lifecycle: no leaks detected
- Gate purity: CQ circuits use only CCX/CX/X gates
- Ready for Phase 67 (controlled Toffoli operations)
- BUG-CQ-TOFFOLI can be removed from STATE.md blockers

## Self-Check: PASSED

All files verified to exist on disk. All commit hashes verified in git log.

---
*Phase: 66-cdkm-ripple-carry-adder*
*Completed: 2026-02-14*
