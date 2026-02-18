# Phase 50: Controlled Context - Research

**Researched:** 2026-02-04
**Domain:** Compiled function integration with quantum conditional (`with qbool:`) blocks
**Confidence:** HIGH

## Summary

This phase makes `@ql.compile` decorated functions work correctly inside `with qbool:` blocks, producing controlled gate variants instead of uncontrolled ones. Currently, when a compiled function is called inside a `with` block, the compilation system ignores the controlled context entirely -- it either captures uncontrolled gates (on first call) or replays the cached uncontrolled sequence (on subsequent calls), regardless of the `_controlled` flag.

The implementation requires three changes: (1) detecting the controlled context inside `CompiledFunc.__call__()` and including it in the cache key, (2) deriving a controlled variant from the optimized uncontrolled gate sequence by adding a control qubit to each gate, and (3) remapping the placeholder control qubit to the actual `_control_bool` qubit at replay time. The existing `with` block infrastructure already ANDs nested control bools into a single qbool, so the compilation system only needs to handle single-control variants.

All infrastructure exists in the codebase. The gate dict format already supports `num_controls` and `controls` fields. The `inject_remapped_gates()` function in `_core.pyx` already handles arbitrary qubit remapping. The `_get_controlled()` and `_get_control_bool()` accessor functions in `_core.pyx` expose the current controlled context.

**Primary recommendation:** Derive controlled variants by transforming each gate in the optimized uncontrolled sequence (incrementing `num_controls` and prepending a placeholder control qubit index), then cache under a key that includes control count. At replay time, remap the placeholder control qubit to the actual `_control_bool` qubit alongside the existing argument qubit remapping.

## Standard Stack

### Core

This phase uses only existing codebase infrastructure -- no external libraries needed.

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `compile.py` | `src/quantum_language/compile.py` | CompiledFunc/CompiledBlock, cache key, capture-replay | Phase 48/49 output, direct modification target |
| `_core.pyx` | `src/quantum_language/_core.pyx` | `_get_controlled()`, `_get_control_bool()`, `inject_remapped_gates()` | Existing controlled context detection and gate injection |
| `qint.pyx` | `src/quantum_language/qint.pyx` | `__enter__`/`__exit__` for `with` blocks | Existing controlled context management |
| `qbool.pyx` | `src/quantum_language/qbool.pyx` | 1-bit quantum integer used as control | Existing control qubit type |
| `qint_preprocessed.pyx` | `src/quantum_language/qint_preprocessed.pyx` | Arithmetic dispatch to controlled variants (`cCQ_add`, etc.) | Reference for how controlled operations work |

### Supporting

| Component | Location | Purpose | When to Use |
|-----------|----------|---------|-------------|
| `openqasm.pyx` | `src/quantum_language/openqasm.pyx` | OpenQASM export for verification | Verifying controlled gates appear in output |
| `test_compile.py` | `tests/test_compile.py` | Existing compile tests | Extend with controlled context tests |
| `test_conditionals.py` | `tests/test_conditionals.py` | Existing `with` block tests | Reference patterns for controlled gate testing |
| `types.h` | `c_backend/include/types.h` | Gate type enum (`Standardgate_t`), `gate_t` structure | Understanding gate control fields |

## Architecture Patterns

### Current Controlled Context Mechanism

The `with qbool:` block works as follows (verified from `qint.pyx` lines 574-673):

1. `__enter__()` sets `_controlled = True` and `_control_bool = self` (the qbool)
2. For nested `with` blocks, the existing control bool is AND'd with the new one: `_control_bool &= self`
3. Every arithmetic operation (e.g., `__add_implementation()` in `qint_preprocessed.pyx`) checks `_get_controlled()` at call time
4. If controlled, the operation dispatches to a controlled C function (e.g., `cCQ_add` instead of `CQ_add`) and passes the control qubit from `_control_bool`
5. `__exit__()` restores `_controlled = False` and `_control_bool = None`

