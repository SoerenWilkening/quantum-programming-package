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
| R12.16 | Single diffusion implementation: variable-branching only. No `_fixed_diffusion` path — fixed branching converges to plain Grover's (use `ql.grover()` for that). | **Done** |
| R12.17 | Marking integrated with variable-branching path: `with ~marked:` wraps the variable diffusion call. No separate marking dispatch. | **Done** |

#### R13: Quantum Walk Skill

Claude Code skill (`/quantum-walk`) for guided development of walk functions.

| ID | Requirement | Status |
|----|-------------|--------|
| R13.1 | Structured discussion phase: state, moves, validity, marking, parameters. | **Done** |
| R13.2 | Quantum function generation following DSL rules (`with` vs `if`, `@ql.compile(inverse=True)`, XOR idioms). | **Done** |
| R13.3 | Automatic classical equivalent generation (with→if, qint→int, qbool→bool). | **Done** |
| R13.4 | CC-as-oracle verification loop: generate scenarios, run classical equivalents, CC judges correctness. Monte Carlo coverage with k≥20 random inputs. | **Done** |
| R13.5 | Independent verifier agent; flags user only for exotic/custom problems. | **Done** |
| R13.6 | Idiom library: ternary assignment, XOR-based modification, counting, compound validity, all-assigned check. Extensible over time. | **Done** |

#### R14: DSL Purity & Simulate-Mode Cleanup

Eliminate all local `simulate` toggles and raw gate patterns from walk modules. The `simulate` option is global — internal helpers must never toggle it.

| ID | Requirement | Status |
|----|-------------|--------|
| R14.1 | `simulate` is a global option only. Remove all local `option('simulate', ...)` toggles from `_flip_all`, `diffusion()` wrapper, and any other internal helper. Tests that need QASM output must set `ql.option('simulate', True)` in their fixture. | **Done** |
| R14.2 | Controlled-AND support: `&` operator inside `with` blocks (controlled context) must work. Implement via C-CCX decomposition (Toffoli + ancilla). Currently raises `NotImplementedError`. | **Done** |
| R14.3 | Replace `_flip_all` single-register calls with `^= 1` or `~reg` directly. Keep `_flip_all` only as multi-register convenience (without simulate toggle). | **Done** |
| R14.4 | Replace `_nested_phase_flip` and `_apply_nested_with` (recursive nested `with` loops) with flat `&`-chain pattern. Depends on R14.2. | **Done** |
| R14.5 | Raise test qubit budget from 17 to 21. Statevector simulation at 21 qubits takes ~0.2s (2M amplitudes), well within acceptable limits. | **Done** |
| R14.6 | `qarray.all()` primitive for multi-controlled operations (future optimization): replace manual `&`-chain loops with internal AND-reduction. Fewer allocations, potential gate-level optimization. | |

#### R15: In-Place Comparison Operators

Replace copy-based `<`, `>`, `<=`, `>=` with in-place borrow-ancilla pattern. Eliminates widened temporary copies and reduces qubit overhead.

| ID | Requirement | Status |
|----|-------------|--------|
| R15.1 | `__lt__` and `__gt__` use borrow-ancilla pattern: allocate single ancilla as (n+1)th bit, perform (n+1)-bit subtraction across `[a, ancilla]`, extract borrow into result qbool, restore via addition, deallocate ancilla. No operand copies. | **Done** |
| R15.2 | `__le__` and `__ge__` automatically benefit (implemented as `~(a > b)` / `~(a < b)`). | **Done** |
| R15.3 | Arithmetic backend supports subtraction/addition across a qint + separate qbool as a split register (qbool acts as MSB). | **Done** |
| R15.4 | No history graph children for comparison temporaries — borrow ancilla is deallocated immediately. | **Done** |
| R15.5 | Both operands unchanged after comparison (operand preservation). | **Done** |

#### R16: Compiled Function Control Propagation

Rework `@ql.compile` pipeline to decouple sequence generation from execution, ensuring correct control propagation from `with` blocks on every call (including the first).

