---
phase: 103-chess-board-encoding-legal-moves
verified: 2026-03-03T20:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
gaps: []
human_verification: []
---

# Phase 103: Chess Board Encoding & Legal Moves Verification Report

**Phase Goal:** Users can encode a chess endgame position and generate legal moves for any piece using quantum primitives
**Verified:** 2026-03-03T20:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A chess position with 2 kings and white knights is encoded as separate qarrays with correct square-to-qubit mapping | VERIFIED | `encode_position()` at line 65 creates 3 numpy arrays (8x8, int), sets bits at `sq // 8, sq % 8`, wraps each as `ql.qarray(arr, dtype=ql.qbool)`. Returns dict with keys `white_king`, `black_king`, `white_knights`. 4 tests in `TestBoardEncoding` + 3 quantum spot-checks all pass. |
| 2 | Knight attack patterns are generated correctly from any square, respecting board boundaries (corner=2, edge=3-4, center=8) | VERIFIED | `knight_attacks()` at line 103 uses 8 L-shaped offsets with `0 <= nr < 8 and 0 <= nf < 8` boundary check. `knight_attacks(0)` returns `[10, 17]` (2 squares). `knight_attacks(27)` returns 8 squares. 8 tests in `TestKnightMoves` all pass. |
| 3 | King moves are generated for all 8 directions with edge-awareness (corner=3, edge=5, center=8) | VERIFIED | `king_attacks()` at line 125 uses 8 adjacent offsets with identical boundary check. All 4 corners verified: a1→3, h1→3, h8→3, a8→3. Center d4→8, edge a4→5. 9 tests in `TestKingMoves` all pass. |
| 4 | Legal move filtering excludes destinations occupied by friendly pieces and squares attacked by opponent king | VERIFIED | `legal_moves_white()` at line 147 computes `friendly_squares = set(wn_squares) | {wk_sq}` and `bk_attack_set = set(king_attacks(bk_sq)) | {bk_sq}`. Filters both sets. `legal_moves_black()` at line 191 builds `white_attack_set` from all white pieces. 10 tests across `TestLegalMoveFiltering` and `TestLegalMovesBlack` all pass. |
| 5 | Legal moves are returned as a deterministic sorted list of (piece_square, destination_square) pairs | VERIFIED | Both `legal_moves_white` and `legal_moves_black` call `.sort()` before return. `legal_moves()` wrapper delegates by side_to_move. Index-in-list equals branch register value. 5 tests in `TestEnumeration` confirm determinism and sort order. |
| 6 | The move oracle is a @ql.compile function that produces a legal move set for a given position | VERIFIED | `get_legal_moves_and_oracle()` at line 435 calls `_make_apply_move()` which applies `@ql.compile(inverse=True)` at line 402. Oracle is typed as `CompiledFunc`. Confirmed via smoke test output: `<CompiledFunc apply_move>`. |
| 7 | The oracle accepts position parameters and returns quantum-encoded move data compatible with Phase 104 branch registers | VERIFIED | Returns dict with `moves`, `move_count`, `branch_width`, and `apply_move`. `branch_width = max(1, math.ceil(math.log2(max(move_count, 1))))`. `apply_move` takes `(wk_arr, bk_arr, wn_arr, branch)` where `branch` is a `ql.qint`. 8 tests in `TestMoveOracle` all pass. |
| 8 | The oracle supports inverse=True for uncomputation in quantum walk operators | VERIFIED | `@ql.compile(inverse=True)` at line 402. `apply_move.inverse` confirmed as a live property (not None). `test_oracle_inverse_exists` and `test_tiny_board_inverse_works` both pass; oracle's `.inverse(wk_arr, bk_arr, wn_arr, branch)` is callable. |
| 9 | A subcircuit spot-check verifies the oracle generates correct quantum gates for a tiny position | VERIFIED | `TestMoveOracleSubcircuit` has 3 tests: `test_tiny_board_spot_check` (a1 king, no knights → 3 moves), `test_tiny_board_inverse_works`, `test_single_knight_circuit` (knight a1 + king e1 → 7 moves). All pass without Qiskit simulation. |

