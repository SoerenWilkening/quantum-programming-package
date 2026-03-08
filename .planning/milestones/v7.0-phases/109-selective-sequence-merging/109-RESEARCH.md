# Phase 109: Selective Sequence Merging - Research

**Researched:** 2026-03-06
**Domain:** Quantum circuit compilation -- sequence merging and cross-boundary gate optimization
**Confidence:** HIGH

## Summary

Phase 109 implements `opt=2` for `@ql.compile`, which automatically identifies overlapping-qubit sequences from the call graph DAG, merges them into unified gate lists, and runs cross-boundary gate optimization (inverse cancellation + rotation merge). The implementation builds entirely on existing infrastructure: `CallGraphDAG.parallel_groups()` for connected-component detection, `_optimize_gate_list()` for multi-pass optimization, and `CompiledBlock` for storing merged results.

The core challenge is correctly concatenating gate lists from multiple CompiledBlocks while preserving per-qubit gate ordering, then running the existing optimizer on the concatenated list to achieve cross-boundary cancellations (e.g., QFT trailing rotations cancelling IQFT leading rotations). The merge must happen after all sequences are captured (first `__call__`) but before the result is cached, and the original DAG must remain accessible for inspection.

**Primary recommendation:** Implement merge as a post-capture step in `_CompiledFunc.__call__()` that (1) uses `parallel_groups()` to find connected components of overlapping nodes, (2) concatenates gates in temporal call order, (3) runs `_optimize_gate_list()` on the merged list, and (4) replays the merged+optimized gates via a new merged `CompiledBlock`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Only merge node pairs connected by overlap edges (sharing qubits) -- non-overlapping nodes stay independent
- Chain merges: if A overlaps B and B overlaps C, merge all three into one block (connected components from overlap graph)
- Configurable merge threshold: default merge on any overlap (1+ shared qubit), user can set minimum via parameter (e.g., `merge_threshold=3`)
- Only sibling overlap edges eligible -- parent-child call edges never trigger merge; `build_overlap_edges()` already skips call-edge pairs
- Simple concatenation in temporal call order: all gates from A, then B, then C
- Per-qubit gate ordering preserved automatically since each sequence's internal ordering is correct
- No qubit remapping needed -- gate lists already use physical qubit indices from capture/replay
- Merged gate list stored as a new CompiledBlock, reusing existing replay/inject infrastructure
- Reuse existing `_optimize_gates` multi-pass optimizer (inverse cancellation + rotation merge) on the concatenated gate list
- Handles QFT/IQFT cancellation naturally since QFT ends with rotations that cancel IQFT's start rotations
- Multi-pass runs until convergence (existing behavior, no changes needed)
- Merged+optimized result cached for subsequent calls with same arguments (follows capture-replay pattern)
- Merge statistics exposed via debug mode: number of merge groups, gates before/after optimization, cancellation count
- Function returns same result as opt=1 (compiled function works normally), but internally replays merged+optimized gate lists
- call_graph still accessible and reflects pre-merge structure (original DAG)
- Merging happens eagerly during first __call__ -- after capturing all sequences, immediately merge overlapping groups and cache
- Parametric + opt=2 combination raises ValueError (not supported in this phase)
- Controlled context (function inside `with qbool:`) supported -- derive controlled variant from merged CompiledBlock using existing controlled derivation code

