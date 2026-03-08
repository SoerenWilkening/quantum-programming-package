# Phase 109: Selective Sequence Merging - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement `opt=2` for `@ql.compile` that automatically identifies overlapping-qubit sequences, merges them into unified CompiledBlocks, and runs cross-boundary gate optimization. Covers requirements CAPI-02, MERGE-01, MERGE-02, MERGE-03.

</domain>

<decisions>
## Implementation Decisions

### Merge candidate selection
- Only merge node pairs connected by overlap edges (sharing qubits) -- non-overlapping nodes stay independent
- Chain merges: if A overlaps B and B overlaps C, merge all three into one block (connected components from overlap graph)
- Configurable merge threshold: default merge on any overlap (1+ shared qubit), user can set minimum via parameter (e.g., `merge_threshold=3`)
- Only sibling overlap edges eligible -- parent-child call edges never trigger merge; `build_overlap_edges()` already skips call-edge pairs

### Gate ordering during merge
- Simple concatenation in temporal call order: all gates from A, then B, then C
- Per-qubit gate ordering preserved automatically since each sequence's internal ordering is correct
- No qubit remapping needed -- gate lists already use physical qubit indices from capture/replay
- Merged gate list stored as a new CompiledBlock, reusing existing replay/inject infrastructure

### Cross-boundary optimization
- Reuse existing `_optimize_gates` multi-pass optimizer (inverse cancellation + rotation merge) on the concatenated gate list
- Handles QFT/IQFT cancellation naturally since QFT ends with rotations that cancel IQFT's start rotations
- Multi-pass runs until convergence (existing behavior, no changes needed)
- Merged+optimized result cached for subsequent calls with same arguments (follows capture-replay pattern)
- Merge statistics exposed via debug mode: number of merge groups, gates before/after optimization, cancellation count

### opt=2 behavior
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

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CallGraphDAG.build_overlap_edges()` (`call_graph.py:206`): Already computes overlap weights between all node pairs -- direct input for merge candidate detection
- `CallGraphDAG.parallel_groups()` (`call_graph.py:239`): Connected components via undirected overlap graph -- same logic needed for chain merge groups
- `_optimize_gates()` (`compile.py:246`): Multi-pass inverse cancellation + rotation merge -- run on concatenated gate list for cross-boundary optimization
- `CompiledBlock` (`compile.py:331`): Stores gate lists, qubit ranges, gate counts -- merged result stored as new CompiledBlock
- `DAGNode.bitmask` (`call_graph.py:132`): NumPy uint64 bitmask for fast qubit overlap computation

### Established Patterns
- Capture-replay: first call captures, subsequent calls replay with qubit remapping
- `_optimize_gates` runs on virtual gate list before caching
- Controlled variant derivation creates new CompiledBlock with control qubit added
- Debug stats via `.stats` property and `debug=True` parameter
- Cache invalidation via `_register_cache_clear_hook`

### Integration Points
- `_CompiledFunc.__call__()` (`compile.py:708`): Main entry -- merge step inserted after DAG building, before caching
- `_CompiledFunc._call_inner()`: Where individual sequences are captured -- merge operates on completed captures
- `self._opt` (`compile.py:688`): Already wired; `opt=2` path needs new merge logic
- `self._call_graph` (`compile.py:689`): DAG available for merge candidate detection

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 109-selective-sequence-merging*
*Context gathered: 2026-03-06*
