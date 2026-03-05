# Architecture Research: Multi-Level Compilation Infrastructure

**Domain:** Quantum circuit compilation infrastructure (integration into existing framework)
**Researched:** 2026-03-05
**Confidence:** HIGH (based on direct source code analysis of existing architecture)

## Existing Architecture Summary

The current system is a three-layer stateless design:

```
┌──────────────────────────────────────────────────────────────────┐
│                     Python Frontend (compile.py)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │ CompiledFunc │  │ CompiledBlock│  │ AncillaRecord         │   │
│  │ (cache,      │  │ (virtual     │  │ (forward call         │   │
│  │  capture,    │  │  gate list,  │  │  tracking for         │   │
│  │  replay)     │  │  qubit map)  │  │  inverse support)     │   │
│  └──────┬───────┘  └──────────────┘  └───────────────────────┘   │
│         │                                                         │
│  Current flow: capture -> extract_gate_range -> virtualise ->     │
│                optimise -> cache -> replay via inject_remapped    │
├──────────────────────────────────────────────────────────────────┤
│                     Cython Bindings (_core.pyx)                    │
│  ┌────────────────────────┐  ┌────────────────────────────────┐  │
│  │ extract_gate_range()   │  │ inject_remapped_gates()        │  │
│  │ (iterate layers,       │  │ (build gate_t on stack,        │  │
│  │  build Python dicts)   │  │  remap qubits, call add_gate) │  │
│  └────────────┬───────────┘  └────────────────┬───────────────┘  │
│               │ Per-gate crossing              │ Per-gate crossing│
├───────────────┴────────────────────────────────┴─────────────────┤
│                     C Backend (optimizer.c + circuit.h)            │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ add_gate():                                                  │ │
│  │   1. allocate_more_qubits() — expand dense arrays if needed  │ │
│  │   2. minimum_layer() — find earliest valid layer             │ │
│  │   3. colliding_gates() — check inverse cancellation          │ │
│  │   4. append_gate() — memcpy into sequence[layer][pos]        │ │
│  │   5. apply_layer() — update occupancy tracking               │ │
│  │                                                              │ │
│  │ Dense arrays:                                                │ │
│  │   gate_index_of_layer_and_qubits[layer][qubit] — int matrix  │ │
│  │   occupied_layers_of_qubit[qubit][index] — per-qubit layers  │ │
│  │   sequence[layer][gate_idx] — 2D jagged gate storage         │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Critical Architectural Facts

1. **Per-gate Cython boundary crossing**: Every gate in `inject_remapped_gates()` builds a `gate_t` on the stack, remaps qubits, and calls `add_gate()` individually. No batch injection path exists.

2. **Dense `gate_index_of_layer_and_qubits`**: Allocated as `int[layer][qubit]` with dynamic growth via `allocate_more_qubits()`. At 8000 max qubits and 300K max layers, this is the primary memory concern.

3. **Stateless capture-replay**: `CompiledFunc._capture()` records `start_layer`/`end_layer`, then `extract_gate_range()` iterates all layers in that range pulling gate dicts. Replay via `inject_remapped_gates()` re-adds gates through `add_gate()`.

4. **Virtual qubit namespace**: `CompiledBlock` stores gates in a virtual qubit space. Parameter qubits map first (positional order), then ancillas. Replay builds `virtual_to_real` mapping for each call site.

5. **Layer floor**: `circuit_t.layer_floor` prevents gates from being placed before a given layer. Used by compiled functions to ensure replayed gates don't interleave with earlier content.

## New Feature Integration Architecture

### opt_flag=1: Call Graph DAG (Sequence-Only Mode)

**What changes:** Sequences are generated in C as normal, but NOT placed into the shared circuit. A call graph DAG is built in Python tracking sequence dependencies and qubit sets.

**Integration design:**

```
┌──────────────────────────────────────────────────────────────────┐
│                  Python Frontend (compile.py)                      │
│                                                                    │
│  ┌──────────────┐     ┌──────────────────────────────────────┐    │
│  │ CompiledFunc │     │ CallGraphDAG (NEW)                   │    │
│  │              │────>│  nodes: Dict[str, SequenceNode]      │    │
│  │ opt_flag=1:  │     │  edges: Set[(parent, child)]         │    │
│  │  capture     │     │  qubit_sets: Dict[str, Set[int]]     │    │
│  │  normally,   │     │                                      │    │
│  │  store in    │     │  add_sequence(name, block, qubits)   │    │
│  │  DAG instead │     │  get_parallel_groups() -> topo sort   │    │
│  │  of circuit  │     │  overlapping_qubits(a, b) -> Set     │    │
│  └──────────────┘     │  to_dot() -> str                     │    │
│                       └──────────────────────────────────────┘    │
│                                                                    │
│  SequenceNode (NEW):                                               │
│    name: str                                                       │
│    block: CompiledBlock (existing — reuse virtual gate list)       │
│    qubit_set: Set[int] (real qubits touched)                       │
│    dependencies: List[SequenceNode] (qubit-based ordering)         │
│    depth_contribution: int (estimated layers)                      │
└──────────────────────────────────────────────────────────────────┘
```

**Key integration points:**

| Integration Point | Existing Component | Change Type | Details |
|---|---|---|---|
| Capture path | `CompiledFunc._capture()` | MODIFY | When `opt_flag=1`, after capture, register node in DAG instead of leaving gates in circuit. Must still extract gates via `extract_gate_range()`. |
| Block reuse | `CompiledBlock` | REUSE (no change) | Virtual gate lists are already self-contained. DAG nodes wrap existing blocks. |
| Circuit suppression | `_core.pyx` / `add_gate()` | NO CHANGE | Gates still flow through `add_gate()` during capture. The key insight: capture already works by recording layer ranges. For opt_flag=1, after capture, the gates exist in the circuit AND in the cached block. The circuit is the "working copy"; the DAG provides the logical structure. |
| Dependency detection | NEW Python code | NEW | Compare `qubit_set` between nodes. If intersection is non-empty, add edge. Topological sort gives parallelism. |

**Architectural decision: Should opt_flag=1 prevent gates from entering the circuit?**

NO. The existing capture mechanism relies on gates being in the circuit to extract them via `extract_gate_range()`. Suppressing `add_gate()` would require a fundamentally different capture path (buffering gates in Python, never touching C). This is high complexity for low value.

Instead: opt_flag=1 means "build the circuit as opt_flag=3 (full expansion), but ALSO build the call graph DAG as a parallel data structure." The DAG is informational for opt_flag=1 -- it becomes actionable at opt_flag=2 for selective merging.

**Alternative considered and rejected:** Intercepting `add_gate()` with a "null circuit" that discards gates but tracks qubit sets. This would require either:
- A new C-level circuit mode flag (invasive, breaks stateless design)
- A Python-level gate buffer replacing the Cython path (duplicates existing infrastructure)

Neither is justified. The existing capture path already extracts gates into Python dicts. The DAG is built from those dicts.

### opt_flag=2: Selective Sequence Merging

**What changes:** Python-level merge heuristic identifies overlapping-qubit sequences, expands selected ones into merged mini-circuits.

**Integration design:**

```
┌──────────────────────────────────────────────────────────────────┐
│                  Python Frontend (compile.py)                      │
│                                                                    │
│  CallGraphDAG                                                      │
│    │                                                               │
│    ├── identify_merge_candidates()                                 │
│    │   Input: DAG nodes with qubit_set overlaps                    │
│    │   Output: List[(node_a, node_b)] to merge                     │
│    │                                                               │
│    ├── merge_sequences(node_a, node_b) -> MergedBlock              │
│    │   1. Union qubit sets                                         │
│    │   2. Concatenate virtual gate lists (remap to shared space)   │
│    │   3. Create new CompiledBlock with merged gates               │
│    │   4. Optionally re-optimize merged gate list                  │
│    │                                                               │
│    └── expand_to_circuit(merged_blocks)                            │
│        For each merged block:                                      │
│          inject_remapped_gates(block.gates, qubit_map)             │
│                                                                    │
│  MergeHeuristic (NEW):                                             │
│    - Overlap threshold: min qubit overlap ratio to consider merge   │
│    - Size threshold: max combined gate count for merging            │
│    - Depth benefit estimate: merged depth vs sequential depth       │
└──────────────────────────────────────────────────────────────────┘
```

**Key integration points:**

| Integration Point | Existing Component | Change Type | Details |
|---|---|---|---|
| Gate list merging | `_optimize_gate_list()` | REUSE | After concatenating gate lists from two blocks, run existing optimizer to cancel inverse pairs at the junction. |
| Virtual qubit remapping | `_remap_gates()`, `_build_virtual_mapping()` | REUSE | Existing helpers handle qubit namespace translation. Merging two blocks requires unifying their virtual spaces. |
| Circuit injection | `inject_remapped_gates()` | REUSE (no change) | Merged blocks are injected into a fresh circuit using the existing per-gate path. |
| Layer floor management | `_set_layer_floor()` / `_get_layer_floor()` | REUSE | Use layer floor to ensure merged blocks are placed after their dependencies. |

**Merge algorithm sketch:**

```python
def merge_sequences(dag, node_a, node_b):
    """Merge two overlapping-qubit sequences into a single block."""
    # 1. Determine unified qubit set
    all_qubits = node_a.qubit_set | node_b.qubit_set

    # 2. Build unified virtual mapping
    #    Parameter qubits from both blocks map to shared virtual space
    unified_mapping = {}
    vidx = 0
    for q in sorted(all_qubits):
        unified_mapping[q] = vidx
        vidx += 1

    # 3. Remap both gate lists to unified space
    gates_a = _remap_gates(node_a.block.gates,
                           _compose_maps(node_a.virtual_to_real, unified_mapping))
    gates_b = _remap_gates(node_b.block.gates,
                           _compose_maps(node_b.virtual_to_real, unified_mapping))

    # 4. Concatenate and optimize
    merged_gates = _optimize_gate_list(gates_a + gates_b)

    # 5. Build merged CompiledBlock
    return CompiledBlock(
        gates=merged_gates,
        total_virtual_qubits=vidx,
        param_qubit_ranges=[(0, vidx)],  # All qubits are "parameters"
        internal_qubit_count=0,
        return_qubit_range=None,
    )
