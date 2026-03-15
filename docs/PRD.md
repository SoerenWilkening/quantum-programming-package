# Quantum Assembly — Product Requirements Document

## 1. Product Vision

Quantum Assembly is a Python framework that enables developers to write quantum algorithms using familiar programming constructs — arithmetic operators, comparisons, conditionals — without ever touching quantum gates. The framework compiles this high-level code into optimized quantum circuits automatically.

**Current milestone**: Redesign the call graph to use execution-order edges and store gate counts on sequences, making the compilation pipeline ready for streaming execution and accurate resource estimation.

**Next milestone**: Extend the framework to solve classical two-player perfect-information games (chess) using quantum walk-based minimax tree evaluation, achieving a quadratic speedup over classical approaches.

---

## 2. Problem Statement

### 2.1 The Algorithm Verification Problem

Quantum algorithms that operate on real-world problem sizes (e.g., chess board evaluation) require hundreds or thousands of qubits. Classical simulation of quantum circuits is limited to ~17 qubits before becoming impractical. This creates a fundamental gap: **we cannot verify the correctness of the algorithms we write**.

Without a verification mechanism, developing complex quantum algorithms is effectively blind — bugs in predicates, move generation, or walk operators cannot be detected until real quantum hardware is available at sufficient scale.

### 2.2 The Algorithm Complexity Problem

Quantum algorithms for game tree evaluation exist in the literature (Montanaro 2015, Farhi/Gutmann 2007) but have never been implemented in a practical programming framework. The gap between theoretical descriptions and working code is significant: encoding game states, generating legal moves, constructing walk operators with variable branching, and composing these into a full minimax solver all require careful engineering.

---

## 3. Users

### 3.1 Primary User

Quantum algorithm researchers and developers who use the Quantum Assembly framework to design, implement, and test quantum algorithms.

### 3.2 User Expectations

- Write algorithm code once; it works in both quantum execution and classical verification modes without modification.
- Verify algorithm correctness at scale through classical sampling, with statistical confidence.
- Build complex quantum algorithms (game solvers) from composable, testable components.

---

## 4. Requirements

### P0 — Must Have

#### R1: Classical Verification Mode

The framework must support a classical execution mode where quantum algorithm code runs on concrete integer values without generating any quantum circuit.

| ID | Requirement |
|----|-------------|
| R1.1 | A framework-level API activates classical mode (e.g., context manager). User algorithm code is unchanged. |
| R1.2 | In classical mode, `qint` operations perform Python integer arithmetic with width-correct semantics (bit masking/truncation). |
| R1.3 | In classical mode, `qbool` context managers (`with` blocks) behave as classical `if` statements. |
| R1.4 | In classical mode, `qarray` operations perform element-wise classical computation. |
| R1.5 | Superposition points (Hadamard, branching) are replaced by random sampling with correct probabilities. |
| R1.6 | Classical mode does not allocate qubits, emit gates, or construct circuits. |
| R1.7 | The verification mode supports repeated runs (N samples) for statistical confidence. |

#### R2: Tic-Tac-Toe Game Engine

A complete quantum walk-based game solver for tic-tac-toe, serving as proof-of-concept and verification benchmark.

| ID | Requirement |
|----|-------------|
| R2.1 | Board state encoding using quantum registers (9 cells, 3 states each). |
| R2.2 | Move legality predicate: cell is empty, correct player's turn, game not over. |
| R2.3 | Win detection predicate: three-in-a-row for either player. |
| R2.4 | Legal move counting: quantum integer holding the number of valid moves. |
| R2.5 | Walk operator with conditional diffusion restricted to valid children only. |
| R2.6 | All predicates verifiable via classical verification mode (R1). |
| R2.7 | Late-game positions (2-3 empty cells) verifiable via quantum simulation within 17-qubit limit. |

#### R3: Walk Operator Correctness

The quantum walk operators must produce only legal game states.

| ID | Requirement |
|----|-------------|
| R3.1 | Walk operator enumerates candidate moves, evaluates legality, counts valid moves, and diffuses only over valid children. |
| R3.2 | Conditional diffusion applies rotation angles parameterized by the valid move count `k`. |
| R3.3 | All intermediate computations (legality flags, move count) are properly uncomputed. |
| R3.4 | Walk operators are verifiable via classical verification mode (property: no illegal moves generated, correct move counts). |

### P1 — Should Have

#### R4: Chess Game Engine

Extension of the game engine to classical chess.

