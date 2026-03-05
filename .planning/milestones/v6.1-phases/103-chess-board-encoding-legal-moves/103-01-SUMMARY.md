---
phase: 103-chess-board-encoding-legal-moves
plan: 01
subsystem: chess-encoding
tags: [chess, move-generation, qarray, qbool, board-encoding, legal-moves]

# Dependency graph
requires:
  - phase: v6.0 (Phases 97-102)
    provides: quantum_language framework with qarray, qbool, @ql.compile
provides:
  - chess_encoding module with board encoding and classical move generation
  - knight_attacks and king_attacks with boundary-aware attack patterns
  - legal_moves_white and legal_moves_black with filtering
  - deterministic sorted move enumeration for branch register compatibility
affects: [103-02 compiled oracle, 104 walk registers, 106 demo scripts]

# Tech tracking
tech-stack:
  added: []
  patterns: [sq = rank * 8 + file indexing, separate qarrays per piece type, sorted move enumeration]

key-files:
  created:
    - src/chess_encoding.py
    - tests/python/test_chess.py
  modified: []

key-decisions:
  - "Square index convention: sq = rank * 8 + file, consistent with qarray[rank, file]"
  - "Black king exclusion zone includes bk_sq itself plus all king_attacks(bk_sq) for white king filtering"
  - "White attack set includes wk_sq itself (occupied square) plus king_attacks + knight_attacks for black king filtering"

patterns-established:
  - "Classical move generation: pure Python functions returning sorted lists of square indices"
  - "Legal move filtering: compute attack/occupancy sets, then filter destinations"
  - "Move enumeration: sorted (piece_sq, dest_sq) tuples with list index = branch register value"

requirements-completed: [CHESS-01, CHESS-02, CHESS-03, CHESS-04]

# Metrics
duration: 5min
completed: 2026-03-03
---

# Phase 103 Plan 01: Classical Chess Module Summary

**Standalone chess encoding module with board-to-qarray encoding, boundary-aware knight/king attack generation, and filtered legal move enumeration for both sides**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T18:59:27Z
- **Completed:** 2026-03-03T19:04:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Built complete chess encoding module at `src/chess_encoding.py` (244 lines) with 6 public functions
- Knight attacks correctly handle all board positions: corners (2 moves), edges (3-4), center (8)
- King attacks correctly handle all board positions: corners (3 moves), edges (5), center (8)
- Legal move filtering excludes friendly-occupied squares and opponent-attacked squares for both sides
- Deterministic sorted move enumeration ready for Phase 104 branch registers
- 43 tests pass (39 classical + 4 quantum spot-checks)

## Task Commits

Each task was committed atomically:

1. **Task 1: Chess encoding module (TDD RED)** - `934dabe` (test)
2. **Task 1: Chess encoding module (TDD GREEN)** - `f255d1b` (feat)
3. **Task 2: Quantum spot-check + __all__ exports** - `948ee8e` (feat)

**Plan metadata:** [pending] (docs: complete plan)

_Note: Task 1 used TDD with separate RED and GREEN commits_

## Files Created/Modified
- `src/chess_encoding.py` - Chess board encoding, move generation, filtering, and enumeration (244 lines)
- `tests/python/test_chess.py` - 43 tests across 8 test classes covering CHESS-01 through CHESS-04

## Decisions Made
- Used `sq = rank * 8 + file` indexing consistently (avoiding demo.py's chess-notation with display-inverted ranks)
- Black king exclusion zone for white king moves includes `{bk_sq} | set(king_attacks(bk_sq))` -- the king square itself plus all attacked squares
- White attack set for black king filtering includes `{wk_sq} | set(king_attacks(wk_sq))` plus all knight attack sets -- wk_sq is both occupied and generates attacks
- Kept module as single file (`chess_encoding.py`) rather than package since it's under 250 lines

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `chess_encoding.py` provides all building blocks for Plan 103-02 (compiled move oracle with @ql.compile)
- Move lists are deterministically sorted, ready for branch register mapping in Phase 104
- Module is standalone and importable from any script

## Self-Check: PASSED

- [x] src/chess_encoding.py exists (245 lines, exceeds 150 min)
- [x] tests/python/test_chess.py exists (493 lines, exceeds 100 min)
- [x] Commit 934dabe (TDD RED) found
- [x] Commit f255d1b (TDD GREEN) found
- [x] Commit 948ee8e (Task 2) found
- [x] 43/43 tests pass
- [x] Module contains encode_position, knight_attacks, king_attacks, legal_moves_white, legal_moves_black, legal_moves
- [x] __all__ export list present

---
*Phase: 103-chess-board-encoding-legal-moves*
*Completed: 2026-03-03*
