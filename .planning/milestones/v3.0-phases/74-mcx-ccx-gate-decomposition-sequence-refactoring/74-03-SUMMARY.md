---
phase: 74-mcx-ccx-gate-decomposition-sequence-refactoring
plan: 03
subsystem: arithmetic
tags: [toffoli, mcx, ccx, and-ancilla, decomposition, cdkm, cla, multiplication, comparison]

# Dependency graph
requires:
  - phase: 74-01
    provides: Split ToffoliAddition.c into CDKM/CLA/Helpers modules
  - phase: 74-02
    provides: T_GATE/TDG_GATE enum, gate primitives, toffoli_decompose field
provides:
  - MCX-free controlled CDKM adder (cQQ_add, cCQ_add) via AND-ancilla CCX decomposition
  - MCX-free controlled BK CLA adder via sequence-based MCX decomposition
  - MCX-free controlled multiplication (cmul_qq width-1 case)
  - MCX-free equality comparison (CQ_equal_width, cCQ_equal_width) via recursive AND-ancilla
  - Python-side AND-ancilla allocation for comparison sequences
  - MCX gate purity test suite (23 tests)
affects: [74-04, 74-05, toffoli-arithmetic, fault-tolerant]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AND-ancilla MCX decomposition: MCX(target, [c1,c2,c3]) -> CCX(anc,c1,c2) + CCX(target,anc,c3) + CCX(anc,c1,c2)"
    - "Recursive MCX decomposition for k>3 controls: peel 2 controls into ancilla, recurse with k-1"
    - "Python-side ancilla allocation for C sequence qubit arrays"

key-files:
  created:
    - tests/python/test_mcx_decomposition.py
  modified:
    - c_backend/src/ToffoliAdditionCDKM.c
    - c_backend/src/ToffoliAdditionCLA.c
    - c_backend/src/hot_path_add_toffoli.c
    - c_backend/src/ToffoliMultiplication.c
    - c_backend/src/IntegerComparison.c
    - c_backend/include/toffoli_arithmetic_ops.h
    - src/quantum_language/qint_comparison.pxi

key-decisions:
  - "AND-ancilla reused per iteration (CCX self-inverse uncomputes after each use)"
  - "Hardcoded cQQ/cCQ sequences bypassed in favor of MCX-free dynamic generator"
  - "Python comparison code allocates AND-ancilla via circuit allocator for sequence qubit arrays"
  - "Recursive MCX decomposition for comparison (sequence-based) vs inline emission for adders (circuit-based)"

patterns-established:
  - "AND-ancilla pattern: MCX(n) -> n-2 ancilla qubits, 2*(n-2)+1 CCX gates"
  - "Sequence-based MCX decomposition: emit_mcx_decomp_seq for sequence builders"
  - "Circuit-based MCX decomposition: emit_cMAJ_decomposed/emit_cUMA_decomposed for inline emission"

requirements-completed: [MCX-DECOMP-01, MCX-DECOMP-02, MCX-PURITY-01]

# Metrics
duration: 45min
completed: 2026-02-17
---

# Phase 74 Plan 03: MCX Decomposition Summary

**AND-ancilla MCX decomposition eliminates all 3+ control gates from controlled CDKM/CLA adders, controlled multiplication, and equality comparisons -- 23 purity tests confirm zero MCX in output**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-02-17
- **Completed:** 2026-02-17
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Decomposed all 9 MCX emission points across CDKM, CLA, multiplication, and comparison
- Fixed Python-side AND-ancilla allocation for equality comparison sequences (3+ bit widths)
- Created comprehensive MCX gate purity test suite covering all Toffoli-mode operations

## Task Commits

Each task was committed atomically:

1. **Task 1: Decompose MCX in CDKM/CLA controlled adders** - `d3306d1` (feat)
2. **Task 2: Decompose MCX in Multiplication and Comparison** - `48071d6` (feat)
3. **Task 3: MCX gate purity test suite** - `1426445` (test)

