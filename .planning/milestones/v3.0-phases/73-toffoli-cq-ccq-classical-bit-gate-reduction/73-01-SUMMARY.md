---
phase: 73-toffoli-cq-ccq-classical-bit-gate-reduction
plan: 01
subsystem: arithmetic
tags: [toffoli, cdkm, bk-cla, cq, ccq, gate-reduction, classical-bit, t-count]

# Dependency graph
requires:
  - phase: 72-performance-polish
    provides: "Hardcoded Toffoli sequences, T-count reporting, MCX decomposition"
  - phase: 71-carry-lookahead-adder
    provides: "BK CLA infrastructure, cQQ/cCQ dispatch, qubit_saving option"
provides:
  - "Inline CQ/cCQ CDKM generators with classical-bit gate simplification"
  - "Inline CQ/cCQ BK CLA generators with classical-bit gate simplification"
  - "Exhaustive CQ/cCQ correctness tests at widths 1-4"
  - "Gate count and T-count reduction verification"
affects: [toffoli-arithmetic, gate-optimization, t-count-reduction]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Classical-bit gate simplification: CX(|0>)=NOP, CCX(|0>)=NOP, CX(|1>)=X, CCX(|1>)=CX"
    - "Inline BK CLA Phase F: temp[i]=|0> after Phase E means copied CX/CCX are NOPs; replaced with direct X/CX for bit=1 positions"

key-files:
  created:
    - tests/test_toffoli_cq_reduction.py
  modified:
    - c_backend/src/ToffoliAddition.c

key-decisions:
  - "Inline CQ/cCQ generators instead of temp-register copy approach for CDKM and BK CLA"
  - "Phase F in BK CLA must be inlined (not copied from QQ) because temp[i]=|0> after Phase E"
  - "UMA gates not simplified (locked decision from research: carry propagation state is quantum)"
  - "cCQ bit=1 positions: CX-init + standard cMAJ (temp entangled with ext_ctrl, cannot simplify)"

patterns-established:
  - "emit_CQ_MAJ/emit_cCQ_MAJ: static helpers for classical-bit-aware MAJ gate emission"
  - "compute_CQ_layer_count/compute_cCQ_layer_count: precise layer counting for allocation"
  - "BK CLA CQ/cCQ: Phases A/E simplified, Phases B/C/D copied from QQ, Phase F inlined"

requirements-completed: [ADD-02, ADD-04, ADD-05, INF-04]

# Metrics
duration: ~25min
completed: 2026-02-17
---

# Phase 73 Plan 01: CQ/cCQ Classical-Bit Gate Reduction Summary

**Inline CQ/cCQ CDKM and BK CLA generators that eliminate gates at zero-bit positions, reducing T-count by 7-14T per zero bit**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- Replaced 4 temp-register CQ/cCQ function bodies with inline generators exploiting known classical bit values
- CDKM CQ/cCQ: skip MAJ gates at bit=0 positions (carry=|0>), fold X-init at bit=1 positions
- BK CLA CQ/cCQ: simplify Phase A/E (skip CCX/CX at bit=0), inline Phase F (temp[i]=|0> after uncompute)
- 39 exhaustive correctness tests verifying all CQ/cCQ addition/subtraction variants at widths 1-4
- Gate count and T-count reduction confirmed: sparse classical values produce fewer gates than dense values
- Zero regressions across 89 existing Toffoli tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement inline CQ/cCQ CDKM and BK CLA generators** - `be93b7b` (feat)
2. **Task 1 fix: BK CLA CQ/cCQ Phase F inline generation** - `804b784` (fix)
3. **Task 2: Write exhaustive correctness and gate reduction tests** - `1ab7945` (test)

## Files Created/Modified
- `c_backend/src/ToffoliAddition.c` - Inline CQ/cCQ CDKM + BK CLA generators with classical-bit gate simplification; 4 new static helpers (emit_CQ_MAJ, emit_cCQ_MAJ, compute_CQ_layer_count, compute_cCQ_layer_count)
- `tests/test_toffoli_cq_reduction.py` - 39 tests: exhaustive CQ/cCQ add/sub (widths 1-4), gate count comparison, T-count reduction, BK CLA correctness, gate purity

## Decisions Made
- Inline CQ/cCQ generators: generate gates directly from classical bit values instead of X-init + copy QQ + X-cleanup
- BK CLA Phase F must be inlined because after Phase E uncomputes temp[i] back to |0>, the original Phase F's CX(self[i], temp[i]) becomes a NOP; replaced with X(self[i]) for bit=1 and CX/CCX for carry
- UMA gates are NOT simplified (carry propagation state is quantum after MAJ, per locked research decision)
- cCQ bit=1 positions use CX-init + standard cMAJ (temp becomes entangled with ext_ctrl, precluding further simplification)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] BK CLA CQ/cCQ Phase F produces wrong results when copying from cached QQ**
- **Found during:** Task 2 (test verification)
- **Issue:** Phase E restores temp[i] to |0>, making Phase F's copied CX(self[i], temp[i]) a NOP instead of adding the classical value
- **Fix:** Inlined Phase F to emit X(self[i])/CX(self[i],ext_ctrl) for bit=1 positions and CX/CCX(self[i], c[i-1]) for carry addition; updated layer count from phase_bcdf to phase_bcd + phase_f
- **Files modified:** c_backend/src/ToffoliAddition.c
- **Verification:** All 6 BK CLA tests pass, all 89 existing tests pass
- **Committed in:** `804b784`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix essential for BK CLA CQ/cCQ correctness. No scope creep.

## Issues Encountered
- Pre-commit hook (clang-format) reformatted ToffoliAddition.c on first commit attempt; re-staged and committed successfully
- Pre-commit hook (ruff-format) reformatted test file; re-staged and committed successfully

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- CQ/cCQ gate reduction complete for both CDKM and BK CLA variants
- Gate count and T-count reduction verified via tests
- Ready for Phase 73 Plan 02 if applicable

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 73-toffoli-cq-ccq-classical-bit-gate-reduction*
*Completed: 2026-02-17*
