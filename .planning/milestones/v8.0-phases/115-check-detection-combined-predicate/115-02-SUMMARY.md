---
phase: 115-check-detection-combined-predicate
plan: 02
subsystem: quantum-predicates
tags: [quantum-chess, combined-predicate, three-way-and, ql-compile, nested-compiled-calls]

# Dependency graph
requires:
  - phase: 115-check-detection-combined-predicate
    plan: 01
    provides: "make_check_detection_predicate, _compute_attack_table, per-position attack_flag pattern"
  - phase: 114-core-quantum-predicates
    provides: "make_piece_exists_predicate, make_no_friendly_capture_predicate"
provides:
  - "make_combined_predicate factory in chess_predicates.py"
  - "TestCombinedPredicate test class (8 tests) and TestScalingPhase115 extension (1 test)"
affects: [116 walk integration]

# Tech tracking
tech-stack:
  added: []
  patterns: ["nested @ql.compile function calls for sub-predicate composition", "three-way AND via chained & operator on intermediate qbools", "circuit-build-only testing when qubit count exceeds simulation budget"]

key-files:
  created: []
  modified:
    - src/chess_predicates.py
    - tests/python/test_chess_predicates.py

key-decisions:
  - "Nested @ql.compile calls work for circuit construction -- sub-predicates called directly inside compiled function"
  - "Combined 2x2 predicate uses 34 qubits (exceeds 17-qubit sim limit) -- tests use circuit-build-only + separate AND composition verification with pre-set qbools"

patterns-established:
  - "Nested compiled function composition: call sub-predicate compiled functions directly inside another @ql.compile body -- avoids inlining verbose logic"
  - "Circuit-build-only testing: when qubit budget exceeded, verify circuit construction succeeds and test composition logic separately with minimal qubits"

requirements-completed: [PRED-04]

# Metrics
duration: 4min
completed: 2026-03-09
---

# Phase 115 Plan 02: Combined Move Legality Predicate Summary

**Combined predicate factory composing piece-exists, no-friendly-capture, and check-safe via nested compiled calls and three-way AND**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-09T12:46:09Z
- **Completed:** 2026-03-09T12:50:09Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- Implemented `make_combined_predicate` factory that composes all three sub-predicates into a single legality check
- Nested `@ql.compile` function calls confirmed working for circuit construction
- Three-way AND composition verified independently with pre-set qbool statevector tests
- All 34 tests pass (25 existing + 9 new), no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for combined predicate** - `d7e31d7` (test)
2. **Task 1 (GREEN): Combined predicate implementation** - `c2bc50a` (feat)

_TDD task: RED committed failing tests, GREEN committed implementation passing all tests._

## Files Created/Modified
- `src/chess_predicates.py` - Added `make_combined_predicate` factory with nested sub-predicate calls, three-way AND, and uncomputation
- `tests/python/test_chess_predicates.py` - Added TestCombinedPredicate (8 tests: 5 circuit-build-only + 3 AND composition statevector), extended TestScalingPhase115 (1 test: 8x8 combined build)

## Decisions Made
- Nested `@ql.compile` function calls work correctly for circuit construction -- sub-predicates called directly inside the compiled body without inlining. This is cleaner than the fallback approach (copying sub-predicate loop logic inline).
- Combined 2x2 predicate uses 34 qubits due to sub-predicate ancillas (flip-and-unflip patterns, `&` operator ancillas), exceeding the 17-qubit statevector simulation limit. Tests use circuit-build-only verification for the full combined predicate, plus separate AND composition tests with pre-set `qbool(True/False)` inputs to verify the three-way AND logic within budget (5 qubits).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adapted tests for qubit budget constraint**
- **Found during:** Task 1 GREEN phase
- **Issue:** Combined predicate on 2x2 board uses 34 qubits (13 data + 3 intermediate + 18 sub-predicate ancillas), far exceeding the 17-qubit simulation limit. Statevector tests fail with OOM (262144MB required).
- **Fix:** Converted all 4 statevector tests to circuit-build-only tests. Added 3 separate AND composition tests using `ql.qbool(True/False)` pre-set values to verify the three-way AND logic within budget (5 qubits total).
- **Files modified:** tests/python/test_chess_predicates.py
- **Verification:** All 9 new tests pass, all 25 existing tests pass
- **Committed in:** c2bc50a (GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test approach adapted per plan's fallback guidance. AND composition correctness verified separately. No scope creep.

## Issues Encountered
- Combined predicate ancilla count (34 qubits on 2x2) is high due to three sub-predicates each allocating their own ancillas (friendly_flag, attack_flag, & operator results). This is expected -- the sub-predicates are designed for correctness, not qubit minimization. On 8x8 boards, the circuit will be large but construction succeeds.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Combined predicate ready for Phase 116 walk integration
- Caller signature: `is_legal(piece_qarray, *friendly_qarrays, king_qarray, *enemy_qarrays, result)` with n_friendly and n_enemy captured in factory closure
- All Phase 114 + Phase 115 predicates complete: piece-exists, no-friendly-capture, check-safe, combined

---
*Phase: 115-check-detection-combined-predicate*
*Completed: 2026-03-09*