**Score:** 9/9 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/chess_encoding.py` | Board encoding, move generation, filtering, enumeration — min 150 lines, contains `def encode_position` | VERIFIED | 476 lines. Contains `encode_position`, `knight_attacks`, `king_attacks`, `legal_moves_white`, `legal_moves_black`, `legal_moves`, `get_legal_moves_and_oracle`, `print_position`, `print_moves`, `sq_to_algebraic`. All in `__all__`. |
| `tests/python/test_chess.py` | Classical unit tests for CHESS-01 through CHESS-04 — min 100 lines, contains `class TestKnightMoves` | VERIFIED | 853 lines. Contains 13 test classes: `TestBoardEncoding`, `TestKnightMoves`, `TestKingMoves`, `TestLegalMoveFiltering`, `TestLegalMovesBlack`, `TestEnumeration`, `TestEdgeCases`, `TestBoardEncodingQuantum`, `TestMoveOracle`, `TestMoveOracleSubcircuit`, `TestEndToEnd`, `TestUtilities`. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/chess_encoding.py` | `quantum_language` | `import quantum_language as ql; ql.qarray, ql.qbool` | WIRED | Line 25: `import quantum_language as ql`. Lines 97-99: `ql.qarray(wk, dtype=ql.qbool)` (3 calls in `encode_position`). Line 402: `@ql.compile(inverse=True)`. Used in substantive operations, not just import. |
| `tests/python/test_chess.py` | `src/chess_encoding.py` | `from chess_encoding import` | WIRED | 80+ import statements in tests importing every public function: `encode_position`, `knight_attacks`, `king_attacks`, `legal_moves_white`, `legal_moves_black`, `legal_moves`, `get_legal_moves_and_oracle`, `print_position`, `print_moves`, `sq_to_algebraic`. |
| `src/chess_encoding.py::move_oracle` | `src/chess_encoding.py::legal_moves_white` | Oracle calls `legal_moves` to get move list | WIRED | Line 465: `moves = legal_moves(wk_sq, bk_sq, wn_squares, side_to_move)` inside `get_legal_moves_and_oracle()`. `legal_moves()` delegates to `legal_moves_white` or `legal_moves_black`. |
| `src/chess_encoding.py::move_oracle` | `quantum_language::compile` | `@ql.compile(inverse=True)` decorator | WIRED | Line 402: `@ql.compile(inverse=True)` decorator on `apply_move` function inside `_make_apply_move()` factory. Smoke test confirms result is `<CompiledFunc apply_move>` with `.inverse` property. |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CHESS-01 | 103-01 | 8x8 board with piece positions encoded as qarray (2 kings + white knights) | SATISFIED | `encode_position()` creates 3 separate `ql.qarray(arr, dtype=ql.qbool)` objects, one per piece type. `TestBoardEncoding` (4 tests) and `TestBoardEncodingQuantum` (4 tests) pass. |
| CHESS-02 | 103-01 | Knight attack pattern generation from any occupied square | SATISFIED | `knight_attacks(square)` with boundary checks. `TestKnightMoves` (8 tests) pass: corners=2, edges=3-4, center=8. |
| CHESS-03 | 103-01 | King move generation (8 adjacent squares, edge-aware) | SATISFIED | `king_attacks(square)` with boundary checks. `TestKingMoves` (9 tests) pass: corners=3, edges=5, center=8. |
| CHESS-04 | 103-01 | Legal move filtering — destination not attacked by opponent, not occupied by friendly piece | SATISFIED | `legal_moves_white()` and `legal_moves_black()` both filter. `TestLegalMoveFiltering` (6 tests), `TestLegalMovesBlack` (4 tests), `TestEdgeCases` (3 tests) pass. |
| CHESS-05 | 103-02 | Move oracle as `@ql.compile` function producing legal move set for current position | SATISFIED | `get_legal_moves_and_oracle()` returns compiled oracle with `apply_move` as `@ql.compile(inverse=True)`. `TestMoveOracle` (8 tests), `TestMoveOracleSubcircuit` (3 tests), `TestEndToEnd` (2 tests) pass. |