**Critical insight:** The `_controlled` flag and `_control_bool` are **global state** checked at gate-emission time. The compile system's `_capture()` runs the function body normally, so captured gates reflect whatever context was active during capture. For replay, `inject_remapped_gates()` bypasses the normal operation dispatch entirely -- it injects gates directly into the circuit without checking `_controlled`.

### Pattern 1: Controlled Variant Derivation from Uncontrolled Sequence

**What:** Transform each gate in the optimized uncontrolled gate list to add one control qubit, producing the controlled variant.

**When to use:** When eagerly compiling both variants on first call, or when a compiled function is first called inside a `with` block.

**How it works:**
- For each gate dict in the uncontrolled sequence:
  - Increment `num_controls` by 1
  - Prepend a placeholder control qubit index to `controls`
  - The gate type stays the same (X with 1 control = CNOT, X with 2 controls = Toffoli, etc.)

**Example:**
```python
_CONTROL_PLACEHOLDER = -1  # Sentinel value for the control qubit virtual index

def _derive_controlled_gates(uncontrolled_gates, control_virtual_idx):
    """Derive controlled variant by adding one control qubit to every gate."""
    controlled = []
    for g in uncontrolled_gates:
        cg = dict(g)
        cg['num_controls'] = g['num_controls'] + 1
        cg['controls'] = [control_virtual_idx] + list(g['controls'])
        controlled.append(cg)
    return controlled
```

**Confidence:** HIGH -- the gate_t structure in types.h explicitly supports variable `NumControls` and a `controls` array. The `inject_remapped_gates()` function in `_core.pyx` (lines 754-776) already handles multi-control gates: for `NumControls <= 2` it uses inline `Control[2]`, for `> 2` it allocates `large_control`.

### Pattern 2: Cache Key with Control Count

**What:** Extend the cache key to include whether the function is being called in a controlled context.

**When to use:** Always, in `CompiledFunc.__call__()`.

**Example:**
```python
def __call__(self, *args, **kwargs):
    quantum_args, classical_args, widths = self._classify_args(args, kwargs)

    # Detect controlled context
    is_controlled = _get_controlled()
    control_count = 1 if is_controlled else 0

    if self._key_func:
        cache_key = self._key_func(*args, **kwargs)
    else:
        cache_key = (tuple(classical_args), tuple(widths), control_count)

    # ... rest of lookup/capture/replay logic
```

**Confidence:** HIGH -- the cache is a simple `OrderedDict` keyed by tuples. Adding an element is trivial.

### Pattern 3: Eager Compilation of Both Variants

**What:** On first call (whether controlled or uncontrolled), compile both variants immediately.

**When to use:** In `__call__()` after a cache miss triggers capture.

**How it works:**
1. First call captures the uncontrolled sequence (function executes normally)
2. Immediately derive the controlled variant from the optimized uncontrolled sequence
3. Cache both under their respective keys
4. Return the first-call result

**Example:**
```python
# After capture and optimization of uncontrolled block:
uncontrolled_key = (tuple(classical_args), tuple(widths), 0)
self._cache[uncontrolled_key] = block

# Derive and cache controlled variant
controlled_block = self._derive_controlled_block(block)
controlled_key = (tuple(classical_args), tuple(widths), 1)
self._cache[controlled_key] = controlled_block
```

**Confidence:** HIGH -- straightforward extension of existing cache logic.

### Pattern 4: Control Qubit Remapping at Replay Time

**What:** At replay time for controlled variants, remap the placeholder control qubit to the actual `_control_bool` qubit.

**When to use:** In `_replay()` when replaying a controlled variant.

**How it works:**
- The controlled variant's gates reference a virtual control qubit index (e.g., `total_virtual_qubits` -- one beyond the uncontrolled variant's virtual qubits)
- The `virtual_to_real` mapping adds an entry mapping this virtual index to the real qubit index of `_control_bool`
- `inject_remapped_gates()` handles the rest

