# Feature Research

**Domain:** Quantum chess move legality in superposition (quantum walk predicate rewrite)
**Researched:** 2026-03-08
**Confidence:** MEDIUM -- Novel application domain; no direct prior art for Montanaro-walk chess predicates. Confidence is HIGH for individual sub-features (knight/king move generation, bitboard-style checks) and MEDIUM for their integration into quantum predicates.

## Feature Landscape

### Table Stakes (Users Expect These)

Features the quantum walk rewrite must have to replace the current classical pre-filtering approach.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Quantum piece-exists predicate | Current classical approach checks source square occupancy at circuit construction time; quantum version must check qarray bit in superposition | MEDIUM | Controlled-NOT on board qarray element. Source square qbool must be \|1> for move to be valid. Single multi-controlled test per move. Depends on existing board qarrays (v6.1). |
| Quantum same-color-capture rejection | Current approach filters `dest not in friendly_squares` classically; quantum version must check target square not occupied by friendly piece | MEDIUM | OR of same-color piece qarrays at destination square. Requires ancilla qbool for the OR result. Must uncompute cleanly. |
| Knight move generation (8 destinations/square) | Knights have exactly 8 possible L-shaped moves (fewer at edges). Already computed classically in `chess_encoding.py`; must become quantum enumeration | HIGH | Up to 8 (src, dst) pairs per knight. Enumerate all structurally possible moves across all 64 squares, validity checked quantumly. Total possible knight moves: up to 336 across all squares (but only populated squares matter in the KNK endgame). |
| King move generation (8 destinations/square) | Kings have exactly 8 adjacent moves (fewer at edges). Already computed classically; must become quantum enumeration | MEDIUM | Simpler than knights -- king moves are local. Up to 8 (src, dst) pairs per king. Same validity predicate structure as knight moves. |
| All-moves enumeration in circuit | Current approach: classical list of legal moves with indices mapping to branch register values. New approach: enumerate ALL structurally possible moves (up to ~218 for KNK endgame), check validity quantumly | HIGH | Branch register must index into the full move table. Moves with invalid source/target get validity=\|0>. The upper bound comes from: 2 kings x max 8 moves + variable knights x max 8 moves per square. Key design decision: static move table computed at circuit construction time from piece types (not positions). |
| Reversible move application oracle | Current `_make_apply_move` uses `@ql.compile(inverse=True)` with conditional CNOT flips. This pattern must extend to all enumerated moves, not just classically-filtered ones | MEDIUM | Same pattern: `with (branch == i): flip src off, flip dst on`. Scales linearly with move count. Already proven in v6.1. Invalid moves (validity=\|0>) produce no board change since the branch condition never fires for the corresponding index. |
| Variable branching integration | D_x diffusion uses `d(x)` = count of valid children. Currently `d_max` from classical move count; must now come from quantum validity ancilla count | LOW | Already implemented in `chess_walk.py` via `evaluate_children` and `precompute_diffusion_angles`. The validity ancillae pattern is unchanged -- what changes is that validity is now computed by a real quantum predicate instead of trivially set to \|1>. |

### Differentiators (Competitive Advantage)

