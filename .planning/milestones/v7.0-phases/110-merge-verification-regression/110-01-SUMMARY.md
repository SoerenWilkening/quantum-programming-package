---
phase: 110-merge-verification-regression
plan: 01
subsystem: testing
tags: [statevector, qiskit, equivalence, opt-levels, parametric, merge]

requires:
  - phase: 109-selective-sequence-merging
    provides: opt=2 merge pipeline with _apply_merge and parametric+opt=2 guard
provides:
  - Statevector equivalence tests proving opt=2 add/mul/grover match opt=3
  - Parametric+opt interaction tests (opt=1 works, opt=3 works, opt=2 raises)
  - Phase-aware statevector comparison helper (_statevectors_equivalent)
affects: [110-02, merge-regression]

tech-stack:
  added: []
  patterns: [statevector-equivalence-comparison, global-phase-normalization]

key-files:
  created:
    - tests/python/test_merge_equiv.py
  modified: []

key-decisions:
  - "Used Statevector.from_instruction() for exact equivalence (no AerSimulator overhead)"
  - "Global phase normalization via first non-zero amplitude alignment"
  - "Grover oracle test uses x==5 predicate at width=4 (7 qubits, safe budget)"
  - "Skipped mul width=5 (17q = budget limit, too risky with overhead)"

patterns-established:
  - "Statevector equivalence: _get_statevector + _statevectors_equivalent pattern for comparing opt levels"

requirements-completed: [MERGE-04]

duration: 9min
completed: 2026-03-06
---

# Phase 110 Plan 01: Merge Equivalence Tests Summary

**Statevector equivalence tests proving opt=2 merged circuits produce identical results to opt=3 for add, mul, and grover oracle at widths 1-4, plus parametric+opt interaction verification**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-06T22:05:13Z
- **Completed:** 2026-03-06T22:14:50Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Exhaustive add equivalence tests at widths 1-4 (all input pairs per width) confirm opt=2 == opt=3
- Exhaustive mul equivalence tests at widths 1-4 (all input pairs per width) confirm opt=2 == opt=3
- Grover oracle equivalence test (x==5, width=4) confirms opt=2 == opt=3
- Parametric+opt interaction: opt=1 works, opt=3 works, opt=2 raises ValueError
- Global phase-aware comparison helper handles physically equivalent circuits that differ by e^(i*theta)

## Task Commits

Each task was committed atomically:

1. **Task 1: Statevector equivalence tests for add, mul, grover oracle** - `0af19d4` (test)
2. **Task 2: Parametric + opt interaction tests** - `49754f7` (test)

## Files Created/Modified
- `tests/python/test_merge_equiv.py` - 265 lines: statevector equivalence tests and parametric interaction tests

## Decisions Made
- Used `Statevector.from_instruction()` instead of AerSimulator for statevector extraction (cleaner, no simulator overhead)
- Global phase normalization via first non-zero amplitude alignment with atol=1e-10
- Grover oracle uses x==5 predicate at width=4 (7 qubits, well within 17-qubit budget)
- Skipped mul width=5 (17 qubits = maximum, too risky with potential overhead)
- Parametric tests verify output correctness via probability distribution (dominant state check)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Equivalence tests complete and passing (15 tests total)
- Ready for 110-02 (opt-level regression across test_compile.py and test_merge.py)
- Pre-existing 14-15 test_compile.py failures remain xfail at all opt levels

## Self-Check: PASSED

- FOUND: tests/python/test_merge_equiv.py (265 lines, min 120 required)
- FOUND: commit 0af19d4 (Task 1: statevector equivalence tests)
- FOUND: commit 49754f7 (Task 2: parametric+opt interaction tests)

---
*Phase: 110-merge-verification-regression*
*Completed: 2026-03-06*