**All 5 requirements (CHESS-01 through CHESS-05) are satisfied.**

No orphaned requirements: REQUIREMENTS.md maps exactly CHESS-01 to CHESS-05 to Phase 103, all accounted for by Plans 103-01 and 103-02.

---

## Anti-Patterns Found

None detected.

- No TODO, FIXME, XXX, HACK, or PLACEHOLDER comments in either file.
- No empty implementations (`return null`, `return {}`, `return []`, stub lambdas).
- No console.log-only handlers.
- No static returns masking missing database/quantum queries.
- `_make_apply_move()` inner `apply_move` function performs real quantum operations (`~boards[board_idx][src_rank, src_file]`) inside `with cond:` blocks, not placeholder prints.

---

## Human Verification Required

None. All phase-103 behaviors are verifiable programmatically:

- Move counts are deterministic integers, confirmed by assertions.
- Board encoding is structural (dict with qarray values), not visual.
- Oracle construction is confirmed by type check (`CompiledFunc`) and `.inverse` property check.
- No UI, real-time behavior, or external services involved.

---

## Commit Verification

All commits documented in SUMMARYs are present in git history:

| Commit | Plan | Description |
|--------|------|-------------|
| `934dabe` | 103-01 | test(103-01): TDD RED — failing chess tests |
| `f255d1b` | 103-01 | feat(103-01): TDD GREEN — chess encoding implementation |
| `948ee8e` | 103-01 | feat(103-01): quantum spot-check tests + `__all__` |
| `fbc885d` | 103-02 | test(103-02): TDD RED — failing oracle tests |
| `f19f945` | 103-02 | feat(103-02): TDD GREEN — compiled move oracle |
| `33bd423` | 103-02 | feat(103-02): end-to-end tests, print utilities, `__all__` polish |

---

## Test Results

```
61 passed in 0.48s
```

All 61 tests green across 13 test classes:

- `TestBoardEncoding` — 4 tests (CHESS-01)
- `TestKnightMoves` — 8 tests (CHESS-02)
- `TestKingMoves` — 9 tests (CHESS-03)
- `TestLegalMoveFiltering` — 6 tests (CHESS-04)
- `TestLegalMovesBlack` — 4 tests (CHESS-04)
- `TestEnumeration` — 5 tests (CHESS-04)
- `TestEdgeCases` — 3 tests (CHESS-04)
- `TestBoardEncodingQuantum` — 4 tests (CHESS-01 quantum wiring)
- `TestMoveOracle` — 8 tests (CHESS-05)
- `TestMoveOracleSubcircuit` — 3 tests (CHESS-05)
- `TestEndToEnd` — 2 tests (full pipeline)
- `TestUtilities` — 5 tests (print_position, print_moves, sq_to_algebraic)

---

## Summary

Phase 103 goal is fully achieved. The codebase delivers:

1. `src/chess_encoding.py` (476 lines, 10 public functions) — a complete, standalone chess domain layer with board encoding, attack pattern generation, legal move filtering for both sides, deterministic sorted enumeration, a compiled move oracle with inverse support, and debug utilities.

2. `tests/python/test_chess.py` (853 lines, 61 tests) — comprehensive coverage of every behavior specified in Plans 103-01 and 103-02, with TDD red/green commits verifiable in git history.

3. All 5 requirements (CHESS-01 through CHESS-05) are satisfied with no orphaned requirements.

4. The `@ql.compile(inverse=True)` oracle is wired to the classical move generation, returns a `CompiledFunc` with a live `.inverse` property, and is ready for Phase 104 consumption via `get_legal_moves_and_oracle(wk_sq, bk_sq, wn_squares, side_to_move)`.

---

_Verified: 2026-03-03T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
