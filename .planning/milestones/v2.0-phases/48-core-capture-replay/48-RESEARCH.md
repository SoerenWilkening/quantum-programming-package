# Phase 48: Core Capture-Replay - Research

**Researched:** 2026-02-04
**Domain:** Quantum circuit gate capture, caching, and replay with qubit remapping
**Confidence:** HIGH

## Summary

Phase 48 implements the `@ql.compile` decorator that captures gate sequences during a function's first call, stores them with virtual qubit references, and replays them with qubit remapping on subsequent calls. The existing codebase already contains all necessary C-level primitives: `add_gate()` for gate injection, `used_layer` for layer tracking, `run_instruction()` for qubit remapping, and `draw_data()` for gate extraction. No new C code is required. Implementation happens at the Python/Cython boundary: two new Cython functions (`extract_gate_range` and `inject_remapped_gates`), one new Python module (`compile.py`), and minor modifications to `_core.pyx` and `__init__.py`.

The core pattern is "capture-and-replay at the circuit level": execute the function normally on first call (all gates flow through `add_gate()` as usual), record the layer range, extract the gate data, build a virtual qubit mapping, cache it, and on subsequent calls inject the cached gates with remapped qubit indices. This avoids any changes to the C backend or the existing qint operator methods.

The critical challenges are: (1) building correct virtual-to-real qubit mappings that handle both parameter qubits and internally-allocated ancillas, (2) snapshot/restore of 8+ global state variables during tracing to prevent pollution, (3) constructing usable return qint/qbool objects on replay with correct ownership metadata for the uncomputation system.

**Primary recommendation:** Implement gate-level capture via layer-range extraction (pattern from `draw_data()`), replay via gate-by-gate `add_gate()` injection (pattern from `run_instruction()`), with Python-level caching and a global state snapshot/restore wrapper around tracing.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `functools.wraps` | stdlib 3.11+ | Preserve function metadata on decorator wrapper | Standard Python decorator pattern |
| Python `inspect.signature` | stdlib 3.11+ | Classify quantum vs classical args at call time | Type inspection for cache key generation |
| Python `collections.OrderedDict` | stdlib 3.11+ | LRU-style cache eviction (ordered insertion) | Lightweight cache with max_cache limit |
| Cython `_core.pyx` | existing | Host `extract_gate_range()` and `inject_remapped_gates()` | Python-C bridge, same module as existing circuit code |
| C `circuit_t.used_layer` | existing | Snapshot layer depth before/after function call | Already exposed via `get_current_layer()` |
| C `circuit_t.layer_floor` | existing | Prevent optimizer from placing replay gates before start point | Already used by `__add__`, `__mul__` etc. |
| C `add_gate()` | existing | Inject individual remapped gates during replay | Central gate insertion API, handles layer assignment |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| C `allocator_alloc()` | existing | Allocate fresh ancilla qubits during replay | When compiled function allocates internal temporaries |
| C `allocator_free()` | existing | Deallocate ancilla qubits on uncomputation | When replay-allocated ancillas are freed |
| `qint(create_new=False, bit_list=...)` | existing pattern | Construct return qint from replay-mapped qubits | Every compiled function that returns a qint/qbool |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Layer-range extraction | Separate circuit buffer (redirect `_circuit` pointer) | Would break allocator continuity, require swapping global pointer |
| Python-level cache dict | C-level compiled block storage | More complex memory management, no perf gain (hot path already in C) |
| Gate-level capture | Operation-level capture (trace ADD/MUL/XOR calls) | More semantic info but requires intercepting all operator methods |
| `add_gate()` per gate in replay | Bulk `run_instruction()` with synthetic `sequence_t` | Faster but requires building C sequence_t from Python -- defer to optimization phase |

**Installation:**
```bash
# No new dependencies required
# Existing build: pip install -e .
```

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
  __init__.py              # MODIFY: add 'compile' to __all__ and imports
  compile.py               # NEW: @ql.compile decorator, CompiledFunc, CompiledBlock (~250 LOC)
  _core.pyx                # MODIFY: add extract_gate_range(), inject_remapped_gates(),
                           #          cache-clear hook in circuit.__init__()
  _core.pxd                # MODIFY: expose gate_t fields and circuit_s.sequence for Cython access
tests/
  test_compile.py          # NEW: tests for @ql.compile decorator
