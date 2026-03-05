---
phase: 103-chess-board-encoding-legal-moves
plan: 02
subsystem: chess-encoding
tags: [chess, move-oracle, ql-compile, inverse, controlled-not, branch-register]

# Dependency graph
requires:
  - phase: 103-01
    provides: chess_encoding module with board encoding, attack patterns, legal move generation
provides:
  - get_legal_moves_and_oracle() factory returning compiled move oracle
  - apply_move @ql.compile(inverse=True) function for conditional move application
  - print_position and print_moves debug/demo utilities
  - sq_to_algebraic notation converter
affects: [104 walk registers, 105 walk operators, 106 demo scripts]

# Tech tracking
tech-stack:
  added: []
  patterns: [factory pattern for @ql.compile closures, controlled NOT via ~qbool, qarray-per-arg for compile cache compatibility]

key-files:
  created: []
  modified:
    - src/chess_encoding.py
    - tests/python/test_chess.py

key-decisions:
  - "Factory pattern for oracle: _make_apply_move() creates @ql.compile function with move_specs baked into closure"
  - "Separate qarray args (wk_arr, bk_arr, wn_arr, branch) instead of dict for compile cache key and inverse support"
  - "Use ~qbool (controlled NOT) instead of ^= 1 (unsupported in controlled context) for square flipping"
  - "inverse is a @property returning _AncillaInverseProxy, called with same qarray args as forward"

patterns-established:
  - "Oracle factory: classical precomputation outside @ql.compile, quantum operations inside"
  - "Controlled NOT pattern: ~board[rank, file] flips qbool within with (cond): context"
  - "Branch register conditioning: cond = branch == i; with cond: for move-index selection"

requirements-completed: [CHESS-05]

# Metrics
duration: 19min
completed: 2026-03-03
---

# Phase 103 Plan 02: Compiled Move Oracle Summary

**Factory-based move oracle with @ql.compile(inverse=True) using controlled NOT gates for branch-register-conditioned move application on board qarrays**

## Performance

- **Duration:** 19 min
- **Started:** 2026-03-03T19:08:07Z
- **Completed:** 2026-03-03T19:26:57Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Built `get_legal_moves_and_oracle()` factory returning compiled oracle with move list, count, branch width, and apply_move function
- Oracle uses `~qbool` (controlled NOT) to flip source/destination squares conditioned on branch register value `== i`
- Factory pattern keeps classical precomputation outside @ql.compile body, only reversible quantum ops inside
- Added print_position, print_moves, sq_to_algebraic utilities for debugging and Phase 106 demo scripts
- End-to-end test validates full pipeline from position setup through oracle creation for both sides
- 61 tests pass across 13 test classes (43 original + 18 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Compiled move oracle and integration tests (TDD RED)** - `fbc885d` (test)
2. **Task 1: Compiled move oracle and integration tests (TDD GREEN)** - `f19f945` (feat)
3. **Task 2: End-to-end verification and module polish** - `33bd423` (feat)

**Plan metadata:** [pending] (docs: complete plan)

_Note: Task 1 used TDD with separate RED and GREEN commits_

## Files Created/Modified
- `src/chess_encoding.py` - Added get_legal_moves_and_oracle, _make_apply_move, _classify_move, print_position, print_moves, sq_to_algebraic (now 470+ lines, 10 public functions)
- `tests/python/test_chess.py` - Added TestMoveOracle (8 tests), TestMoveOracleSubcircuit (3 tests), TestEndToEnd (2 tests), TestUtilities (5 tests)

## Decisions Made
- **Factory pattern over decorator**: `_make_apply_move()` creates the @ql.compile function with move_specs in closure, since classical precomputation must happen outside the compiled body
- **Separate qarray args**: Passing (wk_arr, bk_arr, wn_arr, branch) instead of a dict enables proper compile cache key generation and inverse proxy qubit matching
- **~qbool for controlled NOT**: The framework's `^= 1` raises NotImplementedError in controlled context; `~` (bitwise invert / NOT) supports controlled context via cQ_not
- **.inverse is a property**: The CompiledFunc's `inverse` is a `@property` returning `_AncillaInverseProxy`, not a method -- called as `f.inverse(args)` not `f.inverse()(args)`
- **Board key map**: Internal mapping {"white_king": 0, "black_king": 1, "white_knights": 2} used to index into flat list of qarray args

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Controlled XOR not supported, switched to controlled NOT**
- **Found during:** Task 1 (TDD GREEN)
- **Issue:** `board[piece_type][src_rank, src_file] ^= 1` raises `NotImplementedError: Controlled classical-quantum XOR not yet supported` inside `with cond:` block
- **Fix:** Replaced `^= 1` with `~` (bitwise NOT) which supports controlled context via cQ_not
- **Files modified:** src/chess_encoding.py
- **Verification:** All oracle tests pass
- **Committed in:** f19f945

**2. [Rule 1 - Bug] Dict arg makes compile cache key unhashable**
- **Found during:** Task 1 (TDD GREEN)
- **Issue:** Passing board dict as first arg to @ql.compile function causes `TypeError: unhashable type: 'dict'` during cache key construction
- **Fix:** Redesigned apply_move to take separate qarray args (wk_arr, bk_arr, wn_arr, branch) instead of dict
- **Files modified:** src/chess_encoding.py, tests/python/test_chess.py
- **Verification:** All compile/replay and inverse tests pass
- **Committed in:** f19f945

**3. [Rule 1 - Bug] inverse() is a property, not a method**
- **Found during:** Task 1 (TDD GREEN)
- **Issue:** Test called `apply_move.inverse()` expecting a method return, but `inverse` is a `@property` returning `_AncillaInverseProxy` -- calling it with `()` invokes the proxy's `__call__` with no args
- **Fix:** Updated tests to use `apply_move.inverse(wk, bk, wn, branch)` (access property, then call proxy)
- **Files modified:** tests/python/test_chess.py
- **Verification:** Inverse test passes
- **Committed in:** f19f945

---

**Total deviations:** 3 auto-fixed (3 bugs)
**Impact on plan:** All auto-fixes necessary for framework compatibility. No scope creep. The deviations were framework API discoveries that informed correct usage patterns.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `chess_encoding.py` provides complete building blocks for Phase 104 (walk registers and local diffusion)
- Oracle API: `get_legal_moves_and_oracle()` returns moves, count, branch_width, and compiled apply_move
- Phase 104 can use: `apply_move(board_wk, board_bk, board_wn, branch)` to apply move[branch] conditionally
- Phase 104 can uncompute: `apply_move.inverse(board_wk, board_bk, board_wn, branch)` to reverse move application
- Move lists are deterministically sorted, branch_width provides minimum qint width for registers
- Utility functions ready for Phase 106 demo scripts

## Self-Check: PASSED

- [x] src/chess_encoding.py exists with get_legal_moves_and_oracle
- [x] tests/python/test_chess.py exists with TestMoveOracle, TestMoveOracleSubcircuit, TestEndToEnd, TestUtilities
- [x] Commit fbc885d (TDD RED) found
- [x] Commit f19f945 (TDD GREEN) found
- [x] Commit 33bd423 (Task 2) found
- [x] 61/61 tests pass
- [x] Module __all__ has 10 public functions
- [x] Oracle supports inverse via .inverse property
- [x] print_position and print_moves work correctly

---
*Phase: 103-chess-board-encoding-legal-moves*
*Completed: 2026-03-03*
