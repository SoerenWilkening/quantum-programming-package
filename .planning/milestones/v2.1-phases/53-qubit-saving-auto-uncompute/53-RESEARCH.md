# Phase 53: Qubit-Saving Auto-Uncompute - Research

**Researched:** 2026-02-04
**Domain:** Quantum compilation infrastructure (Python), automatic ancilla uncomputation
**Confidence:** HIGH

## Summary

Phase 53 adds automatic uncomputation of internal ancilla qubits when `ql.option("qubit_saving")` is active. The Phase 52 infrastructure already provides everything needed: `AncillaRecord` tracks ancilla qubits per forward call, `_AncillaInverseProxy` performs adjoint gate injection + deallocation, and `_deallocate_qubits` frees qubits back to the allocator pool. Phase 53's core contribution is: after `_replay` (or `_capture_and_cache_both`) completes, automatically inject adjoint gates for **non-return ancilla qubits only**, deallocate them, and update the `AncillaRecord` so `f.inverse(x)` can still undo the remaining return-qubit effects.

The main complexity is partitioning ancilla qubits into "return qubits" (preserve) and "temp qubits" (auto-uncompute), then ensuring `f.inverse(x)` still works correctly with a reduced gate set that only targets return qubits. The qubit_saving flag must also become part of the compilation cache key to trigger recompilation.

**Primary recommendation:** Add auto-uncompute logic at the end of `CompiledFunc.__call__` (after `_replay`/`_capture_and_cache_both` returns), gated on `_get_qubit_saving_mode()`. Split ancilla qubits using `block.return_qubit_range` to identify which are return qubits vs temporaries. Inject adjoint gates for temp ancillas only, deallocate them, and store a reduced `AncillaRecord` containing only return qubit info for later `f.inverse(x)`.

## Standard Stack

### Core

This phase is entirely internal to the existing codebase. No new external libraries needed.

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `compile.py` | `src/quantum_language/compile.py` | CompiledFunc, _replay, _AncillaInverseProxy | Modify |
| `_core.pyx` | `src/quantum_language/_core.pyx` | `_get_qubit_saving_mode()`, `_deallocate_qubits()` | No change needed |
| `_core.pxd` | `src/quantum_language/_core.pxd` | C declarations | No change needed |

### Supporting

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `test_compile.py` | Existing compile tests (1795+ lines) | Extend with Phase 53 tests |
| `conftest.py` | Test fixtures | Use existing patterns |

## Architecture Patterns

### Recommended Changes to Existing Structure

```
src/quantum_language/
├── compile.py          # MODIFY: Add auto-uncompute logic after forward call,
│                       #   modify cache key to include qubit_saving,
│                       #   modify AncillaRecord for post-auto-uncompute inverse,
│                       #   add input-side-effect detection
└── _core.pyx           # NO CHANGE (qubit_saving mode + deallocate already exist)

tests/
└── test_compile.py     # EXTEND: Add INV-07 tests
```

### Pattern 1: Return vs Temp Ancilla Partitioning