### Claude's Discretion
- How to identify connected components for chain merge (reuse parallel_groups or new helper)
- Cache key strategy for merged blocks (whether to include merge_threshold)
- Where in __call__ flow the merge step is inserted
- How merge_threshold parameter is passed (kwarg on @ql.compile or separate)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAPI-02 | User can set `@ql.compile(opt=2)` to selectively merge overlapping-qubit sequences | `self._opt` already wired in CompiledFunc.__init__ (line 688); opt=2 path needs new merge logic branching from existing opt!=3 DAG code |
| MERGE-01 | Overlapping-qubit sequences automatically identified as merge candidates | `CallGraphDAG.parallel_groups()` returns connected components via overlap graph -- directly reusable for merge group detection |
| MERGE-02 | Merged sequences preserve correct per-qubit gate ordering | Concatenation in temporal (call) order with physical qubit indices preserves ordering; existing `_optimize_gate_list` only cancels/merges adjacent gates, never reorders |
| MERGE-03 | Cross-boundary optimization (e.g., QFT/IQFT cancellation between adjacent sequences) | `_optimize_gate_list()` multi-pass inverse cancellation handles this when gates from sequence A's end are adjacent to sequence B's start in the concatenated list |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rustworkx | >=0.13 | Graph primitives (PyDAG, PyGraph, connected_components) | Already used for CallGraphDAG; provides `rx.connected_components()` for merge group detection |
| numpy | >=1.24 | Bitmask operations for qubit overlap | Already used for DAGNode.bitmask and _popcount_array |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=7.0 | Test framework | All unit and integration tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| parallel_groups() for components | Manual BFS/DFS | parallel_groups already does exactly this with rustworkx -- no reason to rewrite |
| New MergedBlock class | Reuse CompiledBlock | CompiledBlock stores gates + metadata; merged result fits naturally as a new CompiledBlock instance |

## Architecture Patterns

### Recommended Code Location
```
src/quantum_language/
├── compile.py           # Add merge logic to CompiledFunc.__call__
│                        # New: _merge_overlapping_groups() helper
│                        # New: merge_threshold param in __init__
├── call_graph.py        # Existing parallel_groups() reused as-is
│                        # May add merge_groups(threshold) convenience method
tests/python/
├── test_merge.py        # New: merge-specific tests (MERGE-01/02/03)
├── test_call_graph.py   # Existing: may extend for threshold filtering
```

### Pattern 1: Merge Group Detection via parallel_groups()
**What:** Use `CallGraphDAG.parallel_groups()` to find connected components of overlapping nodes, then filter by merge_threshold.
**When to use:** During opt=2 first call, after DAG is built with overlap edges.
**Recommendation:** Reuse `parallel_groups()` directly. It already builds an undirected overlap graph and returns connected components via `rx.connected_components()`. For threshold filtering, add a `merge_groups(threshold=1)` method that filters edges by weight before computing components.

```python
# Recommended: add to CallGraphDAG
def merge_groups(self, threshold: int = 1) -> list[list[int]]:
    """Return merge groups: connected components where all overlap >= threshold.

    Each group is sorted by node index (temporal call order).
    Single-node groups are excluded (nothing to merge).
    """
    n = len(self._nodes)
    if n < 2:
        return []

    g = rx.PyGraph()
    for _ in range(n):
        g.add_node(None)

    bitmasks = np.array([nd.bitmask for nd in self._nodes], dtype=np.uint64)
    for i in range(n):
        overlaps = np.bitwise_and(bitmasks[i], bitmasks[i + 1:])
        weights = _popcount_array(overlaps)
        for j_off in range(len(weights)):
            if weights[j_off] >= threshold:
                g.add_edge(i, i + 1 + j_off, int(weights[j_off]))

    components = rx.connected_components(g)
    # Only return multi-node groups (single nodes don't need merging)
    return [sorted(comp) for comp in components if len(comp) > 1]
```

### Pattern 2: Gate Concatenation and Optimization
**What:** Collect physical gate lists from each node's CompiledBlock in temporal order, concatenate, run `_optimize_gate_list()`.
**When to use:** For each merge group identified by merge_groups().

**Key insight:** Gates in CompiledBlocks use virtual qubit indices. For merging, we need to work with physical qubit indices (post-remapping) since different blocks have different virtual namespaces. The merge should concatenate the physical gates from each sequence.

```python
def _merge_and_optimize(blocks_in_order, optimize=True):
    """Concatenate gate lists from multiple blocks and optimize.

    Parameters
    ----------
    blocks_in_order : list of (CompiledBlock, virtual_to_real_mapping)
        Blocks in temporal call order, with their qubit mappings.

    Returns
    -------
    list[dict]
        Optimized gate list using physical qubit indices.
    """
    merged_gates = []
    for block, v2r in blocks_in_order:
        # Remap virtual gates to physical
        for g in block.gates:
            pg = dict(g)
            pg["target"] = v2r[g["target"]]
            pg["controls"] = [v2r[c] for c in g["controls"]]
            merged_gates.append(pg)

    original_count = len(merged_gates)
    if optimize:
        merged_gates = _optimize_gate_list(merged_gates)

    return merged_gates, original_count
```