| ID | Requirement | Status |
|----|-------------|--------|
| R16.1 | Standardized gate sequences: virtual index 0 reserved for control qubit in all sequences. Uncontrolled sequences do not reference index 0. Controlled sequences add index 0 as control to each gate. | **Done** |
| R16.2 | Both controlled and uncontrolled gate sequences stored per instruction for correct execution in either context. | **Done** |
| R16.3 | Compile phase: function body executes, DSL operators trigger sequence generation (`CQ_add` etc.) but `run_instruction` is NOT called. Instructions stored as IR: `(name, registers, uncontrolled_seq, controlled_seq)`. | **Done** |
| R16.4 | Execute phase: walk instruction IR, call `run_instruction` with qubit mapping. If inside `with` block, map index 0 to control qubit to select controlled sequence. | **Done** |
| R16.5 | Nested `with` blocks collapse to single control via AND-ancilla (Toffoli). Single control slot (index 0) suffices for all nesting depths. | **Done** |
| R16.6 | Compiled flag prevents recompilation on subsequent calls. | **Done** |
| R16.7 | `param_qubit_ranges` uses `(start, end)` format (not `(start, width)`). | **Done** |
| R16.8 | `opt=1` (DAG-only) mode respects the new pipeline and control context. | **Done** |
| R16.9 | Compile replay path (cache hit) inside `with` blocks correctly executes controlled gates, producing non-zero results when conditions are True. | **Done** |
| R16.10 | Stale tests updated to match current behavior: first-call trade-off test reflects that first call is now controlled; `qint` default width test matches auto-width semantics. | **Done** |
| R16.11 | Call graph built once per compiled function — not duplicated on subsequent calls. Each instruction node stores both uncontrolled and controlled gate counts; display format `"gates: 24 / 18"` with `"-"` for unavailable variant. **Bug**: In Toffoli mode, `record_operation` populates `gate_count` but not `uncontrolled_gate_count`/`controlled_gate_count`, so `report()` shows `"- / -"` while `aggregate()` total is correct. | |
| R16.12 | `opt=1` uncontrolled replay injects gates when `simulate=True`. Gate injection skip only applies in tracking-only mode (`simulate=False`). | **Done** |
| R16.13 | Toffoli-mode gate count propagation: `record_operation` populates `uncontrolled_gate_count` when outside `with` block, `controlled_gate_count` when inside. Depth and T-count computed before sequence is freed. | |

#### R17: History Graph Inverse Cancellation

Detect and cancel manual uncomputation in the history graph, avoiding redundant inverse gates.

| ID | Requirement | Status |
|----|-------------|--------|
| R17.1 | Tail-only matching: when an operation is the exact inverse of the last history entry and no active blockers exist, cancel both entries. | |
| R17.2 | Supported inverse pairs: `+= k` / `-= k`, `^= x` / `^= x` (self-inverse), `f()` / `f.inverse()` (matched by sequence pointer). | |
| R17.3 | Blocker mechanism: when a qint is used as a source operand (RHS), a blocker is added to its history referencing the dependent qint. | |
| R17.4 | Blockers cleared on qubit deallocation (uncomputation) of the dependent qint, not on Python GC. Explicit notification mechanism. | |
| R17.5 | No cancellation if active blockers exist after the last history entry. Operation added as normal entry instead. | |
| R17.6 | `*= k` / `//= k` inverse cancellation deferred to future work. | |

#### R18: Compile Module Refactoring

Split the monolithic `compile.py` (2,293 lines) into a `compile/` subpackage with modules ≤ 500–600 lines.

| ID | Requirement | Status |
|----|-------------|--------|
| R18.1 | `compile.py` replaced by `compile/` subpackage. Public API (`@ql.compile` decorator) unchanged. All existing imports continue to work. | |
| R18.2 | Each module in the subpackage ≤ 600 lines. No circular imports. | |
| R18.3 | Logical separation: block types, optimization helpers, virtual mapping, capture, replay, parametric lifecycle, inverse proxies each in their own module. | |
| R18.4 | All existing tests pass without modification (pure refactor, no behavioral change). | |

#### R19: Compiled Function Ancilla Model

Fix the compile layer's ancilla tracking to distinguish transient ancillas (managed by the C layer) from result qubits (new qints returned to the caller).

| ID | Requirement | Status |
|----|-------------|--------|
| R19.1 | During capture, classify non-parameter qubits into two categories: **result qubits** (part of the return value, still allocated when capture completes) and **transient ancillas** (freed by the C layer during the operation). | |
| R19.2 | IR replay path (`_execute_ir`): only allocate fresh qubits for parameter and result virtual indices. Do not allocate for transient ancilla virtual indices — the C layer's `run_instruction` manages its own ancillas internally. | |
| R19.3 | Gate-level replay path (`inject_remapped_gates`): allocate all virtual qubits as before (gates reference them directly). Free transient ancillas after injection since the gates return them to \|0⟩. | |
| R19.4 | Repeated calls to a compiled function do not grow the total qubit count when the function has no result qubits (e.g., in-place addition). | |
| R19.5 | Compiled functions that return new qints (e.g., `c = a * b`) correctly allocate fresh result qubits on each replay. | |