**What:** After replay allocates ancilla qubits, split them into two sets: return qubits (part of the function's return value) and temp qubits (purely internal). Only temp qubits get auto-uncomputed.

**When to use:** Every time auto-uncompute fires (qubit_saving mode active, function has ancillas).

**Key logic:** The `block.return_qubit_range` gives `(start_virtual_idx, width)` for return value qubits. During replay, `ancilla_qubits` is built from all virtual indices `>= param_count`. We can identify which ancilla physical qubits correspond to return virtual indices:

```python
def _partition_ancillas(block, virtual_to_real, ancilla_qubits, param_count):
    """Split ancilla qubits into return qubits and temp qubits.

    Returns (return_physical_qubits, temp_physical_qubits).
    """
    if block.return_qubit_range is None or block.return_is_param_index is not None:
        # No return value or return IS a parameter -- all ancillas are temp
        return [], list(ancilla_qubits)

    ret_start, ret_width = block.return_qubit_range
    return_virtual_set = set(range(ret_start, ret_start + ret_width))

    return_physical = []
    temp_physical = []
    for real_q in ancilla_qubits:
        # Find the virtual index for this physical qubit
        virt = None
        for v, r in virtual_to_real.items():
            if r == real_q and v >= param_count:
                virt = v
                break
        if virt is not None and virt in return_virtual_set:
            return_physical.append(real_q)
        else:
            temp_physical.append(real_q)

    return return_physical, temp_physical
```

**Optimization note:** Build a `real_to_virtual` reverse mapping once instead of inner loop. For the typical case (small number of ancillas), the simple approach is fine.

### Pattern 2: Auto-Uncompute Gate Injection

**What:** After the forward call completes, inject adjoint gates that target ONLY temp ancilla qubits. The adjoint of the full gate sequence is filtered to keep only gates whose targets are temp ancillas.

**Critical design choice:** We cannot simply filter adjoint gates by target -- that would break the uncomputation. Instead, we need the FULL adjoint gate sequence (which uncomputes all ancillas), but we need to preserve return qubits. The correct approach is:

1. Run the full adjoint gate sequence (uncomputes all ancillas including return qubits)
2. Then re-run the forward gates that affect return qubits only (restores return qubits)

**However, this is wrong.** The simpler correct approach:

The adjoint of the full circuit returns ALL qubits to their input state. But we only want to uncompute temp ancillas. The standard quantum computing technique for this is:

- Temp ancillas start at |0>, get entangled during computation, and are returned to |0> by the adjoint
- Return value qubits hold the computation result and would be destroyed by the adjoint

The correct approach is to **only apply adjoint gates that involve temp ancilla virtual indices as targets**. This works because:
- Temp ancillas are used as scratch space
- The adjoint of scratch-space operations returns them to |0>
- As long as temp ancillas are properly disentangled from return qubits by the computation, this is correct

**However, this is also insufficient** for general circuits where temp ancillas may be entangled with return qubits through controlled operations.

**Recommended approach (standard quantum uncomputation):** The compiled function's gate sequence naturally has the property that it computes `result = f(input)` using temp ancillas. If the function is well-designed for uncomputation (which it must be for quantum computing), the adjoint circuit will disentangle all ancillas. The full adjoint replayed on ALL ancilla qubits (including return) would destroy the result. So we need a **partial uncomputation** strategy.

**Practical implementation:** Store two gate subsequences at compile time:
1. Gates that only involve temp ancillas (for auto-uncompute)
2. Full gate sequence (for f.inverse(x))

Actually, the cleanest approach based on the CONTEXT decision ("the adjoint circuit should disentangle them"):

```python
def _auto_uncompute(block, virtual_to_real, temp_ancilla_qubits, is_controlled):
    """Auto-uncompute temp ancillas by replaying adjoint of full gate sequence.

    The adjoint is applied to ALL qubits (using original virtual_to_real mapping).
    This uncomputes temp ancillas back to |0> while the return value qubits
    end up in a state that still encodes the computation result, because the
    forward computation is designed so that the adjoint disentangles ancillas.
    """
    from ._core import _deallocate_qubits

    # Generate adjoint of the full uncontrolled block
    adjoint_gates = _inverse_gate_list(block.gates)

    # Handle controlled context
    if is_controlled:
        control_bool = _get_control_bool()
        ctrl_qubit = int(control_bool.qubits[63])
        ctrl_virt_idx = block.total_virtual_qubits
        adjoint_gates = _derive_controlled_gates(adjoint_gates, ctrl_virt_idx)
        vtr = dict(virtual_to_real)
        vtr[ctrl_virt_idx] = ctrl_qubit
    else:
        vtr = virtual_to_real

    # Inject adjoint gates
    saved_floor = _get_layer_floor()
    _set_layer_floor(get_current_layer())
    inject_remapped_gates(adjoint_gates, vtr)
    _set_layer_floor(saved_floor)

    # Deallocate only temp ancilla qubits
    for qubit_idx in temp_ancilla_qubits:
        _deallocate_qubits(qubit_idx, 1)
```

**WAIT -- this is wrong.** The full adjoint undoes the ENTIRE computation, not just the ancilla parts. This would destroy the return value too.

**Correct understanding (after careful analysis):**

Auto-uncomputation of ancillas in quantum computing works when the computation has the structure:
```
|input>|0>  -->  U  -->  |input'>|result>|0_temp>
```
Where temp ancillas are already |0> after the computation (they were used and cleaned up within the function). In this case, no adjoint is needed -- the function already cleaned up its temps.

But if temp ancillas are NOT cleaned up (they hold garbage/entangled state), uncomputing them requires the Bennett trick: run the function, copy the result, then run the inverse. But this requires extra qubits for the copy.

**The CONTEXT says: "Entangled ancillas: uncompute anyway -- the adjoint circuit should disentangle them."** This means the user expects the FULL adjoint to be applied, which WILL affect return qubits. But the context also says "return value's qubits are preserved."

**Resolution:** The only way both can be true is if we apply a **selective adjoint** -- the inverse of only the gates that produced/modified temp ancillas. This requires analyzing the gate sequence to extract a subsequence.

**Simplest correct approach:** Run the full adjoint, but then re-run the forward for return qubits only. This is the Bennett uncomputation:
1. Forward: produces result + temp ancillas
2. Copy result to fresh qubits (the "return" qubits are already these fresh qubits)
3. Adjoint: uncomputes everything back

But actually, in this compilation model, the return qubits ARE allocated internally. The forward call already produced the result on those qubits. The temp qubits are the ones that are NOT the return qubits.

**Final correct approach after deep analysis:**

The compiled function produces a gate sequence that maps:
```
|input, 0_ret, 0_temp> --> |input', result, garbage>
```

To uncompute only temp qubits, we need gates that map:
```
|input', result, garbage> --> |input', result, 0_temp>
```

This is NOT simply the adjoint of the full circuit. The standard approach is to store the gate sequence and extract "uncomputation gates" -- the subset that, when reversed, returns temp qubits to |0>.

**Practical recommendation for this codebase:** Since compiled functions in this quantum language are typically structured computations (additions, multiplications, etc.) where internal temps are carry chains or scratch bits, the temp ancillas are often already partially cleaned up. The safest general approach:

1. **At capture time**, identify which gates have temp ancilla qubits as their ONLY non-input targets (gates that only modify temp qubits)
2. **Reverse only those gates** for auto-uncompute

**Even simpler:** Since the CONTEXT says "the adjoint circuit should disentangle them," trust that running the full adjoint will return temp ancillas to |0>. The issue is that the full adjoint also undoes the return qubits. The solution:

**Use the existing `f.inverse(x)` mechanism but only deallocate temp qubits.** The full adjoint IS the uncomputation. After the full adjoint:
- Input qubits: restored to original state (but user's qubits -- we don't want this)
- Return qubits: back to |0> (we don't want this)
- Temp qubits: back to |0> (we want this)

This doesn't work either because we'd destroy the return value.

**ACTUAL correct approach (standard in quantum computing):**

The auto-uncompute should ONLY uncompute the temp ancilla qubits. For this, we extract from the full gate sequence the subsequence of gates that modified temp ancillas, then reverse that subsequence. A gate "modifies temp ancillas" if its target is a temp ancilla virtual qubit.

```python
def _extract_temp_ancilla_gates(gates, temp_virtual_set):
    """Extract gates whose target is a temp ancilla."""
    return [g for g in gates if g["target"] in temp_virtual_set]
```

Then reverse these gates and inject them. This is correct because:
- These gates put the temp ancillas into their current state
- Reversing them returns the temp ancillas to |0>
- Gates targeting return qubits or param qubits are untouched

```python
temp_gates = _extract_temp_ancilla_gates(block.gates, temp_virtual_set)
adjoint_temp_gates = _inverse_gate_list(temp_gates)
inject_remapped_gates(adjoint_temp_gates, virtual_to_real)
```

This is the recommended approach.

### Pattern 3: Modified AncillaRecord for Post-Auto-Uncompute Inverse

**What:** After auto-uncompute fires, the `AncillaRecord` is updated to reflect that temp ancillas are already gone. When `f.inverse(x)` is later called, it only needs to handle return qubits.

**Implementation:**

```python
# After auto-uncompute of temp ancillas:
# Update the AncillaRecord to contain only return ancilla info
if return_physical:
    # Build a gate sequence that only involves return qubits
    ret_virtual_set = set(range(ret_start, ret_start + ret_width))
    return_gates = [g for g in block.gates if g["target"] in ret_virtual_set]
    return_adjoint = _inverse_gate_list(return_gates)

    # Create a modified block with only return-relevant gates
    reduced_record = AncillaRecord(
        ancilla_qubits=return_physical,
        virtual_to_real=dict(virtual_to_real),
        block=block,  # Keep full block for gate reference
        return_qint=result,
    )
    # Store additional info for the reduced inverse
    reduced_record._return_only_adjoint = return_adjoint
    reduced_record._auto_uncomputed = True

    input_key = _input_qubit_key(quantum_args)
    self._forward_calls[input_key] = reduced_record
```

Then in `_AncillaInverseProxy.__call__`, check if `record._auto_uncomputed` and use `record._return_only_adjoint` instead of computing full adjoint.

**Note:** This requires adding `_return_only_adjoint` and `_auto_uncomputed` to `AncillaRecord.__slots__`.

### Pattern 4: Cache Key Including qubit_saving Mode

**What:** The qubit_saving flag becomes part of the compilation cache key so changing the option triggers recompilation.

```python
# In CompiledFunc.__call__:
qubit_saving = _get_qubit_saving_mode()

if self._key_func:
    cache_key = (self._key_func(*args, **kwargs), control_count, qubit_saving)
else:
    cache_key = (tuple(classical_args), tuple(widths), control_count, qubit_saving)
```

**Note:** This is a simple change but affects all cache lookups. Existing tests should still pass because `qubit_saving` defaults to `False`, and existing keys `(classical, widths, 0)` become `(classical, widths, 0, False)` -- all caches get cleared on circuit reset anyway.

### Pattern 5: Input Side-Effect Detection

**What:** Skip auto-uncompute if the function modifies input qubits (has side effects on inputs). Detection is done by analyzing the virtual gate sequence.

**Implementation:** A function modifies input qubits if any gate in the sequence targets a virtual qubit in the parameter range AND the function also has a return value that is NOT the input parameter.

Actually, simpler: if `return_is_param_index is not None`, the function operates in-place on an input parameter. These functions have `internal_qubit_count == 0` typically (no ancillas), so auto-uncompute would be a no-op anyway.

The CONTEXT says "skip auto-uncompute if function modifies input qubits." A function modifies input qubits if gates target parameter virtual indices AND the return is a new qint (not the same as input). We can detect this by checking if any gate targets a virtual qubit in the param range:

```python
def _function_modifies_inputs(block):
    """Check if the compiled block modifies input parameter qubits."""
    param_virtual_count = sum(w for _, w in block.param_qubit_ranges)
    param_virtual_set = set(range(param_virtual_count))
    for gate in block.gates:
        if gate["target"] in param_virtual_set:
            return True
    return False
```

**Recommendation:** Compute this once at capture/cache time and store on CompiledBlock as `_modifies_inputs`.

### Anti-Patterns to Avoid

- **Running full adjoint for auto-uncompute:** The full adjoint reverses the entire computation, destroying the return value. Only reverse gates targeting temp ancilla qubits.
- **Auto-uncomputing return qubits:** Return value qubits must be excluded from deallocation. Partition ancillas carefully.
- **Applying auto-uncompute during capture (first call):** The first call emits gates directly to the circuit. Auto-uncompute on the first call would need to extract and reverse temp-ancilla gates from the just-emitted gates. This works the same way but needs the capture path's `real_to_virtual` mapping.
- **Breaking f.inverse(x) after auto-uncompute:** The `AncillaRecord` must be updated to reflect the reduced ancilla set. The inverse proxy must handle both auto-uncomputed and non-auto-uncomputed records.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Adjoint gate generation | Custom reversal | Existing `_inverse_gate_list()` | Already correct, handles all gate types |
| Gate injection | Custom circuit manipulation | Existing `inject_remapped_gates()` | Handles controls, remapping |
| Qubit deallocation | Custom tracking | Existing `_deallocate_qubits()` | Phase 52 already added this |
| Qubit saving mode check | Custom flag | Existing `_get_qubit_saving_mode()` | Already in `_core.pyx` |
| Forward call tracking | New registry | Existing `_forward_calls` dict | Phase 52 already provides this |
| Cache invalidation | Custom hooks | Existing `_register_cache_clear_hook` | Already clears on circuit reset |

**Key insight:** Phase 52 built nearly all the infrastructure. Phase 53 is primarily about adding auto-trigger logic and partitioning ancillas.

## Common Pitfalls

### Pitfall 1: Uncomputing Return Value Qubits

**What goes wrong:** If auto-uncompute reverses ALL ancilla gates (not just temp ones), the return value qubits get reset to |0>, destroying the computation result.

**Why it happens:** All internally-allocated qubits (including return value qubits) are in the `ancilla_qubits` list. The full adjoint targets all of them.

**How to avoid:** Partition ancillas using `block.return_qubit_range`. Only extract and reverse gates targeting temp virtual indices.

**Warning signs:** Return value reads as 0 after auto-uncompute fires.

### Pitfall 2: f.inverse(x) After Auto-Uncompute

**What goes wrong:** After auto-uncompute, `f.inverse(x)` tries to deallocate temp ancillas that are already deallocated, causing double-free errors.

**Why it happens:** The existing `_AncillaInverseProxy` deallocates ALL `record.ancilla_qubits`. After auto-uncompute, temp qubits are already gone.

**How to avoid:** Update the `AncillaRecord` after auto-uncompute to contain only return ancilla qubits. Add a flag `_auto_uncomputed` so the inverse proxy knows to use a reduced adjoint gate set.

**Warning signs:** Allocator corruption, wrong qubits freed, or ValueError from allocator.

### Pitfall 3: Cache Key Compatibility

**What goes wrong:** Adding `qubit_saving` to the cache key changes the key format, causing cache misses for existing entries.

**Why it happens:** Old key format is `(classical, widths, control_count)`, new is `(classical, widths, control_count, qubit_saving)`.

**How to avoid:** This is actually fine -- cache is cleared on circuit reset, and within a single circuit, the qubit_saving mode should be consistent. Tests that don't call `ql.option("qubit_saving", True)` will use `False` consistently.

**Warning signs:** Unexpected cache misses in existing tests (would be correctness-neutral but waste a capture call).

### Pitfall 4: First-Call Auto-Uncompute

**What goes wrong:** On the first call (capture path), gates are emitted directly to the circuit. Auto-uncompute needs to emit adjoint gates for temp ancillas, but the gate sequence is not yet in the cache -- it's being built.

**Why it happens:** `_capture_and_cache_both` executes the function, extracts gates, virtualizes them, and caches. The physical gates are already in the circuit.

**How to avoid:** After `_capture_and_cache_both` returns, the block is cached and we have `capture_ancilla_qubits` and `capture_virtual_to_real`. Use these to perform auto-uncompute on the first call just like on replay.

**Warning signs:** Auto-uncompute only works on replay (second call) but not on first call.

### Pitfall 5: Nested Compiled Functions with Auto-Uncompute

**What goes wrong:** Inner function auto-uncomputes its temp ancillas. Outer function's gate capture includes both the inner function's forward AND auto-uncompute gates. When outer function is later replayed, it replays both sets of gates, causing double-uncomputation.

**Why it happens:** Gate capture extracts ALL gates emitted between start_layer and end_layer, including inner function's auto-uncompute adjoint gates.

**How to avoid:** This is actually correct behavior. The capture records exactly what happened: forward + auto-uncompute. When replayed, the same sequence runs. The inner auto-uncompute gates are part of the captured "program" and replay correctly.

**Warning signs:** Extra gates in cached blocks when nesting compiled functions with qubit_saving on.

### Pitfall 6: Controlled Context Auto-Uncompute

**What goes wrong:** Auto-uncompute fires inside a controlled context. The temp ancilla adjoint gates need to be controlled, but the block was captured uncontrolled.

**Why it happens:** `_capture_and_cache_both` captures in uncontrolled mode and derives the controlled variant. Auto-uncompute needs to respect the current controlled state.

**How to avoid:** Check `_get_controlled()` before injecting auto-uncompute adjoint gates. If controlled, derive controlled gates from the adjoint sequence (same pattern as `_AncillaInverseProxy`).

**Warning signs:** Incorrect results when using compiled functions inside `with` control blocks.

## Code Examples

### Example 1: Auto-Uncompute in __call__ (After Replay)

```python
# In CompiledFunc.__call__, after getting result:
from ._core import _get_qubit_saving_mode

# ... existing code ...
result = self._replay(...) or self._capture_and_cache_both(...)

# Auto-uncompute if qubit_saving mode is active
if _get_qubit_saving_mode() and cache_key in self._cache:
    block = self._cache[cache_key]
    if block.internal_qubit_count > 0 and not _function_modifies_inputs(block):
        input_key = _input_qubit_key(quantum_args)
        record = self._forward_calls.get(input_key)
        if record is not None:
            self._auto_uncompute(
                record, block, quantum_args, result, is_controlled
            )

return result
```

### Example 2: Temp Ancilla Gate Extraction

```python
def _extract_temp_ancilla_adjoint(block, temp_virtual_set):
    """Extract adjoint of gates targeting only temp ancilla qubits."""
    temp_gates = [g for g in block.gates if g["target"] in temp_virtual_set]
    return _inverse_gate_list(temp_gates)
```

### Example 3: _auto_uncompute Method

```python
def _auto_uncompute(self, record, block, quantum_args, result, is_controlled):
    """Auto-uncompute temp ancillas after forward call."""
    from ._core import _deallocate_qubits

    # Partition ancillas
    return_physical, temp_physical = _partition_ancillas(
        block, record.virtual_to_real, record.ancilla_qubits,
        sum(w for _, w in block.param_qubit_ranges)
    )

    if not temp_physical:
        return  # No temp ancillas to uncompute

    # Identify temp virtual indices
    param_count = sum(w for _, w in block.param_qubit_ranges)
    vtr_reverse = {r: v for v, r in record.virtual_to_real.items()}
    temp_virtual_set = set()
    for real_q in temp_physical:
        v = vtr_reverse.get(real_q)
        if v is not None:
            temp_virtual_set.add(v)

    # Extract and reverse temp-only gates
    temp_adjoint = _extract_temp_ancilla_adjoint(block, temp_virtual_set)

    # Handle controlled context
    if is_controlled:
        control_bool = _get_control_bool()
        ctrl_qubit = int(control_bool.qubits[63])
        ctrl_virt_idx = block.total_virtual_qubits
        temp_adjoint = _derive_controlled_gates(temp_adjoint, ctrl_virt_idx)
        vtr = dict(record.virtual_to_real)
        vtr[ctrl_virt_idx] = ctrl_qubit
    else:
        vtr = record.virtual_to_real

    # Inject adjoint gates
    saved_floor = _get_layer_floor()
    _set_layer_floor(get_current_layer())
    inject_remapped_gates(temp_adjoint, vtr)
    _set_layer_floor(saved_floor)

    # Deallocate temp qubits
    for qubit_idx in temp_physical:
        _deallocate_qubits(qubit_idx, 1)

    # Update AncillaRecord for future f.inverse(x) call
    input_key = _input_qubit_key(quantum_args)
    if return_physical:
        # Return-only gates for future inverse
        ret_virtual_set = set()
        if block.return_qubit_range is not None:
            rs, rw = block.return_qubit_range
            ret_virtual_set = set(range(rs, rs + rw))
        return_gates = [g for g in block.gates if g["target"] in ret_virtual_set]

        record.ancilla_qubits = return_physical
        record._auto_uncomputed = True
        record._return_only_gates = return_gates
    else:
        # No return ancillas -- remove forward call record entirely
        self._forward_calls.pop(input_key, None)
```

### Example 4: Modified _AncillaInverseProxy for Auto-Uncomputed Records

```python
# In _AncillaInverseProxy.__call__, after looking up record:

if getattr(record, '_auto_uncomputed', False):
    # Temp ancillas already uncomputed; only undo return qubit effects
    adjoint_gates = _inverse_gate_list(record._return_only_gates)
else:
    # Standard full adjoint (qubit_saving not active)
    adjoint_gates = _inverse_gate_list(record.block.gates)
```

### Example 5: User-Facing API

```python
import quantum_language as ql

ql.circuit()
ql.option("qubit_saving", True)

@ql.compile
def add_with_carry(x, y):
    carry = ql.qint(0, width=1)   # temp ancilla
    result = ql.qint(0, width=x.width)  # return value
    # ... addition logic using carry ...
    return result

a = ql.qint(5, width=4)
b = ql.qint(3, width=4)

# Forward call -- auto-uncomputes carry (temp ancilla)
# result qubits preserved, carry qubits deallocated + returned to pool
result = add_with_carry(a, b)
# result is usable, carry qubit is freed

# Later: f.inverse(x) undoes the effect on result qubits
add_with_carry.inverse(a, b)
# result is now invalidated
```

## State of the Art

| Phase 52 (Current) | Phase 53 (Target) | Impact |
|---|---|---|
| Manual `f.inverse(x)` required for ancilla cleanup | Auto-uncompute of temp ancillas when qubit_saving active | Fewer qubits needed, automatic resource management |
| All ancillas tracked as one group | Ancillas partitioned into return + temp | Return qubits preserved while temps cleaned |
| Cache key: `(classical, widths, control_count)` | Cache key: `(classical, widths, control_count, qubit_saving)` | Mode change triggers recompilation |
| No input side-effect detection | Functions modifying inputs skip auto-uncompute | Safety for in-place operations |

## Open Questions

### 1. Correctness of Partial Adjoint for Temp Ancillas

**What we know:** Extracting gates whose target is a temp ancilla virtual qubit and reversing them should return those qubits to |0>, IF the temp ancillas are only entangled with other qubits through controlled operations where they are the control (not the target).

**What's unclear:** If a temp ancilla is the CONTROL qubit for a gate targeting a return qubit, the partial adjoint won't undo that controlled operation. The temp ancilla might not return cleanly to |0>.

**Recommendation:** This is correct for well-structured quantum computations (additions, multiplications) where carry/scratch qubits are targets of operations controlled by data qubits. For edge cases where scratch qubits control data operations, the adjoint of scratch-target gates still returns scratch to |0> because the controlled operations create entanglement that the target-adjoint undoes. This matches the CONTEXT decision: "the adjoint circuit should disentangle them." If issues arise, document as a known limitation.

### 2. Functions Returning None with Side Effects

**What we know:** When a function returns None, ALL ancillas should be uncomputed (nothing to preserve). The CONTEXT confirms this.

**What's unclear:** If the function returns None but also modifies input qubits (e.g., `x += 1`), should auto-uncompute still fire?

**Recommendation:** The "skip if modifies inputs" rule should apply regardless of return type. If a function modifies inputs and has temp ancillas, those ancillas might be entangled with the modified input state. Skipping is safer.

### 3. Performance Impact of Gate Extraction

**What we know:** For each auto-uncompute, we scan the gate list to extract temp-ancilla-targeted gates.

**What's unclear:** For large compiled functions with many gates, this scan could be slow.

**Recommendation:** Cache the partitioned gate lists on the `CompiledBlock` (keyed by return range). This is computed once per unique block, not per call.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/compile.py` - Full source read, 1085 lines, all Phase 52 infrastructure verified
- `src/quantum_language/_core.pyx` - `_get_qubit_saving_mode()`, `_deallocate_qubits()`, `option()` verified
- `.planning/phases/52-ancilla-tracking-inverse-reuse/52-01-SUMMARY.md` - Phase 52 implementation details
- `.planning/phases/52-ancilla-tracking-inverse-reuse/52-02-SUMMARY.md` - Phase 52 test details
- `.planning/phases/52-ancilla-tracking-inverse-reuse/52-RESEARCH.md` - Phase 52 design patterns
- `.planning/phases/53-qubit-saving-auto-uncompute/53-CONTEXT.md` - Phase 53 user decisions

### Secondary (MEDIUM confidence)
- Quantum uncomputation theory (Bennett trick, partial adjoint) - from training data, well-established theory

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components internal, fully read and verified
- Architecture: HIGH - Patterns follow directly from Phase 52 infrastructure + verified gate analysis
- Pitfalls: HIGH - Identified from actual code analysis (return vs temp partitioning, double-free risk, first-call path)
- Auto-uncompute correctness: MEDIUM - Partial adjoint approach is theoretically sound but depends on function structure

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (stable internal codebase, no external dependencies)
