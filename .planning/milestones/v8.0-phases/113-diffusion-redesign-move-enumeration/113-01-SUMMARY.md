---
phase: 113-diffusion-redesign-move-enumeration
plan: 01
subsystem: quantum-chess
tags: [chess, move-table, quantum-walk, enumeration, tdd]

requires:
  - phase: 106-chess-demo
    provides: chess_encoding module with _KNIGHT_OFFSETS, _KING_OFFSETS
provides:
  - build_move_table() function for position-independent move enumeration
  - Move table test suite (8 tests)
affects: [113-02, 113-03, diffusion-operator, quantum-walk-circuit]

tech-stack:
  added: []
  patterns: [position-independent geometric offset enumeration]

key-files:
  created: [tests/python/test_move_table.py]
  modified: [src/chess_encoding.py]

key-decisions:
  - "No edge-of-board filtering in move table -- quantum predicate handles legality"
  - "8 entries per piece regardless of type (knights and kings both have 8 offsets)"

patterns-established:
  - "Move table pattern: (piece_id, piece_type) -> list[(piece_id, dr, df)] with 8 entries per piece"
  - "Branch register index = sequential position in table (first piece's 8, then second's 8, etc.)"

requirements-completed: [WALK-01]

duration: 4min
completed: 2026-03-08
---

# Phase 113 Plan 01: Move Table Builder Summary

**build_move_table() for position-independent geometric offset enumeration with 8 entries per piece (knight L-shapes + king adjacencies)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-08T14:54:17Z
- **Completed:** 2026-03-08T14:58:21Z
- **Tasks:** 1 (TDD: RED + GREEN + REFACTOR)
- **Files modified:** 2

## Accomplishments
- build_move_table() function added to chess_encoding.py and exported in __all__
- 8 comprehensive tests covering sizes, offsets, piece IDs, indexing, edge cases
- No regressions: all 120 existing chess tests pass
- Table produces exactly 8 * len(pieces) entries regardless of board position

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for build_move_table** - `9fcc6fd` (test)
2. **Task 1 GREEN: Implement build_move_table** - `15e4a93` (feat)

_TDD task: RED committed separately from GREEN. No REFACTOR commit needed (docstring and type hints included in GREEN)._

## Files Created/Modified
- `tests/python/test_move_table.py` - 8 tests for move table sizes, offsets, piece IDs, indexing, empty/single cases
- `src/chess_encoding.py` - Added build_move_table() function with type hints and docstring, added to __all__

## Decisions Made
- No edge-of-board filtering in the move table -- the quantum legality predicate handles that downstream
- Both knights and kings produce exactly 8 entries (matching their offset counts)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- build_move_table() ready for use by diffusion operator (Plan 02) and walk circuit construction (Plan 03)
- Branch register width = ceil(log2(table_length)) for quantum circuit sizing

---
*Phase: 113-diffusion-redesign-move-enumeration*
*Completed: 2026-03-08*
