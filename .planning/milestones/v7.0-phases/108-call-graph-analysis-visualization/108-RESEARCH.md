# Phase 108: Call Graph Analysis & Visualization - Research

**Researched:** 2026-03-06
**Domain:** Python graph analysis, DOT export, text reporting
**Confidence:** HIGH

## Summary

Phase 108 extends the existing `CallGraphDAG` and `DAGNode` classes (built in Phase 107) with four capabilities: per-node metrics (depth, T-count), aggregate totals, DOT visualization, and compilation reports. All work is pure Python on top of the existing rustworkx `PyDAG` and `CompiledBlock` gate lists.

The core technical challenge is computing per-node circuit depth from gate lists (qubit occupancy tracking) and T-count using the dual formula (direct T/Tdg counting + 7*CCX fallback). Aggregate depth requires critical-path analysis through parallel groups, which rustworkx supports natively via `dag_weighted_longest_path_length`. DOT export is straightforward string formatting. No external libraries beyond what's already installed are needed.

**Primary recommendation:** Extend `DAGNode.__slots__` with `depth` and `t_count`, compute both eagerly in `add_node()` by passing gate list data, then add `to_dot()`, `report()`, and `aggregate()` methods to `CallGraphDAG`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Compute all stats eagerly at DAGNode creation time (during __call__)
- Depth calculated via gate list analysis: track qubit occupancy through CompiledBlock's gate list (pure Python, no C calls)
- T-count uses dual formula from v3.0: count T_GATE/TDG_GATE entries, fall back to 7*CCX estimate when toffoli_decompose is off
- Four metrics per node: gate_count (already exists), depth, qubit_count (len(qubit_set)), t_count
- DAGNode.__slots__ extended with depth and t_count fields
- API: `dag.to_dot()` returns valid DOT string
- Node labels show all stats: func_name, gates, depth, qubits, T-count (multi-line label)
- Call edges: solid arrows, labeled "call"
- Overlap edges: dashed arrows, labeled with shared qubit count
- Parallel groups rendered as DOT subgraph clusters with dotted border labeled "Group N"
- API: `dag.report()` returns formatted multi-line string
- Header line: "Compilation Report: <top-level func_name>"
- Table columns: Name | Gates | Depth | Qubits | T-count | Group
- Footer: aggregate totals row
- Parallel group membership shown as group number per node
- API: `dag.aggregate()` returns dict with keys: gates, depth, qubits, t_count
- Gate count aggregate: simple sum across all nodes
- T-count aggregate: simple sum across all nodes
- Qubit count aggregate: union of all node qubit sets (unique physical qubits)
- Depth aggregate: critical-path depth -- sum depths along longest serial chain; parallel groups contribute max(depth within group), not sum

### Claude's Discretion
- Internal depth calculation algorithm details (ASAP scheduling or simpler approach)
- Column alignment and spacing in report table
- DOT graph attributes (rankdir, fontname, etc.)
- How to identify the "top-level function name" for report header

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CGRAPH-04 | Precise gate count, depth, qubit count, and T-count extractable per node from call graph | Extend DAGNode with depth/t_count fields, compute from gate list at creation time |
| CGRAPH-05 | Aggregate totals (gates, depth, T-count) computed across full call graph without building circuit | `dag.aggregate()` method using sum for gates/t_count, union for qubits, critical-path for depth |
| VIS-01 | User can export call graph as DOT string via API | `dag.to_dot()` method generating valid DOT with clusters and styled edges |
| VIS-02 | Compilation report showing per-node stats (gate count, depth, qubit set, parallel group) | `dag.report()` method producing formatted table string |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rustworkx | (installed) | Graph primitives, critical-path computation | Already used for PyDAG in Phase 107; has `dag_weighted_longest_path_length` |
| numpy | (installed) | Bitmask operations for qubit overlap | Already used in call_graph.py |

### Supporting
No additional libraries needed. DOT format is plain text -- no graphviz Python binding required.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled DOT strings | pydot / graphviz package | Overkill for string generation; adds dependency for no benefit |
| Manual critical-path | `rx.dag_weighted_longest_path_length` | rustworkx is already a dependency and handles this natively |

## Architecture Patterns

### Files to Modify
```
src/quantum_language/
├── call_graph.py       # DAGNode (add depth, t_count), CallGraphDAG (add to_dot, report, aggregate)
├── compile.py          # _call_inner and _capture_inner: pass gate list to compute depth/t_count
```

### Pattern 1: Eager Stats Computation at DAGNode Creation
**What:** Compute depth and t_count from the gate list at DAGNode construction time, not lazily.
**When to use:** Every `add_node()` call.
**Details:**

The `add_node()` signature needs extending to accept `depth` and `t_count` (or a gate list from which to compute them). The cleaner approach: compute depth and t_count in `compile.py` at the three call sites where `dag.add_node()` is invoked, then pass the pre-computed values.

