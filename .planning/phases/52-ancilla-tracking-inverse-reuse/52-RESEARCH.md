# Phase 52: Ancilla Tracking & Inverse Qubit Reuse - Research

**Researched:** 2026-02-04
**Domain:** Quantum compilation infrastructure (Python + Cython), ancilla lifecycle management
**Confidence:** HIGH

## Summary

Phase 52 adds ancilla tracking and `f.inverse(x)` / `f.adjoint(x)` semantics to the existing `@ql.compile` infrastructure. The existing codebase already has all the foundational pieces: `CompiledBlock` tracks `internal_qubit_count` and virtual qubit mappings, `_replay` allocates fresh ancillas via `_allocate_qubit()`, `_InverseCompiledFunc` generates adjoint gate sequences, and `allocator_free` deallocates qubits. The main work is:

1. **Forward call tracking**: During `_replay`, record which physical qubits were allocated as ancillas and associate them with the input qubit identity (the "forward call record").
2. **`f.inverse(x)` method**: Look up the forward call record by input qubit identity, replay adjoint gates targeting the *original* ancilla qubits (not fresh ones), then deallocate them.
3. **`f.adjoint(x)` method**: Run adjoint gates with fresh ancillas (standalone, no forward call needed) -- this is the current `_InverseCompiledFunc` behavior.
4. **Return value invalidation**: After `f.inverse(x)`, mark the return qint as uncomputed/invalidated.
5. **Error handling**: Detect double-forward without inverse, inverse-without-forward, and double-inverse.

**Primary recommendation:** Implement ancilla tracking as a per-`CompiledFunc` dictionary mapping input qubit tuples to `AncillaRecord` objects. Modify `_replay` to populate this dictionary. Add `inverse()` and `adjoint()` as methods on `CompiledFunc` that return lightweight proxy objects with `__call__`.

## Standard Stack

### Core

This phase is entirely internal to the existing codebase. No new external libraries needed.

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `compile.py` | `src/quantum_language/compile.py` | CompiledFunc, _InverseCompiledFunc, CompiledBlock | Modify |
| `_core.pyx` | `src/quantum_language/_core.pyx` | `_allocate_qubit()`, `extract_gate_range`, `inject_remapped_gates` | Modify (add `_deallocate_qubits`) |
| `_core.pxd` | `src/quantum_language/_core.pxd` | C declarations including `allocator_free` | No change needed |
| `qint.pyx` | `src/quantum_language/qint.pyx` | qint class with `_is_uncomputed`, `allocated_qubits` | Minor modification (invalidation) |
| `qubit_allocator.h` | `c_backend/include/qubit_allocator.h` | `allocator_alloc`, `allocator_free` | No change needed |

### Supporting

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `test_compile.py` | Existing compile tests | Extend with Phase 52 tests |
| `conftest.py` | Test fixtures | Use existing patterns |

## Architecture Patterns

### Recommended Changes to Existing Structure

```
src/quantum_language/
├── compile.py          # MODIFY: Add AncillaRecord, forward call tracking,
│                       #   f.inverse(x), f.adjoint(x) methods
├── _core.pyx           # MODIFY: Add _deallocate_qubits() Python function
├── _core.pxd           # NO CHANGE (allocator_free already declared)
├── qint.pyx            # MINOR: Add invalidation helper
└── __init__.py          # NO CHANGE (compile already exported)

tests/
└── test_compile.py     # EXTEND: Add INV-01 through INV-06 tests
```

### Pattern 1: AncillaRecord Data Class

**What:** A lightweight record stored per forward call, tracking the physical ancilla qubits and the compiled block used.

**When to use:** Created during every `_replay` call on `CompiledFunc.__call__`, consumed by `f.inverse(x)`.

```python
class AncillaRecord:
    """Record of a single forward call's ancilla allocations."""
    __slots__ = (
        'ancilla_qubits',      # list[int] - physical qubit indices allocated as ancillas
        'virtual_to_real',     # dict[int, int] - full virtual-to-real mapping used
        'block',               # CompiledBlock - the compiled block that was replayed
        'return_qint',         # qint or None - the return value (for invalidation)
    )
```

### Pattern 2: Forward Call Registry (per CompiledFunc)

**What:** A dictionary on `CompiledFunc` mapping input qubit identity to `AncillaRecord`.

**Key design:** The input qubit identity is a tuple of physical qubit indices from all quantum arguments, preserving order. This is the "qubit identity" matching described in the CONTEXT.md decisions.

