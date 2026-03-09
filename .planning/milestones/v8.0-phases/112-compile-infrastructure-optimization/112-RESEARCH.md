# Phase 112: Compile Infrastructure Optimization - Research

**Researched:** 2026-03-08
**Domain:** numpy array operations for qubit set management in compile infrastructure
**Confidence:** HIGH

## Summary

Phase 112 replaces Python set-based qubit set construction and overlap detection in `compile.py` and `call_graph.py` with numpy array operations (`np.unique`, `np.concatenate`, `np.intersect1d`). The scope is well-bounded: three qubit_set construction sites in `compile.py` (parametric replay path ~line 843, cache hit replay path ~line 885, capture finalization ~line 1154) and three overlap computation sites in `call_graph.py` (`build_overlap_edges`, `parallel_groups`, `merge_groups`).

The existing codebase already imports numpy in `compile.py` and the test files use numpy for bitmask assertions. The DAGNode stores `qubit_set` as `frozenset[int]` which is consumed by overlap methods and external code (report, DOT export, aggregate). The migration must maintain `frozenset` compatibility for backward compatibility while using numpy internally for construction and intersection operations.

Profiling infrastructure already exists in `test_compile_performance.py` with timing harness for replay benchmarks. COMP-03 requires establishing a baseline before the migration and measuring after.

**Primary recommendation:** Use numpy arrays as intermediate representation during qubit_set construction (concatenate + unique), convert to frozenset at storage boundary. For overlap detection, add numpy array storage alongside frozenset and use `np.intersect1d` for pairwise comparison.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 | compile.py qubit_set construction uses numpy operations (np.unique/np.concatenate) replacing Python set.update() loops | Three construction sites identified in compile.py; numpy already imported; pattern: concatenate lists -> np.unique -> frozenset at boundary |
| COMP-02 | call_graph.py DAGNode overlap computation uses numpy arrays (np.intersect1d) alongside frozenset for backward compatibility | Three overlap sites identified (build_overlap_edges, parallel_groups, merge_groups); DAGNode needs _qubit_array attribute alongside qubit_set |
| COMP-03 | Profiling baseline established measuring compile performance before/after numpy migration on real workloads | test_compile_performance.py already has timing harness; extend with qubit_set construction and overlap detection benchmarks |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | 2.4.2 | Array operations for qubit index manipulation | Already installed and imported in compile.py; standard for vectorized set operations |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rustworkx | (installed) | DAG graph structure | Already used in call_graph.py; no changes needed |
| pytest | (installed) | Test framework | Existing test infrastructure |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| np.intersect1d | frozenset intersection | frozenset is current approach; numpy wins for larger qubit sets but has overhead for small sets |
| np.unique(np.concatenate(...)) | set.update() loops | numpy is faster for many lists but has fixed overhead; crossover around 50-100 elements |

## Architecture Patterns

### Pattern 1: Numpy Construction with Frozenset Storage Boundary

**What:** Build qubit sets using numpy internally, convert to frozenset at the DAGNode storage point.
**When to use:** Every qubit_set construction site in compile.py.
**Example:**
```python
# BEFORE (current code):
qubit_set = set()
for qa in quantum_args:
    qubit_set.update(_get_quantum_arg_qubit_indices(qa))
if capture_vtr:
    qubit_set.update(capture_vtr.values())

# AFTER (numpy migration):
arrays = [np.array(_get_quantum_arg_qubit_indices(qa), dtype=np.intp)
          for qa in quantum_args]
if capture_vtr:
    arrays.append(np.fromiter(capture_vtr.values(), dtype=np.intp))
qubit_arr = np.unique(np.concatenate(arrays)) if arrays else np.empty(0, dtype=np.intp)
qubit_set = frozenset(qubit_arr.tolist())
```

### Pattern 2: Dual Storage in DAGNode