Three `add_node()` call sites in compile.py:
1. **Line 807** (parametric path) -- has access to `block.gates`
2. **Line 842** (replay/cache-hit path) -- has access to `block.gates`
3. **Line 982** (capture placeholder) -- placeholder with 0 gates, updated at line 1097

For the placeholder path (site 3), depth and t_count start at 0 and get updated after capture completes (same pattern as gate_count update at line 1105).

### Pattern 2: Depth Calculation via Qubit Occupancy Tracking
**What:** Track when each qubit becomes free (ASAP scheduling) through the gate list.
**When to use:** Computing per-node circuit depth.
**Algorithm:**
```python
def _compute_depth(gates: list[dict]) -> int:
    """Compute circuit depth from gate list using qubit occupancy tracking."""
    if not gates:
        return 0
    qubit_time = {}  # qubit_index -> earliest free time step
    for gate in gates:
        target = gate["target"]
        controls = gate["controls"]
        all_qubits = [target] + controls
        # Gate starts at max occupancy of all involved qubits
        start_time = max(qubit_time.get(q, 0) for q in all_qubits)
        end_time = start_time + 1
        for q in all_qubits:
            qubit_time[q] = end_time
    return max(qubit_time.values()) if qubit_time else 0
```

### Pattern 3: Dual T-count Formula
**What:** Count T gates directly, fall back to CCX estimation.
**When to use:** Computing per-node T-count.
**Algorithm:**
```python
# Gate type constants from compile.py + types.h enum
_T_GATE = 10   # T_GATE in Standardgate_t enum
_TDG_GATE = 11  # TDG_GATE in Standardgate_t enum

def _compute_t_count(gates: list[dict]) -> int:
    """Compute T-count from gate list using dual formula."""
    t_direct = 0
    ccx_count = 0
    has_t_gates = False
    for gate in gates:
        gtype = gate["type"]
        if gtype == _T_GATE or gtype == _TDG_GATE:
            t_direct += 1
            has_t_gates = True
        elif gate["num_controls"] >= 2:
            # CCX (Toffoli) or multi-controlled gate
            ccx_count += 1
    # If T gates present, use direct count; otherwise estimate from CCX
    if has_t_gates:
        return t_direct
    else:
        return 7 * ccx_count
```

**Key insight:** When `toffoli_decompose` is ON, the C backend decomposes CCX into Clifford+T gates, so T_GATE/TDG_GATE entries appear in the gate list. When OFF, CCX gates remain intact and we estimate 7 T gates per CCX.

### Pattern 4: Critical-Path Aggregate Depth
**What:** Compute total depth considering parallel execution.
**When to use:** `dag.aggregate()` depth computation.
**Algorithm:**
Use `parallel_groups()` to identify independent groups. For each group, the depth contribution is `max(node.depth for node in group)`. The total depth is the sum of per-group max depths (groups must run serially since they share qubits transitively).

Wait -- the CONTEXT.md says "sum depths along longest serial chain; parallel groups contribute max(depth within group)." This means:
- Nodes in the same parallel group (disjoint qubits) can run simultaneously -> contribute max(depth) of the group
- Groups themselves are serial (they share qubits with other groups) -> sum their max-depths

```python
def aggregate(self) -> dict:
    groups = self.parallel_groups()
    total_gates = sum(n.gate_count for n in self._nodes)
    total_t = sum(n.t_count for n in self._nodes)
    all_qubits = set()
    for n in self._nodes:
        all_qubits.update(n.qubit_set)

    total_depth = 0
    for group in groups:
        group_max_depth = max(self._nodes[idx].depth for idx in group)
        total_depth += group_max_depth

    return {
        "gates": total_gates,
        "depth": total_depth,
        "qubits": len(all_qubits),
        "t_count": total_t,
    }
```

### Pattern 5: DOT Export with Subgraph Clusters
**What:** Generate valid DOT string with styled edges and cluster subgraphs.
**Recommended DOT attributes:**
- `rankdir=TB` (top-to-bottom, natural for call graphs)
- `fontname="Courier"` (monospace for aligned labels)
- Node shape: `box` with multi-line labels using `\n` in label strings
- Call edges: `style=solid`, `label="call"`
- Overlap edges: `style=dashed`, `label="N qubits"`
- Cluster subgraphs: `style=dotted`, `label="Group N"`

### Pattern 6: Report Table Formatting
**What:** Generate aligned text table.
**Recommended approach:** Use f-string formatting with fixed column widths. Python's `str.ljust()`/`str.rjust()` for alignment.

**Top-level function name:** Use `self._nodes[0].func_name` if nodes exist (the first node added is the top-level function in a fresh DAG). This follows from the capture flow: the top-level `__call__` creates the DAG and adds itself as the first node.

