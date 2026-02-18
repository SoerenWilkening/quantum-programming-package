# Phase 56: Forward/Inverse Depth Fix - Research

**Researched:** 2026-02-05
**Domain:** Quantum circuit compilation - forward vs inverse path optimization
**Confidence:** HIGH

## Summary

This research investigates the depth discrepancy between forward compilation (`f(x)`) and inverse compilation (`f.inverse(x)`/`f.adjoint(x)`) in the quantum circuit compilation framework. The issue was identified in the v2.2 milestone planning: "Forward path should match inverse optimization."

After analyzing the codebase, the root cause is clear: **The forward capture path executes the function body directly, which means gates flow through `add_gate()` with its built-in inverse cancellation happening in real-time. The inverse path, however, uses cached gates from the forward capture -- which have already been optimized by `_optimize_gate_list()` -- and simply reverses them.**

The key insight is that both paths produce optimized gate sequences, but through different mechanisms:
- **Forward path:** Optimization via `add_gate()` (C-level, layer-based) + `_optimize_gate_list()` (Python, adjacent cancellation)
- **Inverse/adjoint path:** Reuses already-optimized cached gates, then reverses them

The discrepancy arises because the C-level `add_gate()` optimization and Python-level `_optimize_gate_list()` don't produce identical results in all cases, and the layer assignment during replay may differ from capture.

**Primary recommendation:** The fix should ensure that `f(x)` replay (cached forward path) produces the same circuit depth as `f.adjoint(x)` replay for equivalent operations. This requires investigating where layer assignment diverges between the two replay paths.

## Standard Stack

This phase uses the existing codebase infrastructure:

### Core Files
| File | Purpose | Relevance |
|------|---------|-----------|
| `src/quantum_language/compile.py` | Capture/replay/optimization logic | PRIMARY - contains `_capture`, `_replay`, `_optimize_gate_list`, `_inverse_gate_list` |
| `c_backend/src/optimizer.c` | Gate placement and inverse cancellation | Layer assignment via `add_gate()`, `minimum_layer()`, `layer_floor` |
| `c_backend/src/circuit_stats.c` | Depth calculation | `circuit_depth()` returns `used_layer` |
| `src/quantum_language/_core.pyx` | Cython bindings | `inject_remapped_gates()`, `get_current_layer()`, `_get_layer_floor()` |

### Profiling Infrastructure (Phase 55)
| Tool | Command | Purpose |
|------|---------|---------|
| cProfile | `make profile-cprofile` | Function-level timing |
| `ql.profile()` | Python context manager | Inline profiling |
| pytest-benchmark | `make benchmark` | Reproducible timing |
| Cython annotation | `make profile-cython` | Python/C boundary analysis |

**No new dependencies required.** The fix uses existing profiling infrastructure.

## Architecture Patterns

### Current Compilation Flow

```
@ql.compile decorated function
         |
         v
+--------+--------+
|                 |
v                 v
CAPTURE           REPLAY (cached)
(first call)      (subsequent calls)
|                 |
v                 v
_capture_inner()  _replay()
|                 |
v                 v
Execute func()    inject_remapped_gates()
|                 |
v                 v
add_gate() called inject_remapped_gates()
per gate (C-level calls add_gate() per gate
optimization)     (C-level optimization)
|                 |
v                 v
_optimize_gate_list() [gates already optimized]
(Python-level
optimization)
|                 |
v                 v
Cache gates       Build return qint
```

### Inverse/Adjoint Flow

```
f.adjoint(x) called
         |
         v
_InverseCompiledFunc.__call__()
         |
         v
Check cache, ensure forward captured
         |
         v
_inverse_gate_list(block.gates)
  [reverses order, negates rotation angles]
         |
         v
_original._replay(inverted_block, quantum_args)
         |
         v
inject_remapped_gates(inverted_gates, vtr)
         |
         v
Gates flow through add_gate() with C-level optimization
```

### Key Difference Location

The potential depth discrepancy occurs at **layer assignment** in `optimizer.c`:

```c
// optimizer.c:40-54
layer_t minimum_layer(circuit_t *circ, gate_t *g, layer_t compared_layer) {
    layer_t min_possible_layer = circ->layer_floor;  // <- KEY: layer_floor affects placement
    // ... finds earliest layer where gate can be placed
}
```

During capture:
- `layer_floor` starts at whatever the circuit's current state is
- Gates are placed as function executes
- Some gates may share layers (parallel execution)