```

**Critical constraint:** Merging only works when both sequences have already been captured (their gate lists exist as Python dicts). This means the capture phase must complete for ALL sequences before merging begins. The flow is:

1. Capture all sequences (gates enter circuit via normal `add_gate()` path)
2. Extract all sequences into `CompiledBlock` objects
3. Build DAG with qubit overlap analysis
4. Identify merge candidates
5. Create a NEW circuit (`ql.circuit()`)
6. Inject merged blocks into new circuit via `inject_remapped_gates()`

This "capture-then-rebuild" pattern avoids modifying the C backend.

### opt_flag=3: Full Expansion (No Changes)

Current behavior. All sequences expand directly into the shared circuit. No DAG construction, no merging. This is the existing `@ql.compile` path.

### DOT Visualization

**Integration design:**

```
CallGraphDAG
  └── to_dot() -> str
      Iterate nodes and edges, emit DOT format.
      Node labels: sequence name, gate count, qubit count.
      Edge labels: shared qubit count.
      Parallel groups (no edges between them) get same rank.
```

**Implementation:** Pure Python, no C/Cython changes. Operates on the `CallGraphDAG` data structure. Can optionally use `graphviz` Python package for rendering, but DOT string generation requires no dependencies.

**File location:** New module `src/quantum_language/call_graph.py` or method on `CallGraphDAG` class within compile.py.

### Sparse Circuit Arrays

**What changes:** Replace `gate_index_of_layer_and_qubits` dense `int[layer][qubit]` array with sparse representation when circuit exceeds memory threshold.

**Integration design:**

```
┌──────────────────────────────────────────────────────────────────┐
│                     C Backend (circuit.h / optimizer.c)            │
│                                                                    │
│  circuit_t (MODIFIED):                                             │
│    // Existing dense arrays (kept for small circuits):             │
│    int **gate_index_of_layer_and_qubits;  // [layer][qubit]       │
│                                                                    │
│    // NEW: Sparse mode flag and data                               │
│    int sparse_mode;  // 0=dense (default), 1=sparse               │
│    sparse_layer_t *sparse_layers;  // array of hash maps          │
│                                                                    │
│  sparse_layer_t (NEW struct):                                      │
│    // Hash map: qubit_t -> int (gate index)                        │
│    // Only stores entries where gate_index != -1                   │
│    qubit_t *keys;                                                  │
│    int *values;                                                    │
│    int count;                                                      │
│    int capacity;                                                   │
│                                                                    │
│  Modified functions:                                               │
│    add_gate() — branch on sparse_mode for lookup/update           │
│    append_gate() — branch on sparse_mode for index storage        │
│    colliding_gates() — branch on sparse_mode for index lookup     │
│    merge_gates() — branch on sparse_mode for index reset          │
│    allocate_more_qubits() — skip dense array growth in sparse     │
│    allocate_more_layer() — allocate sparse_layer_t instead        │
└──────────────────────────────────────────────────────────────────┘
```

**Key integration points:**

| Integration Point | Existing Component | Change Type | Details |
|---|---|---|---|
| Gate index lookup | `gate_index_of_layer_and_qubits[layer][qubit]` | MODIFY | 6 access sites in optimizer.c. Each needs `if (sparse_mode)` branch to use hash map lookup instead of array index. |
| Gate index storage | `append_gate()` line 138 | MODIFY | Store in hash map instead of dense array when sparse. |
| Gate index reset | `merge_gates()` lines 73-78 | MODIFY | Remove from hash map instead of setting to -1. |
| Memory allocation | `allocate_more_qubits()` | MODIFY | In sparse mode, skip dense array reallocation for `gate_index_of_layer_and_qubits`. |
| Layer allocation | `allocate_more_layer()` | MODIFY | Allocate `sparse_layer_t` entries instead of/in addition to dense rows. |
| Auto-transition | `add_gate()` or `allocate_more_qubits()` | NEW | When `allocated_qubits * used_layer * sizeof(int)` exceeds threshold (e.g., 100MB), switch to sparse mode. |
| Cython bindings | `extract_gate_range()` | NO CHANGE | Iterates `sequence[layer][gate_idx]` which is unchanged -- sparse mode only affects the index lookup arrays, not the gate storage. |

**Hash map implementation choice:** Use open-addressing with linear probing. The key space is `qubit_t` (unsigned int), values are `int` (gate index). Load factor target: 0.7. This is simpler and cache-friendlier than chaining for the expected access pattern (frequent lookups in hot `add_gate()` path).

**Transition strategy:** The circuit starts in dense mode. When the memory estimate `allocated_qubits * allocated_layer * sizeof(int)` exceeds a configurable threshold, the circuit transitions to sparse mode. This is a one-way transition (no sparse-to-dense). The transition:

1. Allocate `sparse_layer_t` array for all existing layers
2. For each layer, scan dense `gate_index_of_layer_and_qubits[layer]` and insert non-(-1) entries into the hash map
3. Free the dense `gate_index_of_layer_and_qubits` array
4. Set `sparse_mode = 1`

**Performance note:** The sparse path adds a hash lookup per qubit per `add_gate()` call (currently a direct array index). For typical circuits (< 1000 qubits, < 10K layers), dense mode is faster. Sparse mode is a memory optimization for large circuits where the dense array would be prohibitive (e.g., 4000 qubits x 100K layers = 1.6 GB just for the index array).

## Component Inventory

### New Components

| Component | Layer | File | Purpose |
|---|---|---|---|
| `CallGraphDAG` | Python | `compile.py` or new `call_graph.py` | DAG data structure for sequence dependencies |
| `SequenceNode` | Python | Same as above | Node in call graph (wraps CompiledBlock) |
| `MergeHeuristic` | Python | Same as above | Decision logic for which sequences to merge |
| `sparse_layer_t` | C | `c_backend/include/sparse_index.h` (new) | Hash map for sparse gate index |
| Sparse index API | C | `c_backend/src/sparse_index.c` (new) | `sparse_create()`, `sparse_get()`, `sparse_set()`, `sparse_remove()`, `sparse_free()` |

### Modified Components

| Component | Layer | File | Change |
|---|---|---|---|
| `CompiledFunc.__call__()` | Python | `compile.py` | Add `opt_flag` parameter routing |
| `CompiledFunc._capture()` | Python | `compile.py` | When opt_flag=1/2, register in DAG after capture |
| `circuit_t` | C | `circuit.h` | Add `sparse_mode`, `sparse_layers` fields |
| `add_gate()` | C | `optimizer.c` | Branch on `sparse_mode` for index operations |
| `append_gate()` | C | `optimizer.c` | Branch on `sparse_mode` for index storage |
| `colliding_gates()` | C | `optimizer.c` | Branch on `sparse_mode` for index lookup |
| `merge_gates()` | C | `optimizer.c` | Branch on `sparse_mode` for index reset |
| `allocate_more_qubits()` | C | `circuit.c` | Skip dense index growth in sparse mode |
| `allocate_more_layer()` | C | `circuit.c` | Allocate sparse layer entries when sparse |
| `init_circuit()` | C | `circuit.c` | Initialize `sparse_mode=0` |
| `free_circuit()` | C | `circuit.c` | Free sparse layers if allocated |

### Unchanged Components

| Component | Layer | File | Why Unchanged |
|---|---|---|---|
| `extract_gate_range()` | Cython | `_core.pyx` | Iterates `sequence[][]`, not index arrays |
| `inject_remapped_gates()` | Cython | `_core.pyx` | Calls `add_gate()` per gate (sparse handled internally) |
| `CompiledBlock` | Python | `compile.py` | Virtual gate storage is already complete |
| `_optimize_gate_list()` | Python | `compile.py` | Operates on gate dicts, layer-agnostic |
| `_build_virtual_mapping()` | Python | `compile.py` | Pure qubit remapping logic |
| Gate type constants | C | `types.h` | No new gate types needed |
| Qubit allocator | C | `qubit_allocator.h/.c` | Allocation is orthogonal to indexing |

## Data Flow

### opt_flag=1 Flow (Call Graph + Full Expansion)

```
User code: @ql.compile(opt_flag=1)
    │
    ├── f(a, b)  [first call]
    │     │
    │     ├── CompiledFunc.__call__(opt_flag=1)
    │     │     │
    │     │     ├── _capture():
    │     │     │     ├── start_layer = get_current_layer()
    │     │     │     ├── self._func(*args)          # gates flow to circuit via add_gate()
    │     │     │     ├── end_layer = get_current_layer()
    │     │     │     ├── extract_gate_range(start, end)  # pull gates as Python dicts
    │     │     │     └── build CompiledBlock (virtual gate list)
    │     │     │
    │     │     ├── Register in CallGraphDAG:         # NEW
    │     │     │     ├── node = SequenceNode(block, qubit_set)
    │     │     │     ├── for existing_node in dag:
    │     │     │     │     if qubit_set & existing_node.qubit_set:
    │     │     │     │         dag.add_edge(existing_node, node)
    │     │     │     └── dag.add_node(node)
    │     │     │
    │     │     └── Cache block as usual
    │     │
    │     └── return result
    │
    ├── g(c, d)  [second compiled call]
    │     └── Same flow, DAG gains second node + edges
    │
    └── dag.to_dot()  # user requests visualization
          └── Generate DOT string from nodes/edges
