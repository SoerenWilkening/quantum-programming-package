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

## Phase 2c — Unify Diffusion Path ✅

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

### Step 2c.1: Marking on Variable-Branching Path ✅

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

### Step 2c.2: Remove Fixed Diffusion ✅

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

### Step 2c.3: Test Consolidation ✅

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

## Phase 3 — DSL Purity & Simulate-Mode Cleanup ✅

The `simulate` option is a **global setting** — internal helpers must never toggle it.
Currently, `_flip_all` and `diffusion()` locally toggle `simulate=True`, creating a
"mixed simulate mode" that masks bugs and prevents clean DSL replacements.

This phase removes all local toggles, adds controlled-AND support, and replaces
remaining raw gate patterns with pure DSL operations.

**Qubit budget**: Raised from 17 to 21. Verified: 21-qubit statevector simulation
takes ~0.2s (2M amplitudes), well within acceptable limits.

---

### Step 3.1: Remove Local Simulate Toggles ✅

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

### Step 3.2: Controlled-AND Support ✅

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

### Step 3.3: Replace _flip_all with Direct DSL Ops ✅

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

### Step 3.4: Replace Recursive Nested `with` Patterns ✅

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

### Step 3.5: Update Qubit Budget Assertions ✅

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

---

## Phase 4 — In-Place Comparison Operators ✅

Replaces the copy-based `<`/`>` comparisons with an in-place borrow-ancilla pattern.
Currently, `<` and `>` create (n+1)-bit temporary copies of both operands, perform
subtraction on the copies, and extract the MSB. The new approach: allocate a single
ancilla as a borrow bit, subtract in-place across `[a, ancilla]`, extract the result,
add back to restore, deallocate the ancilla. No copies, one temporary ancilla.

### Design Overview

**Current** (copy-based):
```
temp_a = copy(a, width=n+1)     # CNOT copy, widened
temp_b = copy(b, width=n+1)     # CNOT copy, widened
temp_a -= temp_b                # subtraction on copies
result = temp_a.msb             # extract sign
# temp_a, temp_b linger as history children
```

**New** (borrow-ancilla):
```
ancilla = qbool()               # |0⟩, acts as bit n (borrow)
(a, ancilla) -= b               # (n+1)-bit subtraction, ancilla captures borrow
result ^= ancilla               # extract borrow into result
(a, ancilla) += b               # restore a and ancilla
# ancilla back to |0⟩, deallocate
```

