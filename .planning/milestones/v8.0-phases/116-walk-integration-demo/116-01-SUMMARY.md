---
phase: 116-walk-integration-demo
plan: 01
subsystem: quantum-walk
tags: [quantum-predicates, chess-walk, offset-oracle, build-move-table, ql-compile]

# Dependency graph
requires:
  - phase: 113-walk-diffusion
    provides: build_move_table, counting_diffusion_core
  - phase: 114-chess-predicates
    provides: make_piece_exists_predicate, make_no_friendly_capture_predicate
  - phase: 115-check-detection
    provides: make_check_detection_predicate, make_combined_predicate
provides:
  - Rewritten chess_walk.py with quantum predicate integration
  - Offset-based oracle factory _make_apply_move_from_table
  - Simplified walk_step with explicit-arg @ql.compile
  - Cleaned chess_encoding.py without get_legal_moves_and_oracle
affects: [116-02-demo, test-chess-walk]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Offset-based oracle: per-branch source enumeration with classical off-board skip"
    - "Side-aware predicate arg packing via entry_qarray_keys dicts"
    - "Explicit-arg @ql.compile replacing closure/mutable-dict pattern"

key-files:
  created: []
  modified:
    - src/chess_walk.py
    - src/chess_encoding.py

key-decisions:
  - "One combined predicate per move table entry, not per level"
  - "BOARD_KEYS dict for piece_id to board_arrs index resolution"
  - "Oracle enumerates all 64 source squares per branch value, off-board filtered classically"
  - "walk_step uses inline @ql_compile with key based on total qubit count"

patterns-established:
  - "entry_qarray_keys pattern: per-entry dict with piece/friendly/king/enemy keys for argument resolution"

requirements-completed: [WALK-02, WALK-04]

# Metrics
duration: 4min
completed: 2026-03-09
---

# Phase 116 Plan 01: Walk Integration Summary

**Quantum predicate integration into chess walk with offset-based oracle and simplified walk_step**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-09T13:24:07Z
- **Completed:** 2026-03-09T13:28:21Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Rewrote prepare_walk_data to use build_move_table + make_combined_predicate instead of get_legal_moves_and_oracle
- Built new offset-based oracle factory (_make_apply_move_from_table) that enumerates source squares per branch value
- Replaced trivial always-valid predicate with real combined legality predicates (piece-exists AND no-friendly-capture AND check-safe)
- Simplified walk_step: removed closure/mutable-dict pattern, uses explicit-arg @ql.compile
- Removed obsolete get_legal_moves_and_oracle, _make_apply_move, _classify_move from chess_encoding.py

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite prepare_walk_data and build offset-based oracle** - `91f9701` (feat)
2. **Task 2: Rewrite evaluate_children/uncompute_children with quantum predicates and simplify walk_step** - `f2c70af` (feat)

## Files Created/Modified
- `src/chess_walk.py` - Rewritten walk with quantum predicates, offset-based oracle, simplified walk_step
- `src/chess_encoding.py` - Removed get_legal_moves_and_oracle, _make_apply_move, _classify_move; removed unused math import

## Decisions Made
- One combined predicate built per move table entry (not per level) since piece_type varies within white levels (king vs knight entries)
- BOARD_KEYS dict maps piece_id strings to board_arrs tuple indices for qarray resolution
- Oracle iterates all 64 source squares per branch value with classical off-board filtering (no gates for invalid destinations)
- walk_step creates compiled function inline per call rather than caching in module-level global

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- chess_walk.py fully integrated with quantum predicates and offset-based oracle
- Ready for demo.py rewrite and test updates (116-02)
- test_chess.py tests that import get_legal_moves_and_oracle will need updates (those are old Phase 104 tests)

---
*Phase: 116-walk-integration-demo*
*Completed: 2026-03-09*
