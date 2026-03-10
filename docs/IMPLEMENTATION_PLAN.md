# Implementation Plan

Modular, test-driven implementation plan for the Quantum Assembly verification
framework and quantum game engine. Every module targets **≤ 400 LOC** (excluding
tests). Each step lists the files it creates/modifies, what it tests, and its
dependencies.

---

## Notation

| Symbol | Meaning |
|--------|---------|
| **[NEW]** | New file |
| **[MOD]** | Modify existing file |
| **~LOC** | Approximate lines of code (implementation only) |
| **DEP** | Depends on step(s) |

---

## Phase 1 — Classical Verification Foundation (PRD Milestone 1)

### Step 1.1: Classical Mode Flag & Context Manager

**Goal**: Global flag in `_core.pyx` + public API to toggle classical/quantum mode.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/_core.pyx` | [MOD] Add `_classical_mode` flag, getter/setter, context manager support | +40 |
| `src/quantum_language/classical.py` | [NEW] `classical_mode()` context manager, `is_classical()` query, `set_mode()` | ~80 |
| `src/quantum_language/__init__.py` | [MOD] Export `classical_mode`, `is_classical` | +5 |

**Tests** (`tests/python/test_classical_mode.py` [NEW], ~120 LOC):
- `test_default_is_quantum` — flag starts False
- `test_context_manager_activates` — flag True inside `with`
- `test_context_manager_restores` — flag False after `with`
- `test_nested_context_managers` — inner `with` doesn't break outer
- `test_set_mode_manual` — imperative API works
- `test_is_classical_query` — query reflects current state

**DEP**: None (first step).

---

### Step 1.2: `qint` Classical Arithmetic

**Goal**: Every `qint` operator checks the classical flag; if set, does Python `int`
math with width-correct masking. No gates, no qubits.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint.pyx` | [MOD] Add classical early-return path to every operator (`__add__`, `__sub__`, `__mul__`, `__floordiv__`, `__mod__`, `__and__`, `__or__`, `__xor__`, `__invert__`, `__lshift__`, `__rshift__`, augmented assignments) | +120 |
| `src/quantum_language/qint.pyx` | [MOD] Store `_classical_value` attribute on qint, populated in classical mode init | +20 |

**Tests** (`tests/python/test_classical_qint.py` [NEW], ~250 LOC):
- For each operator (`+`, `-`, `*`, `//`, `%`, `&`, `|`, `^`, `~`, `<<`, `>>`):
  - Correct result value
  - Width masking (e.g., 4-bit wraps at 16)
  - Mixed classical qint + classical constant
- `test_no_qubits_allocated` — circuit_stats shows 0 qubits
- `test_no_gates_emitted` — gate count is 0
- `test_augmented_assignment_classical` — `+=`, `-=`, `*=` work
- `test_width_preserved` — result has correct width

**DEP**: Step 1.1

---

### Step 1.3: `qint` Classical Comparisons

**Goal**: Comparison operators return classical `qbool` in classical mode.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint.pyx` | [MOD] Classical path for `__eq__`, `__ne__`, `__lt__`, `__gt__`, `__le__`, `__ge__` | +50 |

**Tests** (`tests/python/test_classical_comparisons.py` [NEW], ~150 LOC):
- Each comparison operator with True/False cases
- Comparison with classical int literal
- Result is a qbool with correct classical value
- No qubits allocated

**DEP**: Step 1.2

---

### Step 1.4: `qbool` Classical Conditionals

**Goal**: `with qbool:` in classical mode acts as `if value:`.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qbool.pyx` | [MOD] Classical path in `__enter__`/`__exit__`: skip control stack, use `if` semantics | +30 |

**Tests** (`tests/python/test_classical_qbool.py` [NEW], ~150 LOC):
- `test_with_true_executes_body` — body runs when qbool is True
- `test_with_false_skips_body` — body skipped when qbool is False
- `test_nested_with_blocks` — inner conditions compose correctly
- `test_and_or_classical` — `&`, `|` between qbools
- `test_conditional_mutation` — `with cond: x += 1` only applies when True
- `test_no_control_stack` — control stack is empty after classical `with`

**DEP**: Step 1.3

---

### Step 1.5: `qarray` Classical Mode

