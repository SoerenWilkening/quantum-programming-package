# Phase 107: Call Graph DAG Foundation - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `opt` parameter to `@ql.compile` and build a call graph DAG that captures program structure (nodes = compiled function calls, edges = qubit dependency) alongside normal circuit expansion. Covers requirements CAPI-01, CAPI-03, CAPI-04, CGRAPH-01, CGRAPH-02, CGRAPH-03.

</domain>

<decisions>
## Implementation Decisions

### opt_flag API surface
- Default `opt=1` (new default) -- DAG built on every `@ql.compile` call, gates still emitted normally
- `opt=3` gives identical behavior to current `@ql.compile()` (full expansion, no DAG) for backward compat
- DAG accessible via property on compiled function: `my_func.call_graph`
- DAG built eagerly during every `__call__`, always available after first call
- All 106+ existing compile tests must pass unchanged when `opt=3` is explicit

### DAG node granularity
- One node per invocation of a `@ql.compile` function (not per unique CompiledBlock)
- If `f` calls `g` twice, that's 2 child nodes for `g` in the DAG
- Hierarchical: nested compiled function calls (f calls g) appear as parent-child edges
- Non-compiled operations (raw qint arithmetic) do NOT appear in the DAG
- Each node carries: function name, qubit set (frozenset of physical qubit indices), gate count, cache key

### Qubit overlap edge semantics
- Directed edges: A -> B means A was called before B and they share qubits
- Edge weight = |qubit_set_A intersection qubit_set_B| (shared qubit count, integer)
- Edges connect any two nodes with overlapping qubits, not just temporally adjacent ones
- No edge between disjoint nodes (absence of edge = independent)

### Concurrency group detection
- Parallel groups identified via connected components of the overlap graph (undirected projection)
- Exposed as method: `dag.parallel_groups()` returning list of node-index sets
- Groups use pure qubit disjointness (no temporal ordering constraint)
- rustworkx `weakly_connected_components()` or equivalent for component detection

### Performance requirement
- Qubit overlap computation must be fast -- NumPy bitmask intersection (bitwise AND + popcount) as baseline
- If NumPy is insufficient for large graphs, investigate Cython or Numba acceleration
- Researcher should benchmark NumPy bitmask approach and determine if optimization is needed

### Claude's Discretion
- Internal DAG class design (CallGraphDAG vs thin wrapper around rustworkx PyDAG)
- How to intercept nested compiled calls for parent-child tracking
- Whether to store the qubit set as NumPy bitmask internally and convert to frozenset for user API
- Edge storage strategy in rustworkx (weight as int attribute vs separate data)

</decisions>

<specifics>
## Specific Ideas

- "Computation of overlapping qubits etc. should work as fast as possible" -- user explicitly wants performance-conscious implementation, NumPy may not be enough
- opt=1 as default is intentional -- the DAG is the primary new feature and should be opt-out, not opt-in

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CompiledBlock` class (`compile.py:321`): Already stores gate lists, qubit ranges, gate counts -- node metadata source
- `_CompiledFunc._cache` (OrderedDict): Existing cache infrastructure, cache_key already captures function identity + widths
- `extract_gate_range()` / `inject_remapped_gates()` in `_core.pyx`: C-level gate extraction/injection primitives
- `_get_mode_flags()` (`compile.py:61`): Mode-aware cache key construction pattern

### Established Patterns
- Capture-replay pattern: First call captures, subsequent calls replay with qubit remapping
- Cache key: `(classical_args, width_tuple, is_controlled, mode_flags)` -- well-established
- `_clear_all_caches()` hook via `_register_cache_clear_hook`: Cache invalidation on circuit reset
- Nested compilation already supported (compiled functions calling compiled functions)

### Integration Points
- `_CompiledFunc.__call__()` (`compile.py:695`): Main entry point where DAG nodes would be created
- `_CompiledFunc._capture_and_cache_both()` (`compile.py:979`): Where qubit sets are first known
- `_CompiledFunc._replay()`: Where qubit remapping happens -- qubit set available from mapping
- `__init__.py`: Would need to export the DAG class and any new API

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 107-call-graph-dag-foundation*
*Context gathered: 2026-03-05*
