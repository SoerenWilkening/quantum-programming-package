---
phase: 104-walk-register-scaffolding-local-diffusion
plan: 01
subsystem: chess-walk
tags: [chess, quantum-walk, registers, one-hot, branch-register, oracle-replay]

# Dependency graph
requires:
  - phase: 103-02
    provides: get_legal_moves_and_oracle() factory with compiled move oracle and .inverse support
provides:
  - create_height_register() for one-hot height register with root initialization
  - create_branch_registers() for per-level branch registers from move data
  - height_qubit() accessor for physical qubit index from depth
  - derive_board_state()/underive_board_state() for forward/reverse oracle replay
  - prepare_walk_data() for alternating side-to-move oracle precomputation
affects: [104-02 local diffusion, 105 walk operators, 106 demo scripts]

# Tech tracking
tech-stack:
  added: []
  patterns: [purely functional walk module (no class), forward/reverse oracle replay for board state derivation]

key-files:
  created:
    - src/chess_walk.py
    - tests/python/test_chess_walk.py
  modified: []

key-decisions:
  - "Purely functional API: 6 standalone functions instead of class, per user decision"
  - "board_arrs as tuple (wk, bk, wn) not dict, matching oracle calling convention"
  - "prepare_walk_data uses static starting position for all levels (classical precomputation)"

patterns-established:
  - "Oracle replay: derive_board_state calls forward, underive calls .inverse in LIFO order"
  - "Height qubit addressing: int(h_reg.qubits[64 - (max_depth+1) + depth])"
  - "Side alternation: level % 2 == 0 is white, odd is black"

requirements-completed: [WALK-01, WALK-02]

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 104 Plan 01: Walk Register Scaffolding Summary

**Purely functional walk register module with one-hot height register, per-level branch registers, and forward/reverse oracle replay for board state derivation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T22:27:10Z
- **Completed:** 2026-03-03T22:30:30Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- Built `src/chess_walk.py` with 6 public functions exported via `__all__`
- One-hot height register correctly initializes root qubit at qubits[63] via emit_x
- Branch registers created with widths from move data, supporting alternating white (5-bit) / black (3-bit) patterns
- derive/underive functions verified to call oracles in correct forward/reverse order via mock-based testing
- prepare_walk_data correctly alternates side_to_move and returns oracle dicts with all required keys
- All 20 tests pass across 5 test classes within 17-qubit budget

## Task Commits

Each task was committed atomically:

1. **Task 1: Register scaffolding and board state replay (TDD RED)** - `01db322` (test)
2. **Task 1: Register scaffolding and board state replay (TDD GREEN)** - `b1e677e` (feat)

**Plan metadata:** [pending] (docs: complete plan)

_Note: Task 1 used TDD with separate RED and GREEN commits_

## Files Created/Modified
- `src/chess_walk.py` - Walk register construction (create_height_register, create_branch_registers), height_qubit accessor, derive/underive_board_state oracle replay, prepare_walk_data convenience function
- `tests/python/test_chess_walk.py` - 20 tests across TestHeightRegister (4), TestBranchRegisters (3), TestHeightQubit (4), TestDeriveUnderiveBoardState (4), TestPrepareWalkData (5)

## Decisions Made
- **Tuple over dict for board_arrs**: Using `(wk, bk, wn)` tuple matches the oracle calling convention directly, avoiding dict unpacking overhead
- **Static position for prepare_walk_data**: All levels use the same starting position for classical precomputation since board state changes are quantum (in superposition at runtime)
- **Mock-based derive/underive testing**: Since board qarrays are 192+ qubits (exceeding 17-qubit budget), oracle call order is verified with MagicMock at circuit-generation level

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] circuit_stats API key mismatch**
- **Found during:** Task 1 (TDD GREEN)
- **Issue:** Test used `circuit_stats()["total_gates"]` but actual API returns `peak_allocated`, not `total_gates`
- **Fix:** Changed test to verify `peak_allocated >= 4` (height register allocates max_depth+1 qubits)
- **Files modified:** tests/python/test_chess_walk.py
- **Verification:** Test passes, confirms register allocation
- **Committed in:** b1e677e

**2. [Rule 1 - Bug] quantum_language.state import broken**
- **Found during:** Task 1 (TDD GREEN)
- **Issue:** `from quantum_language.state import circuit_stats` raises ModuleNotFoundError
- **Fix:** Changed to `import quantum_language as ql; ql.circuit_stats()` using public API
- **Files modified:** tests/python/test_chess_walk.py
- **Verification:** Import succeeds, test passes
- **Committed in:** b1e677e

---

**Total deviations:** 2 auto-fixed (2 bugs in test code)
**Impact on plan:** Both auto-fixes corrected test API usage. No impact on implementation or scope.

## Issues Encountered
None beyond the auto-fixed test API deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `chess_walk.py` provides complete register infrastructure for Phase 104 Plan 02 (local diffusion)
- Plan 02 can import: create_height_register, create_branch_registers, height_qubit, derive_board_state, underive_board_state
- Oracle replay pattern established: derive calls forward oracles, underive calls .inverse in LIFO order
- prepare_walk_data provides precomputed oracle dicts with branch_width for register construction

## Self-Check: PASSED

- [x] src/chess_walk.py exists with 6 public functions in __all__
- [x] tests/python/test_chess_walk.py exists with 20 tests
- [x] Commit 01db322 (TDD RED) found
- [x] Commit b1e677e (TDD GREEN) found
- [x] 20/20 tests pass
- [x] All exports importable: create_height_register, create_branch_registers, derive_board_state, underive_board_state, height_qubit, prepare_walk_data

---
*Phase: 104-walk-register-scaffolding-local-diffusion*
*Completed: 2026-03-03*