**Goal**: `qarray` operations work classically.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qarray.pyx` | [MOD] Classical paths for indexing, element-wise ops | +40 |

**Tests** (`tests/python/test_classical_qarray.py` [NEW], ~120 LOC):
- Create qarray in classical mode, verify element access
- Element-wise arithmetic (if supported)
- 2D array indexing
- No qubits allocated

**DEP**: Step 1.2

---

### Step 1.6: Superposition Sampling

**Goal**: Where the framework would create superposition (Hadamard, uniform
superposition), classical mode samples a concrete value with correct probabilities.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/sampling.py` | [NEW] `sample_hadamard()`, `sample_uniform(width)`, `sample_ry(theta)` — returns 0/1 or int | ~80 |
| `src/quantum_language/_gates.pyx` | [MOD] Hadamard emission checks classical flag, delegates to sampling | +15 |

**Tests** (`tests/python/test_classical_sampling.py` [NEW], ~100 LOC):
- `test_hadamard_returns_0_or_1` — output in {0, 1}
- `test_uniform_in_range` — output in [0, 2^width - 1]
- `test_ry_bias` — run 10K samples, check distribution matches cos²/sin²
- `test_hadamard_distribution` — run 10K samples, check ~50/50

**DEP**: Step 1.1

---

### Step 1.7: Verification Runner

**Goal**: A `verify()` function that runs an algorithm N times in classical mode
and checks a property, reporting pass/fail statistics.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/verify.py` | [NEW] `verify(algorithm, property, samples, **kwargs)` → `VerifyResult` dataclass with `passed`, `failed`, `failures`, `confidence` | ~150 |
| `src/quantum_language/__init__.py` | [MOD] Export `verify` | +2 |

**Tests** (`tests/python/test_verify.py` [NEW], ~150 LOC):
- `test_always_true_property` — 100% pass
- `test_always_false_property` — 100% fail
- `test_partial_failure_reporting` — some pass, some fail, failures captured
- `test_verify_runs_in_classical_mode` — no qubits during verification
- `test_verify_result_fields` — all fields populated
- `test_pytest_integration` — use inside a pytest test with assert

**DEP**: Steps 1.1–1.6

---

### Phase 1 Integration Test

**File**: `tests/python/test_classical_integration.py` [NEW], ~100 LOC

End-to-end: write a small algorithm using qint + comparisons + `with` blocks,
run it via `ql.verify()`, confirm correct classical behavior.

**DEP**: Step 1.7

---

## Phase 2 — Tic-Tac-Toe Predicates (PRD Milestone 2)

### Step 2.1: Board Encoding

**Goal**: Represent a tic-tac-toe board as quantum registers. 9 cells, 2 bits
per cell (00=empty, 01=X, 10=O). Works in both quantum and classical mode.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/__init__.py` | [NEW] Package init | ~5 |
| `src/games/tictactoe/board.py` | [NEW] `TicTacToeBoard` class: `encode(cells)` creates 9 qint(width=2) as qarray, `EMPTY/X/O` constants, `cell(i)` accessor, `from_classical(list)` for testing | ~120 |

**Tests** (`tests/python/test_ttt_board.py` [NEW], ~150 LOC):
- `test_encode_empty_board` — all cells are EMPTY
- `test_encode_specific_position` — X/O placed correctly
- `test_cell_accessor` — returns correct cell value
- `test_classical_mode_no_qubits` — works without circuit
- `test_from_classical` — creates board from plain list
- `test_constants` — EMPTY=0, X=1, O=2

**DEP**: Phase 1

---

### Step 2.2: Turn Detection

**Goal**: Determine whose turn it is by counting X's and O's.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/predicates.py` | [NEW] `count_pieces(board) → (x_count, o_count)`, `whose_turn(board) → qbool` (True=X's turn) | ~80 |

**Tests** (`tests/python/test_ttt_turn.py` [NEW], ~100 LOC):
- Empty board → X's turn
- After 1 move → O's turn
- After 2 moves → X's turn
- Count pieces matches expected values
- All tests run classically via `ql.classical_mode()`

**DEP**: Step 2.1

---

### Step 2.3: Win Detection

**Goal**: Detect three-in-a-row for either player.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/predicates.py` | [MOD] Add `has_won(board, player) → qbool`, `is_terminal(board) → qbool` | +120 |

8 winning lines (3 rows, 3 cols, 2 diagonals). Check each line for three
matching cells.

**Tests** (`tests/python/test_ttt_win.py` [NEW], ~200 LOC):
- X wins each of 8 lines
- O wins each of 8 lines
- No winner on partial board
- Draw detection (full board, no winner)
- Terminal = someone won OR board full
- All tests classical