| ID | Requirement |
|----|-------------|
| R4.1 | Board state encoding for 8x8 chess (piece types, positions). |
| R4.2 | Legal move generation for all piece types (pawns, knights, bishops, rooks, queens, kings). |
| R4.3 | Special move handling: castling, en passant, pawn promotion. |
| R4.4 | Check and checkmate detection. |
| R4.5 | Walk operator supporting up to ~218 legal moves per position. |
| R4.6 | All predicates verifiable via classical verification mode. |

#### R5: Minimax Evaluation

Full minimax tree evaluation using quantum walks.

| ID | Requirement |
|----|-------------|
| R5.1 | Min/max alternation tracking (whose turn it is at each tree level). |
| R5.2 | Terminal node evaluation (win/loss/draw). |
| R5.3 | Value propagation up the tree via the walk structure. |
| R5.4 | Height/depth register tracking current position in the game tree. |

#### R6: Property-Based Verification API

A structured API for defining and running verification checks.

| ID | Requirement |
|----|-------------|
| R6.1 | API for specifying an algorithm, a property to check, and a sample count. |
| R6.2 | Aggregated reporting: pass/fail counts, failure examples, confidence level. |
| R6.3 | Integration with standard testing frameworks (pytest). |

### P2 — Nice to Have

#### R7: Circuit Compilation Pipeline *(promoted from P2)*

Call graph-based compilation pipeline with accurate resource tracking.

| ID | Requirement | Status |
|----|-------------|--------|
| R7.1 | Call graph DAG tracks compiled operations with qubit sets and gate metadata. | **Done** |
| R7.2 | Tracking-only mode: count gates without simulating (no state vector). | **Done** |
| R7.3 | Gate counting on replay: cached sequences report correct counts. | **Done** |
| R7.4 | Cython operations wired to call graph recording during `@ql.compile`. | **Done** |
| R7.5 | Execution-order edges: edges represent sequential ordering, absence of edges means parallelism. Edge from A→B iff B runs after A and they share qubits. | **New** |
| R7.6 | Flat operation DAG: no wrapper/function nodes. Operations are direct DAG nodes. | **New** |
| R7.7 | Graph immutability: after capture, the call graph is frozen. Replay reads only. | **New** |
| R7.8 | Gate counts on sequences: `sequence_t` stores `total_gate_count`, computed at creation time. | **New** |
| R7.9 | Hardcoded counts: all precompiled/hardcoded sequences include correct gate counts. | **New** |
| R7.10 | Gate counts flow from C sequences through `_record_operation` into `DAGNode`. | **New** |

#### R8: Future Compilation Improvements

| ID | Requirement |
|----|-------------|
| R8.1 | Complete and working optimization flags (`opt=0`, `opt=1`, `opt=2`). |
| R8.2 | Streaming gate application (gates applied to QPU without full circuit storage). |

#### R9: Code Maintenance

General improvements to the existing codebase.

| ID | Requirement |
|----|-------------|
| R9.1 | Performance optimization of hot paths in gate emission. |
| R9.2 | Memory footprint reduction. |
| R9.3 | Stability improvements and edge case fixes. |
| R9.4 | Reduction of generated sequence file bloat. |

#### R10: Codebase Cleanup

| ID | Requirement |
|----|-------------|
| R10.1 | Remove dead code and unused modules. |
| R10.2 | Consolidate duplicated logic. |
| R10.3 | Standardize naming conventions across Python and C layers. |

---

## 5. Success Criteria

### 5.0 Call Graph & Compilation Pipeline

- 10 consecutive additions on the same integer produce exactly 10 edges (linear chain), not C(10,2) = 45 overlap edges.
- Operations on disjoint qubits produce parallel branches (no edges between them).
- An operation touching qubits from two independent branches produces edges to both (merge node).
- All nodes reachable from root.
- Graph is unchanged after replay of a compiled function.
- All sequences (including hardcoded) report non-zero gate counts that match actual gate content.
- DAGNode.gate_count is populated from sequence data, not hardcoded to 0.

### 5.1 Classical Verification Mode

- Tic-tac-toe predicates pass 10,000 classical verification runs with zero property violations.
- Classical verification results match independent classical tic-tac-toe engine on all tested positions.
- No measurable performance regression in quantum mode from the classical mode flag check.

### 5.2 Tic-Tac-Toe Engine

- Walk operator generates only legal moves (verified classically across all 9! / symmetry-reduced positions).
- Legal move counts match classical computation for every tested position.
- Win detection agrees with classical engine for every tested position.
- Late-game walk operators produce correct results under quantum simulation (within 17-qubit limit).

### 5.3 Chess Engine

- Walk operator generates only legal moves for all tested positions (verified classically).
- Move counts match a reference classical chess engine (e.g., python-chess) for all tested positions.
- Check/checkmate detection agrees with reference engine.

### 5.4 Minimax Solver