### Anti-Patterns to Avoid
- **Computing stats lazily:** Would require storing gate lists in DAGNode (memory waste) or re-extracting from cache (fragile coupling to compile.py internals)
- **Using graphviz Python package:** Adds unnecessary dependency for string generation
- **Modifying the rustworkx PyDAG edge structure:** Keep edges as-is, just read them for DOT export

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Critical-path depth in DAG | Manual topological sort + DP | `parallel_groups()` + per-group max | Already computed, groups capture serial dependencies correctly |
| DOT graph rendering | PIL/image generation | DOT string + external Graphviz tools | Explicitly out of scope per REQUIREMENTS.md |
| Graph traversal | Manual BFS/DFS | rustworkx built-in methods | Already a dependency, battle-tested |

## Common Pitfalls

### Pitfall 1: Gate Type Constants Out of Sync
**What goes wrong:** Using wrong integer values for T_GATE/TDG_GATE.
**Why it happens:** compile.py only defines constants for types 0-9 (X through M). T_GATE=10 and TDG_GATE=11 are defined in the C enum but not in compile.py.
**How to avoid:** Define `_T_GATE = 10` and `_TDG_GATE = 11` explicitly, matching the `Standardgate_t` enum in `types.h` (line 9 of `_core.pxd`).
**Warning signs:** T-count always zero in non-fault-tolerant mode.

### Pitfall 2: Placeholder Node Update Misses New Fields
**What goes wrong:** The capture path creates a placeholder DAGNode at line 982 with zeros, then updates it at line 1097. If depth/t_count aren't updated there too, they remain 0.
**Why it happens:** Three separate add_node() sites plus one update site -- easy to miss one.
**How to avoid:** Update all four sites systematically. The placeholder update (line 1097-1111) must also set `node.depth` and `node.t_count`.

### Pitfall 3: CCX Detection in Virtual Gate Lists
**What goes wrong:** CCX gates in virtual gate lists use `num_controls >= 2` but controls list may have been remapped.
**Why it happens:** Virtual gates store virtual qubit indices, but the gate type and num_controls remain unchanged.
**How to avoid:** Use `gate["num_controls"] >= 2` for CCX detection (this field is preserved through virtualization). The gate type for CCX is just X (type=0) with 2 controls.

### Pitfall 4: Empty DAG Edge Cases
**What goes wrong:** `aggregate()`, `report()`, or `to_dot()` called on empty DAG.
**Why it happens:** User calls methods before executing compiled function.
**How to avoid:** Return sensible defaults: empty dict for aggregate, minimal string for report, empty DOT digraph for to_dot.

### Pitfall 5: DOT Special Characters in Function Names
**What goes wrong:** Function names containing quotes or special chars break DOT syntax.
**Why it happens:** Python function names are usually safe, but edge cases exist.
**How to avoid:** Escape or sanitize node labels in DOT output.

### Pitfall 6: Parallel Group Index Assignment
**What goes wrong:** Report shows wrong group numbers for nodes.
**Why it happens:** `parallel_groups()` returns `list[set[int]]` -- the set ordering is non-deterministic.
**How to avoid:** Build a `node_index -> group_number` mapping from the groups list. Group numbering follows list order (Group 0, Group 1, etc.).

## Code Examples

### Depth Computation (verified from gate dict structure in _core.pyx:825-834)
```python
# Gate dict structure from extract_gate_range():
# {"type": int, "target": int, "angle": float, "num_controls": int, "controls": [int, ...]}

def _compute_depth(gates):
    """ASAP depth from gate list."""
    if not gates:
        return 0
    qubit_time = {}
    for gate in gates:
        involved = [gate["target"]] + gate["controls"]
        t = max((qubit_time.get(q, 0) for q in involved), default=0)
        for q in involved:
            qubit_time[q] = t + 1
    return max(qubit_time.values(), default=0)
```

### T-Count Computation
```python
_T_GATE = 10   # From Standardgate_t enum in types.h
_TDG_GATE = 11

def _compute_t_count(gates):
    """Dual T-count: direct T/Tdg count, or 7*CCX fallback."""
    t_direct = 0
    ccx_count = 0
    for g in gates:
        gt = g["type"]
        if gt == _T_GATE or gt == _TDG_GATE:
            t_direct += 1
        elif g["num_controls"] >= 2:
            ccx_count += 1
    return t_direct if t_direct > 0 else 7 * ccx_count
```