**Prerequisite**: The C-level adder/subtractor must accept a split register
(a qint's qubit array + a separate qbool qubit as the MSB). This requires
extending the arithmetic backend.

---

### Step 4.1: Split-Register Arithmetic Backend ✅

**Goal**: Extend the C-level subtraction and addition to operate across a qint
register plus an external qbool acting as the MSB. The subtractor/adder treats
`[a_0..a_{n-1}, ancilla_qubit]` as an (n+1)-bit register.

| File | Action | ~LOC |
|------|--------|------|
| `c_backend/include/types.h` | [MOD] Add `extra_msb_qubit` field to subtraction/addition parameters (or add a new function signature) | ~+5 |
| `c_backend/src/hot_path_add.c` | [MOD] Add split-register variant of Toffoli subtractor that accepts an external MSB qubit index | ~+40 |
| `c_backend/src/IntegerAddition.c` | [MOD] Add split-register variant for QFT-path subtractor | ~+30 |
| `src/quantum_language/_core.pxd` | [MOD] Expose new C function signatures to Cython | ~+5 |

**Tests** (`tests/c/test_split_register_arith.c` [NEW], ~150 LOC):
- `test_split_sub_borrow_set` — `[3, 0] - 5` in 4-bit → ancilla = 1 (underflow)
- `test_split_sub_no_borrow` — `[5, 0] - 3` in 4-bit → ancilla = 0
- `test_split_add_restore` — sub then add restores original + ancilla to 0
- `test_split_register_matches_widened` — results identical to full (n+1)-bit subtraction

**DEP**: None

---

### Step 4.2: Rewrite `__lt__` and `__gt__` ✅

**Goal**: Replace copy-based comparison with borrow-ancilla pattern using the
split-register arithmetic from Step 4.1.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint_comparison.pxi` | [MOD] Rewrite `__lt__` (CQ and QQ paths): allocate ancilla qbool, split-register subtraction, extract borrow, split-register addition to restore, deallocate ancilla. Remove CNOT copy logic and widened temporary creation. Same for `__gt__`. | ~-80, +50 |

**Tests** (`tests/python/test_inplace_comparison.py` [NEW], ~200 LOC):
- `test_lt_correctness` — exhaustive check for small widths (3-bit): all a < b pairs
- `test_gt_correctness` — exhaustive check for small widths
- `test_le_ge_derived` — `<=` and `>=` work via `~(>)` / `~(<)`
- `test_operand_preservation` — both operands unchanged after comparison (statevector)
- `test_no_history_children` — result qbool has no history children (no temporaries)
- `test_ancilla_deallocated` — qubit count after comparison matches qubit count before + 1 (result only)
- `test_comparison_in_with_block` — `with (a < b): c += 1` works correctly
- `test_comparison_superposition` — comparison on superposition state produces correct amplitudes

**DEP**: Step 4.1

---

### Step 4.3: Remove Widened Temporary Logic ✅

**Goal**: Clean up the old copy-based comparison code paths. Remove CNOT copy
helpers if they were only used by comparisons.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint_comparison.pxi` | [MOD] Remove `_copy_to_widened` helper and related CNOT copy logic if unused elsewhere. Remove `history.add_child(temp_self)` / `history.add_child(temp_other)` patterns. | ~-60 |

**Tests**: All existing comparison tests pass. No behavioral regression.

**DEP**: Step 4.2

---

### Phase 4 Summary

| Step | What | ~LOC delta | DEP | Status |
|------|------|------------|-----|--------|
| 4.1 | Split-register arithmetic backend | ~+80 | — | ✅ |
| 4.2 | Rewrite `__lt__` and `__gt__` | ~-30 | 4.1 | ✅ |
| 4.3 | Remove widened temporary logic | ~-60 | 4.2 | ✅ |

**Net**: ~-10 LOC implementation, significant qubit reduction per comparison.

---

## Phase 5 — Compiled Function Control Propagation ✅

Reworks the `@ql.compile` pipeline to decouple sequence generation from execution,
ensuring correct control propagation from `with` blocks on every call (including
the first). The previous approach (capture-then-derive) emitted uncontrolled gates
on the first call inside a `with` block. The new approach separates compilation
(sequence generation) from execution (`run_instruction`), storing both controlled
and uncontrolled sequences per instruction.

### Design Overview

**Previous behavior** (broken — steps 5.1–5.3 old were partially implemented):
- Capture cleared control stack → uncontrolled gates emitted to circuit on first call.
- `_derive_controlled_block` created controlled variant post-hoc.
- First call inside `with` always emitted uncontrolled gates (accepted trade-off).
- Replay correctly selected controlled/uncontrolled, but first call was wrong.

**New behavior** (two-step rework):
- **Standardized sequences**: Virtual index 0 is always reserved for the control
  qubit. Uncontrolled sequences don't reference index 0; controlled sequences add
  index 0 as control to each gate. This uniform layout makes control injection a
  simple qubit mapping operation.
- **Compile phase**: Function body executes — DSL operators (`+=`, `<`, etc.)
  trigger sequence generation (`CQ_add`, `CQ_sub`, etc.) but `run_instruction`
  is NOT called. Each instruction is stored as IR:
  `(name, registers, uncontrolled_seq, controlled_seq)`.
- **Execute phase**: Walk the instruction IR, call `run_instruction` with the
  qubit mapping. If inside a `with` block, map index 0 → control qubit to select
  the controlled sequence. If uncontrolled, index 0 is unmapped (never referenced).
- **Nested `with`**: Collapses to single control via AND-ancilla (Toffoli).
  Single control slot (index 0) suffices for all nesting depths.
- **Compiled flag**: Prevents recompilation on subsequent calls.

---

### Step 5.1: Standardize Virtual Qubit Layout *(control at index 0)* ✅

**Goal**: Reserve virtual index 0 for the control qubit in all gate sequences.
Rework the virtual qubit mapping, `param_qubit_ranges` format, and controlled
block derivation. After this step, all `CompiledBlock` instances use the same
virtual qubit layout regardless of whether they are controlled or not.

**Layout change**:
```
Before: [param_a(0..2) | param_b(3..5) | ancillas(6..7)] → control appended at 8
After:  [control(0) | param_a(1..3) | param_b(4..6) | ancillas(7..8)]
```

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile.py` | [MOD] `_build_virtual_mapping`: start `virtual_idx = 1` (reserve 0). | ~+1 |
| `src/quantum_language/compile.py` | [MOD] `_capture_inner`: build `param_ranges` with `(start, end)` format, `vidx` starts at 1. | ~+5, -3 |
| `src/quantum_language/compile.py` | [MOD] `CompiledBlock` docstring: update `param_qubit_ranges` to `(start_virtual_idx, end_virtual_idx)`. | ~+2 |
| `src/quantum_language/compile.py` | [MOD] `_derive_controlled_block`: use `control_virt_idx = 0`, do NOT increment `total_virtual_qubits` (slot already reserved). | ~+3, -5 |
| `src/quantum_language/compile.py` | [MOD] `_derive_controlled_gates`: hardcode control index to 0. | ~+1, -1 |
| `src/quantum_language/compile.py` | [MOD] `_replay`: map index 0 → control qubit when controlled (before param loop); params start at index 1; `expected_param_qubits` uses `(end - start)` sum. | ~+10, -8 |
| `src/quantum_language/compile.py` | [MOD] All consumers of `param_qubit_ranges`: update from `(start, width)` to `(start, end)` format. Affected: `_replay` validation, inverse block construction, merged block construction. | ~+5, -5 |

**Tests** (`tests/python/test_compile_standardized.py` [NEW], ~150 LOC):
- `test_virtual_index_zero_reserved` — captured block's gates never reference virtual index 0 in target or controls
- `test_controlled_block_uses_index_zero` — controlled variant's gates all have 0 in their controls list
- `test_total_virtual_qubits_same` — uncontrolled and controlled blocks have same `total_virtual_qubits`
- `test_param_ranges_start_end_format` — `param_qubit_ranges` uses `(start, end)` tuples
- `test_param_ranges_start_at_one` — first param range starts at virtual index 1
- `test_replay_controlled_vs_uncontrolled` — replay inside `with` produces different gates than replay outside
- `test_replay_ancilla_allocation` — ancilla loop skips index 0, allocates correctly

**DEP**: None

---

### Step 5.2a: Compile-Mode Infrastructure ✅

**Goal**: Add the foundational data structures for instruction-level IR recording.
Compile-mode flag on `CompiledFunc`, `InstructionRecord` dataclass, and
`_instruction_ir` list on `CompiledBlock`. No behavioral change yet — just the
infrastructure that subsequent steps wire into.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile.py` | [MOD] Add `InstructionRecord` dataclass: `(name, registers, uncontrolled_seq, controlled_seq)`. | ~+15 |
| `src/quantum_language/compile.py` | [MOD] Add `_instruction_ir` list to `CompiledBlock.__slots__` and `__init__`. | ~+3 |
| `src/quantum_language/compile.py` | [MOD] Add compile-mode flag (`_compile_mode`) to `CompiledFunc` with context manager or setter to activate/deactivate. | ~+15 |

**Tests** (`tests/python/test_compile_ir_infra.py` [NEW], ~60 LOC):
- `test_instruction_record_fields` — `InstructionRecord` stores name, registers, both sequences
- `test_compiled_block_has_ir_list` — `CompiledBlock._instruction_ir` is an empty list by default
- `test_compile_mode_flag` — flag can be set/unset on `CompiledFunc`

**DEP**: Step 5.1

---

### Step 5.2b: Record Instructions in DSL Operators ✅

**Goal**: Modify DSL operators (`+=`, `-=`, `<`, `&`, etc.) to check the
compile-mode flag. When set, generate the sequence (`CQ_add` etc.) but do NOT
call `run_instruction`. Instead, record an `InstructionRecord` into the active
`CompiledBlock._instruction_ir` list.

**Key change**: Each DSL operator already calls a C function to generate a
`sequence_t` (e.g., `CQ_add(self_bits, classical_value)`), then calls
`run_instruction(seq, ...)`. In compile mode, the second call is skipped and
the sequence is stored as IR instead.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint_arithmetic.pxi` | [MOD] In `__iadd__`, `__isub__`, `__imul__`, etc.: check compile-mode flag, record `InstructionRecord` instead of calling `run_instruction`. | ~+15 |
| `src/quantum_language/qint_comparison.pxi` | [MOD] Same compile-mode check in `__eq__`, `__lt__`, `__gt__`. | ~+10 |
| `src/quantum_language/qint_bitwise.pxi` | [MOD] Same compile-mode check in `__and__`, `__or__`, `__xor__`, `__ixor__`. | ~+10 |

**Tests** (`tests/python/test_compile_ir_recording.py` [NEW], ~120 LOC):
- `test_compile_records_ir` — compiled function produces `InstructionRecord` entries
- `test_ir_entry_per_instruction` — `a += 1; a += 2` produces 2 IR entries
- `test_run_instruction_not_called` — no gates emitted to circuit during compile phase
- `test_ir_stores_sequence` — each IR entry has a valid `sequence_t` (uncontrolled)
- `test_compile_mode_only_during_capture` — compile-mode flag is unset after compilation completes

**DEP**: Step 5.2a

---

### Step 5.2c: Execute Phase *(uncontrolled)* ✅

**Goal**: Add the execute phase that walks the instruction IR and calls
`run_instruction` for each entry. This step handles uncontrolled execution only
— the compiled function works correctly outside `with` blocks.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile.py` | [MOD] Add `_execute_ir(block, qubit_mapping)`: iterate `block._instruction_ir`, call `run_instruction(entry.uncontrolled_seq, qubit_mapping)` for each entry. | ~+25 |
| `src/quantum_language/compile.py` | [MOD] Wire `_execute_ir` into `_capture_and_cache_both` and `_replay` so that after compilation, the IR is executed. Compiled flag prevents recompilation on subsequent calls. | ~+15 |

**Tests** (`tests/python/test_compile_ir_execute.py` [NEW], ~100 LOC):
- `test_execute_emits_gates` — execute phase produces gates in circuit
- `test_execute_matches_direct` — compiled function produces same result as uncompiled equivalent
- `test_compiled_flag_prevents_recompile` — second call skips compilation, replays from IR
- `test_execute_gate_count` — gate count matches expected value

**DEP**: Step 5.2b

---

### Step 5.2d: Controlled Execution *(control injection via index 0)* ✅

**Goal**: Extend the execute phase to handle controlled context. Derive
controlled sequences (add index 0 as control to each gate) and store both
variants per instruction. During execution inside a `with` block, select the
controlled sequence and map index 0 → control qubit.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile.py` | [MOD] In `_execute_ir`: check `_get_controlled()`. If controlled, use `entry.controlled_seq` and map index 0 → `_get_control_bool().qubits[63]`. If uncontrolled, use `entry.uncontrolled_seq`. | ~+15 |
| `src/quantum_language/compile.py` | [MOD] During IR recording (step 5.2b): derive `controlled_seq` from `uncontrolled_seq` by adding index 0 as control to each gate. Store both on `InstructionRecord`. | ~+10 |

**Tests** (`tests/python/test_compile_ir_controlled.py` [NEW], ~150 LOC):
- `test_ir_has_both_sequences` — each IR entry has both controlled and uncontrolled sequences
- `test_execute_controlled` — execute inside `with` block uses controlled sequences
- `test_execute_uncontrolled` — execute outside `with` block uses uncontrolled sequences
- `test_first_call_in_with_correct` — first call of compiled function inside `with` produces controlled gates (the original bug fix)
- `test_nested_with_compiled` — `with c1: with c2: f(x)` produces correct combined-controlled gates
- `test_controlled_vs_uncontrolled_different_gates` — controlled call produces more gates than uncontrolled

**DEP**: Step 5.2c

---

### Step 5.3: `opt=1` and DAG Integration ✅

**Goal**: Ensure `opt=1` (DAG-only) mode works with the new pipeline. DAG nodes
record control context. The instruction IR is compatible with DAG building.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile.py` | [MOD] In `opt=1` path: build DAG nodes from instruction IR. Record control context in DAG node metadata. | ~+15 |
| `src/quantum_language/call_graph.py` | [MOD] `DAGNode` stores `controlled` flag from IR execution context. | ~+5 |

**Tests** (`tests/python/test_compile_dag_control.py` [NEW], ~100 LOC):
- `test_opt1_dag_records_control` — DAG node metadata indicates controlled call
- `test_opt1_ir_compatible` — instruction IR integrates with DAG building
- `test_opt1_no_gate_emission` — `opt=1` with `simulate=False` still records IR without emitting

**DEP**: Step 5.2d

---

### Phase 5 Summary

| Step | What | ~LOC delta | DEP | Status |
|------|------|------------|-----|--------|
| 5.1 | Standardize virtual qubit layout (control at index 0) | ~+10 | — | ✅ |
| 5.2a | Compile-mode infrastructure (flag, `InstructionRecord`, IR list) | ~+33 | 5.1 | ✅ |
| 5.2b | Record instructions in DSL operators (no `run_instruction` in compile mode) | ~+35 | 5.2a | ✅ |
| 5.2c | Execute phase — uncontrolled IR execution | ~+40 | 5.2b | ✅ |
| 5.2d | Controlled execution — control injection via index 0 | ~+25 | 5.2c | ✅ |
| 5.3 | `opt=1` and DAG integration | ~+20 | 5.2d | ✅ |

**Parallelizable**: None — steps are sequential (each builds on the previous).

**Net**: ~+163 LOC implementation, ~+530 LOC tests.

**Key property**: After this phase, calling a compiled function inside a `with`
block produces controlled gates on every call — including the first. No
"uncontrolled first call" trade-off.

---

## Phase 5b — Compile Replay Bug Fixes ✅

Fixes correctness bugs in the compile replay path (cache-hit execution inside
`with` blocks) and updates stale test assertions that no longer match current
behavior after Phase 5 changes.

### Step 5b.1: Fix Compile Replay Inside `with` Blocks ✅

Fixed `_replay` to route through `_execute_ir` when IR entries exist, correctly
handling controlled sequences. Added `_last_replay_used_ir` flag to prevent gate
count double-counting (IR path via `run_instruction` already increments
`circ->gate_count`). Restored opt=1 uncontrolled replay skip while preserving
gate injection for controlled contexts.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile.py` | [MOD] `_replay`: IR path routes through `_execute_ir` with capture→replay qubit mapping. Gate count credit conditional on `_last_replay_used_ir`. opt=1 skips injection only when uncontrolled. | ~+40 |
| `tests/python/test_compile_dag_only.py` | [MOD] Restored strong assertions, fixed simulate mode handling. | ~+20 |
| `tests/python/test_tracking_only.py` | [MOD] Updated to expect `simulate=True` default, explicit `simulate=False` where needed. | ~+15 |

**DEP**: Phase 5 (all steps completed)

---

### Step 5b.2: Update Stale Test Assertions ✅

| File | Action | ~LOC |
|------|--------|------|
| `tests/python/test_compile_nested_with.py` | [MOD] `test_first_call_trade_off`: expected result 1→0, updated docstring. | ~+5, -5 |
| `tests/python/test_api_coverage.py` | [MOD] `test_qint_default_width`: expected width 8→3. | ~+1, -1 |

**DEP**: None

---

### Phase 5b Summary

| Step | What | ~LOC delta | DEP | Status |
|------|------|------------|-----|--------|
| 5b.1 | Fix compile replay inside `with` blocks | ~+40 | Phase 5 | ✅ |
| 5b.2 | Update stale test assertions | ~0 | — | ✅ |

**Net**: ~+75 LOC, 6 previously failing tests now pass.

---

## Phase 5c — Call Graph Deduplication & Simulate Replay ✅

Fixes two issues: (1) the call graph duplicates instruction nodes on each call
to a compiled function, and (2) `opt=1` incorrectly skips gate injection on
uncontrolled replays even when `simulate=True`.

### Problem A — Call graph duplicates nodes on each call

When a compiled function is called multiple times (e.g., first uncontrolled, then
inside a `with` block), `_build_dag_from_ir` runs on every replay and appends new
instruction nodes each time. The call graph should capture the instructions within
the function **once** — subsequent calls should not add more nodes.

Each instruction's `InstructionRecord` already has both `uncontrolled_seq` and
`controlled_seq` pointers. The DAGNode should store both and display both gate
counts: `"gates: 24 / 18"` (uncontrolled / controlled), with `"-"` when a
variant's pointer is 0.

### Problem B — Uncontrolled replay skips gate injection with simulate=True

`_skip_injection = self._opt == 1 and not is_controlled` skips gate injection
for all opt=1 uncontrolled replays, regardless of simulate mode. This is correct
for tracking-only mode (`simulate=False`) but wrong when `simulate=True` — the
user expects gates in the circuit for every call.

---

### Step 5c.1: Cython helper for sequence gate count

**Goal**: Add a Python-callable function to read `total_gate_count` from a
`sequence_t` pointer, so DAGNode can resolve gate counts from both sequence
pointers.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/_core.pyx` | [MOD] Add `def _sequence_gate_count(seq_ptr: int) -> int` that casts to `sequence_t*` and returns `total_gate_count`. Returns 0 for null pointer. | ~+10 |

**Tests**: Unit test calling `_sequence_gate_count` on a known sequence pointer.

**DEP**: None

---

### Step 5c.2: Dual gate counts on DAGNode

**Goal**: Each DAGNode stores both `uncontrolled_seq` and `controlled_seq`
pointers plus resolved gate counts for each. `to_dot()` and `report()` display
both: `"gates: 24 / 18"`, `"-"` for unavailable.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/call_graph.py` | [MOD] Add `uncontrolled_gate_count` and `controlled_gate_count` fields to `DAGNode`. Update `_node_label()` in `to_dot()` and column in `report()` to show `"X / Y"` format with `"-"` for 0. | ~+30 |

**Tests**:
- `test_dag_node_dual_gate_counts` — node with both pointers shows both counts
- `test_dag_node_single_variant` — node with only uncontrolled shows `"24 / -"`
- `test_to_dot_dual_format` — `to_dot()` output contains `"gates: X / Y"`

**DEP**: Step 5c.1

---

### Step 5c.3: Build DAG once per compiled function

**Goal**: `_build_dag_from_ir` only runs on the first call (capture). Store both
sequence pointers per node. Subsequent calls (controlled or uncontrolled replays)
do NOT append additional nodes.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile.py` | [MOD] In `_call_inner`, skip `_build_dag_from_ir` on replay when DAG already has nodes for this function. In `_build_dag_from_ir`, store both `uncontrolled_seq` and `controlled_seq` from `InstructionRecord` (instead of selecting one based on `is_controlled`). | ~+15 |

**Tests**:
- `test_dag_no_duplicate_nodes` — call foo() uncontrolled then controlled; DAG has N instruction nodes (not 2N)
- `test_dag_both_seq_stored` — each node has both sequence pointers from IR

**DEP**: Step 5c.2

---

### Step 5c.4: Fix simulate=True replay gate injection

**Goal**: Gate injection skip only applies when `simulate=False`. With
`simulate=True`, all replays inject gates.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile.py` | [MOD] Change `_skip_injection = self._opt == 1 and not is_controlled` to `_skip_injection = self._opt == 1 and not is_controlled and not option("simulate")`. | ~+1 |

**Tests**:
- `test_simulate_true_uncontrolled_replay_injects` — with simulate=True, calling foo() 3 times produces gates for all 3 calls
- `test_simulate_false_uncontrolled_replay_skips` — with simulate=False, replay still skips (DAG-only mode preserved)

**DEP**: Phase 5b

---

### Step 5c.5: Toffoli-Mode Gate Count Propagation

**Goal**: In Toffoli mode, `record_operation` populates `uncontrolled_gate_count`
(or `controlled_gate_count` when in controlled context) so the DAG report shows
actual counts instead of `"- / -"`.

**Root cause**: `record_operation()` passes `gate_count=gc_delta` to `add_node()`,
but never passes `uncontrolled_gate_count` or `controlled_gate_count`. The
`report()` method reads the dual fields (both default to 0), and
`_format_dual_gates(0, 0)` renders as `"- / -"`. Meanwhile `aggregate()` uses
`node.gate_count` which IS populated — so the total row is correct.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/call_graph.py` | [MOD] `record_operation()`: accept `controlled` bool parameter. When not controlled, pass `uncontrolled_gate_count=gate_count`. When controlled, pass `controlled_gate_count=gate_count`. Also accept and pass through `depth` and `t_count` parameters. | ~+10 |
| `src/quantum_language/qint_arithmetic.pxi` | [MOD] In Toffoli dispatch path: compute depth and T-count from sequence BEFORE `toffoli_sequence_free`. Pass to `_record_operation`. | ~+15 |
| `src/quantum_language/qint_comparison.pxi` | [MOD] Same pattern for comparison operations. | ~+10 |
| `src/quantum_language/qint_bitwise.pxi` | [MOD] Same pattern for bitwise operations. | ~+10 |

**Tests** (`tests/python/test_dag_gate_counts.py` [MOD]):
- `test_toffoli_report_nonzero` — `report()` output shows non-zero gate counts (not `"- / -"`)
- `test_toffoli_uncontrolled_gate_count` — uncontrolled call populates `uncontrolled_gate_count`
- `test_toffoli_controlled_gate_count` — call inside `with` populates `controlled_gate_count`
- `test_toffoli_depth_nonzero` — depth field is populated from sequence data
- `test_toffoli_t_count_nonzero` — T-count field is populated

**DEP**: Step 5c.2

---

### Phase 5c Summary

| Step | What | ~LOC delta | DEP |
|------|------|------------|-----|
| 5c.1 | Cython helper for sequence gate count | ~+10 | — | ✅ |
| 5c.2 | Dual gate counts on DAGNode | ~+30 | 5c.1 | ✅ |
| 5c.3 | Build DAG once per compiled function | ~+15 | 5c.2 | ✅ |
| 5c.4 | Fix simulate=True replay gate injection | ~+1 | Phase 5b | ✅ |
| 5c.5 | Toffoli-mode gate count propagation | ~+45 | 5c.2 | ✅ |

**Parallelizable**: Steps 5c.4 and 5c.5 are independent of each other and of 5c.3.

**Net**: ~+101 LOC implementation. Call graph no longer duplicates on repeated calls. Both gate count variants visible in all arithmetic modes. Simulate=True replays work correctly.

---

## Phase 6 — History Graph Inverse Cancellation ✅

Adds automatic detection and cancellation of manual uncomputation in the
history graph, reducing unnecessary gate overhead when users explicitly reverse
their own operations.

### Design Overview

**Core rule**: When an operation is appended to a qint's history, check if it is
the exact inverse of the tail entry. If yes and no active blockers exist after
that entry, cancel both (remove tail, skip append).

**Blocker mechanism**: When a qint is used as a source operand (RHS of any
operation), a blocker referencing the dependent qint is appended to the source
qint's history. Blockers are cleared when the dependent qint's qubits are
deallocated (uncomputed). This prevents incorrect cancellation when intermediate
state has been read by other qints.

---

### Step 6.1: Blocker Data Structure

**Goal**: Add a `Blocker` type to the history graph. Blockers hold a reference
to the dependent qint and can be queried for liveness (is the dependent qint's
qubits still allocated?).

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/history_graph.py` | [MOD] Add `Blocker` class with `dependent_ref` (reference to qint), `is_active` property (checks qubit allocation status). Add `add_blocker(dependent)` method to `HistoryGraph`. Add `active_blockers_after(index)` query. | ~+40 |

**Tests** (`tests/python/test_history_blockers.py` [NEW], ~120 LOC):
- `test_blocker_active_while_allocated` — blocker is active when dependent qint exists with qubits
- `test_blocker_inactive_after_deallocation` — blocker becomes inactive after dependent's qubits deallocated
- `test_add_blocker` — blocker added to history graph
- `test_active_blockers_after` — query returns only blockers after given index
- `test_multiple_blockers` — multiple blockers from different dependents

**DEP**: None (builds on existing HistoryGraph)

---

### Step 6.2: Blocker Insertion on Source Operand Usage

**Goal**: Every time a qint is used as a source operand (RHS of an operation),
add a blocker to its history graph referencing the result/destination qint.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint_arithmetic.pxi` | [MOD] In `__add__`, `__sub__`, `__mul__`, `__iadd__`, `__isub__`, etc.: after operation, call `other.history.add_blocker(result)` for each source operand. | ~+25 |
| `src/quantum_language/qint_comparison.pxi` | [MOD] In `__eq__`, `__lt__`, `__gt__`: add blockers to source operands. | ~+10 |
| `src/quantum_language/qint_bitwise.pxi` | [MOD] In `__and__`, `__or__`, `__xor__`: add blockers to source operands. | ~+10 |

**Tests** (`tests/python/test_blocker_insertion.py` [NEW], ~150 LOC):
- `test_add_creates_blocker` — `b = a + c` adds blocker to `a` and `c`
- `test_iadd_creates_blocker` — `a += b` adds blocker to `b` (not `a`, since `a` is modified)
- `test_comparison_creates_blocker` — `r = (a < b)` adds blockers to `a` and `b`
- `test_xor_creates_blocker` — `a ^= b` adds blocker to `b`
- `test_no_self_blocker` — in-place operations don't add blocker to self

**DEP**: Step 6.1

---

### Step 6.3: Qubit Deallocation Notification

**Goal**: When a qint's qubits are deallocated (during uncomputation or
explicit cleanup), notify all qints that have blockers referencing it. Blockers
check qubit allocation status — no explicit notification list needed if the
`is_active` check queries the qint's allocation state directly.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/history_graph.py` | [MOD] `Blocker.is_active` checks `dependent_ref.qubits_allocated` (or equivalent). No explicit notification needed if this is a live query. | ~+5 |
| `src/quantum_language/qint.pyx` | [MOD] Add `qubits_allocated` property (True if qint has live qubit assignments). | ~+5 |