**DEP**: Step 2.1

---

### Step 2.4: Move Legality

**Goal**: Predicate: "is this move legal from this position?"

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/predicates.py` | [MOD] Add `is_legal_move(board, cell_index) → qbool` — cell empty AND game not over AND correct turn | +60 |

**Tests** (`tests/python/test_ttt_legality.py` [NEW], ~150 LOC):
- Legal move on empty cell, game in progress
- Illegal: cell occupied
- Illegal: game already won
- Illegal: wrong player's turn (shouldn't happen in normal play, but test anyway)
- Exhaustive: test all 9 cells for a few known positions
- Cross-reference with independent classical engine

**DEP**: Steps 2.2, 2.3

---

### Step 2.5: Legal Move Counting

**Goal**: Count the number of legal moves (empty cells on a non-terminal board).

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/predicates.py` | [MOD] Add `count_legal_moves(board) → qint` | +40 |

**Tests** (`tests/python/test_ttt_counting.py` [NEW], ~120 LOC):
- Empty board → 9
- One move played → 8
- Terminal position → 0
- Various mid-game positions
- Cross-reference with classical computation

**DEP**: Step 2.4

---

### Step 2.6: Classical Cross-Validation

**Goal**: Verify all tic-tac-toe predicates against an independent classical
tic-tac-toe engine across many positions.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/classical_engine.py` | [NEW] Standalone classical tic-tac-toe engine (no quantum imports): `legal_moves(board)`, `has_won(board, player)`, `is_terminal(board)`, `make_move(board, cell, player)` | ~100 |

**Tests** (`tests/python/test_ttt_cross_validation.py` [NEW], ~150 LOC):
- Generate 200+ random game positions (play random games, snapshot states)
- For each position: compare `predicates.has_won` vs `classical_engine.has_won`
- For each position: compare `predicates.count_legal_moves` vs `classical_engine.legal_moves`
- For each position: compare `predicates.is_legal_move` vs `classical_engine.legal_moves`
- Use `ql.verify()` to run property-based checks

**DEP**: Steps 2.1–2.5, Step 1.7

---

## Phase 3 — Walk Operator for Tic-Tac-Toe (PRD Milestone 3)

### Step 3.1: Move Enumeration

**Goal**: Generate candidate moves as quantum register of cell indices.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/walk.py` | [NEW] `enumerate_moves(board) → qarray` of cell indices (0–8), `apply_move(board, cell_index, player) → new_board` | ~150 |

**Tests** (`tests/python/test_ttt_enumeration.py` [NEW], ~120 LOC):
- Enumerate on empty board → 9 candidates
- Enumerate after some moves → correct remaining cells
- `apply_move` produces correct new board state
- Classical mode tests

**DEP**: Phase 2

---

### Step 3.2: Legality Evaluation & Validity Flags

**Goal**: Evaluate legality predicate on each candidate move, produce a qbool
flag per candidate.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/walk.py` | [MOD] Add `evaluate_legality(board, candidates) → qarray[qbool]` — applies `is_legal_move` per candidate, returns validity flags | +80 |

**Tests** (`tests/python/test_ttt_validity.py` [NEW], ~100 LOC):
- All legal → all flags True
- Some occupied → correct flags
- Terminal board → all flags False
- Flag count matches `count_legal_moves`

**DEP**: Steps 2.4, 3.1

---

### Step 3.3: Valid Move Counting (Walk)

**Goal**: Sum validity flags into a quantum integer `k`.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/walk.py` | [MOD] Add `count_valid(flags: qarray[qbool]) → qint` | +30 |

**Tests** (`tests/python/test_ttt_walk_count.py` [NEW], ~80 LOC):
- All valid → k = len(flags)
- None valid → k = 0
- Mixed → correct count

**DEP**: Step 3.2

---

### Step 3.4: Conditional Diffusion