**Example:**
```python
def _replay(self, block, quantum_args):
    virtual_to_real = {}
    vidx = 0
    for qa in quantum_args:
        indices = _get_qint_qubit_indices(qa)
        for real_q in indices:
            virtual_to_real[vidx] = real_q
            vidx += 1

    # Allocate ancillas
    for v in range(vidx, block.total_virtual_qubits):
        if v == block.control_virtual_idx:
            # Map control placeholder to actual control qubit
            control_bool = _get_control_bool()
            virtual_to_real[v] = int(control_bool.qubits[63])
        else:
            virtual_to_real[v] = _allocate_qubit()

    # ... inject and build return value
```

**Confidence:** HIGH -- follows the exact same remapping pattern already used for parameter qubits and ancillas.

### Pattern 5: First Call Inside Controlled Context

**What:** Handle the case where the first call to a compiled function happens inside a `with` block.

**When to use:** When a compiled function is first called inside a `with` block (no uncontrolled variant cached yet).

**How it works:**
- The first call captures the gate sequence
- Because `_controlled = True` during capture, the normal arithmetic operations produce controlled gates (via `cCQ_add`, etc.)
- This captured sequence IS the controlled variant
- To derive the uncontrolled variant, we must also capture an uncontrolled version
- **Decision from CONTEXT.md:** Derive controlled from uncontrolled, not the other way around
- **Implication:** If first called while controlled, we need to temporarily disable the controlled context, capture the uncontrolled variant, then derive the controlled variant

**Critical detail:** During `_capture()`, the function body executes normally. If `_controlled` is `True`, the captured gates already include control qubits from the ambient `_control_bool`. This means:
- We MUST capture the uncontrolled variant first (temporarily set `_controlled = False`)
- Then derive the controlled variant from the uncontrolled optimized sequence
- The function body must execute in uncontrolled mode to get the "base" gate sequence

**Example:**
```python
def _capture_uncontrolled(self, args, kwargs, quantum_args):
    """Capture uncontrolled variant, temporarily disabling controlled context."""
    saved_controlled = _get_controlled()
    saved_control_bool = _get_control_bool()

    _set_controlled(False)
    _set_control_bool(None)
    try:
        block = self._capture(args, kwargs, quantum_args)
    finally:
        _set_controlled(saved_controlled)
        _set_control_bool(saved_control_bool)

    return block
```

**Confidence:** HIGH -- the global state save/restore pattern is well-established (used in `_replay()` for `layer_floor`).

### Anti-Patterns to Avoid

- **Re-capturing the function body for controlled variants:** CONTEXT.md explicitly says "Do NOT re-capture the function body for controlled variants." Derive from the optimized uncontrolled sequence instead. Re-capture would double execution time and might produce different gate sequences if the function has side effects.

- **Multi-control derivation in the compilation system:** Nested `with` blocks AND their control bools into a single qbool before the compiled function sees them. The compilation system never needs to handle more than 1 control qubit. The controlled variant always adds exactly 1 control.

- **Post-hoc control addition on replay:** Do not try to modify replayed gates after injection. The controlled variant must be prepared before replay, stored in the cache, and injected with `inject_remapped_gates()` with the control qubit already in the mapping.

- **Modifying `inject_remapped_gates()` in _core.pyx:** The existing function handles arbitrary `num_controls` correctly. No modification needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Control qubit detection | Custom control tracking | `_get_controlled()` and `_get_control_bool()` from `_core.pyx` | Already tracks global controlled state |
| Multi-control gate support | Custom multi-control logic | `inject_remapped_gates()` with `num_controls > 2` path | Already handles `large_control` allocation for > 2 controls |
| Nested `with` block AND logic | Custom AND implementation | Existing `__enter__` AND logic (`_control_bool &= self`) in `qint.pyx` | Already produces single control qbool |
| Gate remapping | Custom remapping | `inject_remapped_gates()` from `_core.pyx` | Battle-tested qubit remapping |