**Tests** (`tests/python/test_blocker_lifecycle.py` [NEW], ~100 LOC):
- `test_blocker_live_query` — blocker reports active/inactive based on real-time qubit state
- `test_del_clears_blocker` — after `del b` (and GC/uncomputation), blocker on `a` becomes inactive
- `test_with_exit_clears_blocker` — qbool uncomputed in `__exit__` clears its blockers

**DEP**: Step 6.1

---

### Step 6.4: Tail-Only Inverse Cancellation

**Goal**: In the history graph's append path, check if the new entry is the
exact inverse of the tail entry. If yes and no active blockers after the tail,
cancel both.

**Inverse matching rules**:
- Addition sequence ptr + subtraction sequence ptr with same qubit mapping → cancel
- XOR with same operand and qubit mapping → cancel (self-inverse)
- Compiled function sequence ptr + its adjoint sequence ptr → cancel

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/history_graph.py` | [MOD] Add `_is_inverse(entry_a, entry_b)` matcher. Modify `append()`: if tail exists and `_is_inverse(tail, new_entry)` and `not active_blockers_after(tail_index)`, pop tail and skip append. | ~+35 |

**Tests** (`tests/python/test_inverse_cancellation.py` [NEW], ~200 LOC):
- `test_add_sub_cancel` — `a += 3; a -= 3` → empty history
- `test_sub_add_cancel` — `a -= 3; a += 3` → empty history
- `test_xor_self_cancel` — `a ^= 5; a ^= 5` → empty history
- `test_no_cancel_different_values` — `a += 3; a -= 5` → two entries
- `test_no_cancel_with_blocker` — `a += 3; b += a; a -= 3` → no cancellation
- `test_cancel_after_blocker_cleared` — `a += 3; b += a; del b; a -= 3` → cancels
- `test_compiled_inverse_cancel` — `f(a); f.inverse(a)` → empty history
- `test_no_cancel_non_tail` — `a += 3; a += 5; a -= 3` → three entries (not tail match)
- `test_chain_cancellation` — `a += 3; a += 5; a -= 5; a -= 3` → each pair cancels in sequence → empty
- `test_gate_count_reduction` — cancelled operations produce fewer gates in final circuit

**DEP**: Steps 6.2, 6.3

---

### Step 6.5: Compiled Function Inverse Cancellation

**Goal**: Extend inverse matching to recognize compiled function calls and their
inverses. `f(a)` records a history entry with the function's sequence pointer;
`f.inverse(a)` should recognize this as the inverse and cancel.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/history_graph.py` | [MOD] Extend `_is_inverse` to match forward/adjoint sequence pointer pairs. | ~+15 |
| `src/quantum_language/compile.py` | [MOD] When `f.inverse(a)` is called, pass the forward sequence pointer to history so the matcher can identify the pair. | ~+10 |