**Goal**: Rotation parameterized by valid move count `k`, restricted to legal
children only.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/common/diffusion.py` | [NEW] `conditional_diffusion(count_register, max_k, branch_register)` — for each k_val in 1..max_k: `with (count == k_val): Ry(angle(k_val))`. Shared between games. | ~120 |

**Tests** (`tests/python/test_conditional_diffusion.py` [NEW], ~150 LOC):
- Rotation angles correct: `angle(k) = 2 * arcsin(1/sqrt(k))`
- k=1 → no rotation (single child)
- k=2 → equal superposition
- Verify via classical mode: correct angle values computed
- Small-instance quantum simulation (if within 17-qubit budget): verify amplitudes

**DEP**: Step 1.2

---

### Step 3.5: Walk Operator Composition

**Goal**: Compose enumeration + legality + counting + diffusion + uncomputation
into a single walk operator step.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/walk.py` | [MOD] Add `walk_step(board, height_reg, branch_regs)` — one application of the walk operator: enumerate → evaluate legality → count → diffuse → uncompute | +100 |

**Tests** (`tests/python/test_ttt_walk_step.py` [NEW], ~150 LOC):
- Walk step on known position produces only legal child states (classical verification)
- Move counts are correct after walk step
- No illegal states reachable
- Uncomputation leaves ancilla clean (verified classically)
- Property: `for all positions: walk_step produces children ⊆ legal_moves(position)`

**DEP**: Steps 3.1–3.4

---

### Step 3.6: Walk Operator Verification

**Goal**: Thorough property-based verification of the walk operator across all
reachable tic-tac-toe positions.

| File | Action | ~LOC |
|------|--------|------|
| `tests/python/test_ttt_walk_verification.py` | [NEW] Property-based tests using `ql.verify()` | ~200 |

Properties checked (via many classical samples):
- No illegal moves generated (cell occupied, wrong turn, game over)
- Valid move count matches classical engine
- Board state after move is consistent (only one cell changed)
- Applied move matches the branch register selection
- Terminal positions produce 0 children

**DEP**: Steps 3.5, 2.6

---

## Phase 4 — Tic-Tac-Toe Minimax (PRD Milestone 4)

### Step 4.1: Height/Depth Tracking

**Goal**: Track current depth in the game tree. One-hot register for tree level.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/common/tree.py` | [NEW] `create_height_register(max_depth)`, `increment_depth(h)`, `decrement_depth(h)`, `is_at_depth(h, d) → qbool` | ~100 |

**Tests** (`tests/python/test_tree_height.py` [NEW], ~100 LOC):
- Initial depth = 0
- Increment/decrement round-trips
- `is_at_depth` returns correct qbool
- Classical mode: tracks depth as plain int

**DEP**: Phase 1

---

### Step 4.2: Terminal Evaluation

**Goal**: Evaluate terminal nodes: win (+1), loss (-1), draw (0).

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/evaluation.py` | [NEW] `evaluate_terminal(board, maximizing_player) → qint` — returns +1/-1/0 based on win/loss/draw for the maximizing player | ~80 |

**Tests** (`tests/python/test_ttt_evaluation.py` [NEW], ~120 LOC):
- X wins → +1 (when X is maximizing)
- O wins → -1 (when X is maximizing)
- Draw → 0
- Non-terminal → undefined (handled by caller)
- All tested classically and cross-validated

**DEP**: Step 2.3

---

### Step 4.3: Min/Max Alternation

**Goal**: Track whose turn (min or max player) at each tree level.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/common/minimax.py` | [NEW] `is_maximizing(depth_register) → qbool` (even depth = max, odd = min), `propagate_value(child_value, current_best, is_max) → updated_best` | ~120 |

**Tests** (`tests/python/test_minimax_logic.py` [NEW], ~120 LOC):
- Depth 0 = maximizing
- Depth 1 = minimizing
- Propagate: max player picks higher, min player picks lower
- Edge cases: first child sets initial value
- Classical mode only

**DEP**: Step 4.1

---

### Step 4.4: Minimax Walk Composition

**Goal**: Full minimax walk: combine walk operator with min/max alternation and
terminal evaluation. This is the top-level solver.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/minimax.py` | [NEW] `solve(board, max_depth) → evaluation` — construct the full minimax walk: at each level, walk step → if terminal evaluate → propagate up via min/max | ~200 |

**Tests** (`tests/python/test_ttt_minimax.py` [NEW], ~200 LOC):
- Solve from near-terminal positions (1–2 moves left) — verify correct result
- Solve tic-tac-toe from empty board → result should be 0 (draw with optimal play)
- Verify intermediate evaluations at each depth
- Compare against classical minimax on same positions

**DEP**: Steps 4.1–4.3, 3.5

---

### Step 4.5: Classical Minimax Reference