## Files Created/Modified

- `c_backend/src/ToffoliAdditionCDKM.c` - emit_cMAJ/emit_cUMA/emit_cCQ_MAJ get and_anc param; MCX(3) -> 3 CCX; layer counts updated (3->5 per cMAJ/cUMA)
- `c_backend/src/ToffoliAdditionCLA.c` - emit_mcx3_seq/emit_mcx_recursive_seq helpers; controlled BK CLA MCX decomposition
- `c_backend/src/hot_path_add_toffoli.c` - Allocate extra AND-ancilla for all controlled paths (RCA and CLA, QQ and CQ)
- `c_backend/src/ToffoliMultiplication.c` - cmul_qq width-1 MCX(3) -> 3 CCX; inner AND-ancilla for cmul_qq/cmul_cq general case
- `c_backend/src/IntegerComparison.c` - Recursive AND-ancilla MCX decomposition for CQ_equal_width (bits>=3) and cCQ_equal_width (bits>=2)
- `c_backend/include/toffoli_arithmetic_ops.h` - Updated docstrings for new qubit layouts
- `src/quantum_language/qint_comparison.pxi` - Python-side AND-ancilla allocation/free for comparison sequences
- `tests/python/test_mcx_decomposition.py` - 23 MCX purity tests across all operation categories

## Decisions Made

- **AND-ancilla reuse:** Single AND-ancilla qubit reused per CDKM iteration (CCX self-inverse uncomputes it). Saves ancilla budget.
- **Hardcoded sequence bypass:** cQQ/cCQ hardcoded sequences still contain MCX gates; bypassed with comments explaining the dynamic generator is now MCX-free.
- **Python allocator integration:** Comparison sequences need AND-ancilla qubits mapped into the qubit_array. Python `__eq__` allocates via `allocator_alloc` and frees after `run_instruction`.
- **Two decomposition styles:** Adders use inline circuit emission (`add_gate`); comparisons use sequence-based emission (`emit_mcx_decomp_seq`). Both are MCX-free.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Python-side AND-ancilla allocation for equality comparison**
- **Found during:** Task 2 (IntegerComparison.c MCX decomposition)
- **Issue:** C code referenced AND-ancilla qubit indices [bits+1..] in the sequence, but Python's `__eq__` method only provided [0..bits] qubits in the qubit_array. Uninitialized qubit_array entries caused segfault/OOM for width >= 3.
- **Fix:** Updated `qint_comparison.pxi` to allocate AND-ancilla qubits via `allocator_alloc()` and map them into qubit_array at the correct offsets. Free after `run_instruction`.
- **Files modified:** `src/quantum_language/qint_comparison.pxi`
- **Verification:** Width 1-8 equality tests pass. 23 MCX purity tests confirm zero MCX gates.
- **Committed in:** `48071d6` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for correctness. The plan specified C-level decomposition but did not account for the Python-C qubit mapping contract requiring ancilla allocation on the Python side.

## Issues Encountered

- **Pre-commit clang-format:** Reformatted C files on first commit attempt. Re-staged and committed successfully.
- **Large-width equality tests slow:** Width 16+ equality tests (qint-qint path) timeout due to simulation cost. Not a regression -- pre-existing behavior. CQ-specific tests (our changes) complete in < 1 second.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All Toffoli-mode operations now MCX-free (only X/CX/CCX in output)
- Ready for Phase 74-04 (CCX -> Clifford+T decomposition) which depends on MCX elimination
- Ready for Phase 74-05 (hardcoded sequence regeneration) to update cached sequences

## Self-Check: PASSED

- All key files exist (7 modified + 1 created)
- All 3 task commits verified: d3306d1, 48071d6, 1426445
- 23/23 MCX purity tests pass
- 8/8 CQ equality tests pass
- 16/17 core tests pass (1 pre-existing failure unrelated)

---
*Phase: 74-mcx-ccx-gate-decomposition-sequence-refactoring*
*Completed: 2026-02-17*