```

### opt_flag=2 Flow (Selective Merge)

```
Phase 1: Capture all sequences (same as opt_flag=1)
    │
Phase 2: Merge analysis
    │
    ├── dag.identify_merge_candidates()
    │     ├── For each pair (A, B) with overlapping qubits:
    │     │     ├── overlap_ratio = |A.qubits & B.qubits| / min(|A|, |B|)
    │     │     ├── estimated_depth_savings = estimate_merge_benefit(A, B)
    │     │     └── if overlap_ratio > threshold and benefit > min_benefit:
    │     │           candidates.append((A, B))
    │     └── Return sorted candidates
    │
    ├── For each merge candidate:
    │     ├── Unify virtual qubit spaces
    │     ├── Concatenate gate lists
    │     ├── Run _optimize_gate_list() on junction  # reuse existing optimizer
    │     └── Create MergedBlock (new CompiledBlock)
    │
Phase 3: Rebuild circuit
    │
    ├── ql.circuit()  # fresh circuit
    │
    ├── For each block in topological order:
    │     ├── Allocate real qubits for internal/ancilla
    │     ├── Build virtual_to_real mapping
    │     ├── Set layer_floor (from dependency analysis)
    │     └── inject_remapped_gates(block.gates, qubit_map)
    │
    └── Result: optimized circuit with merged sequences
