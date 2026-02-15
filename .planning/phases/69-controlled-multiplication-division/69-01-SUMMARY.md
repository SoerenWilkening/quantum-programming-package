---
phase: 69-controlled-multiplication-division
plan: 01
subsystem: arithmetic
tags: [toffoli, multiplication, controlled, and-ancilla, cdkm, mcx, fault-tolerant]

# Dependency graph
requires:
  - phase: 68-schoolbook-multiplication
    provides: "Toffoli QQ/CQ multiplication (toffoli_mul_qq, toffoli_mul_cq) in ToffoliMultiplication.c"
  - phase: 67-controlled-adder-backend-dispatch
    provides: "toffoli_cQQ_add controlled adder, MCX ownership pattern in run_instruction, hot path dispatch pattern"
provides:
  - "toffoli_cmul_qq: controlled QQ Toffoli multiplication using AND-ancilla pattern"
  - "toffoli_cmul_cq: controlled CQ Toffoli multiplication using cQQ adder with ext_ctrl"
  - "Controlled Toffoli dispatch in hot_path_mul.c (no more QFT fallback for controlled mul)"
affects: [69-02-PLAN, 69-03-PLAN, test_toffoli_multiplication]

# Tech tracking
tech-stack:
  added: []
  patterns: ["AND-ancilla pattern for controlled multiplication (CCX compute + cQQ adder + CCX uncompute)", "Direct MCX(3 controls) emission via add_gate for 1-bit controlled QQ mul"]

key-files:
  created: []
  modified:
    - "c_backend/src/ToffoliMultiplication.c"
    - "c_backend/include/toffoli_arithmetic_ops.h"
    - "c_backend/src/hot_path_mul.c"

key-decisions:
  - "AND-ancilla pattern for controlled QQ mul: reuses proven cQQ adder without modification"
  - "1-bit QQ controlled mul uses direct MCX(3 controls) instead of AND-ancilla overhead"
  - "Controlled CQ mul uses toffoli_cQQ_add with ext_ctrl mapped to control slot (no AND-ancilla needed)"
  - "Carry and AND ancilla allocated before loop, reused per iteration, freed after loop"

patterns-established:
  - "AND-ancilla controlled multiplication: CCX(and_anc, other[j], ext_ctrl) + cQQ_add(and_anc as ctrl) + CCX uncompute"
  - "Direct MCX gate emission via add_gate for small controlled operations"
  - "Controlled CQ multiplication: same loop as uncontrolled CQ but with cQQ_add instead of QQ_add"

# Metrics
duration: 25min
completed: 2026-02-15
---

# Phase 69 Plan 01: Controlled Toffoli Multiplication Summary

**Controlled Toffoli multiplication (cQQ via AND-ancilla + cCQ via ext_ctrl dispatch) with hot_path_mul.c routing -- no more QFT fallback for controlled mul**

## Performance

- **Duration:** 25 min
- **Started:** 2026-02-15T13:02:52Z
- **Completed:** 2026-02-15T13:28:23Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented toffoli_cmul_qq using AND-ancilla pattern: CCX computes AND(other[j], ext_ctrl), cQQ adder uses result as single control, CCX uncomputes AND
- Implemented toffoli_cmul_cq using toffoli_cQQ_add with ext_ctrl mapped to control slot for each set classical bit
- Width 1 special cases: MCX(3 controls) for QQ, CCX via toffoli_cQQ_add(1) for CQ
- Wired controlled Toffoli dispatch in hot_path_mul.c, eliminating QFT fallback for all Toffoli multiplication
- All 81 Toffoli tests and 165 hardcoded sequence tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement toffoli_cmul_qq and toffoli_cmul_cq** - `59f7c9d` (feat)
2. **Task 2: Wire controlled Toffoli dispatch in hot_path_mul.c** - `f709853` (feat)

## Files Created/Modified
- `c_backend/src/ToffoliMultiplication.c` - Added toffoli_cmul_qq (AND-ancilla pattern) and toffoli_cmul_cq (ext_ctrl dispatch) functions
- `c_backend/include/toffoli_arithmetic_ops.h` - Added declarations for controlled multiplication functions with full doc comments
- `c_backend/src/hot_path_mul.c` - Changed ARITH_TOFFOLI dispatch to handle both controlled and uncontrolled paths, removed Phase 69 deferral comments

## Decisions Made
- **AND-ancilla pattern for cQQ mul:** Computes AND(other[j], ext_ctrl) into a fresh ancilla, uses it as single control for the proven toffoli_cQQ_add. Avoids creating a doubly-controlled adder variant. Standard approach from Beauregard (2003), Haner et al. (2018).
- **1-bit MCX special case for cQQ mul:** Emits a single MCX(target=ret[n-1], controls=[self[0], other[j], ext_ctrl]) directly via add_gate, avoiding the 3-CCX overhead of the AND-ancilla pattern for 1 bit.
- **cCQ mul uses cQQ_add directly:** Since classical bit selection is compile-time, only the runtime ext_ctrl needs to gate each addition. Maps ext_ctrl to the control slot of toffoli_cQQ_add. No AND-ancilla needed.
- **Ancilla allocation strategy:** Carry and AND ancilla allocated before the loop and reused each iteration (CDKM returns carry to |0>, CCX uncomputes AND), freed after the loop. This avoids allocator pressure from per-iteration alloc/free.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - build succeeded on first attempt, all existing tests pass without modification.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Controlled Toffoli multiplication ready for Plan 02 (exhaustive verification tests)
- Plan 02 should test: cQQ mul with control=|1> (multiplication happens), control=|0> (no-op), and cCQ mul similarly
- Gate purity checks should verify no QFT gates (H, P) in output
- Result extraction for cQQ: ret at [2*width..3*width-1], ctrl at [3*width]

## Self-Check: PASSED

All files verified present:
- c_backend/src/ToffoliMultiplication.c (contains toffoli_cmul_qq, toffoli_cmul_cq)
- c_backend/include/toffoli_arithmetic_ops.h (contains declarations)
- c_backend/src/hot_path_mul.c (contains controlled dispatch, zero deferral comments)
- .planning/phases/69-controlled-multiplication-division/69-01-SUMMARY.md

All commits verified:
- 59f7c9d: feat(69-01): implement controlled Toffoli multiplication (cQQ and cCQ)
- f709853: feat(69-01): wire controlled Toffoli multiplication dispatch in hot_path_mul.c

---
*Phase: 69-controlled-multiplication-division*
*Completed: 2026-02-15*
