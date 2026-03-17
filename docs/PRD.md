# Quantum Assembly — Product Requirements Document

## 1. Product Vision

Quantum Assembly is a Python framework that enables developers to write quantum algorithms using familiar programming constructs — arithmetic operators, comparisons, conditionals — without ever touching quantum gates. The framework compiles this high-level code into optimized quantum circuits automatically.

**Current milestone**: Per-variable history graph and automatic uncomputation — replacing legacy layer-based uncomputation with per-variable history graphs, triggered by `__exit__`, `__del__`, and measurement. *(Completed)*

---

## 2. Problem Statement

### 2.1 The Compilation Pipeline Problem

As quantum algorithms grow in complexity, the compilation pipeline must accurately track resource usage (gate counts, qubit allocation) and expose parallelism opportunities. The previous call graph used overlap-based edges that scaled quadratically with operation count and did not reflect true execution ordering. Accurate gate counts were not propagated from the C backend through to the Python-level DAG.

---

## 3. Users

### 3.1 Primary User

Quantum algorithm researchers and developers who use the Quantum Assembly framework to design, implement, and test quantum algorithms.

### 3.2 User Expectations

- Write algorithm code using Python arithmetic and comparisons; the framework handles circuit generation.
- Accurate resource estimation (gate counts, qubit usage) from the compilation pipeline.
- Clear visualization of the operation DAG for debugging and optimization.

---

## 4. Requirements

### P0 — Must Have

#### R7: Circuit Compilation Pipeline

Call graph-based compilation pipeline with accurate resource tracking.

| ID | Requirement | Status |
|----|-------------|--------|
| R7.1 | Call graph DAG tracks compiled operations with qubit sets and gate metadata. | **Done** |
| R7.2 | Tracking-only mode: count gates without simulating (no state vector). | **Done** |
| R7.3 | Gate counting on replay: cached sequences report correct counts. | **Done** |
| R7.4 | Cython operations wired to call graph recording during `@ql.compile`. | **Done** |
| R7.5 | Execution-order edges: edges represent sequential ordering, absence of edges means parallelism. Edge from A→B iff B runs after A and they share qubits. | **Done** |
| R7.6 | Flat operation DAG: no wrapper/function nodes. Operations are direct DAG nodes. | **Done** |
| R7.7 | Graph immutability: after capture, the call graph is frozen. Replay reads only. | **Done** |
| R7.8 | Gate counts on sequences: `sequence_t` stores `total_gate_count`, computed at creation time. | **Done** |
| R7.9 | Hardcoded counts: all precompiled/hardcoded sequences include correct gate counts. | **Done** |
| R7.10 | Gate counts flow from C sequences through `_record_operation` into `DAGNode`. | **Done** |

#### R11: Automatic Uncomputation

Per-variable history graph system replacing legacy layer-based uncomputation.

| ID | Requirement | Status |
|----|-------------|--------|
| R11.1 | `HistoryGraph` data structure with append, reverse iteration, weakref children, discard. | **Done** |
| R11.2 | Arithmetic/comparison/bitwise operations record `(sequence_ptr, qubit_mapping, num_ancilla)` into result's history graph. | **Done** |
| R11.3 | `__exit__` uncomputes condition qbool's history in reverse, cascading to orphaned children via weakrefs. | **Done** |
| R11.4 | `__del__` triggers uncomputation when circuit is active; circuit-active guard prevents shutdown firing. | **Done** |
| R11.5 | Measurement discards history graph (collapsed qubits cannot be uncomputed). | **Done** |
| R11.6 | `atexit` hook sets `_circuit_active=False` to prevent `__del__` during interpreter shutdown. | **Done** |
| R11.7 | Legacy layer-based uncomputation (`_start_layer`, `_end_layer`, `_auto_uncompute`) removed. | **Done** |
| R11.8 | End-to-end integration tests covering all uncomputation triggers and edge cases. | **Done** |

#### R12: Quantum Walk Rework

Function-based quantum walk API replacing the monolithic QWalkTree class.