**Key insight:** The `with` block infrastructure already reduces nested controls to a single qbool. The compilation system only needs to handle "0 controls" vs "1 control" -- never multi-control. This dramatically simplifies the implementation.

## Common Pitfalls

### Pitfall 1: First Call Inside Controlled Context Captures Controlled Gates

**What goes wrong:** If the first call happens inside a `with` block, `_capture()` runs the function body with `_controlled = True`. The captured gates include the ambient control qubit. This is the wrong base for deriving variants.

**Why it happens:** `_capture()` calls the function normally, and all arithmetic operations check `_get_controlled()` during execution. If controlled, they call `cCQ_add` etc., which add control qubits to the gates.

**How to avoid:** Always capture in uncontrolled mode. Before calling `_capture()`, save and temporarily clear the controlled state. Restore it after capture. Then derive the controlled variant from the uncontrolled optimized sequence.

**Warning signs:** Gates captured inside `with` block have `num_controls > 0` when they shouldn't; replaying the "controlled" variant outside a `with` block produces gates with extra controls.

### Pitfall 2: Control Qubit Index Collision with Ancilla Qubits

**What goes wrong:** The placeholder virtual index for the control qubit collides with ancilla virtual indices, causing the control qubit to be mapped to a freshly allocated ancilla qubit instead of the actual `_control_bool` qubit.

**Why it happens:** The `_replay()` method allocates ancillas for virtual indices beyond the parameter qubits. If the control qubit placeholder uses one of these indices without being distinguished, it gets treated as an ancilla.

**How to avoid:** Store the control qubit's virtual index in `CompiledBlock` (e.g., `control_virtual_idx`). In `_replay()`, check each virtual index against this before deciding whether to allocate an ancilla or map to `_control_bool`. Alternatively, use the virtual index `total_virtual_qubits` (one beyond the uncontrolled block's range) as the control placeholder, and set `total_virtual_qubits` of the controlled block to `uncontrolled.total_virtual_qubits + 1`.

**Warning signs:** Controlled gates target wrong qubits; OpenQASM export shows controlled gates with unexpected control qubit indices.

### Pitfall 3: Optimization Changes Invalidating Controlled Derivation

**What goes wrong:** The optimized gate list contains merged/cancelled gates that no longer have straightforward controlled counterparts. For example, a merged rotation `P(0.8)` should become `CP(0.8)`, which is fine. But if future optimization produces synthetic gate types, derivation might fail.

**Why it happens:** The optimization in Phase 49 only does adjacent inverse cancellation and rotation merging. Both operations preserve gate types (X, H, P, etc.) that all have well-defined controlled variants. This pitfall is theoretical for current optimization but important for future phases.

**How to avoid:** The current gate types (X, Y, Z, R, H, Rx, Ry, Rz, P, M) all have controlled variants: CX, CY, CZ, CR, CH, CRx, CRy, CRz, CP, and controlled-M. The derivation (adding 1 to `num_controls`) works uniformly. No gate decomposition is needed for the current gate set.

**Warning signs:** Gates in the controlled variant have unexpected types or missing control qubits.

### Pitfall 4: Cache Key Custom `key` Function Ignores Control State

**What goes wrong:** Users who provide a custom `key` function to `@ql.compile(key=...)` may not include the controlled state, causing uncontrolled and controlled variants to collide in the cache.

**Why it happens:** The custom key function receives the same arguments as the decorated function. It has no awareness of the ambient controlled context.

**How to avoid:** When a custom `key` function is provided, wrap it to append the control count: `cache_key = (self._key_func(*args, **kwargs), control_count)`. This ensures controlled and uncontrolled variants always have separate cache entries.

**Warning signs:** Calling a compiled function inside and outside a `with` block produces the same gates; cache has only one entry when it should have two.