```

### Pattern 1: Layer-Range Extraction (from `draw_data()`)
**What:** Read gate data from `circuit_t.sequence[start_layer:end_layer]` into Python dicts
**When to use:** During first call (capture phase) to extract the gates the function generated
**Example:**
```python
# Source: Existing pattern in _core.pyx draw_data() lines 435-461
# New Cython function in _core.pyx:
def extract_gate_range(int start_layer, int end_layer):
    """Extract gates from circuit layers [start_layer, end_layer) as Python list of dicts."""
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
    gates = []
    for layer in range(start_layer, end_layer):
        for gi in range(circ.used_gates_per_layer[layer]):
            g = &circ.sequence[layer][gi]
            gate_dict = {
                'type': <int>g.Gate,
                'target': <int>g.Target,
                'angle': g.GateValue,
                'num_controls': <int>g.NumControls,
                'controls': [<int>g.Control[i] for i in range(min(g.NumControls, 2))]
            }
            if g.NumControls > 2 and g.large_control != NULL:
                gate_dict['controls'] = [<int>g.large_control[i] for i in range(g.NumControls)]
            gates.append(gate_dict)
    return gates
```

### Pattern 2: Gate Injection with Qubit Remapping (from `run_instruction()`)
**What:** Replay cached gates into current circuit with remapped qubit indices
**When to use:** On subsequent calls to replay the cached gate sequence
**Example:**
```python
# Source: Existing pattern in execution.c run_instruction() lines 14-53
# New Cython function in _core.pyx:
def inject_remapped_gates(list gates, dict qubit_map):
    """Inject gates into circuit with qubit index remapping."""
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
    cdef gate_t *g
    for gate_dict in gates:
        g = <gate_t*>malloc(sizeof(gate_t))
        memset(g, 0, sizeof(gate_t))
        g.Gate = <Standardgate_t>gate_dict['type']
        g.Target = qubit_map[gate_dict['target']]
        g.GateValue = gate_dict['angle']
        g.NumControls = gate_dict['num_controls']
        controls = gate_dict['controls']
        if g.NumControls <= 2:
            for i in range(g.NumControls):
                g.Control[i] = qubit_map[controls[i]]
        else:
            g.large_control = <qubit_t*>malloc(g.NumControls * sizeof(qubit_t))
            for i in range(g.NumControls):
                g.large_control[i] = qubit_map[controls[i]]
            g.Control[0] = g.large_control[0]
            g.Control[1] = g.large_control[1]
        add_gate(circ, g)
```

### Pattern 3: Global State Snapshot/Restore (INF-02)
**What:** Save and restore all mutable global state before/after tracing to prevent pollution
**When to use:** During first call (capture phase) around the actual function execution
**Example:**
```python
# Snapshot before tracing
def _snapshot_global_state():
    return {
        'num_qubits': _get_num_qubits(),
        'int_counter': _get_int_counter(),
        'smallest_allocated_qubit': _get_smallest_allocated_qubit(),
        'global_creation_counter': _get_global_creation_counter(),
        'controlled': _get_controlled(),
        'control_bool': _get_control_bool(),
        'list_of_controls': list(_get_list_of_controls()),
        'scope_stack_len': len(_get_scope_stack()),
    }

# NOTE: On first call, tracing runs the function for real.
# The captured gates stay in the circuit. State that must be
# PRESERVED: circuit state (gates stay), qubit allocations (stay).
# State that may need ADJUSTMENT: _int_counter (increment for replay
# qints), _global_creation_counter (increment for replay objects).
# The snapshot/restore is selectively applied, NOT a full rollback.
```

### Pattern 4: Cache Key Construction (CAP-04)
**What:** Build deterministic cache key from function identity + classical args + qint widths
**When to use:** On every call to check cache hit
**Example:**
```python
def _build_cache_key(func, args, kwargs):
    """Build cache key: (func_id, classical_args, quantum_widths)."""
    classical = []
    widths = []
    for arg in args:
        if isinstance(arg, (qint, qbool)):
            widths.append(arg.width)
        else:
            classical.append(arg)
    # kwargs handling similarly
    return (id(func), tuple(classical), tuple(widths))
