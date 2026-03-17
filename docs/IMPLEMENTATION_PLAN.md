# Implementation Plan

Modular, test-driven implementation plan for the Quantum Assembly compilation
pipeline. Every module targets **≤ 400 LOC** (excluding tests). Each step lists
the files it creates/modifies, what it tests, and its dependencies.

---

## Notation

| Symbol | Meaning |
|--------|---------|
| **[NEW]** | New file |
| **[MOD]** | Modify existing file |
| **~LOC** | Approximate lines of code (implementation only) |
| **DEP** | Depends on step(s) |
| **✅** | Completed |

---

## Phase 0 — Call Graph Redesign & Gate Count Storage ✅

### Completed Work ✅

The initial call graph infrastructure is in place:

- `CallGraphDAG` class with rustworkx-backed DAG, `DAGNode` data type
- `record_operation()` wired from Cython arithmetic/bitwise/comparison operations
- Tracking-only mode (`simulate=False`) counts gates without state vector
- Gate counting on replay via `block.original_gate_count`
- `report()` and `to_dot()` output methods

### Step 0.1: Execution-Order Edge Builder ✅

**Goal**: Replace `build_overlap_edges()` with incremental edge construction
during capture using a `last_node_per_qubit` map. Edges represent execution
ordering; absence of edges means operations are independent (parallelizable).

**Algorithm**: For each new operation touching qubits Q:
1. `parents = {last_node[q] for q in Q if q in last_node}`
2. Add edge from each parent → new node
3. If no parents found → edge from root
4. Update `last_node[q] = new_node` for all q in Q

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/call_graph.py` | [MOD] Add `_qubit_last_node: dict[int, int]` to `CallGraphDAG`. New `_connect_by_execution_order(node_idx, qubit_indices)` method. Called from `add_node()`. | +40 |

**Tests** (`tests/python/test_call_graph_edges.py` [NEW], ~200 LOC):
- `test_linear_chain` — 3 ops on same qubits → root→op1→op2→op3 (3 edges)
- `test_parallel_branches` — 2 ops on disjoint qubits → root→op1, root→op2 (2 edges, no edge between them)
- `test_merge_node` — op touching qubits from two independent branches → 2 parent edges
- `test_ten_additions_ten_edges` — 10 ops on same qubits → 10 edges (not 55)
- `test_all_nodes_reachable_from_root` — BFS from root reaches every node
- `test_no_redundant_edges` — no transitive edges (op3 does NOT connect to op1 when op2 is in between)
- `test_single_op` — 1 op → root→op1 (1 edge)
- `test_partial_overlap` — op1 on {0,1}, op2 on {1,2} → op1→op2 (shared qubit 1)

**DEP**: None (modifies existing infrastructure).

---

### Step 0.2: Remove Wrapper/Function Nodes ✅

**Goal**: Operations are direct DAG nodes. No function-level wrapper node.
Remove the `parent_index` parameter and "call" edge type.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/call_graph.py` | [MOD] Remove `parent_index` from `add_node()`, remove "call" edge handling. Root is node 0, operations connect directly. | -20 |
| `src/quantum_language/compile.py` | [MOD] Remove placeholder node creation for compiled functions. Operations add themselves via `record_operation`. No wrapper node. | -40 |

**Tests** (`tests/python/test_call_graph_flat.py` [NEW], ~100 LOC):
- `test_no_wrapper_node` — compiled fn with 3 ops → exactly 3 nodes (+ root)
- `test_no_call_edge_type` — no edge in DAG has `type == "call"`
- `test_report_shows_operations` — `report()` lists operations, not function names

**DEP**: Step 0.1

---

### Step 0.3: Remove `build_overlap_edges()` ✅

**Goal**: Delete the old overlap edge computation entirely. Edges are built
incrementally during capture (Step 0.1), not post-hoc.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/call_graph.py` | [MOD] Delete `build_overlap_edges()` method | -30 |
| `src/quantum_language/compile.py` | [MOD] Remove all calls to `build_overlap_edges()` | -5 |

**Tests** (`tests/python/test_call_graph_edges.py` [MOD]):
- `test_no_overlap_edge_type` — no edge in DAG has `type == "overlap"`
- `test_edge_set_matches_execution_order` — edge set identical to Step 0.1 algorithm output

**DEP**: Step 0.1

---

### Step 0.4: Graph Immutability After Capture ✅

**Goal**: After capture completes, the call graph is frozen. Replay reads the
graph but never modifies it. Attempting to add nodes/edges after freeze raises
an error.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/call_graph.py` | [MOD] Add `_frozen: bool` flag, `freeze()` method. `add_node()` and `add_edge()` raise `RuntimeError` when frozen. | +20 |
| `src/quantum_language/compile.py` | [MOD] Call `dag.freeze()` after capture. Replay path skips all DAG writes. | +10, -15 |

**Tests** (`tests/python/test_call_graph_freeze.py` [NEW], ~120 LOC):
- `test_graph_frozen_after_capture` — `dag._frozen` is True after first compilation
- `test_add_node_after_freeze_raises` — `RuntimeError` on `add_node()` post-freeze
- `test_replay_no_mutation` — compile fn, call it again, assert node count and edge count unchanged
- `test_read_after_freeze` — `report()`, `to_dot()`, `parallel_groups()` still work
- `test_replay_does_not_add_edges` — edge list identical before and after replay

**DEP**: Steps 0.2, 0.3

---

### Step 0.5: Add `total_gate_count` to `sequence_t` ✅

**Goal**: New field in the C `sequence_t` struct. Computed as sum of
`gates_per_layer` whenever a sequence is finalized.

