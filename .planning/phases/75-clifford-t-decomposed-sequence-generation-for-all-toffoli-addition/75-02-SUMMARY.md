---
phase: 75-clifford-t-decomposed-sequence-generation-for-all-toffoli-addition
plan: 02
subsystem: sequences
tags: [clifford-t, bk-cla, carry-lookahead, toffoli, hardcoded-sequences, code-generation]

# Dependency graph
requires:
  - phase: 71-cla-carry-lookahead-adder
    provides: "BK CLA algorithm (bk_compute_merges, 6-phase compute-copy-uncompute pattern)"
  - phase: 74-mcx-ccx-gate-decomposition
    provides: "CCX->Clifford+T decomposition (15-gate pattern), AND-ancilla MCX decomposition"
provides:
  - "BK CLA Clifford+T generation script (scripts/generate_toffoli_clifft_cla.py)"
  - "28 per-width BK CLA Clifford+T C sequence files (QQ/cQQ/CQ_inc/cCQ_inc x widths 2-8)"
  - "Unified BK CLA Clifford+T dispatch file with 4 dispatch functions"
  - "Python BK prefix tree implementation matching C bk_compute_merges()"
affects: [75-03-wiring, toffoli-clifford-t-dispatch]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Python BK prefix tree port for sequence generation", "CCX->Clifford+T expansion in generation scripts"]

key-files:
  created:
    - "scripts/generate_toffoli_clifft_cla.py"
    - "c_backend/src/sequences/toffoli_clifft_cla_qq_*.c (7 files)"
    - "c_backend/src/sequences/toffoli_clifft_cla_cqq_*.c (7 files)"
    - "c_backend/src/sequences/toffoli_clifft_cla_cq_inc_*.c (7 files)"
    - "c_backend/src/sequences/toffoli_clifft_cla_ccq_inc_*.c (7 files)"
    - "c_backend/src/sequences/toffoli_clifft_cla_dispatch.c"
  modified: []

key-decisions:
  - "Python BK prefix tree implementation ported exactly from C bk_compute_merges() in ToffoliAdditionCLA.c"
  - "Width 1 excluded from BK CLA sequences (BK CLA returns NULL for bits < 2, falls back to RCA)"
  - "BK merge counts: width 7 = 7 merges, width 8 = 9 merges (plan said 6 for both, C code produces more)"
  - "CQ increment (value=1) uses classical-bit simplification: only bit 0 active, all other bits NOP"
  - "cCQ increment injects ext_ctrl into all gates, with AND-ancilla for MCX(3) decomposition"

patterns-established:
  - "BK CLA Clifford+T generation pattern: build X/CX/CCX intermediate, expand CCX->15 Clifford+T"
  - "CQ classical-bit simplification for value=1 in BK CLA context"
  - "Controlled CLA: inject ext_ctrl + AND-ancilla MCX decomposition before Clifford+T expansion"

requirements-completed: [INF-03]

# Metrics
duration: 6min
completed: 2026-02-17
---

# Phase 75 Plan 02: BK CLA Clifford+T Sequence Generation Summary

**BK CLA Clifford+T hardcoded sequences for all 4 variants (QQ/cQQ/CQ_inc/cCQ_inc) at widths 2-8 via Python BK prefix tree port and CCX decomposition**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-17T23:31:47Z
- **Completed:** 2026-02-17T23:38:10Z
- **Tasks:** 1
- **Files created:** 30 (1 script + 28 per-width C files + 1 dispatch C file)

## Accomplishments
- Created generate_toffoli_clifft_cla.py (1300 lines) with Python port of C bk_compute_merges()
- Generated 28 per-width C files: 7 widths x 4 variants (QQ, cQQ, CQ_inc, cCQ_inc)
- Generated unified dispatch file with 4 dispatch functions for BK CLA Clifford+T lookup
- All 28 sequences verified: zero CCX gates, max 1 control per gate, only H/T/Tdg/CX/X
- BK merge computation validated against C formula (7*n - 4 + 4*num_merges)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create BK CLA Clifford+T generation script with Python BK prefix tree** - `5ab371d` (feat)

## Files Created/Modified

- `scripts/generate_toffoli_clifft_cla.py` - BK CLA Clifford+T generation script (1300 lines, Python BK prefix tree, 4 variant generators, validation mode)
- `c_backend/src/sequences/toffoli_clifft_cla_qq_2.c` through `..._qq_8.c` - QQ BK CLA Clifford+T sequences (38-788 gates)
- `c_backend/src/sequences/toffoli_clifft_cla_cqq_2.c` through `..._cqq_8.c` - cQQ BK CLA Clifford+T sequences (210-2820 gates)
- `c_backend/src/sequences/toffoli_clifft_cla_cq_inc_2.c` through `..._cq_inc_8.c` - CQ increment Clifford+T sequences (9-561 gates)
- `c_backend/src/sequences/toffoli_clifft_cla_ccq_inc_2.c` through `..._ccq_inc_8.c` - cCQ increment Clifford+T sequences (65-1865 gates)
- `c_backend/src/sequences/toffoli_clifft_cla_dispatch.c` - Unified dispatch with 4 functions

## Decisions Made

1. **BK merge counts differ from plan estimates:** Plan stated "width 8 = 6 merges" but actual C bk_compute_merges() produces 9 merges for n_carries=7 (width 8). Python port matches C exactly. The plan's expected values were approximate; the implementation is correct.

2. **CQ increment classical-bit simplification:** For value=1 (only LSB set), Phase A and Phase E simplify dramatically: only bit 0 generates gates, all other bits produce NOPs. This significantly reduces sequence size (e.g., width 4 CQ_inc = 133 gates vs width 4 QQ = 228 gates).

3. **cCQ increment controlled phases:** Phases B/C/D use the cQQ gate pattern (all gates controlled by ext_ctrl), while Phases A/E/F use direct controlled simplifications. This matches the C toffoli_cCQ_add_bk() structure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed expected BK merge counts in validation**
- **Found during:** Task 1 (validation mode)
- **Issue:** Plan specified width 7 = 6 merges, width 8 = 6 merges, but actual C bk_compute_merges() produces width 7 = 7, width 8 = 9
- **Fix:** Updated expected_merge_counts dict to match actual C output (verified via formula cross-check)
- **Files modified:** scripts/generate_toffoli_clifft_cla.py
- **Verification:** --validate passes for all widths
- **Committed in:** 5ab371d

---

**Total deviations:** 1 auto-fixed (1 bug in plan's expected values)
**Impact on plan:** Corrected expected values to match actual C implementation. No scope creep.

## Issues Encountered

- Pre-commit hooks (ruff, clang-format) required two commit attempts: first to fix Python lint issues (unused variable, set comprehension), second to stage clang-formatted C files.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 29 generated BK CLA Clifford+T C files ready for wiring into dispatch
- Plan 03 can wire these into ToffoliAdditionCLA.c dispatch and add to build system
- Python BK prefix tree implementation available for testing cross-validation

## Self-Check: PASSED

- All 30 files verified present (1 script + 28 per-width C + 1 dispatch)
- Commit 5ab371d verified in git log
- Validation mode confirms all sequences pure Clifford+T (zero CCX, max 1 control)

---
*Phase: 75-clifford-t-decomposed-sequence-generation-for-all-toffoli-addition*
*Completed: 2026-02-17*