```

### Sparse Circuit Transition Flow

```
add_gate(circ, g)
    │
    ├── allocate_more_qubits(circ, g)
    │     │
    │     ├── if !sparse_mode:
    │     │     ├── Grow dense gate_index_of_layer_and_qubits as usual
    │     │     ├── Check memory: if allocated_qubits * allocated_layer * 4 > THRESHOLD
    │     │     │     └── transition_to_sparse(circ)  # one-time migration
    │     │     └── return
    │     │
    │     └── if sparse_mode:
    │           └── No dense array growth needed
    │
    ├── minimum_layer(circ, g, ...)
    │     └── Uses occupied_layers_of_qubit (unchanged — not part of sparse)
    │
    ├── colliding_gates(circ, g, min_layer, ...)
    │     │
    │     ├── if !sparse_mode:
    │     │     └── gate_index = circ->gate_index_of_layer_and_qubits[layer][qubit]
    │     │
    │     └── if sparse_mode:
    │           └── gate_index = sparse_get(&circ->sparse_layers[layer], qubit)
    │                            // returns -1 if not found
    │
    ├── [if inverse: merge_gates — similar sparse branch]
    │
    └── append_gate(circ, g, min_layer)
          │
          ├── memcpy gate into sequence[layer][pos]  (unchanged)
          │
          ├── if !sparse_mode:
          │     └── circ->gate_index_of_layer_and_qubits[layer][target] = pos
          │
          └── if sparse_mode:
                └── sparse_set(&circ->sparse_layers[layer], target, pos)