| File | Action | ~LOC |
|------|--------|------|
| `c_backend/include/types.h` | [MOD] Add `num_t total_gate_count;` to `sequence_t` | +1 |
| `c_backend/src/execution.c` | [MOD] After building a sequence, compute `total_gate_count = sum(gates_per_layer[0..used_layer])` | +5 |

**Tests** (`tests/c/test_sequence_gate_count.c` [NEW], ~80 LOC):
- `test_new_sequence_zero` — freshly allocated sequence has `total_gate_count == 0`
- `test_computed_total_matches_sum` — after building a sequence, `total_gate_count == Σ gates_per_layer`
- `test_single_layer_sequence` — 1 layer, N gates → `total_gate_count == N`

**DEP**: None (C-level only, parallel with Steps 0.1–0.4).

---

### Step 0.6: Compute Counts at Sequence Creation ✅

**Goal**: Every code path that creates a sequence computes `total_gate_count`
after populating `gates_per_layer`. Includes both dynamic and precompiled paths.

| File | Action | ~LOC |
|------|--------|------|
| `c_backend/src/IntegerAddition.c` | [MOD] Set `total_gate_count` after building QFT addition sequences | +10 |
| `c_backend/src/hot_path_add.c` | [MOD] Set `total_gate_count` for toffoli addition sequences | +5 |
| `c_backend/src/hot_path_add_toffoli.c` | [MOD] Set `total_gate_count` for Clifford+T addition sequences | +10 |
| `c_backend/src/ToffoliMultiplication.c` | [MOD] Set `total_gate_count` for multiplication sequences | +5 |
| `c_backend/src/ToffoliDivision.c` | [MOD] Set `total_gate_count` for division sequences | +5 |
| `c_backend/src/ToffoliModReduce.c` | [MOD] Set `total_gate_count` for mod-reduce sequences | +5 |
| `c_backend/src/circuit_allocations.c` | [MOD] Set `total_gate_count = 0` in `alloc_sequence()` | +1 |

**Tests** (`tests/c/test_sequence_gate_count.c` [MOD]):
- `test_addition_sequence_nonzero` — QFT addition sequence has `total_gate_count > 0`
- `test_toffoli_add_sequence_nonzero` — toffoli addition sequence has `total_gate_count > 0`
- `test_multiplication_sequence_nonzero` — multiplication sequence has `total_gate_count > 0`
- `test_count_matches_manual_sum` — for each type, verify `total_gate_count == Σ gates_per_layer`

**DEP**: Step 0.5

---

### Step 0.7: Wire Gate Counts Through Recording Layer ✅

**Goal**: `_record_operation` receives the sequence's `total_gate_count` and
passes it to `DAGNode.gate_count` instead of hardcoding 0.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/call_graph.py` | [MOD] `record_operation()` uses `gate_count` parameter (already exists, currently always 0) | +2 |
| `src/quantum_language/toffoli_dispatch.pxi` | [MOD] After `run_instruction`, read `sequence.total_gate_count` and pass to `record_operation` | +10 |
| `src/quantum_language/qint_arithmetic.pxi` | [MOD] Pass sequence gate count to `record_operation` for QFT-path operations | +10 |
| `src/quantum_language/_core.pxd` | [MOD] Expose `total_gate_count` from `sequence_t` if not already visible | +2 |

**Tests** (`tests/python/test_dag_gate_counts.py` [NEW], ~120 LOC):
- `test_addition_dag_count_nonzero` — after `a + b`, DAGNode.gate_count > 0
- `test_multiplication_dag_count_nonzero` — after `a * b`, DAGNode.gate_count > 0
- `test_dag_count_matches_circuit_count` — DAG total matches `ql.circuit_stats().gate_count`
- `test_report_shows_counts` — `report()` output contains non-zero gate counts

**DEP**: Steps 0.5, 0.6, and Step 0.1 (DAGNode must exist)

---

### Phase 0 Integration Test ✅

**File**: `tests/python/test_call_graph_integration.py` [NEW], ~150 LOC

End-to-end: compile a function with mixed operations (additions, multiplications,
comparisons on different registers), verify:
- Edge structure matches execution-order algorithm
- Parallel branches for independent registers
- Merge nodes where operations touch multiple registers
- Gate counts non-zero throughout
- Graph unchanged after replay
- `to_dot()` produces a clean, readable visualization

**DEP**: Steps 0.1–0.7

---

### Phase 0 Summary

| Step | What | ~LOC | DEP |
|------|------|------|-----|
| 0.1 | Execution-order edge builder | +40 | — |
| 0.2 | Remove wrapper/function nodes | -60 | 0.1 |
| 0.3 | Remove `build_overlap_edges()` | -35 | 0.1 |
| 0.4 | Graph immutability after capture | +30 | 0.2, 0.3 |
| 0.5 | `total_gate_count` field on `sequence_t` | +6 | — |
| 0.6 | Compute counts at sequence creation | +41 | 0.5 |
| 0.7 | Wire counts through recording layer | +24 | 0.5, 0.6, 0.1 |

**Parallelizable**: Steps 0.1–0.4 (Python/Cython) and Steps 0.5–0.6 (C) are
independent and can proceed in parallel.

---

## Phase 1 — Per-Variable History Graph & Automatic Uncomputation ✅

### Step 1.1: History Graph Data Structure ✅

**Goal**: Lightweight `HistoryGraph` class holding `(sequence_ptr, qubit_mapping, num_ancilla)` entries with weakref children. Attached to every qint/qbool on creation.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/history_graph.py` | [NEW] `HistoryGraph` with `append`, `add_child`, `reversed_entries`, `live_children`, `discard`, `uncompute` | +90 |
| `src/quantum_language/qint.pxd` | [MOD] Add `cdef public object history` | +1 |
| `src/quantum_language/qint.pyx` | [MOD] `self.history = HistoryGraph()` in both init paths | +3 |

