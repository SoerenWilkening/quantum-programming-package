# Phase 108: Call Graph Analysis & Visualization - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract per-node metrics (gate count, depth, qubit count, T-count) from the call graph DAG, compute aggregate totals, export DOT visualization, and produce compilation reports. Covers requirements CGRAPH-04, CGRAPH-05, VIS-01, VIS-02.

</domain>

<decisions>
## Implementation Decisions

### Stats extraction
- Compute all stats eagerly at DAGNode creation time (during __call__)
- Depth calculated via gate list analysis: track qubit occupancy through CompiledBlock's gate list (pure Python, no C calls)
- T-count uses dual formula from v3.0: count T_GATE/TDG_GATE entries, fall back to 7*CCX estimate when toffoli_decompose is off
- Four metrics per node: gate_count (already exists), depth, qubit_count (len(qubit_set)), t_count
- DAGNode.__slots__ extended with depth and t_count fields

### DOT visualization
- API: `dag.to_dot()` returns valid DOT string
- Node labels show all stats: func_name, gates, depth, qubits, T-count (multi-line label)
- Call edges: solid arrows, labeled "call"
- Overlap edges: dashed arrows, labeled with shared qubit count (e.g., "4 qubits")
- Parallel groups rendered as DOT subgraph clusters with dotted border labeled "Group N"

### Compilation report
- API: `dag.report()` returns formatted multi-line string
- Header line: "Compilation Report: <top-level func_name>"
- Table columns: Name | Gates | Depth | Qubits | T-count | Group
- Footer: aggregate totals row
- Parallel group membership shown as group number per node

### Aggregate metrics
- API: `dag.aggregate()` returns dict with keys: gates, depth, qubits, t_count
- Gate count: simple sum across all nodes
- T-count: simple sum across all nodes
- Qubit count: union of all node qubit sets (unique physical qubits)
- Depth: critical-path depth -- sum depths along longest serial chain; parallel groups contribute max(depth within group), not sum

### Claude's Discretion
- Internal depth calculation algorithm details (ASAP scheduling or simpler approach)
- Column alignment and spacing in report table
- DOT graph attributes (rankdir, fontname, etc.)
- How to identify the "top-level function name" for report header

</decisions>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CallGraphDAG` class (`call_graph.py`): Already has nodes, overlap edges, parallel_groups() -- extend with stats, to_dot(), report(), aggregate()
- `DAGNode` (`call_graph.py:48`): Has __slots__ with func_name, qubit_set, gate_count, cache_key, bitmask -- extend with depth, t_count
- `circuit_stats()` in `state.py`: Existing stats function for full circuits -- pattern reference for per-node analysis
- Dual T-count formula from v3.0: T_GATE/TDG_GATE counting + 7*CCX fallback

### Established Patterns
- `__slots__` on DAGNode for memory efficiency
- NumPy bitmask operations for fast qubit overlap
- rustworkx PyDAG for graph operations
- CompiledBlock stores gate lists with gate type, qubit indices, parameters

### Integration Points
- `_CompiledFunc.__call__()` in `compile.py`: Where DAGNode is created -- must pass depth/t_count computed from gate list
- `CallGraphDAG` class: Add to_dot(), report(), aggregate() methods
- `__init__.py`: CallGraphDAG already exported -- no new exports needed

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 108-call-graph-analysis-visualization*
*Context gathered: 2026-03-06*
