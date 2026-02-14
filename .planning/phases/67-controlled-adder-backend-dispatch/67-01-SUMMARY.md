---
phase: 67-controlled-adder-backend-dispatch
plan: 01
subsystem: arithmetic
tags: [toffoli, cdkm, controlled-adder, ccx, mcx, ripple-carry]

# Dependency graph
requires:
  - phase: 66-cdkm-ripple-carry-adder
    provides: "Uncontrolled CDKM adder (toffoli_QQ_add, toffoli_CQ_add, emit_MAJ/emit_UMA, alloc_sequence)"
provides:
  - "toffoli_cQQ_add(bits): cached controlled QQ CDKM adder using cMAJ/cUMA chain"
  - "toffoli_cCQ_add(bits, val): per-call controlled CQ adder with CX-init + cCDKM + CX-cleanup"
  - "emit_cMAJ/emit_cUMA: controlled MAJ/UMA helpers using CCX + MCX (3 controls)"
  - "toffoli_sequence_free: large_control cleanup for leak-free MCX deallocation"
affects: [67-02 hot-path dispatch, 67-03 controlled subtraction]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Controlled CDKM via CCX + MCX(3 controls) pattern", "CX-based controlled classical init/cleanup"]

key-files:
  created: []
  modified:
    - c_backend/src/ToffoliAddition.c
    - c_backend/include/toffoli_arithmetic_ops.h

key-decisions:
  - "Control qubit at index 2*bits+1 (not 2*bits) to avoid ancilla collision"
  - "CX (not unconditional X) for cCQ temp init/cleanup to condition on control qubit"
  - "MCX with 3 controls for controlled Toffoli step (a AND b AND ext_ctrl)"

patterns-established:
  - "Controlled CDKM pattern: replace CNOT with CCX and CCX with MCX(3) throughout MAJ/UMA chain"
  - "Controlled CQ pattern: CX-init temp + controlled CDKM core + CX-cleanup"

# Metrics
duration: 5min
completed: 2026-02-14
---

# Phase 67 Plan 01: Controlled CDKM Adder Summary

**Controlled CDKM ripple-carry adder (cQQ/cCQ) using CCX + MCX gates with leak-free large_control cleanup**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-14T22:05:06Z
- **Completed:** 2026-02-14T22:10:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Implemented `emit_cMAJ` and `emit_cUMA` static helpers that condition every gate on an external control qubit using CCX + MCX(3 controls)
- Added `toffoli_cQQ_add(bits)` with separate cache array, 1-bit CCX special case, and general cMAJ/cUMA sweep for bits >= 2
- Added `toffoli_cCQ_add(bits, val)` with CX-based controlled temp init/cleanup and controlled CDKM core
- Fixed `toffoli_sequence_free()` to iterate gates and free `large_control` arrays for MCX gates with NumControls > 2
- Updated header with full qubit layout documentation and ownership contracts for both new functions

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement controlled CDKM adder (cQQ and cCQ) in ToffoliAddition.c** - `0141cd8` (feat)

**Plan metadata:** (pending)

## Files Created/Modified
- `c_backend/src/ToffoliAddition.c` - Added emit_cMAJ/emit_cUMA helpers, toffoli_cQQ_add, toffoli_cCQ_add, fixed toffoli_sequence_free
- `c_backend/include/toffoli_arithmetic_ops.h` - Added declarations for toffoli_cQQ_add and toffoli_cCQ_add with documented qubit layouts

## Decisions Made
- Control qubit placed at index 2*bits+1 (not 2*bits) to avoid collision with ancilla carry qubit
- Used CX (controlled-X) instead of unconditional X for cCQ temp register initialization, ensuring temp is only set when control is |1>
- MCX with 3 controls (a, b, ext_ctrl) for the controlled Toffoli step in cMAJ/cUMA, using the existing mcx() function with large_control allocation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-commit clang-format hook reformatted the C source code on first commit attempt. Re-staged and committed successfully on second attempt. No functional changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- C-level controlled adder functions are ready for hot-path dispatch wiring in Plan 02
- toffoli_cQQ_add returns cached sequences, toffoli_cCQ_add returns fresh per-call sequences
- toffoli_sequence_free handles MCX large_control cleanup for both uncontrolled and controlled sequences
- All 42 existing Toffoli addition tests pass (no regressions)

## Self-Check: PASSED

- FOUND: c_backend/src/ToffoliAddition.c (toffoli_cQQ_add: 8 refs, toffoli_cCQ_add: 2 refs, large_control: 3 refs)
- FOUND: c_backend/include/toffoli_arithmetic_ops.h
- FOUND: 67-01-SUMMARY.md
- FOUND: commit 0141cd8

---
*Phase: 67-controlled-adder-backend-dispatch*
*Completed: 2026-02-14*
