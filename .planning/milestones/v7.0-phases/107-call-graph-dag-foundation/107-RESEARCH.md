# Phase 107: Call Graph DAG Foundation - Research

**Researched:** 2026-03-05
**Domain:** Compile infrastructure / directed acyclic graph overlay
**Confidence:** HIGH

## Summary

Phase 107 adds an `opt` parameter to `@ql.compile` and constructs a call graph DAG that captures program structure (nodes = compiled function invocations, edges = qubit dependency) alongside normal circuit expansion. The existing `compile.py` (1760 lines) provides a solid `CompiledFunc` class with capture/replay mechanics, cache infrastructure, and nested compilation support (`_capture_depth` tracking). The DAG is a Python-level overlay -- no C backend or Cython changes are needed.

The core challenge is intercepting each `CompiledFunc.__call__` to record DAG nodes with qubit sets, then computing pairwise qubit overlaps to form weighted edges. rustworkx 0.17.1 is already installed and provides `PyDAG`, `weakly_connected_components`, and topological sort. NumPy bitmask intersection with a LUT popcount approach handles all-pairs overlap in under 1ms for 50 nodes, which is well within performance requirements given the project's 17-qubit simulation limit.

**Primary recommendation:** Add a thread-local DAG builder stack that `CompiledFunc.__call__` pushes/pops nodes onto. The `opt` parameter controls whether the DAG is built (opt=1, default) or skipped (opt=3, legacy behavior). The DAG object wraps a `rustworkx.PyDAG` with convenience methods for parallel group detection and qubit overlap queries.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Default `opt=1` (new default) -- DAG built on every `@ql.compile` call, gates still emitted normally
- `opt=3` gives identical behavior to current `@ql.compile()` (full expansion, no DAG) for backward compat
- DAG accessible via property on compiled function: `my_func.call_graph`
- DAG built eagerly during every `__call__`, always available after first call
- All 106+ existing compile tests must pass unchanged when `opt=3` is explicit
- One node per invocation of a `@ql.compile` function (not per unique CompiledBlock)
- If `f` calls `g` twice, that's 2 child nodes for `g` in the DAG
- Hierarchical: nested compiled function calls (f calls g) appear as parent-child edges
- Non-compiled operations (raw qint arithmetic) do NOT appear in the DAG
- Each node carries: function name, qubit set (frozenset of physical qubit indices), gate count, cache key
- Directed edges: A -> B means A was called before B and they share qubits
- Edge weight = |qubit_set_A intersection qubit_set_B| (shared qubit count, integer)
- Edges connect any two nodes with overlapping qubits, not just temporally adjacent ones
- No edge between disjoint nodes (absence of edge = independent)
- Parallel groups identified via connected components of the overlap graph (undirected projection)
- Exposed as method: `dag.parallel_groups()` returning list of node-index sets
- Groups use pure qubit disjointness (no temporal ordering constraint)
- rustworkx `weakly_connected_components()` or equivalent for component detection
- NumPy bitmask intersection (bitwise AND + popcount) as baseline for qubit overlap

### Claude's Discretion
- Internal DAG class design (CallGraphDAG vs thin wrapper around rustworkx PyDAG)
- How to intercept nested compiled calls for parent-child tracking
- Whether to store the qubit set as NumPy bitmask internally and convert to frozenset for user API
- Edge storage strategy in rustworkx (weight as int attribute vs separate data)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAPI-01 | User can set `@ql.compile(opt=1)` to generate standalone sequences with call graph DAG (default) | `compile()` decorator accepts keyword args; add `opt` parameter alongside existing `optimize`, `parametric` etc. |
| CAPI-03 | User can set `@ql.compile(opt=3)` for full circuit expansion (backward compatible) | When opt=3, skip all DAG building; existing `__call__` path unchanged |
| CAPI-04 | Existing 106+ compile tests pass unchanged when opt=3 is used | Default must be opt=1 but opt=3 must produce identical behavior to current code (no DAG overhead) |
| CGRAPH-01 | Call graph DAG built from sequence calls with qubit sets per node | DAG builder intercepts `__call__`, records node with qubit set from virtual-to-real mapping |
| CGRAPH-02 | Parallel sequences (disjoint qubit sets) identified as concurrent groups | `rx.connected_components()` on undirected overlap graph |
| CGRAPH-03 | Weighted qubit overlap edges between dependent sequences | NumPy bitmask AND + LUT popcount, store weight as edge data in rustworkx |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rustworkx | 0.17.1 | DAG data structure + graph algorithms | Already installed; Qiskit ecosystem standard for DAGs; fast C++ backend |
| numpy | (installed) | Bitmask qubit overlap computation | Already a project dependency; vectorized bitwise ops |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| threading (stdlib) | -- | Thread-local DAG builder context | Only if thread safety needed; otherwise module-level stack |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rustworkx PyDAG | networkx DiGraph | networkx is slower, not already installed, no C++ backend |
| NumPy bitmask popcount | Python frozenset intersection | frozenset is simpler but 10-50x slower for bulk pairwise operations |
| Module-level builder stack | Context variable (contextvars) | contextvars is cleaner for async but overkill here; module-level matches existing `_capture_depth` pattern |