### DOT Generation
```python
def to_dot(self) -> str:
    """Export call graph as DOT string."""
    lines = ['digraph CallGraph {']
    lines.append('  rankdir=TB;')
    lines.append('  node [shape=box, fontname="Courier"];')

    # Build group membership map
    groups = self.parallel_groups()
    node_to_group = {}
    for gi, group in enumerate(groups):
        for idx in group:
            node_to_group[idx] = gi

    # Emit cluster subgraphs
    for gi, group in enumerate(groups):
        if len(groups) > 1:  # Only cluster if multiple groups
            lines.append(f'  subgraph cluster_{gi} {{')
            lines.append(f'    style=dotted;')
            lines.append(f'    label="Group {gi}";')
        for idx in sorted(group):
            n = self._nodes[idx]
            label = (f"{n.func_name}\\n"
                     f"gates: {n.gate_count}\\n"
                     f"depth: {n.depth}\\n"
                     f"qubits: {len(n.qubit_set)}\\n"
                     f"T-count: {n.t_count}")
            lines.append(f'    n{idx} [label="{label}"];')
        if len(groups) > 1:
            lines.append('  }')

    # Emit edges
    for src, tgt in self._dag.edge_list():
        data = self._dag.get_edge_data(src, tgt)
        if data.get("type") == "call":
            lines.append(f'  n{src} -> n{tgt} [label="call"];')
        elif data.get("type") == "overlap":
            w = data.get("weight", 0)
            lines.append(f'  n{src} -> n{tgt} [style=dashed, label="{w} qubits"];')

    lines.append('}')
    return '\n'.join(lines)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full circuit expansion for stats | Per-node stats from gate lists | Phase 108 (now) | Avoid O(n^2) circuit building for resource estimation |
| `circuit_stats()` (C-level) | Python gate-list analysis | Phase 108 (now) | Stats without circuit allocation |

## Open Questions

1. **Multi-controlled gate T-count estimation**
   - What we know: CCX (2 controls) decomposes to 7 T gates. Gates with 3+ controls have higher T-cost.
   - What's unclear: Should `num_controls > 2` use a different multiplier?
   - Recommendation: Use `7 * ccx_count` for now (matching v3.0 formula). Multi-controlled gates with 3+ controls are rare in practice and can be refined later.

2. **Depth computation for controlled gates with large_control**
   - What we know: Gates with `num_controls > 2` use `large_control` array, but `controls` in the gate dict already includes all controls (see extract_gate_range line 833).
   - What's unclear: No ambiguity -- the gate dict `controls` list is complete.
   - Recommendation: Use `gate["controls"]` directly; it handles all cases.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | (project root, standard pytest discovery) |
| Quick run command | `pytest tests/python/test_call_graph.py -x -v` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CGRAPH-04 | Per-node depth, t_count, qubit_count on DAGNode | unit | `pytest tests/python/test_call_graph.py -x -k "depth or t_count"` | No -- Wave 0 |
| CGRAPH-05 | aggregate() returns correct dict | unit | `pytest tests/python/test_call_graph.py -x -k "aggregate"` | No -- Wave 0 |
| VIS-01 | to_dot() returns valid DOT string | unit | `pytest tests/python/test_call_graph.py -x -k "to_dot"` | No -- Wave 0 |
| VIS-02 | report() returns formatted string with columns | unit | `pytest tests/python/test_call_graph.py -x -k "report"` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_call_graph.py -x -v`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Tests for `_compute_depth()` -- pure function, easy to unit test with crafted gate lists
- [ ] Tests for `_compute_t_count()` -- pure function, test both T-gate and CCX paths
- [ ] Tests for `DAGNode` with depth/t_count fields
- [ ] Tests for `CallGraphDAG.aggregate()` -- empty, single node, parallel groups, serial chain
- [ ] Tests for `CallGraphDAG.to_dot()` -- valid DOT syntax, edges, clusters
- [ ] Tests for `CallGraphDAG.report()` -- header, columns, totals row
- [ ] Integration tests: compile a real function with opt=1, verify depth/t_count on nodes

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/call_graph.py` -- current DAGNode/CallGraphDAG implementation (Phase 107)
- `src/quantum_language/compile.py` -- three add_node() call sites (lines 807, 842, 982) and placeholder update (line 1097)
- `src/quantum_language/_core.pxd:9` -- Standardgate_t enum: T_GATE=10, TDG_GATE=11
- `src/quantum_language/_core.pyx:787-835` -- extract_gate_range() gate dict format
- rustworkx `dag_weighted_longest_path_length` API -- verified via `help()` in Python shell

### Secondary (MEDIUM confidence)
- T-count dual formula from v3.0 (7*CCX fallback) -- referenced in CONTEXT.md decisions, matches C-level gate_counts_t structure in _core.pxd

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all libraries already in use
- Architecture: HIGH -- extending existing classes with well-understood patterns
- Pitfalls: HIGH -- identified from direct code reading of all call sites
- Depth/T-count algorithms: HIGH -- standard ASAP scheduling and known T-count formulas

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable domain, no external dependency changes expected)