**Tests** (`tests/python/test_history_graph.py` [NEW]):
- Append/reverse ordering, len/bool, weakref alive/dead, discard clears entries and children

**DEP**: None

---

### Step 1.2: Record Operations into Per-Variable History ✅

**Goal**: When out-of-place operations produce a new qint/qbool, record `(sequence_ptr, qubit_mapping, num_ancilla)` into the result's history graph. Widened temporaries registered as weakref children.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint_arithmetic.pxi` | [MOD] History recording in `__add__`, `__sub__`, `__neg__`, `__lshift__`, `__rshift__`, `__mul__` | +87 |
| `src/quantum_language/qint_comparison.pxi` | [MOD] History recording in `__eq__`, `__lt__`, `__gt__` (CQ and QQ paths) | +42 |
| `src/quantum_language/qint_bitwise.pxi` | [MOD] History recording in `__and__`, `__or__`, `__xor__` | +29 |

**Tests** (`tests/python/test_history_recording.py` [NEW]):
- Addition/comparison records history, chained expressions record children, input variables have empty history

**DEP**: Step 1.1

---

### Step 1.3: __exit__ Uncomputation for with Blocks ✅

**Goal**: When `with qbool:` exits, uncompute the qbool's history in reverse via `run_instruction(invert=True)`, then cascade to orphaned children.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/history_graph.py` | [MOD] `uncompute(run_fn)` method with reverse iteration and cascade | +25 |
| `src/quantum_language/qint.pyx` | [MOD] `_run_inverted_on_circuit()` helper; `__exit__` calls `history.uncompute()` | +30 |

**Tests** (`tests/python/test_with_uncompute.py` [NEW]):
- With block uncomputes qbool, uncomputes temporaries, preserves live variables, nested with blocks, qubit mapping correctness, exception-in-body handling

**DEP**: Step 1.2

---

### Step 1.4: __del__ Uncomputation with Circuit Guard ✅

**Goal**: When refcount hits zero mid-circuit, `__del__` triggers history uncomputation. Circuit-active flag prevents firing during shutdown.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/_core.pyx` | [MOD] `_circuit_active` flag, `_get_circuit_active()`/`_set_circuit_active()` accessors | +15 |
| `src/quantum_language/qint.pyx` | [MOD] `__del__` checks circuit-active guard, calls `history.uncompute()`, clears layer range | +10 |

**Tests** (`tests/python/test_del_uncompute.py` [NEW]):
- Del uncomputes when circuit active, skips when inactive, cascades to children, EAGER mode, simulation correctness, double-uncompute prevention

**DEP**: Step 1.3

---

### Step 1.5: Measurement Trigger (Discard History) ✅

**Goal**: When measured, discard history graph. Collapsed qubits cannot be uncomputed.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint.pyx` | [MOD] `self.history.discard()` in `measure()` | +1 |

**Tests** (`tests/python/test_measurement_history.py` [NEW]):
- Measurement clears history, measured variable no del uncompute, measurement orphans children

**DEP**: Step 1.1

---

### Step 1.6: atexit Shutdown Guard ✅

**Goal**: `atexit` hook sets `_circuit_active=False` to prevent `__del__` during interpreter shutdown.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/_core.pyx` | [MOD] `atexit.register(_atexit_disable_circuit)` | +5 |

**Tests** (`tests/python/test_del_uncompute.py` [MOD]):
- atexit disables circuit flag, del after shutdown is noop, idempotent, EAGER mode interaction

**DEP**: Step 1.4

---

### Step 1.7: Remove Legacy Layer-Based Uncomputation ✅

**Goal**: Remove `_start_layer`, `_end_layer`, `_uncompute_mode`, `_auto_uncompute()`, `layer_floor` save/restore, and dead helper functions.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint.pxd` | [MOD] Remove `_start_layer`, `_end_layer`, `_uncompute_mode` | -3 |
| `src/quantum_language/qint.pyx` | [MOD] Remove layer tracking, `reverse_circuit_range` usage | -80 |
| `src/quantum_language/qint_comparison.pxi` | [MOD] Remove `layer_floor` save/restore | -40 |
| `src/quantum_language/qint_arithmetic.pxi` | [MOD] Remove `layer_floor` save/restore | -30 |
| `src/quantum_language/qint_bitwise.pxi` | [MOD] Remove `layer_floor` save/restore | -20 |
| `src/quantum_language/qint_division.pxi` | [MOD] Remove `layer_floor` save/restore | -10 |
| `src/quantum_language/compile.py` | [MOD] Remove `_auto_uncompute()`, `_function_modifies_inputs()`, `_partition_ancillas()`, dead parameters | -120 |

**Tests**: Existing tests pass with no behavioral regression.

**DEP**: Steps 1.3–1.6

---

### Phase 1 Integration Test ✅

**File**: `tests/python/test_phase1_integration.py` [NEW], ~770 LOC

End-to-end: 33 tests covering with blocks (simple/compound/nested), variable survival, measurement discard, eager uncomputation, gate count symmetry, exception handling.

**DEP**: Steps 1.1–1.7

---

### Phase 1 Summary

| Step | What | ~LOC | DEP |
|------|------|------|-----|
| 1.1 | History graph data structure | +90 | — |
| 1.2 | Record operations into history | +158 | 1.1 |
| 1.3 | `__exit__` uncomputation | +55 | 1.2 |
| 1.4 | `__del__` uncomputation with circuit guard | +25 | 1.3 |
| 1.5 | Measurement trigger (discard) | +1 | 1.1 |
| 1.6 | atexit shutdown guard | +5 | 1.4 |
| 1.7 | Remove legacy uncomputation | -303 | 1.3–1.6 |