```

### Pattern 5: Virtual Qubit Mapping (CAP-02, CAP-03)
**What:** Map captured gate qubit indices to virtual namespace, then remap to real qubits on replay
**When to use:** After capture (build virtual map) and during replay (apply real map)
**Example:**
```python
# During capture: build virtual mapping from real qubits
# Real qubit indices used by function -> virtual indices 0, 1, 2, ...
def _build_virtual_mapping(gates, param_qubits):
    """Map real qubit indices to virtual namespace."""
    real_to_virtual = {}
    virtual_idx = 0
    # Map parameter qubits first (in order)
    for qubit_indices in param_qubits:
        for real_q in qubit_indices:
            if real_q not in real_to_virtual:
                real_to_virtual[real_q] = virtual_idx
                virtual_idx += 1
    # Map remaining qubits (ancillas/temporaries)
    for gate in gates:
        for real_q in [gate['target']] + gate['controls']:
            if real_q not in real_to_virtual:
                real_to_virtual[real_q] = virtual_idx
                virtual_idx += 1
    # Convert gates to virtual indices
    virtual_gates = _remap_gates(gates, real_to_virtual)
    return virtual_gates, real_to_virtual, virtual_idx

# During replay: build real mapping from caller's qints
def _build_replay_mapping(compiled_block, caller_qints, allocator):
    """Map virtual qubit indices to real qubit indices for replay."""
    virtual_to_real = {}
    vidx = 0
    for qint_arg in caller_qints:
        for i in range(qint_arg.width):
            real_q = qint_arg.qubits[64 - qint_arg.width + i]
            virtual_to_real[vidx] = real_q
            vidx += 1
    # Allocate fresh qubits for ancillas/temporaries
    for v in range(vidx, compiled_block.total_virtual_qubits):
        virtual_to_real[v] = allocator_alloc(allocator, 1, True)
    return virtual_to_real
```

### Pattern 6: Decorator with Both Bare and Parens Forms
**What:** Support `@ql.compile` and `@ql.compile()` and `@ql.compile(max_cache=N)`
**When to use:** Decorator definition in `compile.py`
**Example:**
```python
def compile(func=None, *, max_cache=128, key=None, verify=False):
    """Decorator that compiles a quantum function for cached gate replay."""
    def decorator(fn):
        return CompiledFunc(fn, max_cache=max_cache, key=key, verify=verify)
    if func is not None:
        # Called as @ql.compile (bare)
        return CompiledFunc(func, max_cache=max_cache, key=key, verify=verify)
    # Called as @ql.compile() or @ql.compile(max_cache=N)
    return decorator