**Installation:**
```bash
# No new installations needed -- rustworkx and numpy already available
pip show rustworkx numpy
```

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
├── compile.py           # Modified: add opt parameter, DAG node recording
├── call_graph.py        # NEW: CallGraphDAG class, DAGNode dataclass, builder stack
└── __init__.py          # Modified: export CallGraphDAG if desired
```

### Pattern 1: Thread-Local DAG Builder Stack
**What:** A module-level stack (`_dag_builder_stack`) that tracks the active DAG and parent node during nested `CompiledFunc.__call__` execution. Mirrors the existing `_capture_depth` pattern.
**When to use:** Every `CompiledFunc.__call__` when opt != 3.
**Example:**
```python
# call_graph.py
import numpy as np
import rustworkx as rx

# Module-level builder state (mirrors _capture_depth pattern in compile.py)
_dag_builder_stack = []  # Stack of (CallGraphDAG, parent_node_index)

class DAGNode:
    """Data stored at each node in the call graph DAG."""
    __slots__ = ('func_name', 'qubit_set', 'gate_count', 'cache_key', 'bitmask')

    def __init__(self, func_name, qubit_set, gate_count, cache_key):
        self.func_name = func_name
        self.qubit_set = frozenset(qubit_set)
        self.gate_count = gate_count
        self.cache_key = cache_key
        # Pre-compute bitmask for fast overlap
        self.bitmask = np.uint64(0)
        for q in qubit_set:
            self.bitmask |= np.uint64(1 << q)


class CallGraphDAG:
    """Call graph DAG capturing program structure from @ql.compile calls."""

    def __init__(self):
        self._dag = rx.PyDAG()
        self._nodes = []  # node_index -> DAGNode

    def add_node(self, func_name, qubit_set, gate_count, cache_key, parent_index=None):
        """Add a node to the DAG. If parent_index given, add parent->child edge."""
        node = DAGNode(func_name, qubit_set, gate_count, cache_key)
        idx = self._dag.add_node(node)
        self._nodes.append(node)
        if parent_index is not None:
            # Hierarchical edge (parent called child)
            self._dag.add_edge(parent_index, idx, None)
        return idx

    def build_overlap_edges(self):
        """Compute qubit overlap edges between all node pairs."""
        n = len(self._nodes)
        if n < 2:
            return
        bitmasks = np.array([nd.bitmask for nd in self._nodes], dtype=np.uint64)
        # LUT for popcount
        lut = np.array([bin(i).count('1') for i in range(256)], dtype=np.uint8)
        for i in range(n):
            overlaps = np.bitwise_and(bitmasks[i], bitmasks[i+1:])
            weights = _popcount_array(overlaps, lut)
            for j_off, w in enumerate(weights):
                if w > 0:
                    j = i + 1 + j_off
                    self._dag.add_edge(i, j, int(w))

    def parallel_groups(self):
        """Return list of sets of node indices that are mutually qubit-disjoint."""
        # Build undirected overlap graph
        n = len(self._nodes)
        g = rx.PyGraph()
        for _ in range(n):
            g.add_node(None)
        bitmasks = np.array([nd.bitmask for nd in self._nodes], dtype=np.uint64)
        lut = np.array([bin(i).count('1') for i in range(256)], dtype=np.uint8)
        for i in range(n):
            overlaps = np.bitwise_and(bitmasks[i], bitmasks[i+1:])
            weights = _popcount_array(overlaps, lut)
            for j_off, w in enumerate(weights):
                if w > 0:
                    g.add_edge(i, i + 1 + j_off, int(w))
        return rx.connected_components(g)