#### R20: Hierarchical Compiled Function References

When a compiled function calls another compiled function during capture, store a reference instead of inlining the inner function's gates.

| ID | Requirement | Status |
|----|-------------|--------|
| R20.1 | New IR entry type (`CallRecord`) stores a reference to the inner `CompiledFunc` and the argument mapping, rather than inlining the inner function's gate sequence. | |
| R20.2 | Replay of an outer compiled function recursively delegates to the inner function's `_replay`, with transitive virtual-to-real qubit mapping. | |
| R20.3 | Each compiled function's `CompiledBlock` contains only its own gates and call references — not the flattened gates of all nested functions. | |
| R20.4 | Visualization: each compiled function produces its own sub-diagram. Top-level view shows the call graph with links to sub-diagrams. | |
| R20.5 | Gate counts for hierarchical functions are computed recursively (sum of own gates + referenced function gate counts). | |

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

### 5.0b In-Place Comparisons

- `a < b` and `a > b` allocate at most 1 ancilla qubit (borrow bit), not 2×(n+1)-bit temporary copies.
- Both operands are unchanged after comparison (statevector verification).
- No history graph children created for comparison temporaries.
- Gate count reduced compared to copy-based approach.
- All existing comparison tests pass with identical results.

### 5.0c Compiled Function Control Propagation

- All gate sequences reserve virtual index 0 for the control qubit. Uncontrolled sequences never reference index 0.
- Calling a compiled function inside `with ctrl:` produces a different gate sequence than calling it uncontrolled — including on the first call (no "first call emits uncontrolled" trade-off).
- Compile phase records instruction-level IR without calling `run_instruction`. Execute phase walks the IR and calls `run_instruction` with the correct control context.
- Both controlled and uncontrolled sequences stored per instruction.
- Nested `with c1: with c2: f(x)` produces correct combined-controlled gates via AND-ancilla; single control slot suffices.
- `opt=1` mode correctly handles the new pipeline and control context.

### 5.0c-fix Compile Replay Bug Fixes

- Compiled function replayed (cache hit) inside single `with c(True):` block produces correct result (result=1, not 0).
- Compiled function replayed inside nested `with c1(True): with c2(True):` produces correct result (result=1).
- Compiled function replayed inside 3-level nesting with all conditions True produces correct result.
- Replay produces non-zero gate count for all function sizes (small, medium, large).
- `test_first_call_trade_off` updated: with c2=False on first call, result=0 (controlled execution, trade-off resolved).
- `test_qint_default_width` updated: `ql.qint(5).width == 3` (auto-width).
- All 6 previously failing tests pass.

### 5.0c-fix2 Call Graph Deduplication & Simulate Replay

- Call graph is built once per compiled function on first call. Subsequent calls (controlled or uncontrolled) do NOT append additional nodes.
- Each instruction node stores both `uncontrolled_seq` and `controlled_seq` pointers, with gate counts resolved from `sequence_t.total_gate_count`.
- `to_dot()` and `report()` display both gate counts: `"gates: 24 / 18"` (uncontrolled / controlled). `"-"` shown when a variant's sequence pointer is 0 (unavailable).
- In Toffoli mode, `record_operation` populates `uncontrolled_gate_count` (or `controlled_gate_count` when inside `with`) so the DAG report shows actual counts, not `"- / -"`.
- With `simulate=True`, all compiled function replays inject gates into the circuit — including uncontrolled calls. Gate injection skip restricted to `simulate=False` (tracking-only mode).
- Calling `foo(a, b)` three times with `simulate=True` produces gates in the circuit for all three calls.

### 5.0d History Graph Inverse Cancellation