During replay (forward or inverse):
- `_set_layer_floor(start_layer)` is called (compile.py:987)
- All replayed gates are forced to start at this floor
- This prevents gate reordering into earlier layers

**Hypothesis:** The layer_floor setting during replay may result in different layer packing than original capture, leading to depth differences.

### Pattern 1: Layer Floor Management (Current)

**What:** The replay path sets `layer_floor` to prevent gate reordering
**Where:** `compile.py:985-994`
**Code:**
```python
# compile.py:_replay()
saved_floor = _get_layer_floor()
start_layer = get_current_layer()
_set_layer_floor(start_layer)

inject_remapped_gates(block.gates, virtual_to_real)

end_layer = get_current_layer()
_set_layer_floor(saved_floor)
```

### Pattern 2: Gate Optimization During Capture

**What:** Python-level optimization after C-level gate placement
**Where:** `compile.py:815-818`
**Code:**
```python
# compile.py:_capture_inner()
original_count = len(virtual_gates)
if self._optimize:
    try:
        virtual_gates = _optimize_gate_list(virtual_gates)
    except Exception:
        pass  # Fall back to unoptimised on any error
```

### Anti-Patterns to Avoid

- **Optimizing twice:** Don't apply `_optimize_gate_list()` on already-optimized gates from cache
- **Breaking layer_floor semantics:** The floor prevents reordering for correctness; don't remove it
- **Changing gate ordering semantics:** The order matters for quantum correctness

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Depth calculation | Custom depth counter | `circuit.depth` property | Already implemented correctly in C |
| Gate cancellation | Python-level during replay | C-level `add_gate()` | Already optimized, handles edge cases |
| Profiling | Manual timing | `ql.profile()` context manager | Phase 55 infrastructure |
| Benchmark comparison | Print statements | pytest-benchmark | Statistical rigor |

**Key insight:** The infrastructure for measuring and comparing depths already exists. The fix is about understanding why the two paths produce different depths, not building new measurement tools.

## Common Pitfalls

### Pitfall 1: Conflating Gate Count with Depth

**What goes wrong:** Assuming same gate count means same depth
**Why it happens:** Gates can be parallelized into fewer layers
**How to avoid:** Always compare both `gate_count` AND `depth`
**Warning signs:** Tests pass on gate count but fail on depth comparison

### Pitfall 2: Layer Floor Side Effects

**What goes wrong:** Changing layer_floor affects subsequent operations outside the replay
**Why it happens:** layer_floor is global circuit state
**How to avoid:** Always save and restore layer_floor (current code does this correctly)
**Warning signs:** Operations after compiled function call start at unexpected layers

### Pitfall 3: Optimization Order Sensitivity

**What goes wrong:** `_optimize_gate_list()` results depend on gate order
**Why it happens:** Adjacent cancellation is order-dependent
**How to avoid:** Ensure capture and replay produce equivalent gate orderings before optimization
**Warning signs:** Same function, same input widths, different optimized gate counts

### Pitfall 4: Controlled Variant Divergence

**What goes wrong:** Forward controlled path differs from inverse controlled path
**Why it happens:** Controlled variants add control qubit to every gate
**How to avoid:** Test both uncontrolled and controlled variants
**Warning signs:** Tests pass for uncontrolled, fail for controlled

## Code Examples

### Measuring Depth Discrepancy

```python
# Diagnostic test pattern
import quantum_language as ql
from quantum_language._core import get_current_layer

ql.circuit()

@ql.compile
def example_op(x):
    x += 1
    return x

# Forward path
a = ql.qint(3, width=8)
start_forward = get_current_layer()
example_op(a)
end_forward = get_current_layer()
forward_depth = end_forward - start_forward

# Adjoint path (on fresh qubits)
b = ql.qint(5, width=8)
start_adjoint = get_current_layer()
example_op.adjoint(b)
end_adjoint = get_current_layer()
adjoint_depth = end_adjoint - start_adjoint

# These should be equal for equivalent operations
assert forward_depth == adjoint_depth, f"Depth mismatch: forward={forward_depth}, adjoint={adjoint_depth}"
```

### Profiling the Two Paths

```python
import quantum_language as ql

with ql.profile() as stats:
    ql.circuit()

    @ql.compile
    def add_op(x):
        x += 1
        return x

    # Profile forward path
    for _ in range(100):
        ql.circuit()
        a = ql.qint(3, width=8)
        add_op(a)

    # Profile adjoint path
    for _ in range(100):
        ql.circuit()
        b = ql.qint(3, width=8)
        add_op.adjoint(b)

print(stats.report(sort_key='cumulative', limit=30))
```