- Correctly solves tic-tac-toe (known solution: draw with optimal play from both sides).
- Produces correct evaluations for chess endgame positions with known tablebase solutions.

---

## 6. Scope & Non-Goals

### In Scope

- Classical execution mode for the existing `qint`/`qbool`/`qarray` type system.
- Quantum walk operators for game tree traversal.
- Tic-tac-toe and chess game encoding and predicates.
- Property-based verification of algorithm correctness.
- Minimax evaluation via quantum walks.

### Non-Goals

- Quantum simulation beyond 17 qubits (hardware limitation, not a software goal).
- Execution on real quantum hardware (future milestone).
- AI/heuristic evaluation functions (the solver is exact minimax, not approximate).
- Multiplayer or imperfect-information games.
- GUI or interactive play interface.
- Quantum advantage benchmarking (correctness first, performance later).

---

## 7. Technical Constraints

| Constraint | Impact |
|------------|--------|
| 17-qubit simulation ceiling | Cannot verify algorithms at scale via quantum simulation; classical verification mode is essential |
| Tic-tac-toe requires 18+ qubits | Even the simplest game exceeds simulation limits for full board states |
| Chess has ~218 max legal moves | Conditional diffusion must handle up to 218 rotation cases |
| Division/modulo requires classical divisor | Limits some encoding strategies |
| Existing QWalkTree untrusted | Walk operators must be built from scratch |

---

## 8. Milestones

### Milestone 0: Call Graph & Compilation Pipeline *(active)*

**Completed:**
- Call graph DAG (CallGraphDAG, DAGNode, rustworkx-backed)
- Tracking-only mode (gate counting without simulation)
- Gate counting on replay of cached sequences
- Cython operations wired to call graph recording

**In progress:**
- Execution-order edges (replace overlap edges with qubit-aware sequential edges)
- Flat operation DAG (remove wrapper/function nodes)
- Graph immutability after capture
- Gate counts stored on `sequence_t`, including hardcoded sequences
- Gate counts wired through `_record_operation` → `DAGNode`

### Milestone 1: Classical Verification Foundation

- Classical mode flag and `qint`/`qbool`/`qarray` classical execution
- Superposition sampling (coin flip at Hadamard points)
- Basic verification runner (N samples, property checking)

### Milestone 2: Tic-Tac-Toe Predicates

- Board encoding (9 cells, 2 qubits each)
- Move legality, win detection, move counting predicates
- Classical verification of all predicates
- Late-game quantum simulation tests

### Milestone 3: Walk Operator (Tic-Tac-Toe)

- Candidate move enumeration
- Legality evaluation and counting
- Conditional diffusion parameterized by valid move count
- Uncomputation of intermediate values
- Classical verification: walk produces only legal states

### Milestone 4: Tic-Tac-Toe Minimax

- Height/depth tracking
- Min/max alternation
- Terminal evaluation
- Full minimax walk composition
- Verify: correct solution (draw with optimal play)

### Milestone 5: Chess Predicates

- Board encoding for 8x8 chess
- Legal move generation for all piece types
- Special moves (castling, en passant, promotion)
- Check/checkmate detection
- Classical verification against python-chess

### Milestone 6: Chess Walk Operator & Minimax

- Walk operator scaled to chess branching factor
- Full minimax evaluation
- Endgame tablebase verification

---

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Classical mode misses bugs that only manifest in superposition | Medium | High | Complement with small-instance quantum simulation; test walk operators on tiny graphs |
| Walk operator with variable branching introduces subtle phase errors | Medium | High | Formal verification of rotation angles; cross-check with known small-instance results |
| Chess encoding requires too many qubits for any meaningful quantum simulation | High | Medium | Rely entirely on classical verification; validate approach on tic-tac-toe first |
| Performance overhead of classical mode flag check in quantum mode | Low | Low | Single boolean check per operation; benchmark to confirm negligible impact |
| Existing codebase issues (Tasks 1-2) block progress on Tasks 3 and 5 | Low | Medium | Tasks are independent; address blocking issues as encountered |

---

## 10. References

- Montanaro, A. (2015). "Quantum walk speedup of backtracking algorithms." arXiv:1509.02374
- Farhi, E., Goldstone, J., Gutmann, S. (2007). "A Quantum Algorithm for the Hamiltonian NAND Tree." arXiv:0702144
- Cleve, R., Gavinsky, D., Yonge-Mallo, D.L. (2008). "Quantum Algorithms for Evaluating MIN-MAX Trees." arXiv:0710.5794
- Grinko, D., Gacon, J., Zoufal, C., Woerner, S. (2021). "Iterative Quantum Amplitude Estimation." npj Quantum Information, 7(52)
