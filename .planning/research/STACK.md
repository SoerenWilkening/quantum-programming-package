# Stack Research

**Domain:** Multi-level quantum circuit compilation infrastructure (call graph DAG, sparse circuits, sequence merging)
**Researched:** 2026-03-05
**Confidence:** HIGH

## Executive Summary

The v7.0 multi-level compilation milestone requires **zero new core dependencies**. The two libraries needed for DAG operations and sparse arrays -- rustworkx and scipy -- are already installed. The only new Python dependency is `pydot` (optional, for DOT graph rendering), which is a pure-Python package with minimal footprint. All new functionality operates at the Python level on virtual gate lists within `compile.py`, with no changes to the C backend or Cython bridge.

## Recommended Stack

### Core Technologies (All Existing -- No Changes)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| rustworkx | 0.17.1 (installed) | Call graph DAG representation, topological sort, parallelism detection | Already installed. Written in Rust, 10-100x faster than NetworkX. Same library Qiskit uses for its own compiler DAG. `PyDAG` provides `topological_sort()`, `topological_generations()`, `dag_longest_path()` -- exactly the primitives needed for call graph analysis. |
| scipy.sparse | 1.17.1 (installed) | Sparse circuit arrays for large gate sequences | Already installed. `dok_array` for incremental construction during gate capture, `csr_array` for fast row-sliced replay. Mature, well-tested, zero additional deps. |
| NumPy | 2.4.2 (installed) | Qubit dependency bitmask operations for merge decisions | Already used throughout. Bitwise ops on uint64 arrays give O(1) qubit overlap detection for sequence merging, replacing O(min(A,B)) set intersection. |
| Python | >=3.11 | All new code is pure Python in compile.py | No change. |
| Cython | >=3.0.11,<4.0 | Existing `inject_remapped_gates()` handles Python-to-C boundary | No change. No new Cython needed. |
| C backend | System gcc/clang | Existing `sequence_t` with 2D jagged arrays stays dense | No change. Sparse representation is Python-level only. |

### Supporting Libraries (ONE new optional addition)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydot | >=3.0.0 (NEW, optional) | DOT format export for call graph visualization | Required by `rustworkx.visualization.graphviz_draw()`. Pure Python, only dep is pyparsing. Lazy-import so NOT a hard runtime requirement. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Graphviz (system) | Render DOT to PNG/SVG | Only needed when user calls call graph visualization. Optional system dependency: `apt install graphviz` or `brew install graphviz`. |

## Detailed Technology Analysis

### 1. Call Graph DAG: rustworkx.PyDAG

rustworkx 0.17.1 is already installed as a transitive dependency. Verified available classes and functions:

```python
import rustworkx as rx

# Available DAG primitives (verified via dir(rx)):
rx.PyDAG           # Directed acyclic graph with cycle prevention
rx.topological_sort         # Linear-time node ordering
rx.topological_generations  # Groups independent nodes into parallel layers
rx.dag_longest_path         # Critical path for depth estimation
rx.dag_longest_path_length  # Critical path length
rx.DAGHasCycle              # Exception for cycle detection
rx.DAGWouldCycle            # Exception for edge-add validation
rx.TopologicalSorter        # Iterator-based topological traversal
rx.lexicographical_topological_sort  # Deterministic ordering with key function
```

**Why rustworkx over alternatives:**

| Factor | rustworkx | NetworkX | Custom dict |
|--------|-----------|----------|-------------|
| Already installed | Yes | No | N/A |
| Performance | Rust-native, 10-100x faster | Pure Python | Depends |
| DAG enforcement | Built-in cycle prevention | Manual check | Manual |
| Topological sort | Built-in, multiple variants | Built-in | Must implement |
| Parallel layer detection | `topological_generations()` | `topological_generations()` | Must implement |
| Used by Qiskit compiler | Yes (same lib) | No | No |

**Integration with compile.py:**

Each `CompiledFunction` becomes a node in the `PyDAG`. Edges represent call dependencies (function A calls function B). Node payloads store `CompiledBlock` references. Edge payloads store qubit overlap information for merge decisions.