```python
# On CompiledFunc:
self._forward_calls = {}  # dict[tuple[int,...], AncillaRecord]

# Key construction:
def _input_qubit_key(quantum_args):
    """Build a hashable key from the physical qubits of all quantum arguments."""
    key_parts = []
    for qa in quantum_args:
        key_parts.extend(_get_qint_qubit_indices(qa))
    return tuple(key_parts)
```

### Pattern 3: f.inverse(x) as Method Returning Proxy

**What:** `CompiledFunc.inverse` becomes a method that returns a callable proxy. When called as `f.inverse(x)`, it looks up the forward call, replays adjoint gates on the *original* ancilla qubits, deallocates them, and returns None.

**Key difference from existing `_InverseCompiledFunc`:** The existing inverse allocates fresh ancillas. `f.inverse(x)` must reuse the ancillas from the forward call.

```python
class _AncillaInverseProxy:
    """Proxy returned by f.inverse that targets a prior forward call's ancillas."""

    def __init__(self, compiled_func):
        self._compiled_func = compiled_func

    def __call__(self, *args, **kwargs):
        # 1. Classify args
        quantum_args, classical_args, widths = self._compiled_func._classify_args(args, kwargs)

        # 2. Build input qubit key
        input_key = _input_qubit_key(quantum_args)

        # 3. Look up forward call record
        record = self._compiled_func._forward_calls.get(input_key)
        if record is None:
            raise ValueError(f"No prior forward call found for these qubits")

        # 4. Get adjoint gates from the block
        adjoint_gates = _inverse_gate_list(record.block.gates)

        # 5. Inject adjoint gates using the ORIGINAL virtual_to_real mapping
        inject_remapped_gates(adjoint_gates, record.virtual_to_real)

        # 6. Deallocate ancilla qubits
        for qubit_idx in record.ancilla_qubits:
            _deallocate_qubits(qubit_idx, 1)

        # 7. Invalidate return qint
        if record.return_qint is not None:
            record.return_qint._is_uncomputed = True
            record.return_qint.allocated_qubits = False

        # 8. Remove forward call record
        del self._compiled_func._forward_calls[input_key]

        return None
```

### Pattern 4: f.adjoint(x) as Standalone Reverse

**What:** `f.adjoint(x)` runs the adjoint gate sequence with *fresh* ancillas (no forward call needed). This is essentially the current `_InverseCompiledFunc` behavior, renamed.

**Implementation:** Rename/refactor existing `_InverseCompiledFunc` to serve as `f.adjoint(x)`.

### Pattern 5: _deallocate_qubits Python Function

**What:** A new Python-callable function in `_core.pyx` that wraps `allocator_free`, analogous to `_allocate_qubit`.

**Why needed:** `compile.py` is pure Python and cannot use `cimport`. Currently only Cython files (qint.pyx) can call `allocator_free` directly.

```cython
def _deallocate_qubits(unsigned int start, unsigned int count):
    """Deallocate qubits, returning them to the allocator pool.

    Parameters
    ----------
    start : int
        Starting qubit index.
    count : int
        Number of contiguous qubits to free.
    """
    cdef qubit_allocator_t *alloc
    if not _circuit_initialized:
        raise RuntimeError("Circuit not initialized")
    alloc = circuit_get_allocator(<circuit_s*>_circuit)
    if alloc == NULL:
        raise RuntimeError("No allocator available")
    allocator_free(alloc, start, count)
```

### Anti-Patterns to Avoid

- **Storing forward records by cache key instead of qubit identity:** Cache keys use (classical_args, widths, control_count) which is NOT unique per call. Two different qints with the same width would share a cache key but have different physical qubits. MUST use qubit identity.
- **Modifying `_InverseCompiledFunc` to do ancilla tracking:** The existing `_InverseCompiledFunc` is a standalone adjoint (fresh ancillas). Phase 52 needs a SEPARATE mechanism for `f.inverse(x)` that targets prior forward call ancillas. Keep them distinct.
- **Allocating ancillas in the inverse call:** `f.inverse(x)` must reuse the SAME physical qubits from the forward call. Allocating fresh ones would put adjoint gates on wrong qubits.
- **Auto-invalidating return qint via `__del__`:** The return qint should only be invalidated when `f.inverse(x)` is explicitly called, not via garbage collection.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Adjoint gate generation | Custom gate reversal | Existing `_inverse_gate_list()` | Already correct, tested in Phase 51 |
| Gate injection with remapping | Custom circuit manipulation | Existing `inject_remapped_gates()` | Handles all gate types, controls |
| Qubit allocation | Custom pool | Existing `_allocate_qubit()` / `allocator_alloc` | C-backend handles reuse, stats |
| Qubit deallocation | Custom tracking | New `_deallocate_qubits()` wrapping `allocator_free` | C-backend already handles free-stack |
| Virtual-to-real mapping | New mapping system | Existing `_build_virtual_mapping()` pattern | Already handles params + ancillas |