**What:** Store both `qubit_set` (frozenset, backward compat) and `_qubit_array` (numpy, for fast intersection) in DAGNode.
**When to use:** DAGNode.__init__ and the capture finalization path.
**Example:**
```python
class DAGNode:
    __slots__ = (
        "func_name", "qubit_set", "gate_count", "cache_key",
        "bitmask", "depth", "t_count", "_block_ref", "_v2r_ref",
        "_qubit_array",  # NEW: numpy array for fast overlap
    )

    def __init__(self, func_name, qubit_set, gate_count, cache_key, ...):
        self.qubit_set = frozenset(qubit_set)
        self._qubit_array = np.array(sorted(self.qubit_set), dtype=np.intp)
        # ... rest unchanged
```

### Pattern 3: Numpy Overlap Detection

**What:** Replace `len(qs_i & qs_j)` with `np.intersect1d` on sorted arrays.
**When to use:** `build_overlap_edges`, `parallel_groups`, `merge_groups`.
**Example:**
```python
# BEFORE:
w = len(qs_i & self._nodes[j].qubit_set)

# AFTER:
w = len(np.intersect1d(self._nodes[i]._qubit_array,
                        self._nodes[j]._qubit_array))
```

### Anti-Patterns to Avoid
- **Converting to numpy per-comparison:** Creating numpy arrays inside the O(n^2) loop defeats the purpose. Arrays must be pre-computed and stored on DAGNode.
- **Removing frozenset entirely:** External code (tests, report, DOT export) uses `node.qubit_set` as frozenset. Breaking this interface causes regressions.
- **Using np.intersect1d for tiny sets (<10 elements):** The overhead of numpy function dispatch exceeds frozenset intersection for very small sets. However, for consistency and future-proofing (chess circuits will have larger qubit sets), use numpy uniformly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Array deduplication | Manual loop dedup | `np.unique()` | Handles sorting + dedup in C |
| Array concatenation | Python list extend chains | `np.concatenate()` | Single allocation vs repeated resizing |
| Set intersection | Manual membership loops | `np.intersect1d()` | Vectorized comparison in C |
| Bitmask from array | Python loop with `\|=` | Keep current Python loop OR `np.bitwise_or.reduce(1 << arr)` | Current bitmask approach uses Python int for >64 qubit support; numpy uint64 would overflow. Keep Python int bitmask loop. |

**Key insight:** The bitmask computation must stay as Python int (not numpy) because the project explicitly supports >64 qubits. numpy uint64 would silently overflow.

## Common Pitfalls

### Pitfall 1: dtype Mismatch
**What goes wrong:** Qubit indices from `_get_qint_qubit_indices` are Python ints. Mixing with numpy operations can cause silent type promotion.
**Why it happens:** `_get_qint_qubit_indices` returns a Python list of ints; `capture_vtr.values()` returns dict_values of ints.
**How to avoid:** Always specify `dtype=np.intp` when creating arrays from qubit indices. Use `np.intp` (platform-native int) not `np.int64` for portability.
**Warning signs:** Test failures on 32-bit platforms (unlikely but defensive).

### Pitfall 2: Empty Array Handling
**What goes wrong:** `np.concatenate([])` raises ValueError on empty sequence.
**Why it happens:** Functions with zero quantum args, or capture_vtr being None/empty.
**How to avoid:** Guard with `if arrays:` before concatenate, else use `np.empty(0, dtype=np.intp)`.
**Warning signs:** Crashes on `@ql.compile` functions with no quantum arguments.

### Pitfall 3: Frozenset Backward Compatibility
**What goes wrong:** Tests assert `isinstance(node.qubit_set, frozenset)` and use frozenset operations.
**Why it happens:** 76 existing tests in test_call_graph.py depend on frozenset interface.
**How to avoid:** Keep `qubit_set` as frozenset. Add `_qubit_array` as supplementary attribute.
**Warning signs:** Test failures asserting `frozenset` type or using `&` operator on qubit_set.

### Pitfall 4: Bitmask Overflow with numpy
**What goes wrong:** `1 << q` for q >= 64 overflows numpy uint64.
**Why it happens:** numpy integers have fixed width; Python ints are arbitrary precision.
**How to avoid:** Keep bitmask computation using Python int loop, not numpy. The existing code deliberately uses Python int for >64 qubit support.
**Warning signs:** Incorrect bitmask values for circuits with 64+ qubits.