```python
class CallGraph:
    def __init__(self):
        self.dag = rx.PyDAG()
        self._func_to_node = {}  # CompiledFunction -> node_index

    def register_call(self, caller_func, callee_func, shared_qubits):
        caller_idx = self._ensure_node(caller_func)
        callee_idx = self._ensure_node(callee_func)
        self.dag.add_edge(caller_idx, callee_idx, shared_qubits)

    def execution_order(self):
        return rx.topological_sort(self.dag)

    def parallel_groups(self):
        return rx.topological_generations(self.dag)

    def critical_path_depth(self):
        return rx.dag_longest_path_length(self.dag, lambda n: 1)
```

### 2. Sparse Circuit Arrays: scipy.sparse

scipy 1.17.1 is already installed. Verified the modern array API is available:

- `scipy.sparse.dok_array` -- Dictionary of Keys format, O(1) random insert
- `scipy.sparse.csr_array` -- Compressed Sparse Row, O(nnz) row iteration
- `scipy.sparse.lil_array` -- List of Lists, efficient row-wise construction

**When to use sparse vs dense:**

The existing `CompiledBlock.gates` is a `list[dict]` of virtual gates. For most compiled functions (< 10K gates), this is fine. Sparse representation helps when:

- Circuit has > 50K layers but most layers are sparsely populated (< 10% qubit utilization)
- Multiple compiled blocks are merged and the combined gate list has many "holes"
- Memory pressure from storing large compiled programs with many inactive qubits per layer

**Recommended format lifecycle:**

1. **Capture phase**: Use `dok_array` -- O(1) insert as gates are captured one by one
2. **Optimization phase**: Convert to `csr_array` -- O(nnz) iteration for gate cancellation and merging
3. **Replay phase**: Use `csr_array` -- fast row (layer) iteration for `inject_remapped_gates()`
4. **Density threshold**: Auto-opt-in when `nnz / (layers * qubits) < 0.1`

**Critical constraint: sparse is Python-level only.** The C-level `sequence_t` (types.h line 77-82) stays dense. The 2D jagged array `gate_t **seq` with `gates_per_layer[i]` is already effectively sparse (variable gates per layer). The Python-level sparse representation is for the virtual gate list in `CompiledBlock`, not the physical circuit.

### 3. Sequence Merging: NumPy Bitmask Operations

Qubit dependency analysis for intelligent merging uses NumPy uint64 bitmasks:

```python
import numpy as np

def compute_qubit_mask(block: CompiledBlock) -> np.uint64:
    """Bitmask of all virtual qubits touched by a compiled block."""
    mask = np.uint64(0)
    for g in block.gates:
        mask |= np.uint64(1) << np.uint64(g["target"])
        for c in g["controls"][:g["num_controls"]]:
            mask |= np.uint64(1) << np.uint64(c)
    return mask

def can_merge(block_a, block_b) -> bool:
    """Two blocks can merge if their qubit sets overlap."""
    return bool(block_a.qubit_mask & block_b.qubit_mask)

def are_independent(block_a, block_b) -> bool:
    """Two blocks are independent (parallelizable) if no qubit overlap."""
    return not bool(block_a.qubit_mask & block_b.qubit_mask)
```

**For circuits wider than 64 virtual qubits:** Use `np.ndarray` of uint64 as a bit array. The `CompiledBlock.total_virtual_qubits` field (already exists) determines whether to use scalar uint64 or array bitmask. Most compiled functions use < 64 virtual qubits, so the fast scalar path dominates.

### 4. DOT Visualization: pydot + rustworkx.visualization

`rustworkx.visualization.graphviz_draw()` is available (verified import succeeds). It requires:

1. `pydot` Python package (not currently installed)
2. Graphviz system binary (not currently installed)

Both are only needed for rendering call graphs to images. DOT text output (the string format) can be generated without either, using manual string formatting:

```python
def call_graph_to_dot(graph: CallGraph) -> str:
    """Export call graph as DOT format string (no dependencies needed)."""
    lines = ["digraph CallGraph {"]
    for node_idx in graph.dag.node_indices():
        func = graph.dag[node_idx]
        lines.append(f'  {node_idx} [label="{func.name}"];')
    for edge in graph.dag.edge_list():
        lines.append(f"  {edge[0]} -> {edge[1]};")
    lines.append("}")
    return "\n".join(lines)
```

**Recommendation:** Implement DOT text export with zero dependencies. Add `pydot` as an optional dependency only for image rendering, lazy-imported when `graphviz_draw()` is called.

## Installation

```bash
# No required new packages. Everything core is already installed.

# Optional: for call graph image rendering
pip install pydot>=3.0.0

# Optional: system graphviz for DOT-to-image rendering
# macOS:
brew install graphviz
# Ubuntu/Debian:
apt install graphviz
```

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
visualization = ["pydot>=3.0.0"]
```

Do NOT add pydot to core `dependencies`. It is only needed for call graph image rendering, which is a developer/debug feature. DOT text export works without it.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| rustworkx PyDAG | NetworkX DiGraph | Never for this project. NetworkX is pure Python, 10-100x slower, and would add a new dependency when rustworkx is already installed. |
| rustworkx PyDAG | Custom dict-based DAG | Only if DAG operations are trivially simple (just parent lookup). But topological sort, cycle detection, and parallelism detection justify a real graph library. |
| scipy.sparse dok/csr | Custom sparse dict | Never. scipy.sparse handles format conversion efficiently and is already installed. |
| scipy.sparse | Python dict of lists | Acceptable for prototyping, but scipy gives free CSR conversion for fast layer iteration during replay. |
| pydot | pygraphviz | Never. pygraphviz requires C compiler, SWIG, and system headers at install time. pydot is pure Python. |
| pydot | graphviz (Python package) | Acceptable alternative, but rustworkx's visualization module specifically expects pydot. |
| NumPy uint64 bitmask | Python frozenset | For qubit dependency sets > 64 qubits. frozenset intersection is clean but O(n). Use frozenset only if readability trumps performance in prototype phase. |
| Manual DOT string export | Full graphviz_draw() | For v7.0 MVP -- avoids pydot/graphviz dependency entirely. Add image rendering later. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| NetworkX | Slower, not installed, redundant with rustworkx | rustworkx PyDAG (already installed) |
| pygraphviz | Requires C compiler, SWIG, system headers at install | pydot (pure Python) or manual DOT strings |
| graph-tool | GPL licensed, requires C++ compilation, massive dependency | rustworkx |
| Custom graph implementation | Reinventing topological sort, cycle detection, parallelism detection | rustworkx PyDAG |
| Dense 2D NumPy arrays for sparse circuits | Memory explosion for large circuits with low gate density | scipy.sparse dok_array -> csr_array |
| Modifying C-level sequence_t for sparse | Massive C refactor risking 600K lines of working C code | Keep C dense; sparse only at Python virtual gate level |
| New Cython bindings for DAG | No performance-critical loop in DAG traversal. Python-level is sufficient | Pure Python using rustworkx |
| pandas DataFrame for gate storage | Massive overhead for structured data that is better as dict lists or sparse arrays | list[dict] (small) or scipy.sparse (large) |

## Stack Patterns by Variant

**If circuit has < 10K gates (common case):**
- Use existing `list[dict]` for `CompiledBlock.gates`
- Use uint64 scalar bitmask for qubit overlap
- Because overhead of sparse conversion exceeds savings

**If circuit has > 50K gates with sparse qubit usage:**
- Use `dok_array` during capture, convert to `csr_array` for replay
- Use `np.ndarray` bit array for qubit overlap
- Because memory savings justify conversion overhead

**If call graph has < 20 compiled functions (common case):**
- Use rustworkx PyDAG with simple topological_sort
- Because graph is small enough that parallelism detection overhead is not justified

**If call graph has > 50 compiled functions:**
- Use `topological_generations()` for parallel layer detection
- Use `dag_longest_path()` for critical path estimation
- Because parallelism becomes significant at this scale

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| rustworkx 0.17.1 | Python 3.9+, NumPy 2.x | Already installed and working |
| scipy 1.17.1 | NumPy 2.4.2 | Already installed and working |
| pydot >=3.0.0 | Python 3.9+, pyparsing 3.x | Pure Python, minimal risk |
| Graphviz (system) | pydot 3.x | Only for rendering, not computation |

## Integration Points with Existing Codebase

| Integration Point | File | What Changes |
|-------------------|------|-------------|
| Call graph construction | `compile.py` CompiledFunction.__call__ | Record caller-callee relationships in PyDAG when nested compilation detected |
| Qubit dependency tracking | `compile.py` CompiledBlock | Add `qubit_mask: np.uint64` computed from gates list |
| Sequence merging | `compile.py` _optimize_gate_list | New merge pass using bitmask overlap to identify mergeable adjacent blocks |
| Sparse gate storage | `compile.py` CompiledBlock.gates | Optional sparse representation for blocks exceeding size threshold |
| DOT export | New function in compile.py or separate module | `call_graph_to_dot()` returning DOT string |
| opt_flag levels | `compile.py` compile() decorator | New `opt_flag` parameter: 0=call graph only, 1=selective merge, 2=full expansion |
| Cython bridge | `_core.pyx` inject_remapped_gates | No change -- receives same gate dicts regardless of how they were stored |

## Summary

| Capability | Library | Status | New Dependency? |
|------------|---------|--------|-----------------|
| Call graph DAG | rustworkx.PyDAG | Installed | No |
| Topological ordering | rustworkx.topological_sort | Installed | No |
| Parallelism detection | rustworkx.topological_generations | Installed | No |
| Cycle prevention | rustworkx.DAGWouldCycle | Installed | No |
| Critical path | rustworkx.dag_longest_path | Installed | No |
| DOT text export | Manual string formatting | No library needed | No |
| DOT image rendering | pydot + system Graphviz | NEW (optional) | Yes (optional) |
| Sparse gate arrays | scipy.sparse.dok_array/csr_array | Installed | No |
| Qubit overlap detection | NumPy bitwise uint64 ops | Installed | No |
| Sequence merging algorithm | Pure Python + NumPy | Installed | No |

**Bottom line: Zero new core dependencies. One optional dependency (pydot) for image rendering. All critical functionality maps to already-installed libraries.**

## Sources

- [rustworkx DAG tutorial](https://www.rustworkx.org/tutorial/dags.html) -- DAG API and usage patterns
- [rustworkx visualization docs](https://www.rustworkx.org/visualization.html) -- graphviz_draw requirements (pydot)
- [rustworkx benchmarks vs other libraries](https://www.rustworkx.org/benchmarks.html) -- performance comparison
- [rustworkx topological_sort API](https://www.rustworkx.org/apiref/rustworkx.topological_sort.html) -- confirmed in 0.17.1
- [rustworkx TopologicalSorter API](https://www.rustworkx.org/apiref/rustworkx.TopologicalSorter.html) -- iterator variant
- [scipy.sparse documentation](https://docs.scipy.org/doc/scipy/reference/sparse.html) -- sparse array formats and construction patterns
- [pydot GitHub](https://github.com/pydot/pydot) -- pure Python, pyparsing dependency
- Verified installed versions via `pip list`: rustworkx 0.17.1, scipy 1.17.1, numpy 2.4.2
- Verified `graphviz_draw` import succeeds, pydot not yet installed, Graphviz binary not installed
- Verified scipy.sparse modern array API available: dok_array, csr_array, lil_array
- Codebase: `types.h` (sequence_t structure), `compile.py` (CompiledBlock, CompiledFunction, gate list format)

---
*Stack research for: Quantum Assembly v7.0 -- Multi-level compilation infrastructure*
*Researched: 2026-03-05*
*Conclusion: Zero new core dependencies. rustworkx (DAG), scipy.sparse (sparse arrays), NumPy (bitmasks) are all already installed. One optional new dependency: pydot for DOT image rendering.*