### Layer Floor Investigation

```python
# Diagnostic: capture vs replay layer usage
import quantum_language as ql
from quantum_language._core import get_current_layer, _get_layer_floor

ql.circuit()

@ql.compile
def test_fn(x):
    x += 1
    x += 1  # Two operations
    return x

a = ql.qint(0, width=4)
print(f"Before capture: layer={get_current_layer()}, floor={_get_layer_floor()}")
test_fn(a)  # Capture
print(f"After capture: layer={get_current_layer()}, floor={_get_layer_floor()}")

b = ql.qint(0, width=4)
print(f"Before replay: layer={get_current_layer()}, floor={_get_layer_floor()}")
test_fn(b)  # Replay
print(f"After replay: layer={get_current_layer()}, floor={_get_layer_floor()}")
```

## State of the Art

| Aspect | Current State | Potential Improvement |
|--------|---------------|----------------------|
| Forward capture | Executes func, then optimizes gate list | Could pre-optimize during capture |
| Replay | Injects gates with layer_floor protection | Same mechanism for forward/inverse |
| Adjoint | Reverses already-optimized gates | Same optimization level as forward |
| Depth measurement | `circuit.depth` (C-level) | Already optimal |

**The discrepancy is likely in HOW gates get assigned to layers during replay vs capture, not in the optimization passes themselves.**

## Open Questions

1. **Does layer_floor cause depth inflation during replay?**
   - What we know: layer_floor prevents gate reordering into earlier layers
   - What's unclear: Whether this consistently causes more layers in replay vs capture
   - Recommendation: Add diagnostic logging to compare layer assignments

2. **Do forward and adjoint replays differ in layer assignment?**
   - What we know: Both call `inject_remapped_gates()` with same layer_floor logic
   - What's unclear: Whether gate order in cache affects final layer assignment
   - Recommendation: Add test comparing `f(x)` replay depth to `f.adjoint(x)` replay depth

3. **Is the discrepancy width-dependent?**
   - What we know: Different widths produce different cache entries
   - What's unclear: Whether depth ratio (forward/adjoint) varies with width
   - Recommendation: Test across widths 4, 8, 16, 32

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/compile.py` - Direct code analysis
- `c_backend/src/optimizer.c` - Gate placement logic
- `c_backend/src/circuit_stats.c` - Depth calculation
- `.planning/research/FEATURES-PERFORMANCE.md` - Original issue identification

### Secondary (MEDIUM confidence)
- `tests/test_compile.py` - Existing test patterns for forward/inverse
- `.planning/phases/55-profiling-infrastructure/55-RESEARCH.md` - Profiling infrastructure

### Tertiary (LOW confidence)
- None - all findings verified against source code

## Metadata

**Confidence breakdown:**
- Architecture understanding: HIGH - direct code analysis of compile.py and optimizer.c
- Root cause hypothesis: MEDIUM - requires profiling validation
- Fix approach: MEDIUM - needs diagnostic verification before implementation

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - code-based analysis)

---

## Implementation Guidance for Planner

Based on this research, Phase 56 implementation should follow this sequence:

### Step 1: Diagnostic (FIX-01)
1. Create test that measures depth of `f(x)` capture vs `f(x)` replay vs `f.adjoint(x)` replay
2. Profile all three paths using Phase 55 infrastructure
3. Identify exact location where depths diverge

### Step 2: Root Cause Analysis
1. Add diagnostic logging to `_capture_inner()` and `_replay()` for layer tracking
2. Compare gate-by-gate layer assignment between paths
3. Document findings in test file

### Step 3: Fix Implementation (FIX-02)
Based on diagnostic results, likely fixes:
- **If layer_floor causes inflation:** Adjust layer_floor logic during replay
- **If optimization differs:** Ensure consistent optimization across all paths
- **If gate ordering matters:** Normalize gate order before caching

### Step 4: Verification
1. Add permanent depth comparison tests to `tests/test_compile.py`
2. Test across multiple widths (4, 8, 16)
3. Test both uncontrolled and controlled variants
4. Ensure no regression in existing tests

**Success criteria from ROADMAP.md:**
1. Profiling data shows where forward path diverges from inverse optimization
2. `f(x)` produces circuit depth equal to `f.inverse(x)` for same operations