### Pitfall 5: Performance Regression for Small Sets
**What goes wrong:** numpy function call overhead (~1-5 microseconds per call) can be slower than Python set operations for sets with <10 elements.
**Why it happens:** numpy operations have fixed dispatch overhead that dominates for tiny arrays.
**How to avoid:** Accept this tradeoff -- the goal is to optimize for larger chess circuits. Document if profiling shows regression for small workloads.
**Warning signs:** COMP-03 profiling shows slowdown on existing small test cases.

## Code Examples

### Qubit Set Construction (compile.py)

```python
# Helper function to add at module level in compile.py
def _build_qubit_set_numpy(quantum_args, extra_values=None):
    """Build qubit set using numpy operations.

    Returns (frozenset, np.ndarray) tuple for dual storage.
    """
    arrays = []
    for qa in quantum_args:
        indices = _get_quantum_arg_qubit_indices(qa)
        if indices:
            arrays.append(np.array(indices, dtype=np.intp))
    if extra_values is not None:
        vals = list(extra_values)
        if vals:
            arrays.append(np.array(vals, dtype=np.intp))
    if not arrays:
        arr = np.empty(0, dtype=np.intp)
    else:
        arr = np.unique(np.concatenate(arrays))
    return frozenset(arr.tolist()), arr
```

### DAGNode with Dual Storage (call_graph.py)

```python
import numpy as np

class DAGNode:
    __slots__ = (
        "func_name", "qubit_set", "gate_count", "cache_key",
        "bitmask", "depth", "t_count", "_block_ref", "_v2r_ref",
        "_qubit_array",
    )

    def __init__(self, func_name, qubit_set, gate_count, cache_key, *,
                 depth=0, t_count=0):
        self.func_name = func_name
        self.qubit_set = frozenset(qubit_set)
        self._qubit_array = np.array(sorted(self.qubit_set), dtype=np.intp)
        self.gate_count = gate_count
        self.cache_key = cache_key
        self.depth = depth
        self.t_count = t_count
        self._block_ref = None
        self._v2r_ref = None
        # Bitmask: keep Python int for >64 qubit support
        bitmask = 0
        for q in qubit_set:
            bitmask |= 1 << q
        self.bitmask = bitmask
```

### Overlap with numpy (call_graph.py)

```python
def build_overlap_edges(self):
    n = len(self._nodes)
    if n < 2:
        return
    call_pairs = set()
    for src, tgt in self._dag.edge_list():
        edge_data = self._dag.get_edge_data(src, tgt)
        if isinstance(edge_data, dict) and edge_data.get("type") == "call":
            call_pairs.add((min(src, tgt), max(src, tgt)))
    for i in range(n):
        arr_i = self._nodes[i]._qubit_array
        for j in range(i + 1, n):
            w = len(np.intersect1d(arr_i, self._nodes[j]._qubit_array))
            if w > 0:
                pair = (i, j)
                if pair not in call_pairs:
                    self._dag.add_edge(i, j, {"type": "overlap", "weight": w})
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python set.update() loops | To be replaced with np.unique(np.concatenate()) | Phase 112 | Reduces Python loop overhead for large qubit sets |
| frozenset intersection | To be supplemented with np.intersect1d | Phase 112 | Faster pairwise overlap for many-node DAGs |

## Existing Test Coverage

The following test files exercise the code being modified:

| Test File | Test Count | What It Tests |
|-----------|-----------|---------------|
| test_call_graph.py | 76 | DAGNode, overlap edges, parallel groups, builder stack, integration with compile |
| test_merge.py | 29 | Merge groups, compiled block merging |
| test_compile_performance.py | 2 | Replay timing benchmarks (marked @benchmark) |

**Critical:** The tests in `test_call_graph.py` assert specific behaviors:
- `isinstance(node.qubit_set, frozenset)` (line 39)
- `node.bitmask == np.uint64(...)` (lines 44, 48, 52, 57) -- note tests already use numpy for bitmask assertions
- Frozenset set operations (`&`) used implicitly through DAG overlap methods

The "186+ invocations" mentioned in success criteria likely refers to the total test invocations across all compile-related test files (test_call_graph + test_merge + others that use @ql.compile).

## Profiling Strategy for COMP-03

### Baseline (before migration)
1. Run `test_compile_performance.py` benchmarks to capture replay timing
2. Add micro-benchmarks for:
   - qubit_set construction from quantum_args (time the set.update loop)
   - DAGNode overlap computation (time build_overlap_edges for N-node DAGs)

### After Migration
1. Re-run same benchmarks
2. Compare median times
3. For small circuits (4-bit qint): expect ~neutral or slight regression (numpy overhead)
4. For larger circuits (chess walk with 20+ qubits, many nodes): expect improvement

### Profiling Test Template
```python
import time
import numpy as np
from quantum_language.call_graph import CallGraphDAG

