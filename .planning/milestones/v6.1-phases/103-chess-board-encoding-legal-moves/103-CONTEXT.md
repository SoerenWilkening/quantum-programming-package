# Phase 103: Chess Board Encoding & Legal Moves - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Encode a chess endgame position (2 kings + 2 white knights) and generate legal moves for any piece using quantum primitives. The move oracle produces an enumerated legal move list suitable for Phase 104's branch registers. No walk operators, no diffusion — just board encoding and move generation.

</domain>

<decisions>
## Implementation Decisions

### Board encoding strategy
- Square-centric encoding: qarray of 64 qbools, one per square, storing whether a piece occupies that square
- Separate qarrays per piece type as needed (e.g., white knights, white king, black king) — Claude's discretion on exact layering
- 64 qbools per layer; more qubits than piece-centric but better for downstream phases (attack maps, legality checks, move application)
- Starting positions are classical input — set via X gates at circuit initialization time
- Positions are configurable via Python parameters (not hardcoded)
- Matches the pattern already used in `demo.py` (8x8 qarray of qbool for knight positions)

### Move representation format
- Legal moves represented as an enumerated index list (0..d-1)
- Each index maps to a (piece, destination) pair
- Deterministic ordering: sorted by piece index, then destination square
- Branch register stores the index — maps directly to Montanaro's framework for Phase 104
- Per-side combined list: oracle returns all legal moves for the side to move (both knights + king)

### Move generation approach
- Hybrid: classical precomputation where positions are known, quantum conditionals where branch superposition determines the position
- For the walk: board position at each node is derived by replaying the move sequence from the starting position (as specified in Phase 104 success criteria)
- The move oracle must handle both knight attack patterns (L-shaped, 8 directions) and king moves (8 adjacent, edge-aware)
- Legal move filtering excludes: destinations occupied by friendly pieces, moves that leave own king in check

### Module organization
- Standalone module: create a chess encoding module (not inline in demo.py)
- Reusable by Phase 106's demo scripts and comparison script
- Separate from the quantum_language core library — this is a demo/application module

### Verification approach
- Classical unit tests for move generation correctness: knight moves from every square, king moves with edge awareness, legal move filtering, friendly-piece blocking
- Subcircuit spot-checks: small cases (1 piece, subset of board) simulated via Qiskit within 17-qubit budget
- Tests in main test suite: tests/python/test_chess.py following existing conventions

### Claude's Discretion
- Exact qarray layering for piece types (one qarray per piece type vs combined encoding)
- Oracle API interface design (full position vs incremental)
- Default demo starting position (interesting endgame vs center placement)
- Spot-check priority ordering (encoding vs oracle first)
- Whether to print circuit statistics in Phase 103 or defer to Phase 106

</decisions>

<specifics>
## Specific Ideas

- The existing `demo.py` has a working `knight_moves()` function that computes classical knight attack patterns — this can be reused or adapted
- The milestone context specifies: white has max ~32 moves (5-bit branch register), black has max 8 moves (3-bit branch register) — branch register width per level is fixed at the maximum for that player's turn
- Phase 104 explicitly requires: "board position at any tree node is correctly derived by replaying the move sequence encoded in branch registers 0..d-1 from the starting position" — the move oracle must be compatible with this replay pattern

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/demo.py:knight_moves()`: Classical knight attack pattern generation from any square — computes all 8 L-shaped offsets with boundary checking
- `src/demo.py:attack()`: `@ql.compile` function demonstrating chess-like qarray operations with quantum conditionals
- `qarray`: Supports 2D indexing, element-wise operations, boolean reductions (.any(), .all())
- `qbool`: 1-bit quantum boolean for piece presence/attack flags
- `@ql.compile(inverse=True)`: Capture-replay decorator with automatic inverse — used by walk operators

### Established Patterns
- Quantum conditionals via `with qbool:` for conditional operations based on piece presence
- `qint(value, width=N)` for classical initialization via X gates
- `qarray(data, dtype=ql.qbool)` for board-like structures
- NumPy-style operations on qarray (!=, &, |, any(), all())

### Integration Points
- Move oracle output feeds Phase 104's branch registers (enumerated index list)
- Standalone chess module imported by Phase 106 demo scripts
- Tests use `clean_circuit` fixture (unit tests) and `verify_circuit` fixture (subcircuit simulation)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 103-chess-board-encoding-legal-moves*
*Context gathered: 2026-03-03*