### Pattern 3: Merged Block Storage and Replay
**What:** Store the merged+optimized gate list as a special merged CompiledBlock that replays using physical qubit indices (identity mapping).
**When to use:** After merging, cache the result so subsequent calls replay merged gates.

```python
# The merged block uses physical indices directly
# On replay, inject_remapped_gates with identity mapping
merged_block = CompiledBlock(
    gates=merged_optimized_gates,
    total_virtual_qubits=len(all_physical_qubits),
    param_qubit_ranges=[],  # Not used for merged replay
    internal_qubit_count=0,
    return_qubit_range=None,
    original_gate_count=original_total,
)
```

### Pattern 4: opt=2 Flow in __call__
**What:** Insert merge step after first-call DAG building, before caching.
**When to use:** Only when `self._opt == 2`.

```python
# In __call__, after _call_inner and before return:
if _is_top_level_dag and self._opt == 2 and self._call_graph is not None:
    self._apply_merge(self._call_graph)
```

### Anti-Patterns to Avoid
- **Merging in virtual qubit space:** Each block has its own virtual namespace. Merge must happen in physical qubit space or with a unified remapping.
- **Modifying the original DAG:** The `call_graph` property must reflect pre-merge structure. Merge results should be stored separately.
- **Re-executing function body for merge:** Merge operates on already-captured gate lists, not by re-running functions.
- **Merging parent-child pairs:** Only sibling nodes sharing qubits are merge candidates. `build_overlap_edges()` already enforces this.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connected component detection | Custom BFS/DFS | `rx.connected_components()` via `parallel_groups()` or new `merge_groups()` | Already implemented, tested, handles edge cases |
| Gate cancellation/merge | Custom optimizer | `_optimize_gate_list()` | Multi-pass convergence, handles inverse pairs + rotation merge |
| Gate injection into circuit | Custom circuit manipulation | `inject_remapped_gates()` | C-level function, handles layer management |
| Controlled variant derivation | Custom control logic | `_derive_controlled_gates()` | Already handles num_controls increment + control prepend |

**Key insight:** Almost all building blocks exist. The phase is primarily about orchestrating existing components in the right order.

## Common Pitfalls

### Pitfall 1: Virtual vs Physical Qubit Confusion
**What goes wrong:** Attempting to concatenate gates from different CompiledBlocks in virtual space fails because each block has its own virtual-to-real mapping.
**Why it happens:** CompiledBlock.gates use virtual indices; merging requires a shared namespace.
**How to avoid:** Always remap to physical indices before concatenation, or build a unified virtual mapping across all blocks in the merge group.
**Warning signs:** Gate targets pointing to wrong qubits, incorrect cancellations.

### Pitfall 2: Temporal Order Assumption
**What goes wrong:** Nodes in a merge group are concatenated in arbitrary order instead of call order.
**Why it happens:** `rx.connected_components()` returns sets, not ordered sequences.
**How to avoid:** Sort nodes by their DAG index (which corresponds to temporal call order since `add_node` is called sequentially during capture).
**Warning signs:** Per-qubit gate ordering violations, incorrect simulation results.

### Pitfall 3: Double-Counting Gates After Merge
**What goes wrong:** Both original per-sequence gates AND merged gates get injected into the circuit.
**Why it happens:** Merge step runs after sequences have already been captured and their gates injected.
**How to avoid:** The merge optimization benefit is for subsequent calls (replay). On first call, gates are already in the circuit. The merged block replaces per-sequence replay on subsequent calls, OR the first call needs to extract-and-reinject. Decision: since CONTEXT.md says "merging happens eagerly during first __call__", the first call captures normally, then merging produces a cached merged block for future replays.
**Warning signs:** Gate count doubling, incorrect circuit depth.

### Pitfall 4: Parametric + opt=2 Interaction
**What goes wrong:** Parametric functions with opt=2 produce incorrect results due to angle substitution conflicts with merged gates.
**Why it happens:** Parametric replay uses topology matching, which doesn't account for cross-block merging.
**How to avoid:** Raise `ValueError` early when `parametric=True` and `opt=2` (locked decision).
**Warning signs:** Silent incorrect results.