**Tests** (`tests/python/test_inverse_cancellation.py` [MOD]):
- `test_compiled_fn_cancel` — `f(a); f.inverse(a)` → cancels
- `test_compiled_fn_no_cancel_different_args` — `f(a); g.inverse(a)` → no cancel
- `test_compiled_fn_blocker` — `f(a); b += a; f.inverse(a)` → no cancel

**DEP**: Step 6.4

---

### Phase 6 Summary

| Step | What | ~LOC delta | DEP |
|------|------|------------|-----|
| 6.1 | Blocker data structure | ~+40 | — | ✅ |
| 6.2 | Blocker insertion on source operand usage | ~+45 | 6.1 | ✅ |
| 6.3 | Qubit deallocation notification | ~+10 | 6.1 | ✅ |
| 6.4 | Tail-only inverse cancellation | ~+35 | 6.2, 6.3 | ✅ |
| 6.5 | Compiled function inverse cancellation | ~+25 | 6.4 | ✅ (wired via `compile/_replay.py`) |

**Parallelizable**: Steps 6.2 and 6.3 are independent (both depend only on 6.1).

**Net**: ~+155 LOC implementation, ~+570 LOC tests.

**Future** (not in this phase): `*= k` / `//= k` inverse cancellation.

---

## Phase 7 — Compile Subpackage Refactor ✅