**Key insight:** The existing compilation infrastructure already solves most of the hard problems. Phase 52's core contribution is the *forward call registry* that connects a forward call's ancilla allocations to a later inverse call.

## Common Pitfalls

### Pitfall 1: Controlled Context During Inverse

**What goes wrong:** If `f.inverse(x)` is called inside a `with_(control, lambda: ...)`, the adjoint gates need to be controlled. But the stored `virtual_to_real` mapping from the forward call doesn't include a control qubit.

**Why it happens:** Forward call was uncontrolled, but inverse might be in controlled context.

**How to avoid:** When replaying adjoint gates in `_AncillaInverseProxy.__call__`, check for controlled context. If controlled, derive controlled gates from the adjoint list (using existing `_derive_controlled_gates`) before injecting. The `virtual_to_real` mapping for param + ancilla qubits stays the same; only the control qubit is added.

**Warning signs:** Tests fail when `f.inverse(x)` is called inside `with ctrl:` blocks.

### Pitfall 2: First-Call vs Replay Forward Call Tracking

**What goes wrong:** On the FIRST call to a compiled function, gates are emitted directly to the circuit (capture mode). On subsequent calls, they are replayed. Ancilla tracking must work in BOTH cases.

**Why it happens:** During capture, ancilla qubits are allocated by the function body itself (e.g., `ql.qint()` inside the function). During replay, ancilla qubits are allocated by `_replay`. The physical qubit indices will be DIFFERENT.

**How to avoid:** Track ancillas in `_replay` (which handles both subsequent replay calls AND the return mapping). For the first call, the ancillas are already "naturally" allocated -- we need to extract them from the `_build_virtual_mapping` result. The `real_to_virtual` mapping from capture contains both param and ancilla qubits, so we can compute `ancilla_physical = {real for real, virt in real_to_virtual.items() if virt >= param_virtual_count}`.

**Warning signs:** First forward call followed by inverse works, but replay forward call followed by inverse doesn't (or vice versa).

### Pitfall 3: Non-Contiguous Ancilla Deallocation

**What goes wrong:** `allocator_free(start, count)` expects CONTIGUOUS qubit ranges. But ancillas allocated during a compiled function may not be contiguous if the allocator reuses freed qubits from a free-stack.

**Why it happens:** `_allocate_qubit()` allocates one qubit at a time, potentially returning non-contiguous indices from the freed stack.

**How to avoid:** Track individual qubit indices (not ranges) for ancillas. Call `_deallocate_qubits(qubit, 1)` for each individual ancilla qubit. This is slightly less efficient than batch deallocation but correct for non-contiguous allocations.

**Warning signs:** "Double-free" errors from the allocator, or qubits from other operations being freed.

### Pitfall 4: Return Value Qubits Are Also Ancillas

**What goes wrong:** The return value of a compiled function contains qubits that were internally allocated. These are tracked as ancillas and must be uncomputed by `f.inverse(x)`. But the user holds a reference to the return qint and may try to use it after inverse.

**Why it happens:** The return qint's physical qubits are a SUBSET of the ancilla qubits. After `f.inverse(x)`, those qubits are uncomputed to |0> and deallocated.

**How to avoid:** After `f.inverse(x)` completes, set `return_qint._is_uncomputed = True` and `return_qint.allocated_qubits = False`. This triggers the existing `_check_not_uncomputed()` guard in qint operations.

**Warning signs:** User operates on return qint after inverse, gets wrong results silently (no error).

### Pitfall 5: Cython Rebuild Required

**What goes wrong:** Adding `_deallocate_qubits()` to `_core.pyx` requires Cython compilation. If the build isn't triggered, tests will fail with import errors.

**Why it happens:** `.pyx` files compile to `.c` then to `.so`. The build step is needed.

**How to avoid:** Run `pip install -e .` or `python setup.py build_ext --inplace` after modifying `_core.pyx`. This is already the standard workflow.

**Warning signs:** `ImportError: cannot import name '_deallocate_qubits'`.

### Pitfall 6: Circuit Reset Must Clear Forward Call Registry

