# Phase 121: Chess Engine Rewrite - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Rewrite `examples/chess_engine.py` to demonstrate the full v9.0 feature set (nested `with` blocks, 2D qarrays, `@ql.compile`) in readable natural-programming style. Build a quantum walk search tree over chess moves with walk operators (R_A/R_B) and diffusion. Circuit-build-only — no simulation required. Includes fixing opt=1 compile behavior so gates are NOT flat-expanded on replay (call-graph-only mode), which is required for the engine to compile without OOM.

</domain>

<decisions>
## Implementation Decisions

### Chess scenario
- King + 2 Knights (white) vs King (black) endgame on 8x8 board
- Hardcoded initial position (specific squares baked into example)
- Black to move only (1 ply) — 2-ply is a future phase
- Goal: build the quantum walk search tree, not evaluate or count yet

### Walk tree structure
- 1-ply tree: root → 8 possible king moves (one per direction)
- Fixed 8-direction index: 3-bit branch register encoding N/NE/E/SE/S/SW/W/NW
- **Flow:** (1) evaluate all 8 directions — make move, check legality, store in feasibility register, unmake; (2) apply diffusion conditioned on feasibility; (3) controlled on branch register, apply selected move
- Feasibility register: `ql.qarray(dim=8, dtype=ql.qbool)` — one qbool per direction
- Height register: one-hot 2-qubit qarray (height[0]=leaf, height[1]=root) — extends naturally to 2-ply later
- Walk operators (R_A/R_B) written inline using `ql.diffusion()` and `with` blocks — NOT using QWalkTree class
- Diffusion over all 8 branches with feasibility masking (amplitude only on legal moves)
- Walk step compiled with `@ql.compile(opt=1)` for replay
- Configurable iteration count: `NUM_STEPS = 3` variable, with comment noting first call compiles, rest replay

### Move legality (predicate)
- Full legality check per CHESS-03: piece-exists at source, no friendly capture, not in check after move
- Check detection: scan all 64 squares for white attackers (`with white_knight[a, b]:` / `with white_king[a, b]:`) — correct in superposition, extends to 2-ply
- White attack map: `ql.qarray(dim=(8,8), dtype=ql.qbool)` — binary attacked/not-attacked, sufficient for check detection
- Friendly-capture detection: combined white occupancy board (`white_occ = white_king | white_knight`), check `~white_occ[to_r, to_c]`
- Black representation: `black_king` board only — no separate occupancy needed (black has only a king)
- Attack computation: compiled sub-predicate `@ql.compile(opt=1, inverse=True)` for OOM prevention
- Uncompute attacks after each direction check to free ancilla qubits

### opt=1 compile fix (OOM mitigation)
- **Critical:** opt=1 currently injects ALL gates into flat circuit on replay — this must be fixed for CHESS-02
- New opt=1 behavior: replay skips `inject_remapped_gates()`, only records a DAG node with block reference
- First call (capture) still injects gates into flat circuit (needed for cache); subsequent replays are DAG-only
- Call graph is an operation-level DAG: each node = one quantum operation (e.g., "add a + b"), stores qubits + gate sequence
- Edges represent dependencies based on qubit overlap
- `circuit_stats()` reads from the DAG (sum gate counts, compute depth from longest DAG path, sum T-count)
- This is the new default for opt=1 — not a separate flag
- Opt level semantics: opt=0 flat gate list (original), opt=1 call graph no expansion (NEW), opt=2 call graph + merge, opt=3 no DAG
- Reuse and extend existing `CallGraphDAG` — it already tracks nodes with qubit sets, gate counts, depth, overlap edges
- **Out of scope for this phase:** `to_openqasm()` and `draw_circuit()` from DAG (future work)

### Code style & output
- Incremental refactor of existing `examples/chess_engine.py` — fix bugs during refactor (wrong board variable, broken unpacking, unmake bug)
- Single file with clear sections: (1) move tables, (2) board setup, (3) compiled predicates, (4) walk operators, (5) main execution
- Section header comments (`# === Board Setup ===`) plus brief comments on key quantum decisions (why compile, why uncompute)
- Brief module docstring (2-3 sentences: what, scenario, approach)
- Output when run: position display (ASCII), section progress messages, circuit stats
- No circuit diagram output in this phase
- Chess notation in comments alongside array indices (e.g., `white_king[0, 4] ^= ql.qbool(True)  # e1`)

### Board initialization
- XOR with `ql.qbool(True)` for placing pieces: `board[r, c] ^= ql.qbool(True)`
- Piece boards: one `ql.qarray(dim=(8,8), dtype=ql.qbool)` per piece type (white_king, white_knight, black_king)

### Claude's Discretion
- Exact walk step implementation details within the decided structure
- Error handling and edge cases
- Internal helper function organization
- gc.collect() placement if needed alongside the compile fix

</decisions>

<specifics>
## Specific Ideas

- Walk tree branches represent king move directions (0-7), not a classical list of moves — quantum walk prepares valid children in superposition
- Before branching, all moves must be evaluated (make/check/unmake), feasibility stored in quantum register, THEN diffusion applied
- The call graph DAG should be at the operation level — each node is an instruction (like quantum addition) with its qubits and gate sequence, not at the function-call level

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CallGraphDAG` (compile.py / call_graph.py): Already tracks nodes with qubit sets, gate counts, depth, overlap edges — extend for DAG-only mode
- `ql.diffusion()` (diffusion.py): X-MCZ-X pattern, works on qint/qbool/qarray — use for R_A/R_B inline
- `@ql.compile(opt=1, inverse=True)`: Capture + adjoint support — use for attack computation with uncomputation
- `ql.qarray(dim=(8,8), dtype=ql.qbool)`: 2D board construction (Phase 120) — use for all piece boards and attack map
- Existing `examples/chess_engine.py`: Draft with move helpers and board setup — refactor incrementally

### Established Patterns
- `inject_remapped_gates()` in `_replay()`: The gate injection point to skip for DAG-only replay
- `_build_qubit_set_numpy()`: Already used to build qubit sets for DAG nodes
- `circuit_stats()` in `_core.pyx`: Currently reads flat circuit — needs to check for DAG and sum from nodes instead
- Nested `with` blocks: AND-ancilla composition from Phase 117-118, used for multi-condition checks

### Integration Points
- `compile.py:1491`: `inject_remapped_gates()` call in `_replay()` — conditional skip when opt=1 replay
- `compile.py:897`: Replay path in `_call_inner()` — add DAG-only branch
- `_core.pyx:757`: `circuit_stats()` — add DAG-aware path
- `call_graph.py`: Extend `CallGraphDAG` to store block refs per node for stats computation

</code_context>

<deferred>
## Deferred Ideas

- 2-ply search (black moves, white responds) — future phase after 1-ply works
- Position evaluation / move counting via `ql.count_solutions` or `ql.grover` — future phase (end goal)
- Detection step (checking if walk found a marked node) — future phase
- `to_openqasm()` from DAG — future enhancement
- `draw_circuit()` from DAG with block boundaries — future enhancement
- Sliding piece attack generation (rook/bishop ray-casting) — future phase with more piece types

</deferred>

---

*Phase: 121-chess-engine-rewrite*
*Context gathered: 2026-03-09*