| ID | Requirement | Status |
|----|-------------|--------|
| R12.1 | `walk(is_marked, max_depth, num_moves, *, state, make_move, is_valid)` — builds `WalkConfig` with marking, allocates `WalkRegisters`, returns `(config, registers)`. All parameters required. Detection via phase estimation is a future milestone. | **Done** |
| R12.2 | `walk_diffusion(state, make_move, is_valid, num_moves)` — local diffusion building block. Single implementation path: always evaluates validity quantumly (no fixed-branching shortcut). | **Done** |
| R12.3 | User provides `make_move(state, move_index)` as `@ql.compile(inverse=True)` function. `move_index` is a classical int; the function uses DSL operations (arithmetic, XOR, `with`) — never raw gates. | **Done** |
| R12.4 | User provides `is_valid(state)` and `is_marked(state)` as quantum predicates returning `qbool`. | **Done** |
| R12.5 | Framework manages height register (one-hot), branch registers (one per depth), and count register internally. User never sees these. | **Done** |
| R12.6 | Counting loop: for each move index, apply move → check validity → increment count → undo move. Operates correctly across all computational basis states. | **Done** |
| R12.7 | Conditional branching: Montanaro rotation angles based on count value, creating uniform superposition over valid moves. Includes parent/self component for probability backflow. | **Done** |
| R12.8 | R_A / R_B walk operators: local diffusions at even/odd depths controlled on height register. walk_step = R_B * R_A. | **Done** |
| R12.9 | Detection via quantum phase estimation (Montanaro 2015, Theorem 1). Future milestone — `walk()` returns `(config, registers)` for now. | |
| R12.10 | XOR-based state manipulation replaces raw qubit index manipulation (e.g., `x ^= value` instead of `emit_x(qubit_idx)`). | **Done** |
| R12.11 | Old `QWalkTree` class and `walk.py` removed entirely, along with all associated test files. | **Done** |
| R12.12 | Each implementation file ≤ 400 LOC. | **Done** |
| R12.13 | Correctness verified on tiny problems (≤ 17 qubits) via Qiskit simulation. | **Done** |
| R12.14 | `is_marked` evaluated quantumly, returning `qbool`. Marking = identity (D_x = I for marked nodes per Montanaro 2015). Works with variable-branching diffusion via controlled XOR (Toffoli). | **Done** |
| R12.15 | `walk_operators.py` composes `walk_diffusion.py` — no reimplementation of diffusion logic in the operator layer. | **Done** |
| R12.16 | Single diffusion implementation: variable-branching only. No `_fixed_diffusion` path — fixed branching converges to plain Grover's (use `ql.grover()` for that). | |
| R12.17 | Marking integrated with variable-branching path: `with ~marked:` wraps the variable diffusion call. No separate marking dispatch. | |

#### R13: Quantum Walk Skill

Claude Code skill (`/quantum-walk`) for guided development of walk functions.

| ID | Requirement | Status |
|----|-------------|--------|
| R13.1 | Structured discussion phase: state, moves, validity, marking, parameters. | |
| R13.2 | Quantum function generation following DSL rules (`with` vs `if`, `@ql.compile(inverse=True)`, XOR idioms). | |
| R13.3 | Automatic classical equivalent generation (with→if, qint→int, qbool→bool). | |
| R13.4 | CC-as-oracle verification loop: generate scenarios, run classical equivalents, CC judges correctness. Monte Carlo coverage with k≥20 random inputs. | |
| R13.5 | Independent verifier agent; flags user only for exotic/custom problems. | |
| R13.6 | Idiom library: ternary assignment, XOR-based modification, counting, compound validity, all-assigned check. Extensible over time. | |

#### R14: DSL Purity & Simulate-Mode Cleanup

Eliminate all local `simulate` toggles and raw gate patterns from walk modules. The `simulate` option is global — internal helpers must never toggle it.