```

### Anti-Patterns to Avoid
- **Swapping `_circuit` pointer during capture:** Would break allocator continuity; use layer-range extraction instead
- **Abstract tracing (JAX-style):** Would require rewriting all ~50 Cython operator methods to handle tracer types
- **Storing raw C pointers in Python cache:** Use Python dicts with integer values; avoids dangling pointer issues across circuit resets
- **Modifying captured gate sequence in place:** Always create new gate_t via `malloc()` during injection (same pattern as `run_instruction()`)
- **Forgetting to set `layer_floor` during replay:** Gates may be optimized into earlier layers, breaking uncomputation tracking. Always set `layer_floor = used_layer` before replay, restore after.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gate extraction from circuit | Custom circuit walker | `draw_data()` pattern -- iterate `circ.sequence[layer][gate]` | Handles large_control, all gate types, tested in Phase 45 |
| Qubit remapping during replay | Custom remapping logic | `run_instruction()` pattern -- copy gate_t, remap Target/Control, call `add_gate()` | Handles n-controlled gates, GateValue inversion, memory allocation |
| Layer floor management | Custom gate ordering | `layer_floor` field on `circuit_t` -- set before replay, restore after | Already used by `__add__`, `__mul__` etc. (Quick-013 fix) |
| Qubit ownership transfer | Custom metadata management | `qbool.copy()` pattern -- set `allocated_start`, `allocated_qubits`, `_start_layer`, `_end_layer` | Already handles all ownership metadata correctly |
| Cache eviction (LRU) | Custom data structure | `collections.OrderedDict` with `popitem(last=False)` | Standard Python LRU pattern, O(1) operations |
| Type inspection for args | Custom arg classifier | `isinstance(arg, qint)` check (qbool is subclass of qint) | Python isinstance handles inheritance correctly |

**Key insight:** Every primitive needed for capture-replay already exists in the codebase. The implementation is pure orchestration of existing patterns -- no novel algorithms needed.

## Common Pitfalls

### Pitfall 1: Qubit Index Collision During Replay
**What goes wrong:** Captured gates record concrete qubit indices from the first call. On replay with different qint arguments, the same concrete indices would refer to wrong or unallocated qubits -- corrupting the circuit.
**Why it happens:** The capture extracts raw gate data with absolute qubit indices from the circuit.
**How to avoid:** Convert all qubit indices to a virtual namespace (0, 1, 2...) immediately after extraction. Parameter qubits get virtual indices in parameter order; ancilla qubits get higher virtual indices. On replay, build virtual-to-real mapping from caller's qint `.qubits` arrays and freshly-allocated ancillas.
**Warning signs:** Different circuit output when calling compiled function with different qint args that have same width. Gates targeting qubits outside the allocated range.

### Pitfall 2: Global State Pollution During Tracing
**What goes wrong:** First call executes the function for real, which mutates `_num_qubits`, `_int_counter`, `_global_creation_counter`, `_smallest_allocated_qubit`, and the `ancilla` array. After capture, these reflect the trace execution. If not managed, subsequent code sees incorrect state.
**Why it happens:** The 12+ global variables in `_core.pyx` are modified as side effects of qint creation and gate operations during normal execution.
**How to avoid:** For first call: the function executes normally and its gates ARE the first-call output (no rollback). The key insight is that on first call, the trace IS the real execution. No snapshot/restore needed for the gates or qubit allocations themselves. On replay: adjust `_int_counter` and `_global_creation_counter` appropriately for any replay-created qints. For replay-allocated ancillas: use the allocator directly (not the legacy `ancilla` array).
**Warning signs:** `_int_counter` values jump unexpectedly. qint naming collisions. `_num_qubits` count wrong after compiled function call.

### Pitfall 3: Return Value Not Usable After Replay
**What goes wrong:** On replay, the function body doesn't execute, so no Python qint object is naturally created. If the wrapper returns a stub qint without correct metadata, subsequent operations (arithmetic, comparison, `with` block) fail or produce incorrect circuits.
**Why it happens:** The replay only injects gates -- it doesn't run Python code. A return qint must be manually constructed with correct `.qubits`, `.bits`, `.allocated_start`, `.allocated_qubits`, `_start_layer`, `_end_layer`, and `dependency_parents`.
**How to avoid:** Use `qint(create_new=False, bit_list=replay_qubit_array)` pattern (from `qbool.copy()`). Set `allocated_start` to the first replay-allocated qubit. Set `_start_layer` to the layer before replay, `_end_layer` to layer after replay. Set `allocated_qubits = True` and `operation_type = 'COMPILED'`.
**Warning signs:** `ValueError: Cannot use qbool: already uncomputed` when using replay return value. Missing gates when using replay result in arithmetic.

### Pitfall 4: Ancilla Qubits Not Properly Handled
**What goes wrong:** Functions that allocate temporary internal qubits (e.g., ancillas for carry chains in addition) record those specific qubit indices during capture. On replay, those exact indices may be in use by other qints -- writing gates to occupied qubits.
**Why it happens:** Ancilla allocation is sequential; different call contexts produce different ancilla indices.
**How to avoid:** During virtual mapping construction, all qubits referenced in captured gates (including ancillas) get virtual indices. During replay, ancilla virtual indices map to freshly-allocated qubits from `allocator_alloc()`. The virtual mapping ensures no collision.
**Warning signs:** Replay circuit has fewer qubits than expected. Gate target indices overlap with caller's qints.

### Pitfall 5: Cache Key Missing Width or Classical Values
**What goes wrong:** Two calls with different widths (e.g., `f(qint(5, width=4))` and `f(qint(5, width=8))`) hit the same cache entry. The width=4 gate sequence is replayed onto width=8 qubits, producing an incorrect (shorter) circuit.
**Why it happens:** `CQ_add(bits=4, value=5)` and `CQ_add(bits=8, value=5)` produce structurally different gate sequences. Width is not just a parameter -- it determines the entire circuit structure.
**How to avoid:** Include both quantum argument widths AND classical argument values in the cache key: `(func_id, classical_args_tuple, width_tuple)`. This is requirement CAP-04.
**Warning signs:** Same gate count for different input widths. Incorrect computation results when width varies.

### Pitfall 6: Circuit Reset Doesn't Clear Cache
**What goes wrong:** User calls `ql.circuit()` to start fresh, but compiled function cache still holds gates from the old circuit. Replay injects gates referencing qubits that no longer exist or belong to different variables.
**Why it happens:** The cache is stored on the `CompiledFunc` wrapper, which persists across circuit resets.
**How to avoid:** Hook into `circuit.__init__()` to clear all compilation caches. Maintain a global registry of all `CompiledFunc` instances (weak references) and iterate to clear on circuit reset. This is requirement CAP-05.
**Warning signs:** Gates injected at invalid qubit indices after `ql.circuit()`. Circuit has unexpected gates from previous computations.

### Pitfall 7: Layer Floor Not Set During Replay
**What goes wrong:** Replayed gates get optimized by `add_gate()` into earlier layers, potentially before the replay start point. This breaks `_start_layer`/`_end_layer` tracking and makes uncomputation incorrect.
**Why it happens:** `add_gate()` in `optimizer.c` finds the minimum layer respecting `layer_floor`. If `layer_floor` is 0 (default), gates can be placed anywhere.
**How to avoid:** Before replay, save current `layer_floor`, set it to `used_layer`, replay gates, restore `layer_floor`. This is the exact pattern used in `__add__` (Quick-013 fix, lines 97-100 of `qint_arithmetic.pxi`).
**Warning signs:** Replay gate count matches but circuit depth is shorter than expected. Uncomputation reverses wrong gates.

## Code Examples

### Complete Decorator Flow (compile.py)
```python
# Source: Architecture patterns from existing codebase analysis
import functools
import collections
from ._core import (
    _get_circuit, _get_circuit_initialized,
    get_current_layer, extract_gate_range, inject_remapped_gates,
    _get_num_qubits, _set_num_qubits,
    _get_int_counter, _set_int_counter,
    _get_global_creation_counter,
)
from .qint import qint
from .qbool import qbool