def bench_overlap(n_nodes, qubit_range):
    """Benchmark overlap computation for n_nodes with random qubit sets."""
    dag = CallGraphDAG()
    rng = np.random.default_rng(42)
    for i in range(n_nodes):
        qubits = set(rng.choice(qubit_range, size=min(10, qubit_range), replace=False))
        dag.add_node(f"f{i}", qubits, 100, (i,), depth=5, t_count=3)

    start = time.perf_counter_ns()
    dag.build_overlap_edges()
    elapsed_us = (time.perf_counter_ns() - start) / 1000
    return elapsed_us
```

## Open Questions

1. **Bitmask test assertions use np.uint64**
   - What we know: Tests compare `node.bitmask == np.uint64(0b101)`. Current code computes bitmask as Python int.
   - What's unclear: Whether existing tests pass with Python int bitmask (they likely do due to Python's `==` coercion)
   - Recommendation: Verify tests pass as-is; do not change bitmask to numpy type (>64 qubit support requires Python int)

2. **Pre-existing test failures**
   - What we know: STATE.md notes "14-15 pre-existing test failures in test_compile.py"
   - What's unclear: Which tests fail and whether they intersect with this phase
   - Recommendation: Run full test suite before migration to establish failure baseline; only count new failures as regressions

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pytest configuration in project root |
| Quick run command | `pytest tests/python/test_call_graph.py tests/python/test_merge.py -x -q` |
| Full suite command | `pytest tests/python/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-01 | qubit_set construction uses numpy ops | unit | `pytest tests/python/test_call_graph.py -x -q` | Yes (existing tests cover DAGNode qubit_set) |
| COMP-02 | overlap computation uses numpy arrays | unit | `pytest tests/python/test_call_graph.py::TestBuildOverlapEdges -x -q` | Yes (existing tests cover overlap) |
| COMP-03 | profiling baseline before/after | benchmark | `pytest tests/python/test_compile_performance.py -v -m benchmark -s` | Yes (needs extension) |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_call_graph.py tests/python/test_merge.py -x -q`
- **Per wave merge:** `pytest tests/python/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/python/test_compile_performance.py` -- needs qubit_set construction and overlap micro-benchmarks for COMP-03
- None other -- existing test infrastructure covers COMP-01 and COMP-02 behavioral requirements

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `src/quantum_language/compile.py` (qubit_set construction at lines 843, 885, 1154)
- Direct code inspection of `src/quantum_language/call_graph.py` (overlap at lines 208-215, 237-242, 272-276)
- Direct code inspection of `tests/python/test_call_graph.py` (76 tests)
- numpy 2.4.2 installed and verified

### Secondary (MEDIUM confidence)
- numpy documentation for `np.unique`, `np.concatenate`, `np.intersect1d` -- well-established stable APIs since numpy 1.x

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - numpy already installed and imported; no new dependencies
- Architecture: HIGH - code paths fully inspected; dual-storage pattern is straightforward
- Pitfalls: HIGH - edge cases (empty arrays, >64 qubit bitmask, backward compat) identified from code
- Profiling: MEDIUM - unclear how much speedup numpy provides for current workload sizes; may be negligible

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable domain, numpy API is mature)