Splits the monolithic `compile.py` (2,293 lines) into a `compile/` subpackage.
Pure refactor — no behavioral changes. All existing tests must pass without
modification after each step.

**Target structure** (each module ≤ 600 lines):

```
src/quantum_language/compile/
├── __init__.py      ~110 LOC  Public compile() decorator, re-exports
├── _block.py         ~80 LOC  CompiledBlock, AncillaRecord data classes
├── _func.py         ~500 LOC  CompiledFunc (init, __call__, _call_inner, cache, properties)
├── _capture.py      ~350 LOC  _capture, _capture_inner, _capture_and_cache_both, _derive_controlled_block
├── _replay.py       ~250 LOC  _replay, _apply_merge, merge support
├── _optimize.py     ~280 LOC  Gate optimization, adjoint helpers, controlled derivation, merge_and_optimize
├── _virtual.py      ~200 LOC  _build_virtual_mapping, _remap_gates, return value builders, qubit index helpers
├── _parametric.py   ~250 LOC  Parametric topology extraction and lifecycle (_parametric_call)
├── _inverse.py      ~170 LOC  _InverseCompiledFunc, _AncillaInverseProxy
└── _ir.py           ~120 LOC  _execute_ir, _build_dag_from_ir, IR execution helpers
```

**Design constraints**:
- `_compile_state.py` stays as-is (dependency-free, avoids circular imports with Cython)
- `call_graph.py` stays as-is (independent module, 749 lines — within tolerance)
- Public API is `compile/__init__.py` which re-exports everything that `compile.py` exported
- Internal cross-references use relative imports within the subpackage

---

### Step 7.1: Create Subpackage Skeleton and Move Types

**Goal**: Create `compile/` directory, move `CompiledBlock`, `AncillaRecord`,
constants, and mode flag helpers. Update internal imports. The old `compile.py`
becomes a thin shim importing from the subpackage until all moves are complete.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/__init__.py` | [NEW] Public API: re-export `compile` decorator, `CompiledFunc`, `_clear_all_caches`. Backward-compatible with `from quantum_language.compile import ...`. | ~40 |
| `src/quantum_language/compile/_block.py` | [NEW] Move `CompiledBlock`, `AncillaRecord`, gate type constants (`_X`, `_Y`, etc.), `_MAX_CAPTURE_DEPTH`, `_capture_depth` tracking. | ~100 |
| `src/quantum_language/compile.py` | [MOD] Becomes thin shim: `from .compile import *` (temporary, removed in Step 7.5). | ~5 |

**Tests**: All existing tests pass. `from quantum_language.compile import CompiledFunc` works.

**DEP**: None

---

### Step 7.2: Extract Optimization and Virtual Mapping Helpers

**Goal**: Move gate optimization functions and virtual qubit mapping into
dedicated modules. These are pure functions with no dependency on `CompiledFunc`.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_optimize.py` | [NEW] Move `_optimize_gate_list`, `_gates_cancel`, `_gates_merge`, `_merged_gate`, `_adjoint_gate`, `_inverse_gate_list`, `_derive_controlled_gates`, `_strip_control_qubit`, `_merge_and_optimize`. | ~280 |
| `src/quantum_language/compile/_virtual.py` | [NEW] Move `_build_virtual_mapping`, `_remap_gates`, `_get_qint_qubit_indices`, `_get_qarray_qubit_indices`, `_get_quantum_arg_qubit_indices`, `_build_return_qint`, `_build_return_qarray`, `_build_qubit_set_numpy`, `_input_qubit_key`. | ~200 |

**Tests**: All existing tests pass.

**DEP**: Step 7.1

---

### Step 7.3: Extract Capture and Replay Logic

**Goal**: Move `CompiledFunc`'s capture and replay methods into separate modules.
These become standalone functions that take `CompiledFunc` (or its data) as a
parameter, or remain as methods imported via mixin pattern.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_capture.py` | [NEW] Move `_capture`, `_capture_inner`, `_capture_and_cache_both`, `_derive_controlled_block` and related helpers. | ~350 |
| `src/quantum_language/compile/_replay.py` | [NEW] Move `_replay`, `_apply_merge`, merge-related helpers. | ~250 |
| `src/quantum_language/compile/_ir.py` | [NEW] Move `_execute_ir`, `_build_dag_from_ir`, `_run_instruction_py` and IR execution helpers. | ~120 |

**Tests**: All existing tests pass.

**DEP**: Step 7.2

---

### Step 7.4: Extract Parametric and Inverse Modules

**Goal**: Move the parametric lifecycle and inverse proxy classes into their own
modules. These are the most self-contained pieces.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_parametric.py` | [NEW] Move `_extract_topology`, `_extract_angles`, `_apply_angles`, `_parametric_call` and the parametric state machine. | ~250 |
| `src/quantum_language/compile/_inverse.py` | [NEW] Move `_InverseCompiledFunc`, `_AncillaInverseProxy`. | ~170 |

**Tests**: All existing tests pass.

**DEP**: Step 7.3

---

### Step 7.5: Consolidate CompiledFunc and Remove Shim

**Goal**: The remaining `CompiledFunc` class (init, `__call__`, `_call_inner`,
`_classify_args`, cache management, properties) moves to `_func.py`. Remove the
old `compile.py` shim. Update all external imports.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_func.py` | [NEW] `CompiledFunc` class with core methods. Imports capture/replay/parametric/inverse from sibling modules. | ~500 |
| `src/quantum_language/compile/__init__.py` | [MOD] Final public API: import from `_func`, `_block`, expose `compile` decorator. | ~110 |
| `src/quantum_language/compile.py` | [DEL] Remove the old shim file. | -5 |
| `src/quantum_language/__init__.py` | [MOD] Update import path if needed (should be transparent via subpackage `__init__`). | ~+2 |

**Tests**: All existing tests pass. No `compile.py` file exists (only `compile/` directory).

**DEP**: Step 7.4

---

### Phase 7 Summary

| Step | What | ~LOC delta | DEP |
|------|------|------------|-----|
| 7.1 | Subpackage skeleton + types | ~+145 | — | ✅ |
| 7.2 | Optimization + virtual mapping modules | ~+480 | 7.1 | ✅ |
| 7.3 | Capture, replay, IR modules | ~+720 | 7.2 | ✅ |
| 7.4 | Parametric + inverse modules | ~+420 | 7.3 | ✅ |
| 7.5 | Consolidate CompiledFunc, remove shim | ~+612, -2293 | 7.4 | ✅ |

**Net**: ~+84 LOC (slight growth from module boilerplate/imports).
All modules within 600-line limit. `_func.py` split into `_func.py`, `_dispatch.py`, and `_registry.py`. Stale `compile.py` removed.

---

## Phase 8 — Compiled Function Ancilla Model ✅

Fixes the compile layer's ancilla tracking so that repeated calls to a compiled
function do not grow the total qubit count when the function has no persistent
result qubits. The root cause: the compile layer allocates fresh qubits for
transient ancillas (carry bits, temp registers) that the C layer already manages
internally via `allocator_alloc`/`allocator_free` during `run_instruction`.

### Design Overview

**Three categories of non-parameter qubits in a CompiledBlock**:

1. **Result qubits** — Part of the return value (e.g., `c = a * b` returns `c`).
   Still allocated when capture completes. Must be freshly allocated on each replay.
2. **Transient ancillas** — Freed by the C allocator during the operation (carry bits,
   temp registers in CDKM adders). Appear in the captured gate list but are not alive
   when capture completes. IR replay should NOT allocate them (C manages its own).
3. **Persistent ancillas** — Allocated during capture and not freed, but also not part
   of the return value. These exist if the function creates intermediate qints that
   are neither returned nor uncomputed. Must be allocated on replay.

**Detection approach (Option B)**: After capture, check which non-parameter qubits
are still allocated (not freed by the C allocator). Those are result + persistent.
Everything else is transient. The return value qubit range distinguishes result
from persistent.

---

### Step 8.1: Track Qubit Liveness After Capture

**Goal**: After the function body executes during capture, query the allocator to
determine which captured qubits are still alive (not freed). Classify each
non-parameter virtual qubit as result, persistent, or transient.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_block.py` | [MOD] Add `transient_virtual_indices: frozenset[int]` and `result_virtual_indices: frozenset[int]` to `CompiledBlock`. | ~+10 |
| `src/quantum_language/compile/_capture.py` | [MOD] After capture, query allocator for qubit liveness. Classify virtual qubits. Store on block. | ~+40 |
| `src/quantum_language/_core.pxd` / `_core.pyx` | [MOD] Expose `allocator_is_allocated(qubit_index) -> bool` from C allocator to Python. | ~+15 |
| `c_backend/include/qubit_allocator.h` | [MOD] Add `bool allocator_is_allocated(allocator_t*, qubit_t)` query. | ~+5 |
| `c_backend/src/qubit_allocator.c` | [MOD] Implement `allocator_is_allocated`: check if qubit is in an allocated block. | ~+20 |

