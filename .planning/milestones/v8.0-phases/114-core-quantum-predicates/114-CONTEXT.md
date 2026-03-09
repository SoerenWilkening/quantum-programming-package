# Phase 114: Core Quantum Predicates - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement piece-exists and no-friendly-capture quantum predicates using standard ql constructs (`with qbool:`, qarray element access, `@ql.compile(inverse=True)`). These are standalone predicate functions tested independently. Walk integration (rewiring evaluate_children) is Phase 116.

</domain>

<decisions>
## Implementation Decisions

### Predicate architecture
- Separate `@ql.compile(inverse=True)` functions for piece-exists (PRED-01) and no-friendly-capture (PRED-02)
- Factory pattern: `make_piece_exists_predicate(piece_id, dr, df, board_rows, board_cols)` returns a compiled function, mirroring `_make_apply_move` in chess_encoding.py
- `@ql.compile(inverse=True)` wrapping is inside the factory — caller gets a ready-to-use compiled function with `.inverse()` available
- New file: `src/chess_predicates.py` — dedicated module alongside chess_encoding.py and chess_walk.py

### Superposition handling
- Classical loop over all possible source squares at circuit construction time
- For each (r, f): use `with board[r, f]:` to condition on piece being at that square, then check target condition at (r+dr, f+df)
- Generates O(board_size^2) controlled blocks using only standard ql constructs — no quantum arithmetic on position registers

### Off-board move rejection
- Classical skip in the loop: when iterating (r, f) and computing (r+dr, f+df), skip iterations where destination is out of bounds
- No quantum gates emitted for impossible moves — predicate result stays |0> (not valid) by default
- No explicit quantum bounds check needed — resolved entirely at circuit construction time

### No-piece-exists handling
- If no source square has the piece (all board entries are 0), predicate result stays |0> naturally — no `with board[r,f]:` block fires
- Falls out of the classical-loop design for free

### Friendly capture check
- Side-specific: white moves check white_king + white_knights qarrays, black moves check black_king only
- Factory takes `piece_qarray` (moving piece's board) and `friendly_qarrays` (list of same-color boards)
- Self-capture handled naturally — knight/king offset tables never include (0,0)

### Predicate-to-walk interface
- Predicate writes to a passed-in result qbool (flips to |1> if condition holds)
- Caller owns the ancilla lifecycle — matches existing validity[i] pattern in evaluate_children
- Standalone in this phase — Phase 116 wires into evaluate_children

### Function signature convention
- Factory takes named arrays: `piece_qarray` (the moving piece) and `friendly_qarrays` (list of same-color boards)
- Phase 115 extends with `enemy_qarrays` for check detection

### Board size parameterization
- Predicates parameterized by `board_rows`, `board_cols`
- Tests use 2x2, production uses 8x8 — same code path for both

### Claude's Discretion
- Exact ancilla management within compiled predicate bodies
- How to structure the inner conditional logic (sequential `with` blocks vs accumulated condition)
- Classical helper functions for move validation

</decisions>

<specifics>
## Specific Ideas

- Factory pattern mirrors `_make_apply_move` in chess_encoding.py — classical precomputation outside compiled body, quantum ops inside
- The flat Toffoli-AND constraint (nested `with qbool:` raises NotImplementedError) applies to predicate internals — use sequential controlled blocks, not nested conditionals
- Move table from Phase 113 provides (piece_id, dr, df) triples that parameterize the predicate factories

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_make_apply_move` (chess_encoding.py:390): Factory pattern template for compiled quantum functions with classical closure data
- `@ql.compile(inverse=True)`: Existing compilation infrastructure for forward/inverse lifecycle
- `encode_position` (chess_encoding.py:97): Board qarray creation — used to set up test boards
- `build_move_table` (chess_encoding.py:66): Move enumeration table providing (piece_id, dr, df) triples
- `_KNIGHT_OFFSETS` / `_KING_OFFSETS` (chess_encoding.py:42-63): Geometric offset tables

### Established Patterns
- Flat Toffoli-AND decomposition — no nested `with qbool:` (framework limitation)
- Classical precomputation outside `@ql.compile` body, quantum ops inside
- `with cond:` for single-level conditional control on qbool
- `~board[r, f]` for controlled NOT on qarray elements

### Integration Points
- `evaluate_children` (chess_walk.py:247): Currently uses trivial predicate — Phase 116 will rewire to call real predicates
- `build_move_table` (chess_encoding.py): Provides move data that parameterizes predicate factories
- Phase 115 will compose piece-exists + no-friendly-capture + check detection into combined predicate

</code_context>

<testing>
## Testing Strategy

### Small-board verification (2x2)
- 3 pieces x 4 squares = 12 qbool for board + branch register + ancillae within 17-qubit limit
- Statevector comparison: build circuit with predicate, run Qiskit AerSimulator, check result qbool matches classical evaluation for each basis state
- Cover edge cases: corner positions, off-board moves, piece not present

### Production circuit structure (8x8)
- Circuit-only test (no simulation): verify gate count, qubit count, and that circuit builds without error
- Ensures parameterized code scales correctly from 2x2 to 8x8

</testing>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 114-core-quantum-predicates*
*Context gathered: 2026-03-08*