**Goal**: Independent classical minimax for tic-tac-toe to validate the quantum
version.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/tictactoe/classical_engine.py` | [MOD] Add `minimax(board, is_maximizing) → score` — standard alpha-beta minimax | +60 |

**Tests** (`tests/python/test_ttt_classical_minimax.py` [NEW], ~100 LOC):
- Known endgame positions
- Empty board → 0 (draw)
- Forced-win positions → +1 or -1

**DEP**: Step 2.6

---

## Phase 5 — Chess Predicates (PRD Milestone 5)

### Step 5.1: Board Encoding

**Goal**: Encode an 8×8 chess board. Piece encoding: 4 bits per square
(0=empty, then piece types 1–6 for P/N/B/R/Q/K, bit 3 for color).

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/__init__.py` | [NEW] Package init | ~5 |
| `src/games/chess/board.py` | [NEW] `ChessBoard` class: `encode(fen_or_dict)`, `piece_at(sq) → qint(4)`, `is_empty(sq) → qbool`, `is_color(sq, color) → qbool`, constants for piece types. 8×8 qarray of qint(width=4). | ~200 |

**Tests** (`tests/python/test_chess_board.py` [NEW], ~200 LOC):
- Encode starting position
- Encode custom FEN strings
- `piece_at` returns correct piece type
- `is_empty` correct for empty/occupied
- `is_color` correct for white/black
- Classical mode: no qubits

**DEP**: Phase 1

---

### Step 5.2: Piece Movement — Knights

**Goal**: Knight move generation and legality. Knights move in L-shapes,
independent of board rays — simplest piece to start with.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/moves_knight.py` | [NEW] `knight_attacks(sq) → list[int]` (classical precomputation), `knight_move_legal(board, from_sq, to_sq, color) → qbool` — target not friendly piece | ~80 |

**Tests** (`tests/python/test_chess_knight.py` [NEW], ~150 LOC):
- Corner knight: 2 attacks
- Edge knight: 3–4 attacks
- Center knight: 8 attacks
- Legal move: target empty or enemy
- Illegal: target is friendly piece
- Cross-validate with `python-chess` on 20+ positions

**DEP**: Step 5.1

---

### Step 5.3: Piece Movement — Sliding Pieces (Bishop, Rook, Queen)

**Goal**: Ray-based move generation for sliding pieces.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/moves_sliding.py` | [NEW] `ray_attacks(board, sq, directions) → list[qbool]` for each square on each ray: legal if path clear and target not friendly. `bishop_moves`, `rook_moves`, `queen_moves` as wrappers. | ~250 |

**Tests** (`tests/python/test_chess_sliding.py` [NEW], ~250 LOC):
- Open board: full ray coverage
- Blocked by friendly piece: ray stops
- Capture enemy piece: includes that square, stops after
- Bishop diagonals, rook ranks/files, queen = both
- 20+ positions cross-validated with `python-chess`

**DEP**: Step 5.1

---

### Step 5.4: Piece Movement — Pawns

**Goal**: Pawn move generation including double push, captures, en passant flag.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/moves_pawn.py` | [NEW] `pawn_moves(board, sq, color, en_passant_sq) → list[qbool]` — single push, double push (from starting rank), diagonal captures (including en passant) | ~150 |

**Tests** (`tests/python/test_chess_pawn.py` [NEW], ~200 LOC):
- Single push onto empty square
- Double push from starting rank
- Blocked by piece ahead
- Diagonal capture of enemy
- En passant capture
- No backward moves
- Cross-validate with `python-chess`

**DEP**: Step 5.1

---

### Step 5.5: Piece Movement — King

**Goal**: King moves (1 square any direction) and castling.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/moves_king.py` | [NEW] `king_moves(board, sq, color, castling_rights, in_check_fn) → list[qbool]` — 8 directions + kingside/queenside castling (path clear, not through check) | ~200 |

**Tests** (`tests/python/test_chess_king.py` [NEW], ~200 LOC):
- Normal moves (8 directions, edge clipping)
- Castling: both sides, both colors
- Castling blocked: piece in the way
- Castling through check: illegal
- Castling rights lost: illegal
- Cross-validate with `python-chess`

**DEP**: Steps 5.1, 5.6 (check detection needed for castling)

---

### Step 5.6: Check Detection