**What goes wrong:** `ql.circuit()` creates a new circuit, invalidating all physical qubit indices. If the forward call registry isn't cleared, inverse calls would target invalid qubits.

**Why it happens:** The existing `_clear_all_caches` hook clears compilation caches but wouldn't automatically clear the forward call registry.

**How to avoid:** In `CompiledFunc.clear_cache()`, also clear `self._forward_calls`. The existing `_register_cache_clear_hook` mechanism already calls `clear_cache()` on circuit reset.

**Warning signs:** After `ql.circuit()`, `f.inverse(x)` targets qubits from the old circuit.

## Code Examples

### Example 1: Adding _deallocate_qubits to _core.pyx

```cython
# In _core.pyx, after _allocate_qubit():

def _deallocate_qubits(unsigned int start, unsigned int count):
    """Deallocate qubits, returning them to the allocator pool.

    Parameters
    ----------
    start : int
        Starting qubit index.
    count : int
        Number of contiguous qubits to free.
    """
    cdef qubit_allocator_t *alloc
    if not _circuit_initialized:
        raise RuntimeError("Circuit not initialized")
    alloc = circuit_get_allocator(<circuit_s*>_circuit)
    if alloc == NULL:
        raise RuntimeError("No allocator available")
    allocator_free(alloc, start, count)
```

### Example 2: Forward Call Tracking in _replay

```python
# In CompiledFunc._replay, after allocating ancillas:

# Track ancilla qubits for inverse support
ancilla_qubits = []
for v in range(vidx, block.total_virtual_qubits):
    if block.control_virtual_idx is not None and v == block.control_virtual_idx:
        virtual_to_real[v] = int(control_bool.qubits[63])
    else:
        real_q = _allocate_qubit()
        virtual_to_real[v] = real_q
        ancilla_qubits.append(real_q)

# ... inject gates, build return value ...

# Record forward call
input_key = _input_qubit_key(quantum_args)
if input_key in self._forward_calls:
    raise ValueError(
        f"Forward call with these input qubits already exists. "
        f"Call f.inverse({', '.join(repr(a) for a in quantum_args)}) first."
    )
self._forward_calls[input_key] = AncillaRecord(
    ancilla_qubits=ancilla_qubits,
    virtual_to_real=dict(virtual_to_real),
    block=block,
    return_qint=result,
)
```

### Example 3: First-Call Ancilla Tracking

```python
# During _capture, after _build_virtual_mapping:
# Extract ancilla physical qubits from real_to_virtual mapping

param_real_qubits = set()
for qubit_list in param_qubit_indices:
    param_real_qubits.update(qubit_list)

ancilla_qubits = [
    real for real in real_to_virtual
    if real not in param_real_qubits
]

# Store on the block for later use
block._capture_ancilla_qubits = ancilla_qubits
```

### Example 4: f.inverse(x) Implementation

```python
class _AncillaInverseProxy:
    """Callable that uncomputes a prior forward call's ancillas."""

    def __init__(self, compiled_func):
        self._cf = compiled_func

    def __call__(self, *args, **kwargs):
        quantum_args, _, _ = self._cf._classify_args(args, kwargs)
        input_key = _input_qubit_key(quantum_args)

        record = self._cf._forward_calls.get(input_key)
        if record is None:
            raise ValueError("No prior forward call found for these input qubits")

        # Generate adjoint gates
        adjoint_gates = _inverse_gate_list(record.block.gates)

        # Handle controlled context
        is_controlled = _get_controlled()
        if is_controlled:
            control_bool = _get_control_bool()
            ctrl_qubit = int(control_bool.qubits[63])
            adjoint_gates = _derive_controlled_gates(
                adjoint_gates, record.block.total_virtual_qubits
            )
            vtr = dict(record.virtual_to_real)
            vtr[record.block.total_virtual_qubits] = ctrl_qubit
        else:
            vtr = record.virtual_to_real

        # Inject adjoint gates with original qubit mapping
        saved_floor = _get_layer_floor()
        _set_layer_floor(get_current_layer())
        inject_remapped_gates(adjoint_gates, vtr)
        _set_layer_floor(saved_floor)

        # Deallocate ancilla qubits
        for qubit_idx in record.ancilla_qubits:
            _deallocate_qubits(qubit_idx, 1)

        # Invalidate return qint
        if record.return_qint is not None:
            record.return_qint._is_uncomputed = True
            record.return_qint.allocated_qubits = False

        # Remove record
        del self._cf._forward_calls[input_key]

        return None
```