### Pitfall 5: Cache Key Must Include merge_threshold
**What goes wrong:** Different merge_threshold values produce different optimized gate lists but share the same cache entry.
**Why it happens:** merge_threshold not included in cache key.
**How to avoid:** Include merge_threshold in the merged result's cache key or store it separately from per-sequence cache.
**Warning signs:** Stale merged results when threshold changes between calls.

### Pitfall 6: Controlled Context During Merge
**What goes wrong:** Merged block doesn't properly handle controlled contexts (`with qbool:`).
**Why it happens:** Individual blocks have `control_virtual_idx` set, but merged block needs its own control handling.
**How to avoid:** Derive controlled variant from merged block using `_derive_controlled_gates()` on the merged physical gate list.
**Warning signs:** Missing control qubits in merged+controlled circuits.

## Code Examples

### Existing parallel_groups() (reusable for merge detection)
```python
# Source: call_graph.py:239-266
def parallel_groups(self) -> list[set[int]]:
    n = len(self._nodes)
    if n == 0:
        return []
    g = rx.PyGraph()
    for _ in range(n):
        g.add_node(None)
    if n < 2:
        return [set(comp) for comp in rx.connected_components(g)]
    bitmasks = np.array([nd.bitmask for nd in self._nodes], dtype=np.uint64)
    for i in range(n):
        overlaps = np.bitwise_and(bitmasks[i], bitmasks[i + 1:])
        weights = _popcount_array(overlaps)
        for j_off in range(len(weights)):
            if weights[j_off] > 0:
                g.add_edge(i, i + 1 + j_off, int(weights[j_off]))
    return [set(comp) for comp in rx.connected_components(g)]
```

### Existing _optimize_gate_list() (reuse on merged gates)
```python
# Source: compile.py:245-272
def _optimize_gate_list(gates):
    prev_count = len(gates) + 1
    optimized = list(gates)
    max_passes = 10
    passes = 0
    while len(optimized) < prev_count and passes < max_passes:
        prev_count = len(optimized)
        passes += 1
        result = []
        for gate in optimized:
            if result and _gates_cancel(result[-1], gate):
                result.pop()
            elif result and _gates_merge(result[-1], gate):
                merged = _merged_gate(result[-1], gate)
                if merged is None:
                    result.pop()
                else:
                    result[-1] = merged
            else:
                result.append(gate)
        optimized = result
    return optimized
```

### Existing inject_remapped_gates (C-level gate injection)
```python
# Source: compile.py:1428
# Used in _replay to inject cached gates onto circuit
inject_remapped_gates(block.gates, virtual_to_real)
```

### CompiledFunc.__init__ opt parameter (already wired)
```python
# Source: compile.py:675-688
def __init__(self, func, max_cache=128, key=None, verify=False,
             optimize=True, inverse=False, debug=False,
             parametric=False, opt=1):
    ...
    self._opt = opt
    self._call_graph = None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| opt=3 full expansion | opt=1 DAG-based sequence tracking | Phase 107 (v7.0) | Sequences tracked independently, no cross-boundary optimization |
| No overlap detection | build_overlap_edges() + parallel_groups() | Phase 107 | Overlap infrastructure ready for merge |
| Per-sequence optimization only | Cross-boundary optimization via merge (this phase) | Phase 109 | Enables QFT/IQFT cancellation across sequence boundaries |

## Design Decisions (Claude's Discretion)

### 1. merge_groups() vs reusing parallel_groups()
**Recommendation:** Add a new `merge_groups(threshold=1)` method to `CallGraphDAG` rather than modifying `parallel_groups()`. Reasons:
- `parallel_groups()` has existing tests and semantics (returns ALL components including singletons)
- `merge_groups()` needs threshold filtering and should only return multi-node groups
- Clean separation of concerns

### 2. Cache Key Strategy
**Recommendation:** Store merged result in a separate `_merged_cache` dict on `CompiledFunc`, keyed by `(cache_key, merge_threshold)`. This avoids polluting the per-sequence cache and makes cache invalidation cleaner. The merged cache is cleared on `_reset_for_circuit()`.

### 3. Where Merge Step is Inserted
**Recommendation:** Insert merge step at the end of `__call__()`, after `_call_inner` returns and after the DAG is finalized (overlap edges built). The flow:
1. `__call__` creates DAG, runs `_call_inner` (captures all sequences normally)
2. After `pop_dag_context()` and `build_overlap_edges()`, if `self._opt == 2`:
   - Call `self._apply_merge()` which uses `self._call_graph.merge_groups(threshold)`
   - For each multi-node group, concatenate physical gates, optimize, store merged block
   - On subsequent calls, check merged cache first
3. Return result from original `_call_inner` (first call uses per-sequence gates already in circuit)

### 4. merge_threshold Parameter Passing
**Recommendation:** Add `merge_threshold` as a keyword argument to `@ql.compile()`:
```python
@ql.compile(opt=2, merge_threshold=3)
def my_func(x, y):
    ...