**Goal**: Detect if a king is in check.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/check.py` | [NEW] `is_in_check(board, color) → qbool` — is the king of `color` attacked by any enemy piece? Combines knight attacks, sliding rays, pawn attacks against king square. | ~150 |

**Tests** (`tests/python/test_chess_check.py` [NEW], ~200 LOC):
- Not in check: safe position
- Check by knight
- Check by bishop/queen diagonal
- Check by rook/queen rank/file
- Check by pawn
- Double check
- Cross-validate with `python-chess` on 50+ positions

**DEP**: Steps 5.2, 5.3, 5.4

---

### Step 5.7: Legal Move Aggregation & Counting

**Goal**: Combine all piece moves, filter by "doesn't leave own king in check",
count legal moves.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/legal_moves.py` | [NEW] `generate_legal_moves(board, color, game_state) → list[(from, to, qbool)]` — for each piece of `color`, generate pseudo-legal moves, filter by `is_in_check` after applying. `count_legal_moves(board, color, game_state) → qint`. | ~300 |

**Tests** (`tests/python/test_chess_legal_moves.py` [NEW], ~250 LOC):
- Starting position: 20 legal moves for white
- Pin: pinned piece can't move (would expose king)
- Check: must resolve check
- Checkmate: 0 legal moves
- Stalemate: 0 legal moves (but not in check)
- 30+ positions cross-validated with `python-chess`

**DEP**: Steps 5.2–5.6

---

### Step 5.8: Checkmate & Stalemate Detection

**Goal**: High-level game-over predicates.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/endgame.py` | [NEW] `is_checkmate(board, color, game_state) → qbool`, `is_stalemate(board, color, game_state) → qbool`, `is_game_over(board, color, game_state) → qbool` | ~80 |

**Tests** (`tests/python/test_chess_endgame.py` [NEW], ~150 LOC):
- Scholar's mate position → checkmate
- Stalemate position → stalemate
- Normal position → neither
- Cross-validate with `python-chess`

**DEP**: Steps 5.6, 5.7

---

### Step 5.9: Promotion Handling

**Goal**: Pawn reaching the last rank promotes (default to queen for walk
purposes; full choice not needed for minimax correctness).

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/moves_pawn.py` | [MOD] Add promotion flag to pawn moves on 7th/8th rank | +40 |
| `src/games/chess/legal_moves.py` | [MOD] Handle promotion in move application | +20 |

**Tests** (`tests/python/test_chess_promotion.py` [NEW], ~100 LOC):
- Pawn on 7th rank: promotion moves generated
- Promotion results in queen
- Cross-validate with `python-chess`

**DEP**: Steps 5.4, 5.7

---

### Step 5.10: Chess Cross-Validation Suite

**Goal**: Comprehensive validation against `python-chess` across many positions.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/classical_reference.py` | [NEW] Adapter wrapping `python-chess` for comparison: `ref_legal_moves(fen)`, `ref_is_check(fen)`, `ref_is_checkmate(fen)` | ~80 |
| `tests/python/test_chess_cross_validation.py` | [NEW] Load 100+ FEN positions (opening, middlegame, endgame, edge cases), compare all predicates | ~200 |

**DEP**: Steps 5.1–5.9

---

## Phase 6 — Chess Walk Operator & Minimax (PRD Milestone 6)

### Step 6.1: Chess Move Enumeration

**Goal**: Enumerate candidate moves for the walk operator. Each candidate is a
(from_sq, to_sq) pair packed into a quantum register.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/walk.py` | [NEW] `enumerate_candidates(board, color) → qarray` — generates candidate move registers up to d_max slots | ~200 |

**Tests** (`tests/python/test_chess_enumeration.py` [NEW], ~150 LOC):
- Starting position: 20 candidates marked legal
- Midgame position: correct candidate set
- All candidates are valid (from_sq, to_sq) pairs
- Classical verification

**DEP**: Step 5.7

---

### Step 6.2: Chess Walk Operator

**Goal**: Full walk step for chess: enumerate → legality → count → diffuse →
uncompute.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/walk.py` | [MOD] Add `chess_walk_step(board, height_reg, branch_regs, game_state)` — composes enumeration + legal move evaluation + counting + conditional diffusion + uncomputation | +200 |

**Tests** (`tests/python/test_chess_walk.py` [MOD or NEW], ~200 LOC):
- Walk step produces only legal children (classical verification)
- Move counts match `python-chess`
- Uncomputation leaves registers clean
- Property-based: `for all tested positions: children ⊆ legal_moves`

**DEP**: Steps 6.1, 3.4 (reuses conditional diffusion)

---

### Step 6.3: Chess Terminal Evaluation

**Goal**: Evaluate terminal chess positions.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/evaluation.py` | [NEW] `evaluate_terminal(board, game_state, maximizing_color) → qint` — checkmate = ±1, stalemate/draw = 0 | ~80 |