**Tests** (`tests/python/test_compile_ancilla_classify.py` [NEW], ~150 LOC):
- `test_addition_no_persistent` — `a += 1` has zero result/persistent qubits, all internal are transient
- `test_multiplication_has_result` — `c = a * b; return c` has result qubits matching `c`'s width
- `test_transient_correctly_identified` — carry/temp qubits from addition are in `transient_virtual_indices`
- `test_inplace_no_result` — `a += b; return a` has `return_is_param_index` set, no result qubits

**DEP**: Phase 7 (compile subpackage exists)

---

### Step 8.2: IR Replay Skips Transient Allocation

**Goal**: Modify `_replay` so the IR path only allocates result + persistent
virtual qubits. Transient virtual indices are left unmapped — `run_instruction`
handles its own internal ancillas.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_replay.py` | [MOD] In `_replay`: when using IR path, skip allocation for `block.transient_virtual_indices`. Only allocate for result + persistent indices. | ~+20 |

**Tests** (`tests/python/test_compile_ancilla_replay.py` [NEW], ~200 LOC):
- `test_three_calls_no_qubit_growth` — `foo(a, b)` called 3 times (in-place add), qubit count constant after first call
- `test_multiplication_allocates_result` — `bar(a, b)` returning `a * b` allocates fresh result qubits each call
- `test_ir_replay_qubit_mapping` — IR path maps only param + result qubits, transients unmapped
- `test_gate_replay_still_allocates_all` — gate-level path allocates everything (backward compatibility)
- `test_correctness_preserved` — simulation results identical before and after the fix

**DEP**: Step 8.1

---

### Step 8.3: Gate-Level Replay Frees Transients

**Goal**: For the gate-level replay path (`inject_remapped_gates`), allocate all
virtual qubits as before, but free transient ancillas after injection since the
gates return them to |0⟩.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_replay.py` | [MOD] After `inject_remapped_gates`, deallocate qubits corresponding to `block.transient_virtual_indices`. | ~+10 |

**Tests** (`tests/python/test_compile_ancilla_replay.py` [MOD]):
- `test_gate_replay_frees_transients` — after gate-level replay, transient qubits are back in the free pool
- `test_gate_replay_three_calls_stable` — gate-level path also doesn't grow qubits on repeated calls

**DEP**: Step 8.2

---

### Phase 8 Summary

| Step | What | ~LOC delta | DEP |
|------|------|------------|-----|
| 8.1 | Track qubit liveness, classify ancillas | ~+90 | Phase 7 | ✅ |
| 8.2 | IR replay skips transient allocation | ~+20 | 8.1 | ✅ |
| 8.3 | Gate-level replay frees transients | ~+10 | 8.2 | ✅ |

**Net**: ~+120 LOC implementation, ~+350 LOC tests.

---

## Phase 9 — Hierarchical Compiled Function References *(mostly complete)*

When a compiled function calls another compiled function during capture, store a
reference (call record) instead of inlining the inner function's gates. This
prevents memory explosion for complex nested compilations (e.g., wrapping
`walk_step` in a compiled function).

### Design Overview

**Current behavior**: During capture of outer function `f`, if `f` calls inner
compiled function `g`, then `g`'s gates are inlined into `f`'s `CompiledBlock.gates`.
This means `f`'s block contains ALL gates from ALL nested calls — gate count and
ancilla count grow combinatorially.

**New behavior**: During capture of `f`, when `g` is called:
1. `g` runs normally (capture or replay) — its own gates go to the circuit
2. Instead of extracting `g`'s gates into `f`'s block, a `CallRecord` is stored in
   `f`'s instruction IR referencing `g` and the argument qubit mapping
3. On replay of `f`, the `CallRecord` triggers `g._replay()` with the appropriate
   qubit mapping (transitive: f's virtual→real composed with g's virtual→real)