**Net**: ~+31 LOC implementation, ~+1600 LOC tests

---

## Phase 2 — Quantum Walk Rework

Replaces the monolithic `walk.py` (1618 LOC) with a modular, function-based API.
The user provides `make_move`, `is_valid`, `is_marked` as quantum functions; the
framework handles all internal walk machinery (height register, branch registers,
counting, Montanaro diffusion angles, R_A/R_B, detection).

### Design Overview

**User-facing API**:
```python
# Full walk — detect existence of a marked node
found = ql.walk(state, make_move, is_valid, is_marked,
                max_depth=n, num_moves=m)

# Local diffusion building block — for custom walk operators
ql.walk_diffusion(state, make_move, is_valid, num_moves=m)
```

**User-provided functions**:
- `make_move(state, move_index)` — `@ql.compile(inverse=True)`, transforms state
  by applying classical move index. Uses DSL operations (arithmetic, XOR, `with`).
- `is_valid(state)` — quantum predicate, returns `qbool`.
- `is_marked(state)` — quantum predicate, returns `qbool`.

**Framework-managed registers**:
- Height register: one-hot, `max_depth + 1` qubits
- Branch registers: one per depth, `ceil(log2(num_moves))` qubits each
- Count register: temporary, `ceil(log2(num_moves + 1))` qubits

**Key algorithm** (local diffusion at a node):
1. Count valid children: for each move i, apply → check validity → count → undo
2. Conditional rotation: Montanaro angles based on count, include parent/self for backflow
3. Apply chosen move: controlled on branch register value

**Qubit budget for tests** (must fit ≤ 21 qubits):
- 2 binary variables, ternary encoding: 2×2=4 state + 2 branch + 3 height + 2 count = 11 qubits
- 3 binary variables: 3×2=6 state + 3 branch + 4 height + 2 count = 15 qubits

---

### Step 2.1: Walk Core Types & Angle Computation

**Goal**: Configuration dataclass, Montanaro rotation angle formulas, and register
width computation. Foundation for all subsequent walk modules.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_core.py` | [NEW] `WalkConfig` dataclass, `montanaro_angles(d)`, `root_angle(d, n)`, `branch_width(num_moves)`, `count_width(num_moves)`, `total_walk_qubits()` | ~150 |

**WalkConfig fields**:
- `state` — quantum register (qarray/qint)
- `make_move` — compiled function with inverse
- `is_valid` — quantum predicate
- `is_marked` — quantum predicate (optional, only needed for full walk)
- `max_depth` — int
- `num_moves` — int
- Derived: `branch_width`, `count_width`, `height_width`

**Angle formulas** (Montanaro 2015):
- Parent-children split: `phi = 2 * arctan(sqrt(d))` where d = number of valid children
- Cascade angles: `theta_k = 2 * arctan(sqrt(1 / (d - 1 - k)))` for k = 0..d-2
- Root special case: `phi_root = 2 * arctan(sqrt(n * d_root))` where n = tree size

**Tests** (`tests/python/test_walk_core.py` [NEW], ~150 LOC):
- `test_montanaro_angles_binary` — d=2 gives correct phi and theta values
- `test_montanaro_angles_ternary` — d=3 angles
- `test_root_angle` — root angle formula
- `test_branch_width` — `branch_width(2) == 1`, `branch_width(8) == 3`
- `test_count_width` — `count_width(2) == 2` (stores 0, 1, 2)
- `test_walk_config_validation` — rejects invalid inputs (depth < 1, moves < 1)
- `test_total_walk_qubits` — matches manual calculation

**DEP**: None

---

### Step 2.2: Walk Register Management

**Goal**: Allocate and manage the framework-internal registers (height, branch,
count). Provide helpers to initialize root state and read height.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_registers.py` | [NEW] `WalkRegisters` class: allocate height/branch/count registers, `init_root()`, `current_depth()`, `branch_at(depth)`, `cleanup()` | ~180 |

**WalkRegisters**:
- `height` — qarray of qbools, one-hot encoding (index k = 1 means at depth k)
- `branches` — list of qints, one per depth level, width = `branch_width`
- `count` — qint, width = `count_width`, temporary for counting
- `init_root()` — set height to root state (h[max_depth] = 1, all branches = 0)
- `branch_at(depth)` — return the branch register for given depth

**Tests** (`tests/python/test_walk_registers.py` [NEW], ~150 LOC):
- `test_register_allocation` — correct qubit counts
- `test_init_root_state` — height register has exactly one bit set at max_depth
- `test_branch_registers_zeroed` — all branches start at 0
- `test_total_qubits_matches_config` — sum of all register widths matches `WalkConfig.total_walk_qubits()`
- `test_cleanup_releases_qubits` — registers deallocated

**DEP**: Step 2.1

---

### Step 2.3: Move Counting

**Goal**: Count valid children at the current node via the apply-check-undo loop.
Operates in superposition — each basis state of `state` gets its own count.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_counting.py` | [NEW] `count_valid_children(config, count_reg)` — loop over `num_moves`, apply/check/undo, return count in `count_reg` | ~150 |

**Algorithm**:
```
count = 0
for i in range(num_moves):
    make_move(state, i)
    valid = is_valid(state)
    with valid:
        count += 1
    # valid is uncomputed automatically (history graph)
    make_move.inverse(state, i)