def _popcount_array(arr, lut):
    """Vectorized popcount using byte LUT."""
    result = np.zeros(len(arr), dtype=np.int32)
    for shift in range(0, 64, 8):
        byte_vals = ((arr >> shift) & np.uint64(0xFF)).astype(np.uint8)
        result += lut[byte_vals]
    return result
```

### Pattern 2: Intercepting __call__ for Node Recording
**What:** Modify `CompiledFunc.__call__` to push/pop DAG builder context around the function execution.
**When to use:** When opt=1 (default). The key insight is that qubit sets are available AFTER capture or replay completes.
**Example:**
```python
# In CompiledFunc.__call__, after result is computed:
if self._opt_level != 3 and _dag_builder_stack:
    dag, parent_idx = _dag_builder_stack[-1]
    # Collect physical qubit indices from quantum_args
    qubit_set = set()
    for qa in quantum_args:
        qubit_set.update(_get_quantum_arg_qubit_indices(qa))
    # Include ancilla qubits from block
    block = self._cache.get(cache_key)
    if block and block._capture_virtual_to_real:
        qubit_set.update(block._capture_virtual_to_real.values())
    node_idx = dag.add_node(
        self._func.__name__, qubit_set, len(block.gates) if block else 0,
        cache_key, parent_index=parent_idx
    )
```

### Pattern 3: opt Parameter Integration
**What:** Add `opt` keyword to `compile()` decorator, thread it through `CompiledFunc.__init__`.
**When to use:** Always. The opt parameter is the public API surface.
**Example:**
```python
def compile(func=None, *, opt=1, max_cache=128, key=None, verify=False,
            optimize=True, inverse=False, debug=False, parametric=False):
    # opt=1: build DAG alongside normal expansion (new default)
    # opt=3: full expansion only, no DAG (backward compat)
    ...
```

### Anti-Patterns to Avoid
- **Modifying the C backend or Cython layer:** The DAG is purely Python-level. Do not touch `_core.pyx`, `inject_remapped_gates`, or `extract_gate_range`.
- **Storing DAG in global singleton:** Each top-level compiled function call should own its DAG. Use `call_graph` property on the `CompiledFunc` instance.
- **Lazy DAG edge computation:** Build overlap edges eagerly after each `__call__` completes so `call_graph` is always consistent.
- **Breaking the cache key:** Do NOT include `opt` in the cache key. The opt level controls DAG building, not gate content. A function compiled with opt=1 and opt=3 should share the same cache entries.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DAG data structure | Custom adjacency list | `rustworkx.PyDAG` | Handles node/edge data, topological sort, component detection; C++ backend |
| Connected components | BFS/DFS manual traversal | `rx.connected_components()` / `rx.weakly_connected_components()` | Tested, optimized, handles edge cases |
| Popcount | Python `bin(x).count('1')` in a loop | NumPy byte LUT vectorized | 5-10x faster for bulk operations |
| Qubit set representation | Python set operations for overlap | NumPy uint64 bitmask + bitwise AND | Vectorizable, cache-friendly, handles up to 64 qubits (project max is 17) |

**Key insight:** rustworkx is already the Qiskit ecosystem standard for DAG operations (Qiskit's own transpiler pass manager uses it). Its C++ backend makes graph operations fast enough that the DAG overlay adds negligible overhead to compilation.

## Common Pitfalls

### Pitfall 1: Breaking Existing Tests with Default opt=1
**What goes wrong:** If opt=1 changes any observable behavior (gate sequences, return values, circuit depth), existing tests fail.
**Why it happens:** The DAG builder might interfere with capture/replay timing or qubit allocation.
**How to avoid:** DAG building must be purely observational -- append-only node recording after each `__call__` completes. Never modify gate sequences, cache behavior, or qubit allocation based on opt level.
**Warning signs:** Any existing test fails when opt=1 is default; any difference in gate counts between opt=1 and opt=3.

### Pitfall 2: Qubit Set Collection During Capture vs Replay
**What goes wrong:** During first capture, qubit sets come from the actual execution. During replay, they come from the virtual-to-real mapping. If these differ, DAG edges are wrong.
**Why it happens:** Capture allocates qubits linearly; replay may remap to different physical qubits.
**How to avoid:** Always collect physical qubit indices AFTER the call completes, from the virtual-to-real mapping used for that specific call (both capture and replay paths).
**Warning signs:** DAG shows different qubit sets for same function called on same qint.

### Pitfall 3: Nested Call Parent Tracking
**What goes wrong:** When `f` calls `g` which calls `h`, the parent-child edges get confused if the stack isn't managed correctly.
**Why it happens:** `_capture_depth` already exists but doesn't track parent identity. The DAG builder stack must be pushed/popped in sync with the actual call nesting.
**How to avoid:** Push before calling `_func(*args, **kwargs)` (in capture) or before `inject_remapped_gates` (in replay), pop after. Use try/finally for exception safety.
**Warning signs:** DAG shows flat structure when nested calls exist; wrong parent for deeply nested calls.

### Pitfall 4: DAG Ownership and Lifecycle
**What goes wrong:** Multiple top-level calls to the same compiled function overwrite the previous DAG, or DAGs leak between circuit resets.
**Why it happens:** Unclear ownership semantics.
**How to avoid:** Each `__call__` at the top level (not nested) creates a fresh `CallGraphDAG` stored on the `CompiledFunc` instance. `_reset_for_circuit()` clears it. Nested calls add nodes to the parent's DAG, not their own.
**Warning signs:** `f.call_graph` shows nodes from a previous call; DAG persists after `ql.circuit()`.

### Pitfall 5: opt Parameter vs optimize Parameter Confusion
**What goes wrong:** `opt` (optimization level 1/3) vs `optimize` (bool, gate optimization) could be confused.
**Why it happens:** Similar names, both affect compilation behavior.
**How to avoid:** Clear docstrings. `opt` controls the compilation level (what gets built: DAG + gates vs gates only). `optimize` controls gate-level optimization (cancel inverses, merge rotations). They are orthogonal.
**Warning signs:** Users or code confusing the two; opt=3 incorrectly disabling gate optimization.

## Code Examples

### Existing Entry Point (compile.py line 695)
```python
# Source: src/quantum_language/compile.py:695
def __call__(self, *args, **kwargs):
    """Call the compiled function (capture or replay)."""
    quantum_args, classical_args, widths = self._classify_args(args, kwargs)
    is_controlled = _get_controlled()
    # ... cache key construction ...
    if is_hit:
        result = self._replay(self._cache[cache_key], quantum_args)
    else:
        result = self._capture_and_cache_both(args, kwargs, ...)
    return result