4. `f`'s `CompiledBlock.gates` contains only `f`'s OWN gates (not g's)

**Visualization**: Each compiled function is a node in the call graph. When
rendering, each function's circuit can be shown separately, with call nodes
linking to sub-diagrams.

---

### Step 9.1: CallRecord IR Entry Type ✅

**Goal**: Define a new IR entry type that stores a reference to an inner
`CompiledFunc`, the cache key used, and the argument qubit mapping.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_block.py` | [MOD] Add `CallRecord` dataclass: `compiled_func_ref`, `cache_key`, `quantum_arg_indices` (virtual qubit indices for each arg). Distinguish from `InstructionRecord` via a `kind` field or separate list. | ~+25 |
| `src/quantum_language/_compile_state.py` | [MOD] Add `_record_call(compiled_func, cache_key, quantum_arg_indices)` to record a call during compile-mode. | ~+15 |

**Tests** (`tests/python/test_compile_hierarchical.py` [NEW], ~80 LOC):
- `test_call_record_fields` — `CallRecord` stores func ref, cache key, arg indices
- `test_call_record_in_ir` — recording a call during compile mode appends `CallRecord` to block

**DEP**: Phase 8

---

### Step 9.2: Capture Detects Nested Compiled Functions ✅

**Goal**: During capture of an outer function, when an inner compiled function is
called, record a `CallRecord` instead of letting the inner function's gates
merge into the outer function's circuit gate range.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_capture.py` | [MOD] In `_capture_inner`: detect when a compiled function is called during compile-mode (via nesting depth or compile-mode flag). Instead of extracting inner gates from circuit, record `CallRecord`. | ~+40 |
| `src/quantum_language/compile/_func.py` | [MOD] In `__call__`: when compile-mode is active (we're being called from inside another capture), record `CallRecord` to the parent's IR instead of adding gates to circuit. | ~+30 |

**Tests** (`tests/python/test_compile_hierarchical.py` [MOD]):
- `test_nested_compile_records_call` — outer function's IR contains `CallRecord`, not inner's gates
- `test_nested_own_gates_only` — outer function's gate list excludes inner function's gates
- `test_nested_gate_count` — outer's block.gates is smaller than the flattened total

**DEP**: Step 9.1

---

### Step 9.3: Recursive Replay via CallRecord ✅

**Goal**: During replay of an outer function, when a `CallRecord` is encountered
in the IR, delegate to the inner function's `_replay` with transitive qubit mapping.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_replay.py` | [MOD] In `_replay`: iterate IR entries. For `CallRecord` entries, look up inner function's cached block, build qubit mapping (outer virtual→real composed with inner arg indices), call `inner._replay(block, quantum_args)`. | ~+50 |
| `src/quantum_language/compile/_ir.py` | [MOD] `_execute_ir`: handle `CallRecord` entries by delegating to inner function. | ~+20 |

**Tests** (`tests/python/test_compile_hierarchical.py` [MOD]):
- `test_nested_replay_correct` — outer function replayed produces same simulation result as direct calls
- `test_nested_replay_qubit_mapping` — inner function receives correctly mapped qubits
- `test_nested_three_calls_stable` — repeated replay of outer function doesn't grow qubit count
- `test_deeply_nested` — three levels of nesting (f calls g calls h) works correctly
- `test_nested_controlled` — outer called inside `with` block propagates control to inner functions

**DEP**: Step 9.2

---

### Step 9.4: Hierarchical Gate Count and Visualization ✅

**Goal**: Gate counts for hierarchical functions are computed recursively. DAG
visualization shows call relationships with links to per-function sub-diagrams.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_func.py` | [MOD] `gate_count` property: own gates + sum of referenced function gate counts (via `CallRecord` refs). | ~+15 |
| `src/quantum_language/call_graph.py` | [MOD] `to_dot()`: render `CallRecord` nodes differently (dashed border or subgraph link). `report()`: show hierarchical breakdown. | ~+30 |

**Tests** (`tests/python/test_compile_hierarchical.py` [MOD]):
- `test_hierarchical_gate_count` — total matches sum of all functions' own gates
- `test_report_shows_hierarchy` — report distinguishes own gates from referenced
- `test_dot_shows_call_edges` — DOT output contains call relationship edges

**DEP**: Step 9.3

---

### Phase 9 Summary

| Step | What | ~LOC delta | DEP |
|------|------|------------|-----|
| 9.1 | CallRecord IR entry type | ~+40 | Phase 8 | ✅ |
| 9.2 | Capture detects nested compiled functions | ~+70 | 9.1 | ✅ |
| 9.3 | Recursive replay via CallRecord | ~+70 | 9.2 | ✅ |
| 9.4 | Hierarchical gate count and visualization | ~+45 | 9.3 | ✅ |

**Net**: ~+225 LOC implementation, ~+400 LOC tests.

**Key property**: After this phase, wrapping `walk_step` (or any complex nested
compilation) in a `@ql.compile` function no longer causes memory explosion. Each
function manages its own gates and ancillas independently.

---

## Phase 10 — Per-Context Caching & Zero-Arg Function Fix

**Fixes**: Compiled function gate count accuracy across controlled/uncontrolled
contexts (issues 1, 3, 4) and `KeyError` crash for zero-arg compiled functions
(issue 2).

**Root cause (issues 1, 3, 4)**: A single cache entry stores both controlled and
uncontrolled variants.  `_derive_controlled_block` creates the controlled variant
by adding a control qubit to each virtual gate, but this does not reflect the
actual controlled dispatch cost (different adder selection, different ancilla
counts).  `_replay_hit` always credits the base block's `original_gate_count`,
which reflects whichever context was captured first.  Nested compiled function
`CallRecord.gate_count_delta` inherits this mismatch, causing the outer
function's gate total to diverge from the uncompiled equivalent.

**Root cause (issue 2)**: Zero-arg compiled functions have no parameter qubits.
`real_to_virtual` is built from `raw_gates`, which excludes inner call gate
ranges.  Physical qubits only touched by nested compiled functions are missing
from the mapping.  The fallback `real_to_virtual.get(phys, phys)` maps them to
raw physical indices that collide with reserved virtual slots (e.g., index 0
for the control qubit).  During replay, `virtual_to_real[0]` is never populated
→ `KeyError: 0`.

---

### Step 10.1: Per-Context Cache Key

**Goal**: Include `is_controlled` in the cache key so controlled and uncontrolled
calls produce separate cache entries.  Each context captures independently with
its own correct `original_gate_count`.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_func.py` | [MOD] In `__call__`: add `control_count` (0 or 1) to `cache_key` tuple. | ~+3 |

**Tests** (`tests/python/test_compile_per_context.py` [NEW], ~150 LOC):
- `test_separate_cache_entries` — after calling `foo` both uncontrolled and controlled, `foo._cache` has 2 entries
- `test_uncontrolled_gate_count` — uncontrolled call credits correct uncontrolled cost
- `test_controlled_gate_count` — controlled call credits correct controlled cost
- `test_order_independent` — uncontrolled-first and controlled-first produce same per-call gate counts
- `test_nested_controlled_gate_count` — outer calling inner inside `with`: total matches uncompiled equivalent

**DEP**: None (modifies existing cache key construction).

---

### Step 10.2: Remove Derived Controlled Block

**Goal**: Remove `_derive_controlled_block`, `_capture_and_cache_both`, and all
proportional estimation code.  Capture stores a single block per cache entry
(no `controlled_block` attribute).

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_capture.py` | [MOD] Remove `_capture_and_cache_both` and `_derive_controlled_block`. Replace with `_capture_and_cache` that captures, caches the block, records forward call, and returns. No controlled variant derivation. | ~-80 |
| `src/quantum_language/compile/_func.py` | [MOD] Replace `_capture_and_cache_both` calls with `_capture_and_cache`. Remove `_derive_controlled_block` method. | ~-10 |
| `src/quantum_language/compile/_dispatch.py` | [MOD] Remove `_block_dual_gate_counts`, `_update_dag_variant_counts`, `_update_dag_variant_counts_proportional`. Simplify `_replay_hit` and `_capture_miss` — no dual-variant logic. | ~-80 |
| `src/quantum_language/compile/_block.py` | [MOD] Remove `controlled_block` attribute from `CompiledBlock`. Remove `control_virtual_idx`. | ~-5 |
| `src/quantum_language/compile/_replay.py` | [MOD] Remove controlled variant selection from `_replay` (no more `block.controlled_block`). The block IS the correct variant for the current context. | ~-10 |
| `src/quantum_language/compile/__init__.py` | [MOD] Remove re-exports of deleted functions. | ~-5 |

**Tests** (`tests/python/test_compile_per_context.py` [MOD]):
- `test_no_controlled_block_attr` — cached blocks have no `controlled_block`
- `test_cache_miss_controlled` — controlled call after uncontrolled is a cache miss (separate key)
- Existing compile tests updated for new behavior (controlled calls produce separate cache entries)

**DEP**: Step 10.1

---

### Step 10.3: Replay Gate Credit Fix

**Goal**: Ensure `_replay_hit` credits gate count from the block that was actually
replayed (now always the correct context since each context has its own entry).
Clean up the credit logic.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_dispatch.py` | [MOD] In `_replay_hit`: simplify gate credit — always use `block.original_gate_count` from the cache entry (which is context-correct after Step 10.1). Remove `_used_ir` conditional branching for gate credit. | ~-15 |

**Tests** (`tests/python/test_compile_per_context.py` [MOD]):
- `test_replay_credits_correct_context` — controlled replay credits controlled cost, uncontrolled replay credits uncontrolled cost
- `test_nested_replay_total_matches_uncompiled` — outer(inner_uc + eq + inner_ctrl) total equals manual equivalent

**DEP**: Step 10.2

---

### Step 10.4: Zero-Arg Function Virtual Mapping Fix

**Goal**: After building `real_to_virtual` from `raw_gates`, scan `CallRecord`
`quantum_arg_indices` and add any unmapped physical qubits as new virtual
indices.  This ensures zero-arg compiled functions correctly map all qubits
referenced by nested compiled function calls.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/compile/_capture.py` | [MOD] In `_capture_inner`, after `_build_virtual_mapping`, iterate `ir_block._call_records` and for each `quantum_arg_indices` entry, add unmapped physical qubits to `real_to_virtual` with new virtual indices.  Update `total_virtual` and `internal_count`. | ~+15 |

**Tests** (`tests/python/test_compile_zero_arg.py` [NEW], ~120 LOC):
- `test_zero_arg_no_keyerror` — `@ql.compile def main(): walk_step(...)` called twice without crash
- `test_zero_arg_gate_count` — gate count matches uncompiled equivalent
- `test_zero_arg_call_record_qubits_mapped` — all CallRecord qubit indices present in `real_to_virtual`
- `test_zero_arg_replay_allocates_ancillas` — replay allocates correct number of internal qubits

**DEP**: Step 10.2 (CallRecord structure unchanged, but capture flow simplified)

---

### Step 10.5: DAG Report Dual-Context Display

**Goal**: Update DAG report to show dual `U/C` values for gates, depth, and
T-count.  Values populated only from actually-compiled contexts.  Each operation
appears once; both columns filled as captures occur.  Separate per-context totals.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/call_graph.py` | [MOD] `DAGNode`: add `uncontrolled_depth`, `controlled_depth`, `uncontrolled_t_count`, `controlled_t_count` fields (alongside existing `uncontrolled_gate_count`, `controlled_gate_count`). Update `record_operation` to populate the correct variant's fields based on `controlled` flag. | ~+20 |
| `src/quantum_language/call_graph.py` | [MOD] `report()`: expand dual format to depth and T-count columns. `aggregate()` returns dual totals. `_format_dual_gates` generalized to `_format_dual`. | ~+30 |
| `src/quantum_language/call_graph.py` | [MOD] `_build_dag_from_ir`: when building DAG nodes for the second context, update existing nodes (match by `operation_type` + position) instead of appending duplicates. | ~+25 |
| `src/quantum_language/compile/_dispatch.py` | [MOD] In `_replay_hit` / `_capture_miss`: when building DAG, populate the current context's counts on the node. On second-context replay, locate existing node and fill the other variant's counts. | ~+20 |

**Tests** (`tests/python/test_dag_dual_context.py` [NEW], ~150 LOC):
- `test_report_uc_only` — only uncontrolled compiled: shows `"16 / -"` format
- `test_report_both_contexts` — both compiled: shows `"16 / 28"` with correct values
- `test_report_dual_totals` — totals row shows separate U and C sums
- `test_report_dual_depth` — depth column shows dual values
- `test_report_three_ops_three_rows` — `foo` with 3 add_cq ops displays 3 rows, not 6
- `test_aggregate_dual` — `aggregate()` returns dict with `gates_uc`, `gates_cc`, `depth_uc`, `depth_cc`

**DEP**: Steps 10.1–10.3

---

### Phase 10 Summary

| Step | What | ~LOC delta | DEP |
|------|------|------------|-----|
| 10.1 | Per-context cache key | ~+3 | None |
| 10.2 | Remove derived controlled block | ~-190 | 10.1 |
| 10.3 | Replay gate credit fix | ~-15 | 10.2 |
| 10.4 | Zero-arg function virtual mapping fix | ~+15 | 10.2 |
| 10.5 | DAG report dual-context display | ~+95 | 10.1–10.3 |

**Net**: ~-90 LOC implementation (net reduction from removing derivation/estimation
code), ~+420 LOC tests.

**Key properties**:
- Controlled and uncontrolled calls to the same function produce correct, independent gate counts regardless of call order.
- Compiled function wrapping nested compiled functions (including zero-arg pattern) produces gate counts equal to the uncompiled equivalent.
- `@ql.compile def main(): walk_step(config, registers)` works without crashing.
- DAG report shows accurate per-context metrics without estimation or derivation.

---

## Phase 11 — Calling-Context DAG Semantics

Rework DAG U/C semantics so that the controlled/uncontrolled split reflects the
**calling context** of the enclosing compiled function, not whether individual
operations are internally controlled. Show separate report/DOT sections per
context. Track AND operations from nested `with` blocks as DAG nodes.

### Step 11.1: Core calling-context infrastructure ✅

**Goal**: Add calling-context stack, update `record_operation` and
`_add_nested_call_dag_node` to use calling context for U/C assignment. Add
internal-control detection via control-depth baseline comparison. Prefix
operation names with `c_` only for internal control.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/call_graph.py` | [MOD] Add `_calling_context_stack`, `push/pop/current_calling_context`. Rewrite `record_operation` U/C logic. Disable `backfill_call_node_siblings`. | ~+60 |
| `src/quantum_language/compile/_func.py` | [MOD] Push/pop calling context in `__call__`. Compute `_has_internal_control` from control depth. Rewrite `_add_nested_call_dag_node` — no sibling lookup, use outer calling context for U/C. | ~+40 |
| `src/quantum_language/compile/_dispatch.py` | [MOD] Skip merge when node counts differ. Copy `func_name` from uncontrolled capture in merge. | ~+10 |

**DEP**: None (builds on Phase 10)

---

### Step 11.2: AND operations as DAG nodes ✅

**Goal**: Track `_toffoli_and` / `_uncompute_toffoli_and` (nested `with` block
control merging) as DAG nodes so the controlled context's cost accounts for
them.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/_gates.pyx` | [MOD] Add `record_operation("and", ...)` calls in `_toffoli_and` and `_uncompute_toffoli_and`. `controlled=False`, `gate_count=1`, `t_count=7`. | ~+20 |

**DEP**: Step 11.1

---

### Step 11.3: Separate report and DOT sections ✅

**Goal**: `report()` and `to_dot()` show independent Uncontrolled / Controlled
sections, since the two contexts can have different DAG structures (AND nodes
only exist in controlled). Store `func_name` on `CallGraphDAG`.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/call_graph.py` | [MOD] Rewrite `report()` with `_section()` helper. Rewrite `to_dot()` with `context` parameter. Add `func_name` to `CallGraphDAG.__init__`. | ~+60 |
| `src/quantum_language/compile/_func.py` | [MOD] Pass `func_name=self._func.__name__` to `CallGraphDAG()`. | ~+1 |

**DEP**: Step 11.1

---

### Step 11.4: Arithmetic operations — calling-context cleanup

**Goal**: Simplify `_record_operation` calls in `qint_arithmetic.pxi`. Remove
the `if _controlled: _uc=0/_cc=gc else: _uc=gc/_cc=0` blocks — `record_operation`
now handles U/C via the calling context stack automatically.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint_arithmetic.pxi` | [MOD] Simplify `_record_operation` calls for `add_qq`, `mul_cq`, `mul_qq`. Remove `_uc_gc`/`_cc_gc` variables in Toffoli path. Just pass `gate_count=gc_delta`. | ~-30 |

**Tests** (`tests/python/test_dag_calling_context.py` [NEW]):
- `test_add_qq_uc_cc` — quantum-quantum add in uncontrolled/controlled contexts
- `test_mul_cq_uc_cc` — classical multiply in uncontrolled/controlled contexts
- `test_mul_qq_uc_cc` — quantum-quantum multiply

**DEP**: Step 11.1

---

### Step 11.5: Bitwise operations — calling-context cleanup

**Goal**: Same simplification for all bitwise operations.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint_bitwise.pxi` | [MOD] Simplify `_record_operation` calls for `xor`, `and`, `or`, `not`, `lshift`, `rshift`, `rlshift`. Remove Toffoli-path `_uc/_cc` if/else blocks. | ~-40 |

**Tests** (append to `tests/python/test_dag_calling_context.py`):
- `test_xor_uc_cc` — XOR in uncontrolled/controlled contexts
- `test_and_or_uc_cc` — AND/OR bitwise ops
- `test_shift_uc_cc` — left/right shift ops

**DEP**: Step 11.1

---

### Step 11.6: Division and comparison operations — calling-context cleanup

**Goal**: Same simplification for division and comparison operations.

| File | Action | ~LOC |
|------|--------|------|
| `src/quantum_language/qint_division.pxi` | [MOD] Simplify `_record_operation` calls for `div`, `mod`. | ~-10 |
| `src/quantum_language/qint_comparison.pxi` | [MOD] Simplify `_record_operation` calls for comparison ops. | ~-5 |

**Tests** (append to `tests/python/test_dag_calling_context.py`):
- `test_div_mod_uc_cc` — division/modulo in uncontrolled/controlled contexts
- `test_comparison_uc_cc` — comparison ops (eq, lt, gt, etc.)

**DEP**: Step 11.1

---

### Phase 11 Summary

| Step | What | ~LOC delta | DEP |
|------|------|------------|-----|
| 11.1 ✅ | Core calling-context infrastructure | ~+110 | None |
| 11.2 ✅ | AND operations as DAG nodes | ~+20 | 11.1 |
| 11.3 ✅ | Separate report/DOT sections | ~+60 | 11.1 |
| 11.4 | Arithmetic ops cleanup | ~-30 | 11.1 |
| 11.5 | Bitwise ops cleanup | ~-40 | 11.1 |
| 11.6 ✅ | Division/comparison ops cleanup | ~-15 | 11.1 |

**Net**: ~+105 LOC implementation, ~+200 LOC tests.

**Key properties**:
- DAG U/C reflects calling context, not internal control state.
- Controlled context shows AND nodes from nested `with` blocks.
- All integer operations (arithmetic, bitwise, division, comparison) use consistent calling-context tracking.
- Report shows separate sections per context with correct totals.
- R7.13 fulfilled: all integer operations use calling-context DAG tracking.