```

**Tests** (`tests/python/test_walk_counting.py` [NEW], ~200 LOC):
- `test_count_all_valid` — all moves valid → count == num_moves (statevector check)
- `test_count_none_valid` — no moves valid → count == 0
- `test_count_partial` — some moves valid → correct count
- `test_count_superposition` — state in superposition, different basis states yield different counts
- `test_state_restored` — state is unchanged after counting (apply/undo is clean)
- `test_inverse_consistency` — make_move followed by make_move.inverse is identity

All tests use ≤ 11 qubits (2-variable ternary encoding).

**DEP**: Step 2.1

---

### Step 2.4: Conditional Branching

**Goal**: Given a count of valid children, create a uniform superposition over
valid move indices in the branch register, including the parent/self component.
Then apply the chosen move.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_branching.py` | [NEW] `branch_to_children(config, count_reg, branch_reg)` — conditional rotation based on count, superposition over valid moves, apply chosen move. `unbranch(config, count_reg, branch_reg)` — inverse. | ~250 |

**Algorithm**:
1. Conditioned on `count == c` for each possible c:
   - Apply Ry rotation with angle `phi(c)` to split parent/children amplitude
   - Apply cascade rotations `theta_k(c)` to distribute amplitude among c children
2. For each move i: controlled on `branch == i`, check validity, apply move if valid
3. The result: state is in superposition over all valid children + parent component

**Tests** (`tests/python/test_walk_branching.py` [NEW], ~200 LOC):
- `test_branch_uniform_superposition` — with all moves valid, branch register is uniform
- `test_branch_includes_parent` — parent component has correct amplitude (1/sqrt(d+1))
- `test_branch_respects_validity` — invalid moves get zero amplitude
- `test_unbranch_inverse` — branch followed by unbranch restores original state
- `test_branch_angles_correct` — amplitudes match Montanaro formulas

**DEP**: Steps 2.1, 2.3

---

### Step 2.5: Local Diffusion Operator

**Goal**: User-facing `walk_diffusion()` that combines counting + branching into a
single reflection operator at the current depth. Satisfies D² = I.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_diffusion.py` | [NEW] `walk_diffusion(state, make_move, is_valid, num_moves)` — public API. Internally: count → branch → phase flip → unbranch → uncount. | ~200 |

**Structure**: The local diffusion is a reflection about the subspace spanned by
{parent, valid_children}. Implemented as:
1. `count_valid_children()` — fill count register
2. `branch_to_children()` — create superposition in branch register
3. Phase flip on branch register (MCZ or Z)
4. `unbranch()` — inverse of step 2
5. Inverse of counting — undo step 1

**Tests** (`tests/python/test_walk_local_diffusion.py` [NEW], ~200 LOC):
- `test_reflection_property` — D applied twice returns to original state (|ψ⟩ → D²|ψ⟩ = |ψ⟩, tolerance 1e-6)
- `test_diffusion_amplitudes` — after one D, amplitudes match expected reflection
- `test_diffusion_at_root` — root diffusion uses root angle formula
- `test_diffusion_no_valid_children` — identity when no children are valid
- `test_walk_diffusion_api` — public API callable with correct signature

All tests use ≤ 15 qubits.

**DEP**: Steps 2.3, 2.4

---

### Step 2.6: Walk Operators (R_A, R_B, walk_step)

**Goal**: Height-controlled walk operators that apply local diffusion at
even/odd depths. walk_step = R_B * R_A, compiled for replay.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_operators.py` | [NEW] `build_R_A(config, registers)`, `build_R_B(config, registers)`, `walk_step(config, registers)` — compiled walk step. | ~300 |

**R_A**: For each even depth d (excluding root): controlled on `height[d]`,
apply local diffusion at depth d.

**R_B**: For each odd depth d: controlled on `height[d]`, apply local diffusion.
Plus root (always included in R_B).

**walk_step**: R_B * R_A, decorated with `@ql.compile` for gate caching.

**Tests** (`tests/python/test_walk_ops.py` [NEW], ~250 LOC):
- `test_R_A_even_depths_only` — R_A acts only on even-depth height qubits
- `test_R_B_odd_depths_plus_root` — R_B acts on odd depths and root
- `test_disjointness` — R_A and R_B height controls do not overlap
- `test_walk_step_compiled` — second call replays cached gates
- `test_walk_step_preserves_norm` — unitary (|ψ| = 1 after walk step)

Tests use 2-variable ternary encoding (11 qubits).

**DEP**: Steps 2.2, 2.5

---

### Step 2.7: Full Walk & Detection

**Goal**: `ql.walk()` — the complete algorithm. Initialize root, iterate
walk steps, detect marked nodes via root overlap measurement.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_search.py` | [NEW] `walk(state, make_move, is_valid, is_marked, max_depth, num_moves)` — public API. Initializes registers, marks leaves, iterates walk_step, measures root overlap. Returns bool. | ~250 |

**Algorithm** (Montanaro detection):
1. Allocate WalkRegisters, initialize root state
2. Apply marking oracle: for each leaf state, check `is_marked`, phase-flip if true
3. Iterate walk_step for O(sqrt(tree_size)) steps
4. Measure root overlap — if above threshold, marked node exists
5. Cleanup registers

**Tests** (`tests/python/test_walk_search.py` [NEW], ~250 LOC):
- `test_detect_known_marked` — tiny tree with known marked leaf → returns True
- `test_detect_no_marked` — tree with no solutions → returns False
- `test_ilp_2var` — 2-variable binary ILP: find x0, x1 ∈ {0,1} satisfying x0 + x1 ≥ 1
  (3 of 4 leaves are solutions, detection should succeed)
- `test_ilp_3var` — 3-variable ILP with tighter constraint (15 qubits)
- `test_walk_returns_bool` — return type is bool
- `test_walk_classical_verification` — run classical equivalents of make_move/is_valid/is_marked
  to confirm the problem setup is correct before quantum execution

**DEP**: Steps 2.6, 2.5

---

### Step 2.8: Migration & Exports

**Goal**: Update public API, deprecate old QWalkTree, update skill file.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/__init__.py` | [MOD] Add `walk`, `walk_diffusion` exports. Deprecation warning on `QWalkTree` import. | +10 |
| `src/quantum_language/walk.py` | [MOD] Add deprecation warning at top; keep for backward compatibility during transition. | +5 |
| `.claude/commands/quantum-walk.md` | [NEW] Skill file (created in this phase). | ~200 |