# Global registry for cache invalidation on circuit reset
_compiled_funcs = []  # List of weakref to CompiledFunc instances

class CompiledBlock:
    """A captured and virtualized gate sequence."""
    __slots__ = ('gates', 'total_virtual_qubits', 'param_qubit_ranges',
                 'internal_qubit_count', 'return_qubit_range')

    def __init__(self, gates, total_virtual_qubits, param_qubit_ranges,
                 internal_qubit_count, return_qubit_range):
        self.gates = gates
        self.total_virtual_qubits = total_virtual_qubits
        self.param_qubit_ranges = param_qubit_ranges
        self.internal_qubit_count = internal_qubit_count
        self.return_qubit_range = return_qubit_range


class CompiledFunc:
    """Wrapper for @ql.compile decorated functions."""

    def __init__(self, func, max_cache=128, key=None, verify=False):
        functools.update_wrapper(self, func)
        self._func = func
        self._cache = collections.OrderedDict()
        self._max_cache = max_cache
        self._key_func = key
        self._verify = verify
        # Register for cache invalidation
        import weakref
        _compiled_funcs.append(weakref.ref(self))

    def __call__(self, *args, **kwargs):
        # Classify args
        quantum_args = []
        classical_args = []
        widths = []
        for arg in args:
            if isinstance(arg, qint):
                quantum_args.append(arg)
                widths.append(arg.width)
            else:
                classical_args.append(arg)

        # Build cache key
        if self._key_func:
            cache_key = self._key_func(*args, **kwargs)
        else:
            cache_key = (tuple(classical_args), tuple(widths))

        if cache_key in self._cache:
            # REPLAY PATH
            return self._replay(self._cache[cache_key], quantum_args)
        else:
            # CAPTURE PATH
            block = self._capture(args, kwargs, quantum_args, widths)
            # Store in cache with eviction
            self._cache[cache_key] = block
            if len(self._cache) > self._max_cache:
                self._cache.popitem(last=False)  # Remove oldest
            # First call: function already executed, return its result
            return block._first_call_result

    def _capture(self, args, kwargs, quantum_args, widths):
        """Capture gate sequence during first call."""
        # Record start layer
        start_layer = get_current_layer()

        # Collect parameter qubit indices BEFORE execution
        param_qubit_indices = []
        for qa in quantum_args:
            indices = [int(qa.qubits[64 - qa.width + i]) for i in range(qa.width)]
            param_qubit_indices.append(indices)

        # Execute function normally (gates flow to circuit as usual)
        result = self._func(*args, **kwargs)

        # Record end layer
        end_layer = get_current_layer()

        # Extract captured gates
        raw_gates = extract_gate_range(start_layer, end_layer)

        # Build virtual mapping
        virtual_gates, real_to_virtual, total_virtual = \
            _build_virtual_mapping(raw_gates, param_qubit_indices)

        # Determine return value qubit range (if result is qint)
        return_range = None
        if isinstance(result, qint):
            ret_indices = [int(result.qubits[64 - result.width + i])
                          for i in range(result.width)]
            virt_ret = [real_to_virtual[r] for r in ret_indices]
            return_range = (min(virt_ret), result.width)

        # Build compiled block
        param_ranges = []
        vidx = 0
        for qa in quantum_args:
            param_ranges.append((vidx, qa.width))
            vidx += qa.width
        internal_count = total_virtual - vidx

        block = CompiledBlock(
            gates=virtual_gates,
            total_virtual_qubits=total_virtual,
            param_qubit_ranges=param_ranges,
            internal_qubit_count=internal_count,
            return_qubit_range=return_range,
        )
        block._first_call_result = result
        return block

    def _replay(self, block, quantum_args):
        """Replay cached gates with qubit remapping."""
        # Build virtual-to-real mapping
        virtual_to_real = {}
        vidx = 0
        for qa in quantum_args:
            for i in range(qa.width):
                real_q = int(qa.qubits[64 - qa.width + i])
                virtual_to_real[vidx] = real_q
                vidx += 1

        # Allocate fresh ancillas for internal qubits
        # (uses allocator_alloc via Cython)
        for v in range(vidx, block.total_virtual_qubits):
            virtual_to_real[v] = _allocate_qubit()  # wrapper around allocator_alloc

        # Set layer_floor to prevent gate reordering
        start_layer = get_current_layer()
        _save_and_set_layer_floor(start_layer)

        # Inject remapped gates
        inject_remapped_gates(block.gates, virtual_to_real)

        end_layer = get_current_layer()
        _restore_layer_floor()

        # Build return qint if applicable
        if block.return_qubit_range is not None:
            return _build_return_qint(block, virtual_to_real, start_layer, end_layer)
        return None

    def clear_cache(self):
        """Clear this function's compilation cache."""
        self._cache.clear()
