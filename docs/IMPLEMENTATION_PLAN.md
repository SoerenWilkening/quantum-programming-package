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
