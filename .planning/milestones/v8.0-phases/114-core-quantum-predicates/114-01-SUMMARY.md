---
phase: 114-core-quantum-predicates
plan: 01
subsystem: quantum-predicates
tags: [ql-compile, qarray, qbool, chess, predicate, factory-pattern, statevector]

# Dependency graph
requires:
  - phase: 113-diffusion-redesign
    provides: move table with (piece_id, dr, df) triples and factory pattern template
provides:
  - make_piece_exists_predicate factory function in src/chess_predicates.py
  - Statevector-verified piece-exists predicate for 2x2 and 8x8 boards
affects: [114-02-no-friendly-capture, 115-check-detection, 116-walk-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [quantum-predicate-factory, classical-precomputation-with-ql-compile, flat-with-blocks]

key-files:
  created: [src/chess_predicates.py, tests/python/test_chess_predicates.py]
  modified: []

key-decisions:
  - "Used .adjoint() instead of .inverse() for predicate reversal -- .inverse() requires ancilla allocation which piece-exists does not have"
  - "XOR=OR equivalence documented for single-piece-per-square basis states"

patterns-established:
  - "Predicate factory: classical valid_sources precomputation outside @ql.compile, flat with/~ blocks inside"
  - "Statevector test helper: ql.to_openqasm() -> qiskit.qasm3.loads() -> AerSimulator for 2x2 board verification"
  - "make_small_board helper for creating arbitrary-size test boards without encode_position"

requirements-completed: [PRED-01, PRED-05]

# Metrics
duration: 15min
completed: 2026-03-08
---

# Phase 114 Plan 01: Piece-Exists Predicate Summary

**Piece-exists quantum predicate factory using @ql.compile(inverse=True) with flat with/~ pattern, statevector-verified on 2x2 boards**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-08T20:25:20Z
- **Completed:** 2026-03-08T20:39:52Z
- **Tasks:** 1 (TDD: red + green)
- **Files modified:** 2

## Accomplishments
- make_piece_exists_predicate factory correctly identifies piece presence via statevector verification
- Off-board moves produce zero quantum gates (classical skip at construction time)
- .adjoint() roundtrip returns result qbool to |0> confirming reversibility
- 8x8 circuit builds without error (no simulation needed)
- 127 chess-related tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for piece-exists predicate** - `c481177` (test)
2. **Task 1 (GREEN): Implement piece-exists predicate factory** - `f938e53` (feat)

_TDD task with red/green commits._

## Files Created/Modified
- `src/chess_predicates.py` - Piece-exists predicate factory with @ql.compile(inverse=True)
- `tests/python/test_chess_predicates.py` - 7 tests: 4 statevector, 2 compile/adjoint, 1 scaling

## Decisions Made
- Used `.adjoint()` instead of `.inverse()` for predicate reversal. The `.inverse()` API uncomputes ancillas from a prior forward call, but piece-exists allocates no ancillas (no new qbool/qint inside the compiled body). The `.adjoint()` API runs the gate sequence in reverse, which is the correct operation for this case.
- Used `qiskit.qasm3.loads()` (not `QuantumCircuit.from_qasm_str()`) since `ql.to_openqasm()` emits OpenQASM 3.0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed QASM export API mismatch**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Plan specified `ql.qasm()` which doesn't exist; project uses `ql.to_openqasm()` returning QASM 3.0
- **Fix:** Changed to `ql.to_openqasm()` + `qiskit.qasm3.loads()` matching existing test patterns
- **Files modified:** tests/python/test_chess_predicates.py
- **Verification:** All 7 tests pass
- **Committed in:** f938e53

**2. [Rule 1 - Bug] Replaced .inverse() with .adjoint() for ancilla-free predicate**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `.inverse()` requires prior forward call record which only exists when ancillas are allocated; piece-exists has none
- **Fix:** Changed TestCompileInverse to use `.adjoint()` which runs adjoint gates without ancilla tracking
- **Files modified:** tests/python/test_chess_predicates.py
- **Verification:** Adjoint roundtrip returns result to |0> with P(0) = 1.0
- **Committed in:** f938e53

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correct API usage. No scope creep.

## Issues Encountered
- Full test suite (1649 tests) exceeds container memory/time budget. Verified zero regressions via chess-specific subset (127 tests). Pre-existing failure in test_api_coverage.py is unrelated.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- chess_predicates.py module established with factory pattern ready for Plan 02 (no-friendly-capture)
- make_small_board helper and statevector test pattern reusable for Plan 02 tests
- .adjoint() discovery applies to all ancilla-free predicates

## Self-Check: PASSED

All artifacts verified:
- src/chess_predicates.py (82 lines, min 40)
- tests/python/test_chess_predicates.py (191 lines, min 60)
- make_piece_exists_predicate export present
- @ql.compile(inverse=True) decorator present
- Commits c481177 (RED) and f938e53 (GREEN) verified in git log

---
*Phase: 114-core-quantum-predicates*
*Completed: 2026-03-08*