```

### Cache Clear Hook in circuit.__init__()
```python
# Source: Existing circuit.__init__() in _core.pyx, line 261-284
# ADD to circuit.__init__() after existing state resets:

# Clear all compilation caches (CAP-05)
from .compile import _clear_all_caches
_clear_all_caches()
```

### Return Value Construction on Replay
```python
# Source: Pattern from qbool.copy() in qbool.pyx lines 76-88
def _build_return_qint(block, virtual_to_real, start_layer, end_layer):
    """Construct usable qint from replay-mapped qubits."""
    import numpy as np
    ret_start, ret_width = block.return_qubit_range

    # Build qubit array for return qint (right-aligned in 64-element array)
    ret_qubits = np.ndarray(64, dtype=np.uint32)
    first_real_qubit = None
    for i in range(ret_width):
        virt_q = ret_start + i
        real_q = virtual_to_real[virt_q]
        ret_qubits[64 - ret_width + i] = real_q
        if first_real_qubit is None:
            first_real_qubit = real_q

    # Create qint with existing qubits (no allocation)
    result = qint(create_new=False, bit_list=ret_qubits, width=ret_width)

    # Transfer ownership metadata
    result.allocated_start = first_real_qubit
    result.allocated_qubits = True
    result._start_layer = start_layer
    result._end_layer = end_layer
    result.operation_type = 'COMPILED'

    return result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full abstract tracing (JAX) | Tape-style capture-replay | N/A (architecture decision) | Avoids rewriting 50+ Cython operator methods |
| Separate circuit buffer for capture | Layer-range extraction from existing circuit | N/A (architecture decision) | Preserves allocator continuity, zero C changes |
| Global `QPU_state` register-based API | Explicit parameters via `run_instruction()` | Phase 11 | Clean gate flow, explicit qubit arrays enable remapping |
| Monolithic circuit construction | Layer floor + start/end layer tracking | Phases 17-41 | Enables scoped gate extraction and uncomputation |

**Deprecated/outdated:**
- Legacy `ancilla` numpy array tracking: Still exists but deprecated. Replay should use `allocator_alloc()` directly.
- Legacy `_smallest_allocated_qubit` tracking: Maintained for backward compat. Replay should not rely on it.

## Open Questions

