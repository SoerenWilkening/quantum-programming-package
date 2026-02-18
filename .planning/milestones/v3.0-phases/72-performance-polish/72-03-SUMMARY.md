---
phase: 72-performance-polish
plan: 03
subsystem: arithmetic
tags: [toffoli, multiplication, mcx-decomposition, and-ancilla, gate-optimization]

# Dependency graph
requires:
  - phase: 68-toffoli-multiplication
    provides: "Toffoli schoolbook QQ/CQ multiplication using CDKM adders"
  - phase: 69-controlled-toffoli-multiplication
    provides: "Controlled QQ/CQ multiplication with AND-ancilla pattern"
  - phase: 67-controlled-toffoli-addition
    provides: "Controlled CDKM adder (cQQ_add) with MCX(3-control) gates"
provides:
  - "MCX-free QQ multiplication via AND-ancilla decomposition of 3-control gates"
  - "MCX tracking in gate_counts (separate CCX vs MCX(3+) counting)"
  - "T-count and MCX count exposed in Python gate_counts dict"
affects: [72-performance-polish, controlled-multiplication, gate-statistics]

# Tech tracking
tech-stack:
  added: []
  patterns: ["AND-ancilla MCX decomposition for inline gate emission"]

key-files:
  created:
    - "tests/test_mul_addsub.py"
  modified:
    - "c_backend/src/ToffoliMultiplication.c"
    - "c_backend/include/circuit_stats.h"
    - "c_backend/src/circuit_stats.c"
    - "src/quantum_language/_core.pxd"
    - "src/quantum_language/_core.pyx"

key-decisions:
  - "Inline decomposed controlled CDKM adder instead of calling cached toffoli_cQQ_add()"
  - "AND-ancilla reused per iteration (starts and ends at |0> each step)"
  - "Carry and AND ancilla both allocated before loop, freed after"
  - "Separate CCX (2 controls) from MCX (3+ controls) in gate_counts_t for accurate tracking"

patterns-established:
  - "emit_cMAJ_decomposed/emit_cUMA_decomposed: inline CCX-only controlled CDKM gates"
  - "emit_controlled_add_decomposed: full controlled addition without MCX(3+) gates"

requirements-completed: [MUL-05]

# Metrics
duration: 22min
completed: 2026-02-16
---

# Phase 72 Plan 03: AND-Ancilla MCX Decomposition for QQ Multiplication Summary

**Eliminate all MCX(3-control) gates from QQ multiplication using AND-ancilla decomposition into pure CCX, with MCX tracking in gate_counts**

## Performance

- **Duration:** 22 min
- **Started:** 2026-02-16T22:49:02Z
- **Completed:** 2026-02-16T23:11:02Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Replaced all MCX(3-control) gates in toffoli_mul_qq with AND-ancilla decomposed CCX gates
- QQ multiplication circuits now contain ONLY X and CCX gates (zero MCX, zero QFT gates)
- Added MCX(3+) vs CCX(2) distinction in gate_counts for accurate tracking
- Exposed 'MCX' and 'T' keys in Python gate_counts dict
- 20 new verification tests + 21 existing tests all pass (41 total)

## Task Commits

Each task was committed atomically:

1. **Task 1: AND-ancilla MCX decomposition for QQ multiplication** - `208e45c` (feat)
2. **Task 2: Verification tests and MCX tracking in gate_counts** - `1281a79` (test)

## Files Created/Modified
- `c_backend/src/ToffoliMultiplication.c` - Optimized toffoli_mul_qq with inline decomposed controlled CDKM adder; new static helpers emit_cMAJ_decomposed, emit_cUMA_decomposed, emit_controlled_add_decomposed
- `c_backend/include/circuit_stats.h` - Added mcx_gates field to gate_counts_t, updated T-count formula
- `c_backend/src/circuit_stats.c` - Separate CCX (2 controls) from MCX (3+ controls) counting
- `src/quantum_language/_core.pxd` - Added mcx_gates and t_count to gate_counts_t Cython declaration
- `src/quantum_language/_core.pyx` - Exposed 'MCX' and 'T' keys in gate_counts property
- `tests/test_mul_addsub.py` - 20 verification tests: exhaustive correctness, gate count validation, non-regression

## Decisions Made
- **Inline vs cached sequence:** Emit decomposed gates directly via add_gate() rather than building and caching a sequence. This avoids complexity of managing variable-width sequences and allows the AND-ancilla qubit to be resolved at emission time.
- **AND-ancilla reuse:** Single AND-ancilla allocated before the loop, reused per iteration. Each decomposed cMAJ/cUMA compute-uncompute cycle restores the ancilla to |0>.
- **Width-1 optimization:** Width-1 iterations use a single CCX (2 controls: self[0], other[j]) instead of the original cQQ_add(1) CCX. This is equivalent but avoids the sequence lookup overhead.
- **MCX tracking in gate_counts:** Added separate MCX(3+) counting to gate_counts_t to enable testing the optimization's key claim (zero 3-control gates). This is a backward-compatible addition -- CCX count now excludes MCX(3+), matching user expectations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added MCX tracking to gate_counts_t**
- **Found during:** Task 2 (verification tests)
- **Issue:** The existing circuit_stats.c counted all X-type gates with 2+ controls as CCX, making it impossible to verify that MCX(3-control) gates were eliminated. The plan's test draft assumed 'other' count would capture MCX, but MCX gates have Gate=X so they were counted as CCX.
- **Fix:** Added mcx_gates field to gate_counts_t struct, separated CCX (exactly 2 controls) from MCX (3+ controls), exposed 'MCX' and 'T' keys in Python gate_counts dict.
- **Files modified:** circuit_stats.h, circuit_stats.c, _core.pxd, _core.pyx
- **Verification:** gate_counts['MCX'] = 0 for optimized QQ mul, gate_counts['MCX'] = 3 for controlled QQ mul (which still uses MCX internally)
- **Committed in:** 1281a79 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical functionality)
**Impact on plan:** The MCX tracking addition was essential to verify the optimization's correctness claim. No scope creep.

## Issues Encountered
None - the AND-ancilla decomposition worked correctly on the first attempt, producing identical multiplication results to the original implementation across all tested widths and input pairs.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- QQ multiplication now uses pure CCX gates, ready for further gate-count optimizations
- Controlled QQ multiplication (toffoli_cmul_qq) still uses MCX(3-control) from toffoli_cQQ_add -- could be optimized with the same technique in a future plan
- Gate count tracking now distinguishes CCX from MCX, enabling accurate benchmarking

## Self-Check: PASSED

All files verified present:
- c_backend/src/ToffoliMultiplication.c
- c_backend/include/circuit_stats.h
- c_backend/src/circuit_stats.c
- src/quantum_language/_core.pxd
- src/quantum_language/_core.pyx
- tests/test_mul_addsub.py
- .planning/phases/72-performance-polish/72-03-SUMMARY.md

All commits verified:
- 208e45c: feat(72-03): AND-ancilla MCX decomposition for QQ multiplication
- 1281a79: test(72-03): add MUL-05 verification tests and MCX tracking in gate_counts

---
*Phase: 72-performance-polish*
*Completed: 2026-02-16*