### Example 5: User-Facing API

```python
import quantum_language as ql

ql.circuit()

@ql.compile
def ripple_carry_add(x, y):
    """Addition that allocates ancilla qubits internally."""
    carry = ql.qint(0, width=1)  # ancilla
    result = ql.qint(0, width=x.width)
    # ... addition logic using carry ...
    return result

a = ql.qint(5, width=4)
b = ql.qint(3, width=4)

# Forward call - allocates ancillas
result = ripple_carry_add(a, b)
# result is a qint holding the sum, ancillas tracked internally

# ... use result in some computation ...

# Inverse call - uncomputes ancillas, deallocates them
ripple_carry_add.inverse(a, b)
# result is now invalidated
# ancilla qubits are freed for reuse

# Standalone adjoint (no prior forward call needed)
c = ql.qint(7, width=4)
d = ql.qint(2, width=4)
ripple_carry_add.adjoint(c, d)  # fresh ancillas, runs reverse circuit
```

## State of the Art

| Old Approach (v2.0) | Current Approach (v2.1 Phase 52) | Impact |
|---|---|---|
| `_InverseCompiledFunc` allocates fresh ancillas for adjoint | `f.inverse(x)` reuses original ancillas, `f.adjoint(x)` for standalone | Enables true uncomputation (ancillas to \|0>) |
| No ancilla tracking - fire-and-forget allocation | Forward call registry tracks per-call ancilla physical qubits | Enables qubit reuse after inverse |
| No Python-level `allocator_free` | `_deallocate_qubits()` exposed in `_core.pyx` | Pure Python compile.py can deallocate |
| Return qint has no lifecycle management | Return qint invalidated after inverse | Prevents use-after-uncompute bugs |

## Open Questions

### 1. First-Call Forward Tracking

**What we know:** During the first call (capture), the function body executes normally and ancillas are allocated by `ql.qint()` inside the function. These qubits are captured in the `real_to_virtual` mapping. We can identify ancilla qubits as those not in `param_qubit_indices`.

**What's unclear:** Should the first call be tracked in `_forward_calls` for inverse support? The first call's gates are already in the circuit (not replayed), so `f.inverse(x)` after the first call would need to reverse those actual circuit gates.

**Recommendation:** YES, track first calls. The adjoint gate approach works regardless -- `inject_remapped_gates` with the adjoint gates and original mapping will add the correct uncomputation gates even though the forward gates were emitted directly. The forward gates don't need to be "removed" -- they just get reversed by appending adjoint gates. This is exactly how quantum uncomputation works.

### 2. f.adjoint(x) Ancilla Tracking

**What we know:** CONTEXT.md lists this as "Claude's Discretion" -- whether `f.adjoint(x)` also tracks ancillas.

**What's unclear:** Should calling `f.adjoint(x)` also register a forward call that can be inversed?

**Recommendation:** NO. `f.adjoint(x)` is a standalone operation. It should NOT populate `_forward_calls`. If a user wants to uncompute an adjoint call, they would call the forward function. Keep `adjoint` simple and stateless.

### 3. Controlled Inverse Interaction with Replay System

**What we know:** CONTEXT.md lists this as "Claude's Discretion". The controlled context adds a control qubit to all gates.

**What's unclear:** When `f.inverse(x)` is called inside a controlled context, should the adjoint gates be controlled?

**Recommendation:** YES. The adjoint gates should respect the current controlled context, just like forward calls do. The implementation adds the control qubit to the adjoint gate list before injection (Pattern shown in Example 4 above).

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/compile.py` - Full source read, 921 lines
- `src/quantum_language/_core.pyx` - Allocation functions, gate extraction/injection
- `src/quantum_language/_core.pxd` - C declarations for allocator API
- `src/quantum_language/qint.pyx` - qint data model, uncomputation mechanism
- `src/quantum_language/qint.pxd` - qint attribute declarations
- `c_backend/include/qubit_allocator.h` - Allocator C API (alloc, free, stats)
- `tests/test_compile.py` - 1795 lines of existing tests covering all Phase 48-51 features

### Secondary (MEDIUM confidence)
- `.planning/phases/52-ancilla-tracking-inverse-reuse/52-CONTEXT.md` - Phase decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components are internal to this codebase, fully read and understood
- Architecture: HIGH - Patterns follow directly from existing compilation infrastructure
- Pitfalls: HIGH - Identified from actual code analysis (non-contiguous allocation, controlled context, first-call vs replay)

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (stable internal codebase, no external dependencies)