**Tests** (`tests/python/test_walk_migration.py` [NEW], ~80 LOC):
- `test_walk_import` — `from quantum_language import walk, walk_diffusion` works
- `test_qwalktree_deprecation` — importing `QWalkTree` raises DeprecationWarning
- `test_walk_api_signature` — `walk()` accepts correct parameters

**DEP**: Steps 2.7, all previous steps

---

### Phase 2 Integration Test

**File**: `tests/python/test_walk_integration.py` [NEW], ~300 LOC

End-to-end tests combining all walk components on complete tiny problems:

- `test_binary_sat_2var` — 2-variable SAT: (x0 OR x1). Ternary encoding, 11 qubits.
  Define make_move (assign first unassigned), is_valid (constraint not violated),
  is_marked (all assigned + clause satisfied). Walk detects solution.
- `test_binary_sat_unsatisfiable` — 2-variable unsatisfiable formula. Walk returns False.
- `test_walk_diffusion_standalone` — Use walk_diffusion() building block independently
  to verify reflection property on a real problem state.
- `test_classical_quantum_agreement` — Run classical equivalents of all functions on
  exhaustive inputs, verify quantum walk result matches classical brute force.
- `test_custom_walk_via_diffusion` — User builds R_A/R_B manually from walk_diffusion()
  (the "power user" path).

**DEP**: Steps 2.1–2.8

---

### Phase 2 Summary

| Step | What | ~LOC | File | DEP |
|------|------|------|------|-----|
| 2.1 | Walk core types & angles | ~150 | `walk_core.py` | — |
| 2.2 | Walk register management | ~180 | `walk_registers.py` | 2.1 |
| 2.3 | Move counting | ~150 | `walk_counting.py` | 2.1 |
| 2.4 | Conditional branching | ~250 | `walk_branching.py` | 2.1, 2.3 |
| 2.5 | Local diffusion operator | ~200 | `walk_diffusion.py` | 2.3, 2.4 |
| 2.6 | Walk operators (R_A, R_B) | ~300 | `walk_operators.py` | 2.2, 2.5 |
| 2.7 | Full walk & detection | ~250 | `walk_search.py` | 2.5, 2.6 |
| 2.8 | Migration & exports | ~15 | `__init__.py`, `walk.py` | 2.7 |

**Parallelizable**: Steps 2.2 and 2.3 are independent (both depend only on 2.1).

**Total**: ~1495 LOC implementation across 7 new files (all ≤ 300 LOC),
~1780 LOC tests across 9 test files. Replaces 1618 LOC monolithic `walk.py`.

---

## Phase 2b — Quantum Walk Bug Fixes ✅

Fixed correctness bugs discovered during review of Phase 2:

1. Classical evaluation of quantum predicates → quantum evaluation via `is_marked(state)` returning `qbool`
2. Raw `emit_x(qubit_idx)` → DSL `_flip_all` helper wrapping qint/qbool registers
3. Wrong marking semantics → D_x = I for marked nodes (Montanaro 2015), diffusion only on unmarked
4. Simulation-based detection → removed; `walk()` returns `(config, registers)`, phase estimation is future milestone
5. Duplicated diffusion logic → `walk_operators.py` composes `walk_diffusion.py` via `control_qubit` parameter
6. Deprecated `QWalkTree` → deleted along with all associated test files

### Phase 2b Summary

| Step | What | Status |
|------|------|--------|
| 2b.1 | Remove walk.py & old tests | ✅ |
| 2b.2 | Replace emit_x with DSL operators | ✅ |
| 2b.3 | Quantum marking in walk operators | ✅ |
| 2b.4 | Deduplicate walk operators | ✅ |
| 2b.5 | Rewrite walk_search.py | ✅ |
| 2b.6 | Update quantum walk skill | ✅ |

---

## Phase 2c — Unify Diffusion Path

The walk currently has two diffusion implementations:

- **Variable-branching** (`_variable_diffusion`): evaluates `is_valid` per child quantumly, counts valid children into a quantum register, applies conditional Montanaro rotations per count value. Correct for all trees.
- **Fixed-branching** (`_fixed_diffusion`): takes a classical `int d`, assumes all `num_moves` children are always valid. Only correct for perfectly regular trees with no pruning.

**Problem**: The fixed path is wrong for any real backtracking problem (the whole point is pruning via `is_valid`). It converges to plain Grover's algorithm, which already has `ql.grover()`. Meanwhile, marking only works on the fixed path — the variable path warns and ignores `is_marked`.

**Solution**: Remove `_fixed_diffusion` entirely. Unify on `_variable_diffusion` as the single diffusion implementation. Make marking work with variable branching — controlled XOR inside `with ~marked:` decomposes to Toffoli gates, which the framework handles natively.

### Design After Phase 2c

**`_apply_local_diffusion` (single path)**:
```python
def _apply_local_diffusion(config, registers, depth):
    if depth == 0:
        return  # leaf

    if config.is_marked is not None:
        marked = config.is_marked(config.state)
        _flip_all(marked)
        with marked:  # executes on UNMARKED nodes
            _do_variable_diffusion(config, registers, depth)
        _flip_all(marked)
    else:
        _do_variable_diffusion(config, registers, depth)
```

Controlled XOR inside `with marked:` → each X gate becomes a CNOT, each CNOT becomes a Toffoli. The framework's `with qbool:` mechanism handles this natively.

**`walk()` API**: `state`, `make_move`, `is_valid` are all required. No optional-but-actually-needed parameters.

