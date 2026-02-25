---
phase: 92-modular-toffoli-arithmetic
plan: 01
subsystem: arithmetic
tags: [beauregard, modular-addition, toffoli, cdkm, rca]

# Dependency graph
requires:
  - phase: 91-arithmetic-bug-fixes
    provides: "Clean orphan-qubit pattern for CDKM adder, working CQ/QQ primitives"
provides:
  - "Beauregard 8-step modular CQ addition (toffoli_mod_add_cq)"
  - "Beauregard 8-step modular QQ addition (toffoli_mod_add_qq)"
  - "Controlled modular CQ/QQ addition (toffoli_cmod_add_cq, toffoli_cmod_add_qq)"
  - "Modular CQ/QQ subtraction via N-complement (toffoli_mod_sub_cq, toffoli_mod_sub_qq)"
  - "Controlled modular CQ/QQ subtraction (toffoli_cmod_sub_cq, toffoli_cmod_sub_qq)"
affects: [92-02, 92-03, shor-algorithm]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Beauregard 8-step modular addition with clean ancilla uncomputation", "AND-ancilla pattern for doubly-controlled operations", "N-complement subtraction wrapper"]

key-files:
  created: []
  modified:
    - "c_backend/src/ToffoliModReduce.c"
    - "c_backend/include/toffoli_arithmetic_ops.h"

key-decisions:
  - "Beauregard 8-step sequence replaces broken add+reduce pattern for clean ancilla uncomputation"
  - "QQ subtraction uses temp register with N-complement: temp = N - other, mod_add_qq(value, temp, N), uncompute temp"
  - "CDKM QQ adder modifies register b (position bits..2*bits-1), NOT register a -- source goes to a-position, target to b-position"
  - "AND-ancilla pattern for doubly-controlled operations: CCX(and_anc, ctrl1, ctrl2); op(and_anc); CCX(and_anc, ctrl1, ctrl2)"
  - "Direct calls to toffoli_CQ_add/toffoli_QQ_add (forces RCA), not hot_path dispatch (which could select CLA)"

patterns-established:
  - "Beauregard 8-step: add a, sub N, copy sign, cond add N, sub a, flip, copy sign, add a"
  - "CDKM register convention: a-register = source (preserved), b-register = target (modified)"

requirements-completed: [MOD-01, MOD-02, MOD-03]

# Metrics
duration: 25min
completed: 2026-02-25
---

# Phase 92-01: Beauregard Modular Add/Sub Summary

**Beauregard 8-step modular CQ/QQ addition and subtraction at C level with zero persistent ancillae**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Replaced broken add+reduce modular addition with Beauregard 8-step sequence that cleanly uncomputes all ancillae
- Implemented all 8 variants: CQ add/sub, QQ add/sub, each with uncontrolled and controlled versions
- Fixed critical CDKM QQ register ordering bug (source at a-position, target at b-position)

## Task Commits

1. **Task 1: Beauregard CQ add/sub** - `2916033` (feat) - 8-step CQ modular addition, controlled CQ, CQ subtraction via N-complement
2. **Task 2: Beauregard QQ add/sub** - `2916033` (feat) - QQ modular addition with temp register padding, QQ subtraction via complement-and-add
3. **Bug fix: CDKM register swap** - `37ffa9e` (fix) - Corrected QQ register ordering in mod_qq_add and mod_cqq_add

## Files Created/Modified
- `c_backend/src/ToffoliModReduce.c` - Beauregard modular add/sub for CQ and QQ (8 public functions + 6 static helpers)
- `c_backend/include/toffoli_arithmetic_ops.h` - Function declarations for all modular add/sub variants

## Decisions Made
- Beauregard 8-step replaces add+reduce to avoid persistent ancilla leak
- QQ subtraction uses temp register: compute (N - other), add to value, uncompute temp
- CDKM register ordering: b-register is modified, a-register is preserved (header comment in ToffoliAdditionCDKM.c is misleading)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] CDKM QQ register ordering bug**
- **Found during:** QQ verification testing
- **Issue:** mod_qq_add and mod_cqq_add placed target at CDKM a-position and source at b-position, but CDKM computes b += a (not a += b)
- **Fix:** Swapped register assignments so source goes to a (preserved) and target goes to b (modified), matching hot_path_add_toffoli.c convention
- **Files modified:** c_backend/src/ToffoliModReduce.c
- **Verification:** 10/10 QQ add+sub tests pass after fix
- **Committed in:** 37ffa9e

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Critical correctness fix. Without it, all QQ operations returned self value unchanged.

## Issues Encountered
- CDKM header comment says "a (target, modified)" but actually b is modified. Confirmed by examining hot_path_add_toffoli.c lines 98-106 which explicitly swaps registers.

## Next Phase Readiness
- All modular add/sub primitives available for Plan 02 (multiplication + Python rewiring)
- Register ordering convention now documented in code comments

---
*Phase: 92-modular-toffoli-arithmetic*
*Completed: 2026-02-25*
