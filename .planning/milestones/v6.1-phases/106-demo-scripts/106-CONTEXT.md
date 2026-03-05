# Phase 106: Demo Scripts - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Create runnable demo scripts showcasing the manual quantum walk on a chess game tree and comparing circuit statistics against the QWalkTree API. Circuit generation only -- no Qiskit simulation (qubit count exceeds 17-qubit budget). This is the final phase of v6.1.

</domain>

<decisions>
## Implementation Decisions

### Demo output content
- Full walkthrough style: print board position, legal moves per side, tree structure summary (branching per level), walk operators, and circuit statistics (qubits, gates, depth)
- Progressive output: print each section as it happens (position -> moves -> registers -> building walk step... -> stats)
- Per-section timing: time each major step (move generation, register creation, walk step compilation) and print duration
- Optional circuit visualization: add a `--visualize` flag (or similar variable) to generate PNG via `ql.draw_circuit()`; skip by default since chess circuits are huge

### Starting position
- Use interesting endgame position: wk=e4 (sq 28), bk=e8 (sq 60), wn=[c3 (sq 18)]
- max_depth = 1 (single ply, white moves only, ~150 qubits)
- Position configured via module-level constants at top of script (WK_SQ, BK_SQ, WN_SQUARES, MAX_DEPTH) -- easy to modify

### Comparison script
- Build walk step only (no detect()) -- create QWalkTree with same branching structure, compile walk_step(), print circuit stats
- Always-accept trivial predicate matching the manual approach (all children valid in precomputed KNK endgame)
- Side-by-side comparison table: Metric | Manual | QWalkTree | Delta -- clean, scannable format

### File organization
- Replace existing src/demo.py with the chess walk demo (old prototype code superseded)
- New src/chess_comparison.py for QWalkTree comparison script
- Smoke test only: single test verifying demo main() completes without error and produces non-zero circuit stats

### Claude's Discretion
- Exact print formatting and section headers
- Which circuit statistics to include (gate types, T-count, etc.)
- Smoke test implementation details
- How to structure the --visualize flag (argparse vs module variable)

</decisions>

<specifics>
## Specific Ideas

- chess_encoding.py has print_position() and print_moves() helpers ready to use
- chess_walk.py has all_walk_qubits() for register introspection
- ql.circuit_stats() available for gate counts, depth, qubit count
- QWalkTree class in walk.py takes max_depth, branching, and predicate parameters
- The comparison should use same branching factors as the manual approach for fair comparison

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `chess_encoding.py:print_position()`: ASCII board visualization
- `chess_encoding.py:print_moves()`: Move list with algebraic notation
- `chess_encoding.py:encode_position()`: Creates board qarrays
- `chess_encoding.py:get_legal_moves_and_oracle()`: Returns moves + compiled oracle
- `chess_walk.py:create_height_register()`, `create_branch_registers()`: Register construction
- `chess_walk.py:prepare_walk_data()`: Precomputes move data per level
- `chess_walk.py:walk_step()`: Compiled U = R_B * R_A
- `chess_walk.py:all_walk_qubits()`: Wraps height + branch qubits for stats
- `ql.circuit_stats()`: Gate counts, depth, qubit count
- `ql.draw_circuit()`: PIL Image circuit visualization

### Established Patterns
- `@ql.compile` with closure cache for walk_step (module-level CompiledFunc)
- Purely functional module style (no class) in chess_walk.py
- QWalkTree class-based API in walk.py with `walk_step()` method and `detect()`
- `time.time()` for section timing (used in existing demo.py)

### Integration Points
- chess_encoding.py and chess_walk.py are standalone modules in src/
- QWalkTree imported from quantum_language.walk
- Tests in tests/python/ following existing conventions

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 106-demo-scripts*
*Context gathered: 2026-03-05*