| ID | Requirement | Status |
|----|-------------|--------|
| R14.1 | `simulate` is a global option only. Remove all local `option('simulate', ...)` toggles from `_flip_all`, `diffusion()` wrapper, and any other internal helper. Tests that need QASM output must set `ql.option('simulate', True)` in their fixture. | |
| R14.2 | Controlled-AND support: `&` operator inside `with` blocks (controlled context) must work. Implement via C-CCX decomposition (Toffoli + ancilla). Currently raises `NotImplementedError`. | |
| R14.3 | Replace `_flip_all` single-register calls with `^= 1` or `~reg` directly. Keep `_flip_all` only as multi-register convenience (without simulate toggle). | |
| R14.4 | Replace `_nested_phase_flip` and `_apply_nested_with` (recursive nested `with` loops) with flat `&`-chain pattern. Depends on R14.2. | |
| R14.5 | Raise test qubit budget from 17 to 21. Statevector simulation at 21 qubits takes ~0.2s (2M amplitudes), well within acceptable limits. | |
| R14.6 | `qarray.all()` primitive for multi-controlled operations (future optimization): replace manual `&`-chain loops with internal AND-reduction. Fewer allocations, potential gate-level optimization. | |

### P1 — Should Have

#### R8: Future Compilation Improvements

| ID | Requirement |
|----|-------------|
| R8.1 | Complete and working optimization flags (`opt=0`, `opt=1`, `opt=2`). |
| R8.2 | Streaming gate application (gates applied to QPU without full circuit storage). |

### P2 — Nice to Have

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

### 5.1 Quantum Walk Rework

- `ql.walk()` returns `(config, registers)` for use with `walk_step`. Detection via phase estimation is a future milestone.
- `ql.walk_diffusion()` satisfies reflection property: D² = I (statevector amplitude tolerance ~1e-6).
- Counting loop produces correct valid-child count across superposition of basis states.
- R_A and R_B operate on disjoint height register qubits (even vs odd depths).
- walk_step = R_B * R_A compiles and replays correctly (gate sequence cached).
- Old `walk.py` and all associated test files removed.
- All test circuits use ≤ 21 qubits (raised from 17; 21-qubit statevector simulation ~0.2s).
- No implementation file exceeds 400 LOC.
- `/quantum-walk` skill produces correct quantum functions with passing verification loop.
- Marking is quantum: `is_marked(state)` returns `qbool`, diffusion applied only to unmarked nodes (`with ~marked:`). No classical enumeration.
- No `emit_x` in walk modules — all state manipulation via DSL operators.
- `walk_operators.py` calls into `walk_diffusion.py` — no duplicated diffusion logic.
- Single diffusion path: variable-branching only. No fixed-branching shortcut.
- `walk()` requires `state`, `make_move`, `is_valid` — no optional-but-actually-needed parameters.

---

## 6. Scope & Non-Goals

### In Scope

- Call graph-based compilation pipeline with execution-order edges and gate count tracking.
- Tracking-only mode for resource estimation without simulation.
- Graph immutability after capture for safe replay.
- Function-based quantum walk API (`walk`, `walk_diffusion`) with user-provided move/validity/marking functions.
- Claude Code skill for guided quantum walk development with CC-as-oracle verification.
- Future: optimization flags and streaming gate application.

### Non-Goals

- Quantum simulation beyond 17 qubits (hardware limitation, not a software goal).
- Execution on real quantum hardware (future milestone).
- GUI or interactive interface.
- Quantum advantage benchmarking (correctness first, performance later).

---

## 7. Technical Constraints

| Constraint | Impact |
|------------|--------|
| 17-qubit simulation ceiling | Cannot verify algorithms at scale via quantum simulation |
| Division/modulo requires classical divisor | Limits some encoding strategies |

---

## 8. Milestones

### Milestone 0: Call Graph & Compilation Pipeline *(completed)*

- Call graph DAG (CallGraphDAG, DAGNode, rustworkx-backed)
- Tracking-only mode (gate counting without simulation)
- Gate counting on replay of cached sequences
- Cython operations wired to call graph recording
- Execution-order edges (replace overlap edges with qubit-aware sequential edges)
- Flat operation DAG (remove wrapper/function nodes)
- Graph immutability after capture
- Gate counts stored on `sequence_t`, including hardcoded sequences
- Gate counts wired through `_record_operation` → `DAGNode`

### Milestone 1: Per-Variable History Graph & Automatic Uncomputation *(completed)*