**Module layering after Phase 2c**:
- `walk_core.py` — types + angles (unchanged)
- `walk_counting.py` — count valid children (unchanged)
- `walk_branching.py` — conditional branching (unchanged)
- `walk_diffusion.py` — single-node diffusion: only `_variable_diffusion`, `walk_diffusion_with_regs`, `walk_diffusion` (public). No `_fixed_diffusion`, no `walk_diffusion_fixed`.
- `walk_registers.py` — register management (unchanged)
- `walk_operators.py` — R_A/R_B composing walk_diffusion, marking wraps variable diffusion
- `walk_search.py` — thin shell, `walk()` requires state/make_move/is_valid

---

### Step 2c.1: Marking on Variable-Branching Path

**Goal**: Make marking work with variable-branching diffusion. Remove the warning
that `is_marked` is ignored. Wrap `_variable_diffusion` with `with ~marked:`.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_operators.py` | [MOD] Remove warning about marking being ignored in variable-branching path. Restructure `_apply_local_diffusion`: evaluate `is_marked(state)` → `with ~marked:` wraps the variable diffusion call. Single code path for both marked and unmarked walks. | ~-20 |

**Key change**: The `with marked:` block wraps the entire variable diffusion call.
Controlled XOR operations inside `make_move` become Toffoli gates under the
marking control — this is handled natively by the framework.

**Tests** (`tests/python/test_walk_marking.py` [MOD]):
- Update marking tests to use variable branching (provide `make_move`, `is_valid`, `state`)
- `test_marking_with_variable_branching` — marking + validity evaluation in same walk step
- `test_controlled_xor_under_marking` — verify `make_move` operations are correctly controlled
- Verify norm preservation and D²=I with marking + variable branching

**DEP**: Phase 2b (all steps completed)

---

### Step 2c.2: Remove Fixed Diffusion

**Goal**: Delete `_fixed_diffusion`, `walk_diffusion_fixed`, and `_apply_fixed_diffusion`.
Make `state`, `make_move`, `is_valid` required in `walk()`. Single diffusion path.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_diffusion.py` | [MOD] Delete `_fixed_diffusion` (~40 LOC) and `walk_diffusion_fixed` (~25 LOC). Remove `_precompute_angles` usage for fixed path. Keep `_variable_diffusion`, `walk_diffusion_with_regs`, `walk_diffusion`. | ~-65 |
| `src/quantum_language/walk_operators.py` | [MOD] Delete `_apply_fixed_diffusion` (~15 LOC). `_apply_local_diffusion` becomes a single path: always variable diffusion, optionally wrapped with marking. | ~-15 |
| `src/quantum_language/walk_search.py` | [MOD] Make `state`, `make_move`, `is_valid` required positional parameters. Remove `if state is None: ql.circuit()` branch. | ~-10 |
| `src/quantum_language/__init__.py` | [MOD] Remove `walk_diffusion_fixed` from exports if present. | ~-1 |

**Tests**:
- Remove fixed-branching tests from `test_walk_local_diffusion.py` (5 tests in `TestReflectionPropertyFixed`, `TestNoValidChildren`)
- Remove fixed-branching tests from `test_walk_operators_fn.py`
- Update `test_walk_search.py` — `walk()` no longer accepts state=None
- Update `test_walk_marking.py` — remove tests that use fixed-branching config
- Verify all remaining tests pass

**DEP**: Step 2c.1

---

### Step 2c.3: Test Consolidation

**Goal**: Clean up test files after the fixed-branching removal. Merge or remove
tests that are redundant now that there's a single diffusion path.

| File | Action | ~LOC |
|------|--------|------|
| `tests/python/test_walk_local_diffusion.py` | [MOD] Remove `TestReflectionPropertyFixed`, `TestDiffusionAmplitudes` (fixed-specific). Keep `TestVariableBranching`, `TestS0Reflection`, `TestQubitBudget`. | ~-150 |
| `tests/python/test_walk_marking.py` | [MOD] Remove tests that construct fixed-branching configs. All marking tests use variable branching. | ~-100 |
| `tests/python/test_walk_operators_fn.py` | [MOD] Remove fixed-branching operator tests. All operator tests use variable branching. | ~-50 |
| `tests/python/test_walk_migration.py` | [MOD] Update to verify `walk_diffusion_fixed` is NOT importable. | ~+5 |

**DEP**: Step 2c.2

---

### Phase 2c Summary

| Step | What | ~LOC delta | File(s) | DEP |
|------|------|------------|---------|-----|
| 2c.1 | Marking on variable-branching path | ~-20 | `walk_operators.py`, `test_walk_marking.py` | 2b |
| 2c.2 | Remove fixed diffusion, require state/make_move/is_valid | ~-90 | `walk_diffusion.py`, `walk_operators.py`, `walk_search.py` | 2c.1 |
| 2c.3 | Test consolidation | ~-300 tests | 4 test files | 2c.2 |

**Net result**: ~90 LOC implementation reduction, ~300 LOC test reduction, single
diffusion path, marking works with all walk configurations.

---

## Phase 3 — DSL Purity & Simulate-Mode Cleanup

The `simulate` option is a **global setting** — internal helpers must never toggle it.
Currently, `_flip_all` and `diffusion()` locally toggle `simulate=True`, creating a
"mixed simulate mode" that masks bugs and prevents clean DSL replacements.

This phase removes all local toggles, adds controlled-AND support, and replaces
remaining raw gate patterns with pure DSL operations.

**Qubit budget**: Raised from 17 to 21. Verified: 21-qubit statevector simulation
takes ~0.2s (2M amplitudes), well within acceptable limits.

---

### Step 3.1: Remove Local Simulate Toggles

