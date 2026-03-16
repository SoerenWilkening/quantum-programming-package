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

**Qubit budget for tests** (must fit ≤ 17 qubits):
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

## Phase 2b — Quantum Walk Bug Fixes

Fixes correctness bugs discovered during review of Phase 2. The core issues:

1. **Classical evaluation of quantum predicates**: `walk_search.py` evaluates `is_marked` by brute-forcing all 2^n values classically — fundamentally wrong for quantum computing. Must evaluate quantumly.
2. **Raw gate usage**: `emit_x(qubit_idx)` used throughout walk modules instead of DSL operators (`x ^= value`).
3. **Wrong marking semantics**: Code applies phase flips on marked nodes (Grover-style). Per Montanaro 2015, D_x = I (identity) for marked nodes — diffusion only on unmarked nodes.
4. **Wrong detection algorithm**: Simulation-based overlap comparison instead of phase estimation. Phase estimation is postponed; remove wrong code, add TODO.
5. **Duplicated logic**: `walk_operators.py` reimplements diffusion instead of composing `walk_diffusion.py`.

### Design Corrections

**Marking = identity** (Montanaro 2015, Theorem 1):
- If node x is marked: D_x = I (do nothing)
- If node x is unmarked: D_x = I − 2|ψ_x⟩⟨ψ_x| (standard diffusion)

The correct pattern in `_apply_local_diffusion`:
```python
if config.is_marked is not None:
    marked = config.is_marked(config.state)
    with ~marked:
        _do_diffusion(config, registers, depth)
else:
    _do_diffusion(config, registers, depth)
```

**Module layering after fixes**:
- `walk_core.py` — types + angles (unchanged)
- `walk_counting.py` — count valid children (unchanged, already correct quantum pattern)
- `walk_branching.py` — conditional branching (fix: replace emit_x with DSL)
- `walk_diffusion.py` — single-node diffusion (fix: replace emit_x with DSL)
- `walk_registers.py` — register management (unchanged)
- `walk_operators.py` — R_A/R_B composing walk_diffusion, with `is_marked` check (rewrite: remove duplicated diffusion, add marking)
- `walk_search.py` — thin shell building walk operator, TODO for phase estimation detection (rewrite: remove classical evaluation + simulation)

---

### Step 2b.1: Remove walk.py & Old Tests

**Goal**: Delete the deprecated `QWalkTree` class and all associated test files.
Clean up `__init__.py` exports.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk.py` | [DEL] Remove entirely | -1620 |
| `src/quantum_language/__init__.py` | [MOD] Remove `QWalkTree` import and `__all__` entry | -5 |
| `tests/python/test_walk_operators.py` | [DEL] Old QWalkTree-based operator tests | - |
| `tests/python/test_walk_detection.py` | [DEL] Old QWalkTree-based detection tests | - |
| `tests/python/test_walk_diffusion.py` | [DEL] Old QWalkTree-based diffusion tests (not test_walk_local_diffusion.py) | - |
| `tests/python/test_walk_tree.py` | [DEL] Old QWalkTree encoding tests | - |
| `tests/python/test_walk_predicate.py` | [DEL] Old predicate evaluation tests | - |
| `tests/python/test_walk_variable.py` | [DEL] Old variable branching tests | - |
| `tests/python/test_counting_diffusion.py` | [DEL] Old counting diffusion tests | - |
| Other QWalkTree test files | [DEL] All remaining test files that import QWalkTree | - |
| `tests/python/test_walk_migration.py` | [MOD] Remove QWalkTree deprecation tests, keep new API tests | - |

**Tests**: Verify `from quantum_language import walk, walk_diffusion` still works.
Verify `QWalkTree` is no longer importable. Run full suite — no import errors.

**DEP**: None

---

### Step 2b.2: Replace emit_x with DSL Operators

**Goal**: Replace all `emit_x(qubit_idx)` calls in walk modules with qint/qbool
DSL equivalents. Remove `.qubits[...]` access patterns.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_branching.py` | [MOD] Replace `emit_x` with `branch ^= 1 << bit` or equivalent XOR operations. Remove raw qubit index access. | ~-20 |
| `src/quantum_language/walk_diffusion.py` | [MOD] Replace `emit_x` with DSL XOR. | ~-10 |
| `src/quantum_language/walk_operators.py` | [MOD] Replace `emit_x` with DSL XOR. | ~-15 |
| `src/quantum_language/walk_search.py` | [MOD] Replace `emit_x` with DSL XOR. | ~-10 |
| `src/quantum_language/walk_registers.py` | [MOD] Replace `emit_x` in `init_root` with DSL. | ~-2 |

**Preserved**: `emit_mcz` (no DSL equivalent). `emit_ry` (Montanaro rotations, acceptable).

**Tests**: All existing walk tests must pass unchanged. Add grep-based test that
no walk_*.py file contains `emit_x(`.

**DEP**: Step 2b.1 (walk.py removed first to reduce noise)

---

### Step 2b.3: Quantum Marking in Walk Operators

**Goal**: Add `is_marked` check to the local diffusion dispatch in `walk_operators.py`.
Per Montanaro: D_x = I for marked nodes, standard diffusion for unmarked.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_operators.py` | [MOD] In `_apply_local_diffusion`: if `config.is_marked` is set, evaluate `is_marked(state)` quantumly, apply diffusion only `with ~marked:`. | +15 |

**Algorithm in `_apply_local_diffusion`**:
```
if config.is_marked is not None and config.state is not None:
    marked = config.is_marked(config.state)
    with ~marked:
        _do_diffusion(...)
    # marked nodes: identity (nothing happens)