- `a += 3; a -= 3` results in empty history for `a`.
- `a ^= 5; a ^= 5` results in empty history for `a`.
- `f(a); f.inverse(a)` results in empty history for `a`.
- `a += 3; b += a; a -= 3` does NOT cancel (blocker from `b` is active).
- `a += 3; b += a; del b; a -= 3` DOES cancel (blocker cleared on `b`'s deallocation).
- No cancellation attempted for `*=` / `//=`.

### 5.1a Compile Module Refactoring

- `compile.py` no longer exists as a single file; replaced by `compile/` subpackage.
- `from quantum_language.compile import CompiledFunc` and `@ql.compile` continue to work (backward-compatible public API).
- Every module in `compile/` is ≤ 600 lines.
- No circular imports between subpackage modules.
- All existing compile-related tests pass without modification.

### 5.1b Compiled Function Ancilla Model

- Calling `foo(a, b)` three times (where `foo` does only in-place additions) does NOT increase total qubit count beyond the first call's allocation.
- Calling `bar(a, b)` that returns `c = a * b` correctly allocates fresh result qubits on each replay.
- IR replay path does not allocate qubits for transient ancillas (carry bits, temp registers) — only for parameters and result qubits.
- Gate-level replay path allocates all virtual qubits and frees transients after injection.
- `block.total_virtual_qubits` is split into `param_virtual_count`, `result_virtual_count`, and `transient_virtual_count`.

### 5.1c Hierarchical Compiled Function References

- Wrapping `walk_step` in a compiled function does not cause memory explosion.
- Outer compiled function's `CompiledBlock` contains `CallRecord` entries for inner compiled functions, not their flattened gates.
- Replay of outer function delegates to inner function's `_replay` recursively.
- Each compiled function's gate count in the DAG is its own gates + sum of referenced function gate counts (recursive).
- Visualization produces per-function sub-diagrams linked from the top-level call graph.

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
- Compile module refactoring: `compile.py` → `compile/` subpackage (≤ 600 LOC per module).
- Compiled function ancilla model: distinguish transient ancillas from result qubits.
- Hierarchical compiled functions: nested calls stored as references, not inlined.
- Future: optimization flags and streaming gate application.

### Non-Goals

- Quantum simulation beyond 21 qubits (hardware limitation, not a software goal).
- Execution on real quantum hardware (future milestone).
- GUI or interactive interface.
- Quantum advantage benchmarking (correctness first, performance later).

---

## 7. Technical Constraints

| Constraint | Impact |
|------------|--------|
| 21-qubit simulation ceiling | Cannot verify algorithms at scale via quantum simulation |
| Division/modulo requires classical divisor | Limits some encoding strategies |
| Arithmetic backend assumes contiguous registers | Split-register operations (qint + qbool as MSB) implemented for in-place comparisons |
| Gate sequences use variable control index | Standardization to index 0 required for compile pipeline rework (Phase 5) |
| Compile layer conflates transient and result ancillas | IR replay double-allocates C-managed ancillas; each compiled function replay grows qubit count |
| Nested compiled functions inline inner gates | Memory explosion when wrapping complex functions (e.g., walk_step) in a compiled function |

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

### Milestone 2c: Unify Diffusion Path *(completed)*

Simplifies the walk implementation by removing the fixed-branching diffusion path and unifying on variable-branching diffusion as the single implementation:

- **Remove `_fixed_diffusion`**: The fixed-branching path assumes all `num_moves` children are always valid (classical `int d`). This is only correct for perfectly regular trees with no pruning — but the whole point of backtracking is pruning via `is_valid`. The fixed case converges to plain Grover's algorithm, which already has `ql.grover()`. Remove `_fixed_diffusion`, `walk_diffusion_fixed`, and `_apply_fixed_diffusion`.
- **Marking on variable-branching path**: Remove the warning that marking is ignored in variable branching. Controlled XOR inside `with ~marked:` decomposes to Toffoli gates, which the framework handles natively. Wrap `_variable_diffusion` with `with ~marked:` in `_apply_local_diffusion`.
- **Require `state`, `make_move`, `is_valid` in `walk()`**: These are no longer optional. Every walk needs a state register and move/validity callbacks. Simplifies the API and removes the three-way dispatch.
- **Test consolidation**: Remove fixed-branching tests, update marking tests to use variable branching. Net LOC reduction in both implementation and tests.

### Milestone 2d: DSL Purity & Simulate-Mode Cleanup *(completed)*

- Removed all local `option('simulate', ...)` toggles from internal helpers
- Implemented controlled-AND (`&` inside `with` blocks) via C-CCX decomposition
- Replaced single-register `_flip_all` calls with `^= 1` / `~` DSL operators
- Replaced recursive nested `with` patterns with flat `&`-chain + single `with combined:` block
- Raised test qubit budget from 17 to 21

### Milestone 3: In-Place Comparison Operators *(completed)*

- Extended arithmetic backend with split-register subtraction/addition (qint + separate qbool as MSB)
- Rewrote `__lt__` and `__gt__` in `qint_comparison.pxi` to use borrow-ancilla pattern
- Removed widened temporary copy logic and history graph child tracking for comparisons
- Verified operand preservation and result correctness via statevector simulation

### Milestone 4: Compiled Function Control Propagation *(completed)*

Rework `@ql.compile` pipeline to decouple sequence generation from execution:

- **Step 1 — Standardize gate sequences**: Reserve virtual index 0 for control qubit. All sequences use a standardized layout where index 0 is the control slot. Uncontrolled sequences don't reference it; controlled sequences add it as control on each gate. `param_qubit_ranges` switched to `(start, end)` format.
- **Step 2 — Decouple compile from execute**: Compile phase runs the function body — DSL operators trigger sequence generation (`CQ_add` etc.) but do NOT call `run_instruction`. Instructions stored as IR: `(name, registers, uncontrolled_seq, controlled_seq)`. Execute phase walks the IR, calls `run_instruction` with qubit mapping, injecting control via index 0 when inside `with` block. Compiled flag prevents recompilation.
- First call inside `with` block now produces controlled gates (no uncontrolled-first-call trade-off)
- Nested `with` blocks work via AND-ancilla with single control slot
- `opt=1` DAG integration builds DAG nodes from instruction IR with control metadata

### Milestone 4b: Compile Replay Bug Fixes *(completed)*

Fixes correctness bugs in the compile replay path and updates stale test assertions after Phase 5:

- **Replay inside `with` blocks**: Fixed `_replay` to route through `_execute_ir` when IR entries exist, correctly handling controlled sequences. Gate count double-counting fixed via `_last_replay_used_ir` flag. opt=1 DAG-only replay skip restored for uncontrolled contexts while preserving gate injection for controlled contexts.
- **Stale first-call trade-off test**: Updated to expect `result=0` (first call now correctly controlled after Phase 5).
- **Stale qint default width test**: Updated to expect `width=3` (auto-width for value 5).

### Milestone 4c: Call Graph Deduplication & Simulate Replay

Fixes call graph duplication on repeated calls, incorrect gate injection skip with `simulate=True`, and Toffoli-mode gate count propagation:

- **Call graph built once**: `_build_dag_from_ir` only runs on first call/capture. Each DAGNode stores both `uncontrolled_seq` and `controlled_seq` pointers. Gate counts resolved from `sequence_t.total_gate_count` via Cython helper.
- **Dual gate count display**: `to_dot()` and `report()` show `"gates: 24 / 18"` (uncontrolled / controlled), `"-"` for unavailable variants.
- **Toffoli-mode gate count fix**: `record_operation` populates `uncontrolled_gate_count` (or `controlled_gate_count` when inside `with`) so the DAG report shows actual counts instead of `"- / -"`. Depth and T-count computed from sequence before it is freed.
- **Simulate=True replay fix**: Gate injection skip (`_skip_injection`) restricted to `simulate=False`. With `simulate=True`, all replays (including uncontrolled) inject gates into the circuit.

### Milestone 5: History Graph Inverse Cancellation

Detect and cancel manual uncomputation in the history graph:

- Add blocker mechanism: source operand usage adds blockers referencing dependent qints
- Blockers cleared on qubit deallocation (explicit notification, not Python GC)
- Tail-only cancellation for `+=`/`-=`, `^=` self-inverse, `f()`/`f.inverse()` pairs
- `*=`/`//=` deferred to future work

### Milestone 6: Compile Module Refactoring

Split the monolithic `compile.py` (2,293 lines) into a `compile/` subpackage:

- **Subpackage structure**: `compile/__init__.py` (public API), `_block.py` (CompiledBlock, InstructionRecord), `_func.py` (CompiledFunc core), `_capture.py` (capture logic), `_replay.py` (replay logic), `_optimize.py` (gate optimization, adjoint helpers), `_virtual.py` (virtual mapping, return value construction), `_parametric.py` (parametric topology and lifecycle), `_inverse.py` (InverseCompiledFunc, AncillaInverseProxy)
- Every module ≤ 600 lines, no circular imports
- Pure refactor — all existing tests pass without modification

### Milestone 7: Compiled Function Ancilla Model

Fix the compile layer's ancilla tracking to distinguish transient from result qubits:

- **Transient ancilla identification**: After capture, qubits that are not parameters and not part of the return value and were freed by the C allocator are classified as transient
- **IR replay fix**: Only allocate parameter + result virtual qubits; skip transient virtual indices since `run_instruction` manages its own ancillas
- **Gate-level replay fix**: Allocate all virtual qubits (gates reference them), free transients after injection
- Repeated calls no longer grow qubit count for in-place operations

### Milestone 8: Hierarchical Compiled Function References

Store references to inner compiled functions instead of inlining their gates:

- **CallRecord IR entry**: New entry type storing reference to inner `CompiledFunc` and argument mapping
- **Recursive replay**: Outer function delegates to inner function's `_replay` with transitive qubit mapping
- **Visualization**: Per-function sub-diagrams linked from top-level call graph
- **Gate counts**: Computed recursively (own gates + referenced function gate counts)

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