```

## Architectural Patterns

### Pattern 1: Capture-Then-Analyze (for DAG Construction)

**What:** Gates flow through the existing `add_gate()` path during capture. After capture completes, the extracted gate list (already virtualized as a `CompiledBlock`) is registered in the DAG. The circuit retains the gates for opt_flag=1 (informational DAG) or is rebuilt for opt_flag=2 (merge optimization).

**When to use:** Always for opt_flag=1 and opt_flag=2. This preserves the existing capture mechanism without modification.

**Trade-offs:**
- Pro: Zero changes to C backend for DAG construction
- Pro: Reuses existing `CompiledBlock` virtual gate lists
- Con: For opt_flag=2, the initial circuit is built and then discarded (rebuilt with merges)
- Con: Gates cross the Cython boundary twice (once during capture, once during rebuild)

### Pattern 2: Dual-Mode Index Storage (for Sparse Circuit)

**What:** The `gate_index_of_layer_and_qubits` lookup uses either dense arrays (direct index) or sparse hash maps, selected by a flag on `circuit_t`. All access sites branch on this flag.

**When to use:** Sparse mode activates automatically when memory exceeds a threshold.

**Trade-offs:**
- Pro: Small circuits pay zero overhead (dense path is unchanged)
- Pro: Large circuits avoid OOM from the dense index matrix
- Con: Branch prediction cost in hot `add_gate()` path (mitigated: branch is highly predictable after transition)
- Con: Hash map lookups are slower than array indexing (~3-5x per lookup)

### Pattern 3: Layered opt_flag Semantics

**What:** opt_flag values form a hierarchy where higher values include lower values' behavior:
- opt_flag=1: Build DAG (informational) + full expansion
- opt_flag=2: Build DAG + selective merge + partial expansion
- opt_flag=3: Full expansion only (current behavior, no DAG)

**When to use:** User-facing API parameter on `@ql.compile`.

**Trade-offs:**
- Pro: opt_flag=3 is zero-cost (current path, no DAG overhead)
- Pro: opt_flag=1 adds only Python-level overhead (DAG construction)
- Con: opt_flag=2 requires circuit rebuild (capture + rebuild = 2x circuit construction)

## Anti-Patterns

### Anti-Pattern 1: Modifying add_gate() for DAG Construction

**What people might do:** Add a "DAG mode" flag to `add_gate()` that buffers gates instead of placing them in the circuit.

**Why it's wrong:** The existing capture mechanism already extracts gates into Python dicts via `extract_gate_range()`. Adding buffering to the C layer duplicates this functionality, adds complexity to the hot path, and breaks the stateless C backend design principle. Every subsequent feature would need to handle two code paths in C.

**Do this instead:** Use the existing capture-then-extract pattern. Build the DAG in Python from extracted gate lists.

### Anti-Pattern 2: Sparse-by-Default

**What people might do:** Start all circuits in sparse mode for uniformity.

**Why it's wrong:** Hash map lookups are 3-5x slower than array indexing. For the 95% of circuits that fit in memory with dense arrays, this is pure overhead. The framework benchmarks show circuit generation speed is a competitive advantage.

**Do this instead:** Start dense, auto-transition when memory threshold is exceeded. Keep dense as the fast path.

### Anti-Pattern 3: Deep Merge Recursion

**What people might do:** Merge sequences transitively (A merges with B, then AB merges with C, etc.) producing one giant sequence.

**Why it's wrong:** This converges to opt_flag=3 (full expansion) with extra overhead. The value of opt_flag=2 is selective merging of specific pairs with high qubit overlap, not global circuit flattening.

**Do this instead:** Limit merging to direct pairs. Use a merge benefit threshold. If merging all candidates would produce a single sequence, that is opt_flag=3 -- just use opt_flag=3.

## Suggested Build Order

Build order follows dependency chain. Each phase is independently testable.

### Phase 1: Sparse Circuit Arrays (C Backend)

**Rationale:** Independent of Python changes. Unlocks large circuit support. Most isolated change -- only touches C backend with clear access-site modifications.

**Components:**
1. `sparse_index.h` / `sparse_index.c` -- hash map implementation
2. Add `sparse_mode`, `sparse_layers` to `circuit_t`
3. Modify 6 access sites in `optimizer.c` with `if (sparse_mode)` branches
4. Add `transition_to_sparse()` function
5. Modify `allocate_more_qubits()` and `allocate_more_layer()`
6. Modify `init_circuit()` and `free_circuit()`

**Test:** Create circuits exceeding threshold, verify same gate output in sparse vs dense mode.

### Phase 2: Call Graph DAG (Python)

**Rationale:** Depends on nothing new in C. Uses existing `CompiledBlock`. Foundation for opt_flag=1 and opt_flag=2.

**Components:**
1. `CallGraphDAG` class with `add_node()`, `add_edge()`, `topological_sort()`
2. `SequenceNode` wrapping `CompiledBlock` + qubit set
3. Qubit overlap detection (`overlapping_qubits()`)
4. Parallel group identification (`get_parallel_groups()`)

**Test:** Build DAG from manually constructed CompiledBlocks, verify topology.

### Phase 3: DOT Visualization (Python)

**Rationale:** Depends on Phase 2 (DAG). Simple output formatting.

**Components:**
1. `to_dot()` method on `CallGraphDAG`
2. Node/edge formatting with gate count, qubit count labels

**Test:** Generate DOT from test DAG, verify valid DOT syntax.

### Phase 4: opt_flag=1 Integration (Python)

**Rationale:** Depends on Phase 2 (DAG). Wires DAG construction into `CompiledFunc`.

**Components:**
1. Add `opt_flag` parameter to `@ql.compile` decorator
2. Modify `CompiledFunc.__call__()` to construct DAG when opt_flag=1
3. Expose DAG as property on `CompiledFunc` (`.call_graph`)

**Test:** `@ql.compile(opt_flag=1)` produces correct DAG alongside normal circuit.

### Phase 5: Sequence Merging (Python)

**Rationale:** Depends on Phase 2 (DAG) and Phase 4 (opt_flag integration). Most complex new logic.

**Components:**
1. `MergeHeuristic` with configurable thresholds
2. `merge_sequences()` -- unify virtual spaces, concatenate, optimize
3. `expand_to_circuit()` -- rebuild circuit from merged blocks
4. Circuit rebuild orchestration (fresh `ql.circuit()` + inject)

**Test:** Merge two sequences with known qubit overlap, verify merged circuit has fewer gates than sequential.

### Phase 6: opt_flag=2 Integration (Python)

**Rationale:** Depends on Phase 4 (opt_flag=1 working) and Phase 5 (merging). Wires everything together.

**Components:**
1. Modify `CompiledFunc.__call__()` for opt_flag=2 flow
2. Add circuit rebuild step after all captures complete
3. Handle edge cases: empty merges, single-sequence programs

**Test:** End-to-end: `@ql.compile(opt_flag=2)` with overlapping sequences produces optimized circuit with correct behavior (verified via Qiskit simulation).

## Scaling Considerations

| Concern | Small Circuit (<100 qubits) | Medium Circuit (100-2000 qubits) | Large Circuit (2000+ qubits) |
|---|---|---|---|
| Index memory | Dense arrays: trivial | Dense arrays: ~100MB | Sparse transition needed |
| DAG construction | Negligible overhead | O(n^2) pair comparison manageable | May need qubit-set indexing |
| Merge analysis | Exhaustive pair scan OK | Heuristic filtering needed | Must limit candidate pairs |
| Circuit rebuild (opt_flag=2) | Fast | 2x construction cost | Consider incremental merge |

### First bottleneck: Dense index memory

At 4000 qubits and 50K layers, `gate_index_of_layer_and_qubits` = 4000 * 50000 * 4 bytes = 800 MB. This is the first thing that breaks. Sparse mode is the fix.

### Second bottleneck: Per-gate Cython crossing

Each gate in `inject_remapped_gates()` builds a `gate_t` on the stack, remaps qubits, and calls `add_gate()`. For circuits with millions of gates, this is O(n) Python-C crossings. Future optimization: batch injection via a C-level function that takes a flat array of gate data. NOT needed for v7.0 -- the per-gate path works and is already optimized (stack-allocated `gate_t`, Phase 84).

## Sources

- Direct source analysis of `compile.py` (1100+ lines), `_core.pyx` (1011 lines), `circuit.h` (174 lines), `optimizer.c` (217 lines), `types.h` (90 lines)
- Existing architectural decisions documented in `.planning/PROJECT.md` (406 lines of decisions)
- Prior architecture research in `.planning/research/ARCHITECTURE-COMPILE-DECORATOR.md`

---
*Architecture research for: Multi-level quantum circuit compilation infrastructure*
*Researched: 2026-03-05*