**Goal**: Remove all `option('simulate', True/False)` toggles from internal helpers.
The `simulate` option is set globally by the user or test fixture. Internal code
must not care about it — if `simulate=False`, ALL operations skip gate storage
(not just selected ones).

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/diffusion.py` | [MOD] Remove simulate toggle from `_flip_all`. Remove simulate toggle from `diffusion()` wrapper. | ~-15 |
| `tests/python/test_walk_marking.py` | [MOD] Add `ql.option('simulate', True)` to `_init_circuit()`. | +1 |
| `tests/python/test_walk_search.py` | [MOD] Add `ql.option('simulate', True)` to `_init_circuit()`. | +1 |
| `tests/python/test_walk_operators_fn.py` | [MOD] Add `ql.option('simulate', True)` to `_init_circuit()`. | +1 |

**Tests**: All existing walk tests pass with simulate=True set globally. Qubit
budget assertions updated from 17 to 21 where needed.

**DEP**: None

---

### Step 3.2: Controlled-AND Support

**Goal**: Make the `&` operator on qbools work inside `with` blocks (controlled
context). Currently raises `NotImplementedError: Controlled quantum-quantum AND
not yet supported`.

**Implementation**: In `__and__` (qint_bitwise.pxi), when inside a controlled
context (`_get_controlled()` returns True), decompose the controlled Toffoli
(C-CCX) into standard Toffolis + ancilla. The C-CCX gate (4-qubit: 1 control
on the AND, 2 inputs, 1 output) decomposes into 3 standard Toffolis with one
ancilla qubit.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint_bitwise.pxi` | [MOD] Add controlled-AND path in `__and__`: detect controlled context, decompose C-CCX into Toffolis + ancilla. | ~+30 |

**Tests** (`tests/python/test_controlled_and.py` [NEW], ~100 LOC):
- `test_and_outside_with` — `a & b` works as before (no regression)
- `test_and_inside_with` — `with ctrl: c = a & b` produces correct result
- `test_and_nested_with` — `with c1: with c2: d = a & b` (double-controlled AND)
- `test_and_chain_inside_with` — `with ctrl: combined = a & b & c` (chained)
- `test_controlled_and_statevector` — verify correct amplitudes via simulation

**DEP**: None (parallel with Step 3.1)

---

### Step 3.3: Replace _flip_all with Direct DSL Ops

**Goal**: Replace single-register `_flip_all(reg)` calls with `reg ^= 1` (for
qbool) or `~reg` directly. Keep `_flip_all` only for multi-register convenience
(without simulate toggle).

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_operators.py` | [MOD] Replace `_flip_all(marked)` with `marked ^= 1` (2 call sites). Remove `_flip_all` import. | ~-2 |
| `src/quantum_language/walk_branching.py` | [MOD] Replace `_flip_all(target_w)` with `target_w ^= 1` in no-controls paths of `_multi_controlled_ry` and `_multi_controlled_x`. Keep `_flip_all` in controlled paths (inside `with` blocks) until controlled-XOR is supported. | ~-4 |

**Tests**: All walk tests pass. Qubit budget limits updated to 21.

**DEP**: Step 3.1 (simulate toggles removed first)

---

### Step 3.4: Replace Recursive Nested `with` Patterns

**Goal**: Replace `_nested_phase_flip` (diffusion.py) and `_apply_nested_with`
(walk_diffusion.py) — both use recursive `with bits[idx]: _recurse(idx+1)` —
with flat `&`-chain pattern: `combined = bits[0]; for b in bits[1:]: combined &= b;
with combined: body()`.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/diffusion.py` | [MOD] Replace `_nested_phase_flip` body with `&`-chain + `with combined: target.phase += pi`. | ~-5 |
| `src/quantum_language/walk_diffusion.py` | [MOD] Replace `_apply_nested_with` body with `&`-chain + `with combined: body_fn()`. | ~-10 |

**Tests**: Existing diffusion and walk diffusion tests verify correctness (D²=I).

**DEP**: Step 3.2 (controlled-AND must work inside `with` blocks)

---

### Step 3.5: Update Qubit Budget Assertions

**Goal**: Update all test assertions that enforce the 17-qubit limit to use 21.

| File | Action | ~LOC |
|------|--------|------|
| `tests/python/test_walk_marking.py` | [MOD] Update qubit budget assertions from 17 to 21. | ~+2 |
| `tests/python/test_walk_operators_fn.py` | [MOD] Update qubit budget assertions from 17 to 21. | ~+2 |
| `tests/python/test_walk_search.py` | [MOD] Update qubit budget assertions from 17 to 21. | ~+2 |
| `tests/python/test_walk_local_diffusion.py` | [MOD] Update qubit budget assertions from 17 to 21. | ~+2 |

**Tests**: All qubit budget tests pass with new limit.

**DEP**: Steps 3.1, 3.3 (simulate cleanup may change qubit counts)

---

### Phase 3 Summary

| Step | What | ~LOC delta | DEP |
|------|------|------------|-----|
| 3.1 | Remove local simulate toggles | ~-15 | — |
| 3.2 | Controlled-AND support | ~+30 | — |
| 3.3 | Replace `_flip_all` with `^= 1` / `~` | ~-6 | 3.1 |
| 3.4 | Replace recursive nested `with` | ~-15 | 3.2 |
| 3.5 | Update qubit budget to 21 | ~+8 | 3.1, 3.3 |

**Parallelizable**: Steps 3.1 and 3.2 are independent and can proceed in parallel.
Steps 3.3 and 3.4 follow their respective prerequisites. Step 3.5 is a final
sweep after the other changes land.

**Future** (not in this phase): `qarray.all()` primitive to replace manual `&`-chain
loops with internal AND-reduction.