Features that go beyond basic move legality replacement and represent genuine advances.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Quantum check detection (king safety) | No existing quantum chess implementation checks whether a king is in check as a quantum predicate. Google's Quantum Chess uses measurement-based resolution (collapses superposition). This project would compute check status reversibly in superposition, preserving coherence for the walk. | HIGH | Must detect if any opponent piece attacks the king's square AFTER the proposed move. For KNK endgame: check if black king is adjacent to white king's new square (king adjacency), or if any opponent knight attacks the king. Requires computing attack sets quantumly on the post-move board state. |
| Position-independent move enumeration | Current code hardcodes moves for a specific starting position (`get_legal_moves_and_oracle` takes explicit squares). Quantum enumeration works for ANY position in superposition -- the same circuit handles all board states arising in the walk tree | HIGH | This is the core motivation for the rewrite. Classical pre-filtering can only generate moves for known positions. At depth > 0 in the walk tree, positions exist only in superposition. Quantum predicates evaluate legality for all positions simultaneously. |
| Compile infrastructure: numpy qubit sets | Replace Python `set.update()` loops in `compile.py` (lines 843-890, 1125-1160) and `frozenset` intersection in `call_graph.py` with numpy bitset array operations | MEDIUM | These are hot paths during compilation of large functions like the move oracle. Numpy uint64 arrays with bitwise AND/OR/popcount eliminate per-element Python iteration overhead. Qubit indices are bounded integers (typically < 1000), fitting in a compact bitset. |
| Compiled predicate caching | The legality predicate is the same function called for every move candidate. `@ql.compile` should capture it once and replay for each enumerated move, amortizing compilation cost | MEDIUM | Requires the predicate to be parameterized by move index only (board qarrays and piece-type are structural). The factory pattern from `_make_apply_move` already demonstrates this approach. |
| T-count-aware predicate design | Design legality predicates to minimize Toffoli/T-gate count since they run inside the walk operator (called O(sqrt(T)) times by Montanaro's detection algorithm) | MEDIUM | Every extra T gate in the predicate multiplies by walk iterations. Use AND-ancilla MCX decomposition (already in v3.0) and minimize multi-controlled gates. The existing T-count reporting (v3.0) enables data-driven optimization. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full chess rule support (castling, en passant, pawn promotion) | Completeness | Massively inflates move enumeration and predicate complexity. Castling alone requires tracking whether king/rook have moved (additional state qubits). En passant requires move history register. Pawn promotion creates piece-type superposition. Scope explosion for marginal benefit in a KNK endgame demo. | Keep the KNK (kings + knights) piece set. Demonstrate the quantum predicate pattern; extending to full chess is a future module. |
| Measurement-based move legality (Google Quantum Chess style) | Google's approach is well-documented and uses iSWAP gates for movement | Measurement collapses superposition, destroying the quantum walk structure. Montanaro's algorithm requires the predicate to be reversible (no measurement). Measurement-based legality is fundamentally incompatible with backtracking walk operators R_A/R_B. | Fully reversible predicate oracles with ancilla-based computation and clean uncomputation. |
| Sliding piece attack detection (bishops, rooks, queens) | Natural extension of attack detection for check | Sliding pieces require ray-tracing along ranks/files/diagonals with blocking piece detection. This is O(7) checks per direction, 4-8 directions per piece, each requiring path-occupancy AND gates and ancilla chains. Qubit and gate count explodes. | Knights and kings only -- both have fixed, position-dependent attack sets computable with constant-depth circuits. No ray-tracing needed. |
| Dynamic piece count (variable number of knights) | Generality | The branch register width and move enumeration table size depend on the maximum possible move count, which depends on piece count. Variable piece counts mean variable circuit topology, breaking `@ql.compile` caching. | Fix piece count at circuit construction time. The factory pattern already handles this -- piece count is a classical parameter to the oracle factory. |
| Quantum board with piece-type encoding (log2 qubits per square) | Using log2(piece_types) qubits per square instead of separate qarrays per piece type for compactness | More compact encoding but makes predicate queries much harder. Checking "is there a white knight on square X?" requires decoding the piece-type register with ancillae and controlled operations. Separate qarrays allow direct single-qubit queries. | Keep the current separate-qarray-per-piece-type encoding from `chess_encoding.py`. Direct qbool access per square per piece type. |
| Quantum move generation for ALL 64 source squares | Enumerating moves from every square even when piece types have at most a few pieces | For 2 kings + N knights, most of the 64 squares are empty. Enumerating moves from all 64 sources creates 64 x 8 = 512 entries per piece type, mostly invalid. Wastes branch register width. | Enumerate moves only from squares that CAN contain a piece of the given type. For KNK: at most ~3 source squares for white (1 king + up to 2 knights), 1 for black king. The structural move table is still position-independent because piece-exists is checked quantumly. |

## Feature Dependencies

```
[Board encoding as qarrays] (EXISTING v6.1)
    |
    +---> [Quantum piece-exists predicate]
    |         |
    |         +---> [Quantum same-color-capture rejection]
    |         |         |
    |         |         +---> [Combined legality predicate]
    |         |
    |         +---> [Quantum check detection]
    |                   |
    |                   +---> [Combined legality predicate (with check)]
    |
    +---> [All-moves enumeration in circuit]
              |
              +---> [Knight move generation in superposition]
              |
              +---> [King move generation in superposition]
              |
              +---> [Reversible move application oracle] (EXISTING pattern v6.1)

[Combined legality predicate]
    +---> [Variable branching integration]
              +---> [Rewritten evaluate_children in chess_walk.py]
                        +---> [D_x local diffusion] (EXISTING v6.1, unchanged)

[Compile infrastructure: numpy qubit sets] (INDEPENDENT)
    +--enhances--> [All-moves enumeration] (faster compilation)
    +--enhances--> [Compiled predicate caching]
```

### Dependency Notes

- **Check detection requires move generation patterns:** To determine if a king is in check, you need to know what squares opponent pieces can attack. Knight attacks from a given square are fixed patterns (the 8 L-shaped offsets). King attacks are the 8 adjacent squares. Both can be precomputed as static lookup tables at circuit construction time, then the predicate checks if any opponent piece occupies one of those attacking squares.
- **All-moves enumeration is the foundation:** Every quantum legality feature builds on having a complete enumeration of structurally possible moves in the circuit. This is the first thing to build.
- **Numpy qubit sets are independent:** The compile infrastructure optimization has no dependency on chess features and can be built and tested in isolation. It directly benefits compilation speed of the larger move enumeration oracles.
- **Variable branching is the integration point:** The existing `evaluate_children` / `apply_diffusion` pattern in `chess_walk.py` already supports variable branching via validity ancillae. The real quantum predicates plug into the validity computation without changing the diffusion structure.
- **Check detection is additive:** The basic legality predicate (piece-exists AND no-friendly-capture) works without check detection. Check detection adds a third AND condition. It can be developed and tested independently, then composed into the combined predicate.

## MVP Definition

### Launch With (v8.0 core)

Minimum to demonstrate quantum move legality replacing classical pre-filtering.

- [ ] All-moves enumeration table -- precompute ALL structurally possible (src, dst) pairs for knights and kings at circuit construction time, assign branch register indices
- [ ] Quantum piece-exists predicate -- `@ql.compile` function checking `board_arr[src_rank, src_file]` for the appropriate piece-type qarray, storing result in validity ancilla
- [ ] Quantum same-color-capture rejection -- check no friendly piece on target square
- [ ] Combined legality predicate -- AND of piece-exists and no-friendly-capture, stored in per-move validity qbool
- [ ] Rewritten chess_walk.py -- `evaluate_children` calls the quantum predicate instead of the trivial "all valid" pattern
- [ ] Compile infrastructure numpy optimization -- replace `set.update()` loops with numpy bitset operations in compile.py and call_graph.py

### Add After Validation (v8.x)

Features to add once core quantum legality is proven correct.

- [ ] Quantum check detection -- after-move king safety check via quantum attack set computation (knight attacks + king adjacency)
- [ ] T-count optimization pass -- minimize T-gates in the legality predicate circuit
- [ ] Predicate compilation caching -- ensure the legality predicate compiles once and replays efficiently per move index

### Future Consideration (v9+)

- [ ] Extend to additional piece types (bishops, rooks, pawns) -- requires sliding piece attack detection
- [ ] Quantum evaluation function (material counting in superposition) -- deferred EVAL-01/EVAL-02
- [ ] Position-independent walk for deeper tree exploration beyond depth 2

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| All-moves enumeration in circuit | HIGH | MEDIUM | P1 |
| Quantum piece-exists predicate | HIGH | LOW | P1 |
| Quantum same-color-capture rejection | HIGH | LOW | P1 |
| Rewritten chess_walk.py with quantum predicates | HIGH | MEDIUM | P1 |
| Numpy qubit set operations in compile.py/call_graph.py | MEDIUM | MEDIUM | P1 |
| Quantum check detection (king safety) | HIGH | HIGH | P2 |
| Compiled predicate caching | MEDIUM | LOW | P2 |
| T-count-aware predicate design | MEDIUM | MEDIUM | P2 |
| Sliding piece attack detection | LOW | HIGH | P3 |
| Full chess rule support | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v8.0 launch
- P2: Should have, add in v8.x
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Google Quantum Chess (Cirq) | Queens Univ. Quantum Chess | This Project (v8.0) |
|---------|----------------------------|---------------------------|---------------------|
| Move legality | Measurement-based collapse; iSWAP gates for movement; pieces in superposition resolved by measurement | Classical rule engine with quantum state tracking | Reversible quantum predicate; no measurement; compatible with Montanaro walk operators |
| Superposition handling | 64-qubit board (one per square); piece-type not encoded quantumly | Per-square qubits | Separate qarrays per piece type (192 qubits for 3 piece types); structural clarity over qubit efficiency |
| Check detection | "All superpiece kings must be in check" -- measurement-based rule | Classical | Quantum predicate computing attack sets reversibly in superposition (P2 feature) |
| Move generation | Classical move generation + quantum execution (iSWAP) | Classical | Quantum enumeration of ALL structurally possible moves with quantum validity filtering via predicates |
| Uncomputation | Not needed (measurement-based game, not search algorithm) | Not applicable | Full reversible uncomputation required for walk operator compatibility (R_A/R_B) |
| Walk integration | None (interactive game, not optimization/search) | None | Montanaro backtracking walk with quantum predicates driving variable branching d(x) |

## Qubit Budget Analysis

Critical constraint: the 17-qubit Qiskit/Aer simulation limit (from project memory).

| Component | Qubits (minimal KNK) | Notes |
|-----------|----------------------|-------|
| Board qarrays (3 x 8x8 qbool) | 192 | White king + black king + white knights. Dominates qubit budget. |
| Height register (depth=2) | 3 | One-hot encoding for 3 levels (root + 2 depths) |
| Branch registers (2 levels) | ~8-10 | ceil(log2(move_count)) per level; move_count up to ~24 for KNK |
| Validity ancillae | ~16-24 per level | One per enumerated move at current depth |
| Predicate ancillae | ~2-4 per move check | piece-exists check, no-capture check, check detection temp |
| **Total** | **~230+** | Far exceeds 17-qubit simulation limit |

**Verification strategy (since simulation is infeasible for the full walk):**

1. **Unit test individual predicates on tiny boards** -- e.g., 2x2 or 3x3 board qarrays (4-9 qubits per piece type) with 1-2 move candidates. Verify via statevector simulation.
2. **Classical equivalence checking** -- for each position in the classical move table, verify that the quantum predicate produces the same validity result as `legal_moves_white`/`legal_moves_black`.
3. **Gate-level structure inspection** -- verify compiled predicate output has expected gate count, depth, and T-count without running simulation.
4. **Subsystem verification** -- test move application oracle, piece-exists predicate, and capture rejection independently before composing.
5. **Small-board integration test** -- reduce to 2x2 board with 1 king + 1 knight; full walk with quantum predicates fits in ~40-50 qubits (still above 17-qubit limit but verifiable with MPS simulator).

## Detailed Feature Specifications

### Quantum Piece-Exists Predicate

**Interface:**
```python
@ql.compile(inverse=True)
def piece_exists(piece_arr, src_rank, src_file, result_qbool):
    """Check if piece_arr[src_rank, src_file] == |1>.
    Store result in result_qbool via CNOT."""
    # CNOT from piece_arr[src_rank, src_file] to result_qbool
    with piece_arr[src_rank, src_file]:
        ~result_qbool  # flip result if piece exists
```

**Gate cost:** 1 CNOT per check. Trivially cheap.

### Quantum Same-Color-Capture Rejection

**Interface:**
```python
@ql.compile(inverse=True)
def no_friendly_capture(wk_arr, wn_arr, dst_rank, dst_file, result_qbool):
    """Check that no friendly piece occupies (dst_rank, dst_file).
    result_qbool = NOT(wk_arr[dst] OR wn_arr[dst])."""
    # Compute OR of all friendly piece types at destination
    # Use ancilla for intermediate OR
    temp = ql.qbool()
    with wk_arr[dst_rank, dst_file]:
        ~temp
    with wn_arr[dst_rank, dst_file]:
        ~temp  # temp = wk[dst] OR wn[dst] (via two CNOTs)
    # result = NOT temp
    ~result_qbool  # start at |1> (valid)
    with temp:
        ~result_qbool  # flip to |0> if any friendly piece present
```

**Gate cost:** ~4 CNOTs + ancilla. Still very cheap.

### Quantum Check Detection (king safety)

**Interface:**
```python
@ql.compile(inverse=True)
def king_not_in_check(opponent_king_arr, opponent_knight_arr,
                       my_king_rank, my_king_file, result_qbool):
    """Check that no opponent piece attacks (my_king_rank, my_king_file).

    For each attack pattern (8 king adjacents, 8 knight L-shapes):
    - Compute the attacking square coordinates
    - If on-board, check if opponent piece exists there
    - OR all attack results into a single 'in_check' ancilla
    - result_qbool = NOT in_check
    """
```

**Gate cost:** Up to 16 CNOT checks (8 king + 8 knight attack squares) + OR reduction. Moderate cost per move, but multiplied by move count.

**Key insight:** The attack square coordinates are computable classically at circuit construction time (they depend only on the king's destination square, which is part of the move table entry). Only the "is opponent piece at attack square?" check is quantum.

### All-Moves Enumeration

**Design:** At circuit construction time, precompute a static table of ALL structurally valid (piece_type, src_square, dst_square) triples:
- For each square that CAN contain a white knight: 8 L-shaped destinations (filtered for board bounds)
- For each square that CAN contain a white king: 8 adjacent destinations (filtered for board bounds)
- For each square that CAN contain a black king: 8 adjacent destinations (filtered for board bounds)

The "can contain" set is known at construction time from the initial position plus all possible positions reachable in the walk tree. For the KNK endgame with fixed piece count, this is all 64 squares for each piece type (worst case), but practically much smaller.

**Branch register:** Width = ceil(log2(total_moves)). For KNK: ~5 bits (up to 24 moves per side per position).

## Sources

- [Google Quantum Chess (Cirq)](https://quantumai.google/cirq/experiments/unitary/quantum_chess/concepts) -- iSWAP-based moves, measurement-based legality, controlled gates for blocking
- [Montanaro, "Quantum walk speedup of backtracking algorithms"](https://arxiv.org/abs/1509.02374) -- Predicate oracle interface P_x, walk operator structure, O(sqrt(T)) query complexity
- [Martiel, "Practical implementation of a quantum backtracking algorithm"](https://link.springer.com/chapter/10.1007/978-3-030-38919-2_49) -- Practical predicate oracle resource estimates, graph coloring implementation
- [Cantwell, Quantum Chess Documentation](https://cantwellc.github.io/QuantumChessDocs/rules.html) -- Full quantum chess rule set, split/merge moves
- [Knight Pattern - Chessprogramming wiki](https://www.chessprogramming.org/Knight_Pattern) -- Classical knight attack bitboard patterns (L-shaped offsets)
- [Square Attacked By - Chessprogramming wiki](https://www.chessprogramming.org/Square_Attacked_By) -- Classical attack detection algorithms
- [psitae/game-tree (GitHub)](https://github.com/psitae/game-tree) -- Quantum algorithm for game tree evaluation
- Existing codebase: `chess_encoding.py` (classical moves), `chess_walk.py` (walk operators), `walk.py` (QWalkTree), `compile.py` (set.update loops), `call_graph.py` (frozenset overlap)

---
*Feature research for: Quantum chess move legality in superposition*
*Researched: 2026-03-08*