1. **Multi-return value handling**
   - What we know: Single qint return is straightforward via `create_new=False`. Tuple returns need multiple qubit ranges tracked.
   - What's unclear: How to handle `return a, b` where both `a` and `b` are qints that were modified in-place.
   - Recommendation: Start with single return value. For tuple returns, track each return value's qubit range separately in `CompiledBlock.return_qubit_ranges: list[tuple]`. For in-place modifications of input qints, these need no explicit return handling (the caller's qints already reference the correct qubits -- the gates were applied to them during replay).

2. **Verify mode implementation detail**
   - What we know: `@ql.compile(verify=True)` should run both capture and replay, compare gate sequences.
   - What's unclear: How to compare gate sequences when optimization during add_gate may reorder gates between capture and replay.
   - Recommendation: Compare using `draw_data()` output (which normalizes to layer/gate structure) rather than raw gate lists. Accept layer differences if gate types and qubit targets match.

3. **In-place modification of input qints**
   - What we know: Functions like `def inc(a): a += 1; return a` modify the input qint in place. During capture, this is natural. During replay, the gates need to target the caller's qint qubits.
   - What's unclear: Whether the virtual mapping correctly handles this when the return value IS one of the input qints (not a new allocation).
   - Recommendation: This should work naturally -- the parameter qubits are mapped to virtual indices 0..N, and since the function modifies them in-place, the captured gates already target those same virtual indices. On replay, they map to the caller's real qubits. The return value can share qubit indices with a parameter. Track this with a flag: `return_is_param_index: int | None`.

4. **Interaction with `qubit_saving_mode` (eager uncomputation)**
   - What we know: In eager mode, intermediate qints are uncomputed immediately during execution. Their forward+reverse gates would be captured during tracing.
   - What's unclear: Whether replayed forward+reverse pairs get correctly cancelled by the `add_gate()` optimizer.
   - Recommendation: Defer to Phase 49 (optimization/uncomputation). For Phase 48, document that `@ql.compile` functions should be called with `qubit_saving_mode=False` (default). The optimization phase will handle this interaction.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis (all HIGH confidence):**
  - `c_backend/include/types.h` -- `gate_t` and `sequence_t` definitions (lines 56-83)
  - `c_backend/include/circuit.h` -- `circuit_t` structure with `used_layer`, `layer_floor`, `allocator` (lines 54-81)
  - `c_backend/src/execution.c` -- `run_instruction()` qubit remapping pattern (lines 14-53)
  - `c_backend/src/execution.c` -- `reverse_circuit_range()` layer iteration (lines 57-104)
  - `c_backend/src/circuit_output.c` -- `circuit_to_draw_data()` gate extraction (lines 590-699)
  - `c_backend/src/optimizer.c` -- `add_gate()` with layer_floor and merge_gates (lines 40-220)
  - `c_backend/include/optimizer.h` -- `add_gate()` signature (line 22)
  - `src/quantum_language/_core.pyx` -- 12+ global state variables (lines 25-47), circuit class (lines 247-674)
  - `src/quantum_language/qint.pyx` -- qint construction and ownership (lines 89-301)
  - `src/quantum_language/qint_arithmetic.pxi` -- layer_floor pattern in `__add__` (lines 90-121)
  - `src/quantum_language/qbool.pyx` -- ownership transfer in `copy()` (lines 76-88)
  - `src/quantum_language/qint.pxd` -- qint cdef attributes (lines 1-25)
  - `src/quantum_language/__init__.py` -- public API surface (lines 169-196)

- **Prior research (HIGH confidence):**
  - `.planning/research/SUMMARY-COMPILE-DECORATOR.md` -- comprehensive v2.0 research with architecture, pitfalls, phase plan
  - `.planning/research/ARCHITECTURE-COMPILE-DECORATOR.md` -- detailed gate flow analysis, data structures, build order
  - `.planning/phases/48-core-capture-replay/48-CONTEXT.md` -- user decisions constraining this phase

### Secondary (MEDIUM confidence)
- PennyLane QNode tape-based queuing pattern (v0.44.0) -- validates tape-style capture approach
- Cirq FrozenCircuit pattern -- validates immutable compiled circuit concept

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components are existing codebase primitives with verified patterns
- Architecture: HIGH -- two existing patterns (draw_data extraction, run_instruction remapping) directly map to capture/replay
- Pitfalls: HIGH -- 7 pitfalls identified from direct codebase analysis; all have concrete prevention strategies
- Code examples: HIGH -- derived from actual codebase patterns with specific line references

**Research date:** 2026-02-04
**Valid until:** 2026-03-06 (stable domain, no external dependency changes expected)