### Pitfall 5: First-Call Result Inside Controlled Context

**What goes wrong:** If the first call is inside a `with` block, the function executes in temporarily-disabled uncontrolled mode (per Pitfall 1 fix). But the caller expects controlled gates in the circuit. After capture, the controlled variant's gates must be injected into the circuit, but the first-call result from the uncontrolled execution is wrong.

**Why it happens:** The first call puts uncontrolled gates into the circuit (since we disabled controlled mode for capture). But the user called this inside a `with` block and expects controlled gates.

**How to avoid:** When the first call happens inside a controlled context:
1. Capture in uncontrolled mode (gates go into circuit as uncontrolled)
2. Derive controlled variant
3. Erase the uncontrolled gates from the circuit (use `_set_layer_floor` to rewind) OR replay the controlled variant over them
4. Return the correct first-call result

**Alternative approach:** Capture normally (in controlled mode) as a fallback -- this IS the "re-capture" fallback mentioned in CONTEXT.md. Then derive the uncontrolled variant by stripping controls. But this is harder.

**Recommended approach:** If the first call happens inside a `with` block, capture in uncontrolled mode, then immediately replay the controlled variant into the circuit. The first-call result comes from the uncontrolled execution (which is correct for the return value -- it's the same computation). The circuit gets the controlled gates via controlled-variant replay.

**Warning signs:** First call inside `with` block produces uncontrolled gates in the circuit.

### Pitfall 6: `_list_of_controls` Not Restored After Capture

**What goes wrong:** If we temporarily set `_controlled = False` and `_control_bool = None` for capture, but the original context had nested `with` blocks with `_list_of_controls` populated, failing to restore `_list_of_controls` could break subsequent operations.

**Why it happens:** The `__enter__` method pushes to `_list_of_controls` for nested `with` blocks.

**How to avoid:** Save and restore `_list_of_controls` along with `_controlled` and `_control_bool` during the temporary uncontrolled capture.

**Warning signs:** Operations after the compiled function call inside nested `with` blocks use wrong control qubits.

## Code Examples

### Deriving Controlled Gate List from Uncontrolled

```python
def _derive_controlled_gates(gates, control_virtual_idx):
    """Add one control qubit to every gate in the list.

    Each gate's num_controls is incremented by 1, and the
    control_virtual_idx is prepended to the controls list.
    """
    controlled = []
    for g in gates:
        cg = dict(g)
        cg['num_controls'] = g['num_controls'] + 1
        cg['controls'] = [control_virtual_idx] + list(g['controls'])
        controlled.append(cg)
    return controlled
```

Source: Derived from `gate_t` structure in `c_backend/include/types.h` (lines 66-75) and `inject_remapped_gates()` in `_core.pyx` (lines 754-776).

### Extended Cache Key with Control Count

```python
def __call__(self, *args, **kwargs):
    quantum_args, classical_args, widths = self._classify_args(args, kwargs)

    is_controlled = _get_controlled()
    control_count = 1 if is_controlled else 0

    if self._key_func:
        cache_key = (self._key_func(*args, **kwargs), control_count)
    else:
        cache_key = (tuple(classical_args), tuple(widths), control_count)

    if cache_key in self._cache:
        self._cache.move_to_end(cache_key)
        return self._replay(self._cache[cache_key], quantum_args)
    else:
        # Cache miss -- ensure both variants exist
        return self._capture_and_cache_both(args, kwargs, quantum_args,
                                             classical_args, widths,
                                             is_controlled, cache_key)
```

Source: Extension of `CompiledFunc.__call__()` in `compile.py` (lines 357-379).

### Creating Controlled CompiledBlock from Uncontrolled

```python
def _derive_controlled_block(self, uncontrolled_block):
    """Create a controlled CompiledBlock from an uncontrolled one."""
    # Control qubit gets the next virtual index after all uncontrolled qubits
    control_virt_idx = uncontrolled_block.total_virtual_qubits

    controlled_gates = _derive_controlled_gates(
        uncontrolled_block.gates, control_virt_idx
    )

    return CompiledBlock(
        gates=controlled_gates,
        total_virtual_qubits=uncontrolled_block.total_virtual_qubits + 1,
        param_qubit_ranges=list(uncontrolled_block.param_qubit_ranges),
        internal_qubit_count=uncontrolled_block.internal_qubit_count,
        return_qubit_range=uncontrolled_block.return_qubit_range,
        return_is_param_index=uncontrolled_block.return_is_param_index,
        original_gate_count=uncontrolled_block.original_gate_count,
    )
    # Store control qubit virtual index for replay remapping
    controlled_block.control_virtual_idx = control_virt_idx
```

Source: Derived from `CompiledBlock` class in `compile.py` (lines 177-226).

### Replay with Control Qubit Remapping

```python
def _replay(self, block, quantum_args):
    virtual_to_real = {}
    vidx = 0
    for qa in quantum_args:
        indices = _get_qint_qubit_indices(qa)
        for real_q in indices:
            virtual_to_real[vidx] = real_q
            vidx += 1

    # Allocate ancillas for internal qubits
    for v in range(vidx, block.total_virtual_qubits):
        if hasattr(block, 'control_virtual_idx') and v == block.control_virtual_idx:
            # Map to actual control qubit from _control_bool
            control_bool = _get_control_bool()
            virtual_to_real[v] = int(control_bool.qubits[63])
        else:
            virtual_to_real[v] = _allocate_qubit()

    # ... layer_floor save, inject_remapped_gates, build return value
```

Source: Extension of `CompiledFunc._replay()` in `compile.py` (lines 485-519).

### Temporary Uncontrolled Capture

```python
def _capture_uncontrolled(self, args, kwargs, quantum_args):
    """Capture gates in uncontrolled mode, saving/restoring controlled context."""
    saved_controlled = _get_controlled()
    saved_control_bool = _get_control_bool()
    saved_list_of_controls = list(_get_list_of_controls())

    _set_controlled(False)
    _set_control_bool(None)

    try:
        block = self._capture(args, kwargs, quantum_args)
    finally:
        _set_controlled(saved_controlled)
        _set_control_bool(saved_control_bool)
        _set_list_of_controls(saved_list_of_controls)

    return block
```

Source: Pattern from `_replay()` layer_floor save/restore in `compile.py` (lines 501-509); controlled context accessors from `_core.pyx` (lines 88-113).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Compiled functions ignore controlled context | Separate controlled/uncontrolled cached variants | Phase 50 | `@ql.compile` works inside `with` blocks |
| Cache key: (classical_args, widths) | Cache key: (classical_args, widths, control_count) | Phase 50 | Prevents controlled/uncontrolled cache collision |
| No controlled gate derivation | Derive controlled variant from uncontrolled optimized sequence | Phase 50 | Single capture, two cached variants |

## Open Questions

1. **Measurement gates in controlled context**
   - What we know: Gate type M (Measurement) exists in the `Standardgate_t` enum. Adding a control to a measurement gate is physically meaningful (controlled-measurement) but unusual.
   - What's unclear: Whether `@ql.compile` decorated functions ever contain measurement gates. The current gate types (X, Y, Z, R, H, Rx, Ry, Rz, P) all have well-defined controlled variants.
   - Recommendation: Add control to measurement gates just like any other gate (increment `num_controls`). If this causes issues, the silent re-capture fallback will handle it. LOW risk since compiled functions typically perform unitary operations, not measurements.
   - Confidence: MEDIUM

2. **First call inside `with` block: circuit correctness**
   - What we know: If we capture in uncontrolled mode (temporarily disabling `_controlled`), the uncontrolled gates end up in the circuit. But the user expects controlled gates.
   - What's unclear: Whether we can/should erase the uncontrolled gates and replay the controlled variant, or whether we should let the first call proceed normally in controlled mode and treat it as the re-capture fallback.
   - Recommendation: The simplest correct approach is: (a) always capture uncontrolled, (b) if the call was controlled, erase the captured gates from the circuit by tracking start/end layer, then replay the controlled variant. The `_set_layer_floor()` mechanism and `extract_gate_range()` / layer tracking provide the tools to do this.
   - Alternative: If first call is inside `with`, capture in controlled mode (let the function run naturally producing controlled gates). Store this as the controlled variant. Derive the uncontrolled variant by stripping the control qubit from each gate. This avoids the erase-and-replay complexity but requires "de-controlling" which is the reverse of the normal derivation direction.
   - Confidence: MEDIUM -- both approaches are viable; implementation will determine which is simpler.

3. **Re-capture fallback trigger conditions**
   - What we know: CONTEXT.md says "If derivation fails for any gate, silently fall back to re-capture as a fallback."
   - What's unclear: What specific conditions would cause derivation to fail? With the current gate set (X, Y, Z, R, H, Rx, Ry, Rz, P, M), all gates can have controls added trivially. The fallback may never trigger with current gate types.
   - Recommendation: Implement the fallback by wrapping `_derive_controlled_gates()` in a try/except. If any exception occurs, fall back to re-capturing in controlled mode. For now, the fallback is defensive -- it guards against future gate types that might not support adding controls.
   - Confidence: HIGH -- the fallback is simple to implement and provides safety.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/compile.py` -- CompiledFunc, CompiledBlock, _capture, _replay, cache key construction (read in full, 606 lines)
- `src/quantum_language/_core.pyx` -- `_get_controlled()`, `_get_control_bool()`, `inject_remapped_gates()`, `extract_gate_range()`, global state accessors (read in full, 853 lines)
- `src/quantum_language/qint.pyx` -- `__enter__()`, `__exit__()` context manager protocol, control state management (read lines 574-673)
- `src/quantum_language/qint_preprocessed.pyx` -- Arithmetic dispatch to controlled variants (`cCQ_add`, `cQQ_add`), control qubit placement in `qubit_array` (read lines 705-763)
- `src/quantum_language/qbool.pyx` -- qbool class, 1-bit qint subclass (read in full, 89 lines)
- `c_backend/include/types.h` -- `gate_t` structure with `Control[MAXCONTROLS]`, `large_control`, `NumControls` (read in full, 84 lines)
- `c_backend/include/gate.h` -- Gate creation functions showing controlled variants (cx, ccx, mcx, cp, cz, cy) (read in full, 52 lines)
- `tests/test_compile.py` -- All Phase 48/49 compile tests including uncomputation integration (read in full, 983 lines)
- `tests/test_conditionals.py` -- `with qbool:` block tests with controlled arithmetic (read in full, 314 lines)

### Secondary (MEDIUM confidence)
- `.planning/phases/49-optimization-uncomputation/49-RESEARCH.md` -- Phase 49 research documenting optimization and uncomputation patterns (read in full)
- `.planning/phases/50-controlled-context/50-CONTEXT.md` -- User decisions for this phase (read in full)
- `.planning/STATE.md` -- Project state and prior decisions (read in full)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components exist in codebase, verified by reading source
- Architecture: HIGH -- patterns derived from existing code (controlled context mechanism in qint.pyx, cache system in compile.py, gate dict format in _core.pyx)
- Pitfalls: HIGH -- identified from actual code flow analysis of capture inside controlled context, cache key collision, and control qubit remapping
- Gate derivation: HIGH -- gate_t structure explicitly supports variable num_controls; inject_remapped_gates handles arbitrary controls
- First-call-inside-with-block handling: MEDIUM -- two viable approaches identified, implementation will determine preferred approach

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (stable codebase, internal project)