**Tests** (`tests/python/test_chess_evaluation.py` [NEW], ~100 LOC):
- Checkmate for maximizing player → -1
- Checkmate for opponent → +1
- Stalemate → 0
- Non-terminal → sentinel

**DEP**: Step 5.8

---

### Step 6.4: Chess Minimax Solver

**Goal**: Compose walk operator + evaluation + min/max alternation into a full
chess minimax solver.

| File | Action | ~LOC |
|------|--------|------|
| `src/games/chess/minimax.py` | [NEW] `solve(board, game_state, max_depth) → evaluation` — full minimax walk for chess | ~200 |

**Tests** (`tests/python/test_chess_minimax.py` [NEW], ~200 LOC):
- Mate-in-1 positions: finds the win
- Drawn endgames (e.g., K vs K): evaluates as 0
- Positions with known tablebase evaluations
- Compare against classical minimax on depth-limited search

**DEP**: Steps 6.2, 6.3, 4.3

---

### Step 6.5: Endgame Tablebase Verification

**Goal**: Validate chess minimax against known endgame tablebase results.

| File | Action | ~LOC |
|------|--------|------|
| `tests/python/test_chess_tablebase.py` | [NEW] Test suite using known KQK, KRK, KPK endgame positions with known outcomes | ~150 |

**DEP**: Step 6.4

---

## Summary

### File Count by Phase

| Phase | New Files | Modified Files | New Test Files |
|-------|-----------|---------------|----------------|
| 1: Classical Verification | 3 | 4 | 8 |
| 2: Tic-Tac-Toe Predicates | 3 | 1 | 7 |
| 3: TTT Walk Operator | 2 | 1 | 7 |
| 4: TTT Minimax | 3 | 1 | 5 |
| 5: Chess Predicates | 9 | 1 | 11 |
| 6: Chess Walk & Minimax | 4 | 1 | 6 |
| **Total** | **24** | **9** | **44** |

### Module Size Budget

Every implementation module targets ≤ 400 LOC. The largest are:

| Module | ~LOC | Justification |
|--------|------|---------------|
| `chess/legal_moves.py` | ~300 | Aggregates all piece types, filtering |
| `chess/moves_sliding.py` | ~250 | 4 ray directions × multiple logic |
| `tictactoe/walk.py` | ~360 | Grows across Steps 3.1–3.5 |
| `chess/walk.py` | ~400 | Grows across Steps 6.1–6.2 |
| `verify.py` | ~150 | Standalone utility |

If any module approaches 400 LOC during implementation, split it.

### Dependency Graph (Simplified)

```
Phase 1 (Classical Verification)
  ├── Phase 2 (TTT Predicates)
  │     ├── Phase 3 (TTT Walk)
  │     │     └── Phase 4 (TTT Minimax) ←── Phase 4.3 (common/minimax)
  │     └── Phase 2.6 (Cross-validation)
  │
  ├── Phase 5 (Chess Predicates)  [can start after Phase 1, parallel with 2-4]
  │     └── Phase 6 (Chess Walk & Minimax)
  │           ├── reuses: common/diffusion (Phase 3.4)
  │           └── reuses: common/minimax (Phase 4.3)
  │
  └── Phase 4.1 (common/tree) + Phase 3.4 (common/diffusion)
        [shared components, built during TTT, reused by chess]
```

### Parallelizable Work

- **Phase 2 + Phase 5.1–5.4**: TTT predicates and chess board encoding + piece
  moves are independent after Phase 1 completes.
- **Phase 3.4** (conditional diffusion) is game-agnostic and can be built early.
- **Phase 4.1–4.3** (tree/minimax common) are game-agnostic.

### Testing Strategy

1. **Unit tests**: Every function has direct tests (classical mode).
2. **Cross-validation**: Game predicates validated against independent engines
   (`classical_engine.py` for TTT, `python-chess` for chess).
3. **Property-based**: Walk operators verified via `ql.verify()` with statistical
   confidence (10K+ samples for critical properties).
4. **Small-instance quantum**: Late-game TTT (2–3 empty cells) verified via
   Qiskit simulation within 17-qubit budget where feasible.
5. **Regression**: Each step's tests form a regression suite that guards against
   breakage from later changes.