- `HistoryGraph` class with `(sequence_ptr, qubit_mapping, num_ancilla)` entries and weakref children
- Operations record history on result qint/qbool (arithmetic, comparison, bitwise)
- `__exit__` uncomputes condition qbool history in reverse, cascading to orphaned children
- `__del__` triggers uncomputation mid-circuit with circuit-active guard
- Measurement discards history (collapsed qubits)
- `atexit` shutdown guard prevents `__del__` during interpreter shutdown
- Legacy layer-based uncomputation removed (`_start_layer`, `_end_layer`, `_auto_uncompute`)
- End-to-end integration tests across all uncomputation triggers

### Milestone 2: Quantum Walk Rework — Initial Implementation *(completed, needs bug fixes)*

- Function-based walk API: `ql.walk()` and `ql.walk_diffusion()` replace monolithic `QWalkTree`
- User provides `make_move`, `is_valid`, `is_marked` as quantum functions using DSL
- Framework manages height register, branch registers, counting, Montanaro diffusion angles
- Counting loop: apply-check-undo per move, in superposition across all basis states
- Conditional branching with parent/self component for probability backflow
- R_A/R_B walk operators, walk_step = R_B * R_A
- Claude Code skill (`/quantum-walk`) for guided quantum walk function development
- Correctness verified on tiny (≤ 17 qubit) problems via simulation

### Milestone 2b: Quantum Walk Bug Fixes *(completed)*

Fixed correctness bugs discovered during review of the initial walk implementation:

- **Quantum marking**: Replaced classical `is_marked` evaluation with quantum evaluation: `is_marked(state)` returns `qbool`, marking = identity (D_x = I per Montanaro 2015)
- **Remove `emit_x`**: Replaced all `emit_x(qubit_idx)` with DSL equivalents via `_flip_all` helper
- **Remove classical detection**: Removed simulation-based overlap detection; `walk()` returns `(config, registers)` for manual walk step iteration. Phase estimation detection is a future milestone.
- **Deduplicate operators**: `walk_operators.py` now composes `walk_diffusion.py` via `control_qubit` parameter
- **Remove `walk.py`**: Deleted the deprecated `QWalkTree` class and all associated test files
- **Rewrite `walk_search.py`**: `walk()` builds `WalkConfig` with `is_marked` and returns `(config, registers)`

### Milestone 2c: Unify Diffusion Path *(current)*

Simplifies the walk implementation by removing the fixed-branching diffusion path and unifying on variable-branching diffusion as the single implementation:

- **Remove `_fixed_diffusion`**: The fixed-branching path assumes all `num_moves` children are always valid (classical `int d`). This is only correct for perfectly regular trees with no pruning — but the whole point of backtracking is pruning via `is_valid`. The fixed case converges to plain Grover's algorithm, which already has `ql.grover()`. Remove `_fixed_diffusion`, `walk_diffusion_fixed`, and `_apply_fixed_diffusion`.
- **Marking on variable-branching path**: Remove the warning that marking is ignored in variable branching. Controlled XOR inside `with ~marked:` decomposes to Toffoli gates, which the framework handles natively. Wrap `_variable_diffusion` with `with ~marked:` in `_apply_local_diffusion`.
- **Require `state`, `make_move`, `is_valid` in `walk()`**: These are no longer optional. Every walk needs a state register and move/validity callbacks. Simplifies the API and removes the three-way dispatch.
- **Test consolidation**: Remove fixed-branching tests, update marking tests to use variable branching. Net LOC reduction in both implementation and tests.

---

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Performance overhead of flag checks in quantum mode | Low | Low | Single boolean check per operation; benchmark to confirm negligible impact |

---

## 10. References

- Grinko, D., Gacon, J., Zoufal, C., Woerner, S. (2021). "Iterative Quantum Amplitude Estimation." npj Quantum Information, 7(52)
- Montanaro, A. (2018). "Quantum speedup of backtracking algorithms." Theory of Computing. (arXiv:1509.02374)
- Gavinsky, D., et al. "Quantum Walks for Min-Max Evaluation." (for adversarial/two-player game tree search)
