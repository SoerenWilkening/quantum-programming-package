# Phase 115: Check Detection & Combined Predicate - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement check detection predicate (king safety via attack tables) and combined move legality predicate composing piece-exists, no-friendly-capture, and check detection into a single qbool. All predicates use standard ql constructs (`with qbool:`, `&` operator, `@ql.compile(inverse=True)`). Walk integration is Phase 116.

</domain>

<decisions>
## Implementation Decisions

### Check detection approach
- Position-based check detection: classical loop over all possible king squares, `with king_qarray[r, f]:` to condition on king being there, then check if enemy pieces attack that square
- No discovered checks possible in KNK (no sliding pieces) — moving a knight never exposes the king
- Parameterized by move: for king moves, check enemies attacking destination (r+dr, f+df); for knight moves, check enemies attacking king's current position (r, f)
- Side-specific factories: factory takes enemy_qarrays + enemy attack offsets specific to each side (white king safety: check black king adjacency only; black king safety: check white king adjacency + white knight L-shapes)
- Result polarity: |1> = king is safe (NOT in check) — consistent with piece-exists and no-friendly-capture where |1> means "condition passed"

### Attack table structure
- Classical Python precomputation at circuit construction time, same pattern as Phase 114's valid_sources
- Merged attacker list: for each possible king square (r,f), precompute ALL (ar, af, enemy_qarray) triples that could attack it — single loop in quantum body
- New parameterized helpers using _KNIGHT_OFFSETS/_KING_OFFSETS with (row, col) pairs and board_rows/board_cols bounds checking — existing 8x8 helpers stay for classical move generation
- Mirror no-friendly-capture logic pattern: start by flipping result to |1> (optimistic: assume safe), then un-flip for each enemy found at an attacking square using `&` operator

### Combined predicate composition
- Sequential calls + AND: call each sub-predicate separately, each writes to its own result qbool, then AND the three results into a final qbool
- Combined predicate is itself a @ql.compile(inverse=True) factory — allocates three intermediate qbools, calls sub-predicates, ANDs into final result
- Factory builds all three sub-predicates internally from raw parameters — single entry point for callers
- Three-way AND via chained `&` operator: `result = a & b`, then `final = result & c` — two Toffoli gates, one intermediate ancilla

### File & signature design
- Extend chess_predicates.py — all predicate factories in one module
- Check detection: `make_check_detection_predicate(moving_piece_type, dr, df, board_rows, board_cols, enemy_attacks)` where enemy_attacks is list of (offset_list, piece_type_str) tuples. Returns compiled func: `check_safe(king_qarray, *enemy_qarrays, result)`
- Combined: `make_combined_predicate(piece_type, dr, df, board_rows, board_cols, enemy_attacks)` returns compiled func: `is_legal(piece_qarray, *friendly_qarrays, king_qarray, *enemy_qarrays, result)`. Internally builds all three sub-predicates.

### Claude's Discretion
- Exact ancilla management within compiled predicate bodies
- Internal structure of the attack table precomputation helpers
- How the combined predicate orders sub-predicate calls
- Classical helper functions for offset computation

</decisions>

<specifics>
## Specific Ideas

- King position is in superposition — cannot classically know where the king is, must iterate quantumly over all possible positions
- Mirror the proven flip-and-unfip pattern from no-friendly-capture: optimistic flip to |1>, then conditionally un-flip when enemy found
- Factory pattern mirrors Phase 114's make_piece_exists_predicate and make_no_friendly_capture_predicate — classical closure data outside @ql.compile, quantum ops inside
- The flat Toffoli-AND constraint (nested `with qbool:` raises NotImplementedError) applies — use sequential controlled blocks and `&` operator

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `make_piece_exists_predicate` (chess_predicates.py:25): Sub-predicate for combined composition
- `make_no_friendly_capture_predicate` (chess_predicates.py:87): Sub-predicate for combined composition, AND logic pattern to mirror
- `_KNIGHT_OFFSETS` / `_KING_OFFSETS` (chess_encoding.py:42-63): Geometric offset tables for attack computation
- `knight_attacks()` / `king_attacks()` (chess_encoding.py:135-176): Classical attack helpers (8x8 only) — reference for correctness but not reusable for parameterized boards
- `legal_moves_white()` / `legal_moves_black()` (chess_encoding.py): Classical equivalents for test verification
- `@ql.compile(inverse=True)`: Compilation infrastructure for forward/inverse lifecycle
- `encode_position` (chess_encoding.py:97): Board qarray creation for test setup

### Established Patterns
- Flat Toffoli-AND decomposition — no nested `with qbool:` (framework limitation)
- Classical precomputation outside `@ql.compile` body, quantum ops inside
- XOR = OR pattern valid for single-piece-per-square (KNK endgame)
- `&` operator for Toffoli-controlled operations (auto-uncomputed ancilla)
- Variadic `*args` signature with result qbool as last argument

### Integration Points
- Phase 116 will call combined predicate from evaluate_children in chess_walk.py
- build_move_table (chess_encoding.py) provides (piece_id, dr, df) triples that parameterize the predicate factories
- Phase 114's piece-exists and no-friendly-capture are sub-predicates composed inside the combined predicate

</code_context>

<testing>
## Testing Strategy

### Small-board verification (2x2)
- Statevector comparison: build circuit with check detection / combined predicate, run Qiskit AerSimulator, check result qbool matches classical evaluation for each basis state
- Classical equivalents from legal_moves_white()/legal_moves_black() for correctness reference
- Cover edge cases: king adjacent to enemy king, knight attacking king, no-check positions

### Production circuit structure (8x8)
- Circuit-only test (no simulation): verify gate count, qubit count, and that circuit builds without error
- Ensures parameterized code scales correctly from 2x2 to 8x8

</testing>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 115-check-detection-combined-predicate*
*Context gathered: 2026-03-09*