else:
    _do_diffusion(...)
```

**Tests** (`tests/python/test_walk_operators_fn.py` [MOD]):
- `test_marked_node_gets_identity` — mark all nodes → walk step is identity
- `test_unmarked_node_gets_diffusion` — no marking → standard diffusion (existing)
- `test_partial_marking` — some nodes marked, some not → correct selective diffusion
- Verify via statevector that marked basis states are unchanged

**DEP**: Step 2b.2

---

### Step 2b.4: Deduplicate Walk Operators

**Goal**: `walk_operators.py` should compose `walk_diffusion.py` for the actual
diffusion math, not reimplement it. Remove `_height_controlled_diffusion` and
`_height_controlled_variable_diffusion` — replace with calls to
`walk_diffusion_fixed` / `walk_diffusion_with_regs`.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_operators.py` | [MOD] Replace ~200 LOC of duplicated diffusion logic with calls to `walk_diffusion.py` functions. `_apply_local_diffusion` becomes a thin dispatch: height control + marking check + call to walk_diffusion. | ~-150 |
| `src/quantum_language/walk_diffusion.py` | [MOD] Ensure `walk_diffusion_fixed` accepts height control qubit parameter for controlled operation. | ~+20 |

**Tests**: All existing walk operator tests must pass. Verify no `_precompute_angles`
import in walk_operators.py (it should come through walk_diffusion).

**DEP**: Step 2b.3

---

### Step 2b.5: Rewrite walk_search.py

**Note**: This step changes the `walk()` signature from the current
`walk(is_marked, max_depth, num_moves)` returning `bool` to
`walk(state, make_move, is_valid, is_marked, *, max_depth, num_moves)`
returning `(config, registers)`. When this step lands, update PRD R12.1
to reflect the new signature.

**Goal**: Remove the wrong classical marking oracle and simulation-based detection.
Replace with a thin shell that builds the walk operator with marking.
Add TODO docstring for phase estimation detection.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/walk_search.py` | [MOD] Remove `_evaluate_is_marked_classically`, `_apply_phase_on_pattern`, `_apply_marking_phase`, `_simulate_statevector`, `_measure_root_overlap`, `_measure_root_overlap_unmarked`. Keep `walk()` as public API that builds a WalkConfig with `is_marked` and calls `walk_step`. Add TODO docstring for phase estimation. | ~-200 |
| `tests/python/test_walk_search.py` | [MOD] Remove tests for classical evaluation. Add tests for quantum marking integration (walk_step with is_marked produces correct operator). | ~-100, +50 |
| `tests/python/test_walk_integration.py` | [MOD] Update integration tests to match new API (no detection yet, test operator construction). | ~-50, +30 |

**`walk()` after rewrite**:
```python
def walk(state, make_move, is_valid, is_marked, *,
         max_depth, num_moves):
    """Build quantum walk operator with marking.

    Constructs the walk operator U = R_B * R_A where D_x = I for
    marked nodes (per Montanaro 2015). The operator can be used
    with phase estimation for detection.

    TODO: Phase estimation-based detection. Currently returns the
    WalkConfig and WalkRegisters for manual use.
    """
    config = WalkConfig(
        state=state, make_move=make_move, is_valid=is_valid,
        is_marked=is_marked, max_depth=max_depth, num_moves=num_moves,
    )
    registers = WalkRegisters(config)
    registers.init_root()
    return config, registers
```

**Tests**:
- `test_walk_returns_config_and_registers` — correct types returned
- `test_walk_operator_with_marking_preserves_norm` — walk_step on marked config is unitary
- `test_walk_operator_marking_identity_on_marked` — marked states unchanged after walk_step

**DEP**: Steps 2b.3, 2b.4

---

### Step 2b.6: Update Quantum Walk Skill

**Goal**: Update the `/quantum-walk` skill file to reflect corrected semantics.

| File | Action | ~LOC |
|------|--------|------|
| `.claude/commands/quantum-walk.md` | [MOD] Clarify: `is_marked` is quantum (returns qbool), marking = identity, no classical evaluation. Update API section for new `walk()` return type. | ~+15 |

**DEP**: Step 2b.5

---

### Phase 2b Summary

| Step | What | ~LOC delta | File(s) | DEP |
|------|------|------------|---------|-----|
| 2b.1 | Remove walk.py & old tests | ~-1620 impl, ~-2000 tests | `walk.py`, 10+ test files | — |
| 2b.2 | Replace emit_x with DSL | ~-60 | walk_branching/diffusion/operators/search/registers | 2b.1 |
| 2b.3 | Quantum marking in operators | ~+15 | `walk_operators.py` | 2b.2 |
| 2b.4 | Deduplicate operators | ~-130 | `walk_operators.py`, `walk_diffusion.py` | 2b.3 |
| 2b.5 | Rewrite walk_search.py | ~-220 | `walk_search.py`, tests | 2b.3, 2b.4 |
| 2b.6 | Update quantum walk skill | ~+15 | `quantum-walk.md` | 2b.5 |

**Parallelizable**: None — each step depends on the previous (incremental cleanup).

**Net result**: Significant LOC reduction, correct quantum semantics throughout,
clean module layering with no duplication.
