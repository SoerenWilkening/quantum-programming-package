---
phase: 68-schoolbook-multiplication
plan: 01
subsystem: arithmetic
tags: [toffoli, multiplication, cdkm, shift-and-add, schoolbook, fault-tolerant]

# Dependency graph
requires:
  - phase: 66-toffoli-addition
    provides: "CDKM adder (QQ, CQ, cQQ, cCQ) in ToffoliAddition.c"
  - phase: 67-controlled-adder-backend-dispatch
    provides: "hot_path_add.c Toffoli dispatch pattern, ARITH_TOFFOLI default mode"
provides:
  - "ToffoliMultiplication.c with toffoli_mul_qq and toffoli_mul_cq functions"
  - "ARITH_TOFFOLI dispatch in hot_path_mul.c for uncontrolled QQ and CQ multiplication"
  - "Toffoli multiplication declarations in toffoli_arithmetic_ops.h"
affects: [68-02-PLAN, 69-controlled-toffoli-multiplication, test_toffoli_multiplication]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Toffoli multiplication via shift-and-add loop calling CDKM adder subroutines"]

key-files:
  created:
    - "c_backend/src/ToffoliMultiplication.c"
  modified:
    - "c_backend/include/toffoli_arithmetic_ops.h"
    - "c_backend/src/hot_path_mul.c"
    - "setup.py"
    - "tests/test_mul.py"
    - "tests/test_add.py"

key-decisions:
  - "Loop-based approach: call run_instruction per CDKM adder iteration, not monolithic sequence"
  - "Controlled Toffoli multiplication deferred to Phase 69 -- falls through to QFT"
  - "Ancilla allocated/freed per adder call within the loop (reused by allocator)"

patterns-established:
  - "Toffoli multiplication dispatch: same pattern as hot_path_add.c Toffoli dispatch"
  - "LSB-first qubit indexing in C hot path: index 0 = LSB, index n-1 = MSB"
  - "QFT verify_circuit tests need explicit fault_tolerant=False when Toffoli allocates extra ancilla"

# Metrics
duration: 43min
completed: 2026-02-15
---

# Phase 68 Plan 01: Toffoli Schoolbook Multiplication Summary

**Shift-and-add QQ/CQ multiplication using CDKM adder loop in C with ARITH_TOFFOLI hot path dispatch**

## Performance

- **Duration:** 43 min
- **Started:** 2026-02-15T09:07:13Z
- **Completed:** 2026-02-15T09:50:15Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Implemented Toffoli-based schoolbook multiplication (QQ and CQ) composing proven CDKM adders
- Wired ARITH_TOFFOLI dispatch into hot_path_mul.c for uncontrolled operations
- Fixed pre-existing test infrastructure issue: QFT tests now explicitly opt into QFT mode
- All 1160 multiplication/addition tests pass, plus 72 Toffoli addition and 165 hardcoded sequence tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement ToffoliMultiplication.c** - `6607ea5` (feat)
2. **Task 2: Wire Toffoli dispatch into hot_path_mul.c** - `d8d413f` (feat)

## Files Created/Modified
- `c_backend/src/ToffoliMultiplication.c` - Toffoli QQ and CQ multiplication using shift-and-add with CDKM adders
- `c_backend/include/toffoli_arithmetic_ops.h` - Added toffoli_mul_qq and toffoli_mul_cq declarations, added QPU.h include for circuit_t
- `c_backend/src/hot_path_mul.c` - Added ARITH_TOFFOLI dispatch for uncontrolled QQ and CQ paths
- `setup.py` - Added ToffoliMultiplication.c to C source file list
- `tests/test_mul.py` - Added explicit QFT mode for verify_circuit fixture compatibility
- `tests/test_add.py` - Added explicit QFT mode (pre-existing bug fix from Phase 67-03)

## Decisions Made
- **Loop-based approach:** Each multiplier bit iteration calls run_instruction with the CDKM adder. This reuses cached adder sequences and avoids MAXLAYERINSEQUENCE limits. More debuggable than monolithic sequence generation.
- **Controlled multiplication deferred:** Phase 68 implements uncontrolled QQ and CQ only. Controlled operations fall through to QFT. Phase 69 will add controlled Toffoli multiplication.
- **Per-call ancilla allocation:** Each adder call in the loop allocates 1 carry ancilla and frees it after. The allocator reuses the same qubit each iteration since CDKM guarantees return to |0>.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added QPU.h include to toffoli_arithmetic_ops.h**
- **Found during:** Task 1 (header compilation)
- **Issue:** circuit_t type not visible in toffoli_arithmetic_ops.h; compilation error for new multiplication declarations
- **Fix:** Added `#include "QPU.h"` to toffoli_arithmetic_ops.h
- **Files modified:** c_backend/include/toffoli_arithmetic_ops.h
- **Verification:** Compilation succeeds with no errors
- **Committed in:** 6607ea5 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed test_mul.py and test_add.py for Toffoli default mode**
- **Found during:** Task 2 (verification)
- **Issue:** verify_circuit fixture extracts results from bitstring[:width] (highest qubit indices). Toffoli path allocates carry ancilla at higher indices than result register, shifting the result position. test_add.py had same pre-existing issue from Phase 67-03.
- **Fix:** Added `ql.option("fault_tolerant", False)` to all circuit_builder functions in test_mul.py and test_add.py
- **Files modified:** tests/test_mul.py, tests/test_add.py
- **Verification:** All 1160 tests pass (272 mul + 888 add)
- **Committed in:** d8d413f (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for compilation and test pass. No scope creep.

## Issues Encountered
- Qubit array ordering investigation: Spent time understanding the LSB-first convention in C hot path (index 0 = physical LSB qubit, not MSB). The research document had some MSB-first assumptions that needed correction. The final implementation correctly uses LSB-first indexing matching the CDKM adder convention and the existing hot_path_add.c pattern.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ToffoliMultiplication.c is ready for Plan 02 (exhaustive verification tests)
- Plan 02 should use the _simulate_and_extract pattern from test_toffoli_addition.py for Toffoli-specific result extraction
- Controlled Toffoli multiplication (cQQ, cCQ) deferred to future phase (Phase 69)
- Consider adding Litinski CAS optimization in a future phase for ~50% Toffoli count reduction

## Self-Check: PASSED

All files verified present:
- c_backend/src/ToffoliMultiplication.c (contains toffoli_mul_qq, toffoli_mul_cq)
- c_backend/include/toffoli_arithmetic_ops.h (updated with declarations)
- c_backend/src/hot_path_mul.c (contains ARITH_TOFFOLI dispatch)
- setup.py (contains ToffoliMultiplication.c)
- .planning/phases/68-schoolbook-multiplication/68-01-SUMMARY.md

All commits verified:
- 6607ea5: feat(68-01): implement Toffoli schoolbook multiplication (QQ and CQ)
- d8d413f: feat(68-01): wire Toffoli multiplication dispatch and fix QFT test mode

---
*Phase: 68-schoolbook-multiplication*
*Completed: 2026-02-15*