```

### Qubit Index Collection (compile.py)
```python
# Source: src/quantum_language/compile.py (capture path, line 872-874)
param_qubit_indices = []
for qa in quantum_args:
    param_qubit_indices.append(_get_quantum_arg_qubit_indices(qa))

# Source: src/quantum_language/compile.py (replay path, line 1241-1247)
virtual_to_real = {}
vidx = 0
for qa in quantum_args:
    indices = _get_quantum_arg_qubit_indices(qa)
    for real_q in indices:
        virtual_to_real[vidx] = real_q
        vidx += 1
```

### rustworkx PyDAG API (verified locally, v0.17.1)
```python
import rustworkx as rx

dag = rx.PyDAG()
n0 = dag.add_node({'name': 'f', 'qubits': frozenset({0, 1})})
n1 = dag.add_node({'name': 'g', 'qubits': frozenset({1, 2})})
dag.add_edge(n0, n1, {'weight': 1})

# Component detection on undirected graph
g = rx.PyGraph()
g.add_nodes_from(range(3))
g.add_edge(0, 1, 1)
comps = rx.connected_components(g)  # [{0, 1}, {2}]

# Topological sort
rx.topological_sort(dag)  # NodeIndices[0, 1]
```

### NumPy Bitmask Overlap (benchmarked locally)
```python
import numpy as np

def popcount_array(arr, lut):
    """Vectorized popcount via byte lookup table."""
    result = np.zeros(len(arr), dtype=np.int32)
    for shift in range(0, 64, 8):
        byte_vals = ((arr >> shift) & np.uint64(0xFF)).astype(np.uint8)
        result += lut[byte_vals]
    return result

# Build LUT once
LUT = np.array([bin(i).count('1') for i in range(256)], dtype=np.uint8)