```
Store as `self._merge_threshold` in `CompiledFunc.__init__`, default to 1.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=7.0 |
| Config file | pytest.ini or pyproject.toml (project-level) |
| Quick run command | `pytest tests/python/test_merge.py -x -v` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAPI-02 | `@ql.compile(opt=2)` accepted, produces correct results | integration | `pytest tests/python/test_merge.py::test_opt2_basic -x` | No -- Wave 0 |
| MERGE-01 | Overlapping sequences auto-detected as merge candidates | unit | `pytest tests/python/test_merge.py::test_merge_group_detection -x` | No -- Wave 0 |
| MERGE-02 | Merged sequences preserve per-qubit gate ordering | unit+integration | `pytest tests/python/test_merge.py::test_gate_ordering_preserved -x` | No -- Wave 0 |
| MERGE-03 | Cross-boundary optimization fires (QFT/IQFT cancellation) | integration | `pytest tests/python/test_merge.py::test_cross_boundary_cancellation -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_merge.py -x -v`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/python/test_merge.py` -- covers CAPI-02, MERGE-01, MERGE-02, MERGE-03
- [ ] Framework install: already available (pytest in project dependencies)

## Open Questions

1. **Physical vs Virtual Gate Merging**
   - What we know: CompiledBlock.gates use virtual indices; each block has its own virtual_to_real mapping stored during capture
   - What's unclear: Whether we should merge in physical space (simpler but loses reusability) or build a unified virtual space
   - Recommendation: Merge in physical space for first call, then store merged physical gates. For replay, use identity mapping. This is simpler and aligns with "merged+optimized result cached" decision.

2. **First Call Behavior with opt=2**
   - What we know: First call captures normally (gates already in circuit). Merging produces a cached block for future replays.
   - What's unclear: Should the first call also benefit from merged optimization (by extracting and re-injecting)?
   - Recommendation: First call runs with per-sequence optimization only (existing behavior). Merged optimization benefits replay calls. This avoids the complexity of extract-reinject on first call.

3. **Accessing per-sequence blocks for gate concatenation**
   - What we know: During `_call_inner`, blocks are cached in `self._cache` keyed by cache_key. DAG nodes store `cache_key` but not the blocks directly.
   - What's unclear: How to map DAG node indices to their corresponding CompiledBlocks and virtual_to_real mappings.
   - Recommendation: During capture, store a reference to the block and v2r mapping on the DAGNode (or in a parallel structure indexed by node index). This enables merge to access per-sequence data.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/call_graph.py` -- Full source read, parallel_groups() at line 239, build_overlap_edges() at line 206
- `src/quantum_language/compile.py` -- Full source read, CompiledFunc at line 645, _optimize_gate_list at line 245, CompiledBlock at line 331, _replay at line 1384
- `tests/python/test_call_graph.py` -- Existing test patterns for DAG functionality

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions -- locked decisions from user discussion

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, no new dependencies
- Architecture: HIGH -- building on existing patterns (parallel_groups, _optimize_gate_list, CompiledBlock)
- Pitfalls: HIGH -- identified from direct code reading (virtual/physical qubit mapping, temporal ordering, cache keys)

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable internal codebase, no external dependencies changing)