# 50 nodes, all-pairs overlap: <1ms per iteration
bitmasks = np.array([...], dtype=np.uint64)
for i in range(n):
    overlaps = np.bitwise_and(bitmasks[i], bitmasks[i+1:])
    weights = popcount_array(overlaps, LUT)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@ql.compile` with no opt param | `@ql.compile(opt=1)` with DAG | This phase | New default; opt=3 preserves old behavior |
| No call graph visibility | `func.call_graph` property | This phase | Users can inspect program structure |
| No parallel sequence detection | `dag.parallel_groups()` | This phase | Foundation for future merge optimization (Phase 109) |

**Deprecated/outdated:**
- Nothing deprecated -- this phase adds new capability without removing anything

## Open Questions

1. **Should the DAG distinguish hierarchical (parent-child) edges from overlap edges?**
   - What we know: CONTEXT.md specifies "Hierarchical: nested compiled function calls (f calls g) appear as parent-child edges" AND "Directed edges: A -> B means A was called before B and they share qubits"
   - What's unclear: Are these the same edge set or separate? A parent calling a child always shares qubits (parent's qubit set includes child's).
   - Recommendation: Use two edge types in rustworkx edge data: `{'type': 'call', 'weight': None}` for hierarchical edges and `{'type': 'overlap', 'weight': N}` for qubit overlap edges. The overlap edge builder ignores parent-child pairs to avoid double-counting.

2. **How should `call_graph` behave when a compiled function is called multiple times?**
   - What we know: "DAG built eagerly during every `__call__`" -- CONTEXT.md says built on every call
   - What's unclear: Does each call replace the previous DAG, or accumulate?
   - Recommendation: Each top-level call replaces the previous DAG. The most recent call's structure is what matters. Store as `self._call_graph` on the `CompiledFunc` instance.

3. **Qubit set for the parent node in nested calls**
   - What we know: Each node carries its qubit set. A parent function that calls children may touch qubits both directly (raw operations) and indirectly (via compiled children).
   - What's unclear: Should parent's qubit set include children's qubits?
   - Recommendation: Parent's qubit set = union of all physical qubits touched during its entire execution (param qubits + ancilla qubits), which naturally includes children's qubits since they operate on the same circuit.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (configured in pytest.ini) |
| Config file | pytest.ini |
| Quick run command | `pytest tests/python/ -x -q` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAPI-01 | `@ql.compile(opt=1)` produces DAG + normal gates | unit | `pytest tests/python/test_call_graph.py::test_opt1_produces_dag -x` | Wave 0 |
| CAPI-03 | `@ql.compile(opt=3)` matches current behavior exactly | unit | `pytest tests/python/test_call_graph.py::test_opt3_backward_compat -x` | Wave 0 |
| CAPI-04 | 106+ existing tests pass with opt=3 | regression | `pytest tests/python/ -v --ignore=tests/python/test_call_graph.py` | Existing |
| CGRAPH-01 | DAG nodes contain function name, qubit set, gate count, cache key | unit | `pytest tests/python/test_call_graph.py::test_dag_node_metadata -x` | Wave 0 |
| CGRAPH-02 | Disjoint qubit sets form separate parallel groups | unit | `pytest tests/python/test_call_graph.py::test_parallel_groups -x` | Wave 0 |
| CGRAPH-03 | Overlapping qubit sets produce weighted edges | unit | `pytest tests/python/test_call_graph.py::test_overlap_edges -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_call_graph.py -x -q`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/python/test_call_graph.py` -- covers CAPI-01, CAPI-03, CGRAPH-01, CGRAPH-02, CGRAPH-03
- [ ] No framework install needed (pytest already configured)
- [ ] No conftest changes needed (existing conftest.py sufficient)

## Sources

### Primary (HIGH confidence)
- **compile.py** (1760 lines) -- read in full; `CompiledFunc.__call__`, `_capture`, `_replay`, `compile()` decorator API
- **rustworkx 0.17.1** -- verified locally: `PyDAG.add_node/add_edge`, `connected_components`, `weakly_connected_components`, `topological_sort` all work as expected
- **NumPy bitmask benchmark** -- verified locally: matrix all-pairs overlap for 50 nodes completes in <1ms

### Secondary (MEDIUM confidence)
- **CONTEXT.md** -- user decisions on DAG semantics, node granularity, edge semantics
- **REQUIREMENTS.md** -- requirement definitions and phase mapping

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - rustworkx and numpy already installed and verified
- Architecture: HIGH - patterns derived from reading existing compile.py source; builder stack mirrors established `_capture_depth` pattern
- Pitfalls: HIGH - identified from code reading (capture vs replay qubit paths, nested call tracking, lifecycle management)

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain; no external dependencies changing)
