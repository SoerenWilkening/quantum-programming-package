# Phase 49: Optimization & Uncomputation - Research

**Researched:** 2026-02-04
**Domain:** Quantum circuit optimization and compiled function uncomputation integration
**Confidence:** HIGH

## Summary

This phase adds two capabilities to the `@ql.compile` decorator system (Phase 48): (1) optimizing captured gate sequences before caching, and (2) integrating compiled function outputs with the existing automatic uncomputation system so that qints returned from compiled functions can be correctly uncomputed when they go out of scope.

The codebase already has all the infrastructure needed. The C backend provides `circuit_optimize()` (in `circuit_optimizer.c`) which copies a circuit through `add_gate()` to get inverse cancellation for free. The Python layer has `extract_gate_range()`, `inject_remapped_gates()`, and `reverse_instruction_range()`/`reverse_circuit_range()` for gate manipulation. The uncomputation system in `qint.pyx` tracks `_start_layer`, `_end_layer`, and `operation_type` on each qint, using `reverse_circuit_range()` in `_do_uncompute()` to append adjoint gates. The `CompiledFunc`/`CompiledBlock` classes in `compile.py` already handle capture, caching, and replay.

**Primary recommendation:** Implement optimization as a Python-level gate list transformation (operating on the list-of-dicts format used by `CompiledBlock.gates`), not by round-tripping through a temporary C `circuit_t`. For uncomputation, set `_start_layer`/`_end_layer`/`operation_type` on the qint returned from `_replay()` so the existing `_do_uncompute()` mechanism works unchanged.

## Standard Stack

### Core

This phase uses only existing codebase infrastructure -- no external libraries needed.

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `compile.py` | `src/quantum_language/compile.py` | CompiledFunc/CompiledBlock, capture-replay | Phase 48 output, direct modification target |
| `_core.pyx` | `src/quantum_language/_core.pyx` | `extract_gate_range`, `inject_remapped_gates`, `reverse_instruction_range` | Existing gate manipulation primitives |
| `circuit_optimizer.c` | `c_backend/src/circuit_optimizer.c` | `circuit_optimize()`, `gates_are_inverse()` | Existing C-level optimization |
| `qint.pyx` | `src/quantum_language/qint.pyx` | `_do_uncompute()`, `_start_layer`/`_end_layer` tracking | Existing uncomputation system |
| `optimizer.c` | `c_backend/src/optimizer.c` | `add_gate()` with inline inverse cancellation | Already merges inverse gates during placement |

### Supporting

| Component | Location | Purpose | When to Use |
|-----------|----------|---------|-------------|
| `gate.c` | `c_backend/src/gate.c` | `gates_are_inverse()` | Understanding gate cancellation rules |
| `execution.c` | `c_backend/src/execution.c` | `reverse_circuit_range()` | Understanding adjoint generation |
| `test_compile.py` | `tests/test_compile.py` | Existing compile tests | Extend with optimization/uncomputation tests |
| `test_uncomputation.py` | `tests/test_uncomputation.py` | Existing uncomputation tests | Reference patterns for new tests |

## Architecture Patterns

### Pattern 1: Python-Level Gate List Optimization

**What:** Optimize the `list[dict]` gate sequence stored in `CompiledBlock.gates` directly in Python, rather than constructing a temporary C circuit for optimization.

**When to use:** Always for Phase 49 optimization.

**Why:** The captured gate sequence is already in Python dict format (`{'type': int, 'target': int, 'angle': float, 'num_controls': int, 'controls': list}`). Round-tripping through a C `circuit_t` would require building a temporary circuit, calling `circuit_optimize()`, then re-extracting -- complex and fragile. The optimization rules (inverse cancellation, rotation merging) are straightforward to implement on the dict list.

**Example:**
```python
def _optimize_gate_list(gates):
    """Optimize a list of gate dicts by cancelling adjacent inverses and merging rotations."""
    if not gates:
        return gates

    optimized = []
    for gate in gates:
        if optimized and _gates_cancel(optimized[-1], gate):
            optimized.pop()  # Cancel inverse pair
        elif optimized and _gates_merge(optimized[-1], gate):
            optimized[-1] = _merged_gate(optimized[-1], gate)
        else:
            optimized.append(gate)
    return optimized
```

**Confidence:** HIGH -- the gate dict format is well-established (Phase 48), and this approach avoids C memory management complexity.

### Pattern 2: Uncomputation via _start_layer/_end_layer on Replay Results

**What:** When `_replay()` builds a return qint, set `_start_layer`, `_end_layer`, and `operation_type` so `_do_uncompute()` works unchanged.

**When to use:** In `CompiledFunc._replay()` when constructing the return qint.

**Why:** The existing uncomputation system in `qint._do_uncompute()` calls `reverse_circuit_range(_circuit, self._start_layer, self._end_layer)` to append adjoint gates. If the replay result has these fields set correctly to bracket the replayed gates, uncomputation works automatically. The `_build_return_qint()` helper already sets `_start_layer` and `_end_layer` -- this just needs `operation_type = "COMPILED"` to be set so the uncomputation cascade recognizes it as an intermediate (not a user-created variable).

**Example:**
```python
# In _build_return_qint or _replay:
result._start_layer = start_layer  # Layer before inject_remapped_gates
result._end_layer = end_layer      # Layer after inject_remapped_gates
result.operation_type = "COMPILED"  # Marks as intermediate for uncomputation
```

**Confidence:** HIGH -- `_build_return_qint()` already sets these fields (lines 199-200 in compile.py).

### Pattern 3: Optimization at Capture Time

**What:** Run optimization immediately after `_capture()` builds the `CompiledBlock`, before storing in cache.

**When to use:** In `CompiledFunc._capture()` after building the block but before returning it.

**Why:** Per the CONTEXT.md decisions, optimization happens at capture time so the cache stores the optimized version and all replays benefit. The `optimize` flag (defaulting to `True`) controls whether optimization runs.

**Example:**
```python
def _capture(self, args, kwargs, quantum_args):
    # ... existing capture logic ...
    block = CompiledBlock(gates=virtual_gates, ...)

    if self._optimize:
        original_count = len(block.gates)
        block.gates = _optimize_gate_list(block.gates)
        block._original_gate_count = original_count

    block._first_call_result = result
    return block
```

**Confidence:** HIGH -- straightforward integration point.

### Pattern 4: Stats Exposure on CompiledFunc

**What:** Expose `original_gates`, `optimized_gates`, `reduction_percent` as properties on `CompiledFunc` by aggregating across cached blocks.

**When to use:** For programmatic inspection; foundation for Phase 51 debug mode.

**Confidence:** HIGH -- simple property implementations.

### Anti-Patterns to Avoid

- **Round-tripping through C circuit_t for optimization:** Building a temporary circuit, optimizing in C, then re-extracting gates is fragile. The `circuit_optimize()` function copies the entire circuit structure and relies on `add_gate()` inline merging. This works for whole-circuit optimization but is overkill for a gate list. Use Python-level optimization instead.

- **Re-optimizing the inverse sequence:** Per CONTEXT.md, the uncomputation (inverse) sequence should NOT be re-optimized. Simply reverse the optimized forward sequence and negate phase angles.

- **Registering replay results gate-by-gate with uncomputation:** Per CONTEXT.md, the compiled function output registers as a single block (via `_start_layer`/`_end_layer`), not individual operations.

- **Modifying qint.__del__ or _do_uncompute():** The existing uncomputation system works as-is. Phase 49 only needs to set the right metadata on returned qints.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gate inverse detection | Custom inverse logic | Port `gates_are_inverse()` rules from `gate.c` lines 445-470 | Proven correct, handles P gate angle comparison |
| Adjoint gate generation | Custom adjoint code | Follow `reverse_circuit_range()` pattern (negate `GateValue`) | Self-adjoint gates (X, H, CX) have GateValue that doesn't affect inversion; only P gates need angle negation |
| Qubit allocation for ancillas | Manual qubit tracking | `_allocate_qubit()` from `_core.pyx` | Already used in `_replay()` |
| Scope-based uncomputation | New uncomputation mechanism | Existing `_do_uncompute()` + `_start_layer`/`_end_layer` | Phase 18/19/41 system is mature |

**Key insight:** Nearly all infrastructure exists. This phase is primarily about wiring existing systems together (optimization on captured gates, metadata on replayed results) rather than building new subsystems.

## Common Pitfalls

### Pitfall 1: First-Call Gates Already in Circuit

**What goes wrong:** The first call to a compiled function executes normally, putting gates into the circuit. If you also inject optimized gates, you get duplicate gates.

**Why it happens:** `_capture()` runs the function body which adds gates to the circuit normally. The optimization only affects the cached gate list for future replays.

**How to avoid:** On first call, the circuit already has the unoptimized gates from normal execution. Do NOT inject optimized gates for the first call. Only replays use the optimized sequence. The stats should reflect that the first call is unoptimized.

**Warning signs:** Gate count doubles after first call with optimization enabled.

### Pitfall 2: Gate Dict Keys Must Match Exactly

**What goes wrong:** Optimization creates gate dicts with missing or extra keys, causing `inject_remapped_gates()` to fail.

**Why it happens:** `inject_remapped_gates()` in `_core.pyx` (line 754-776) requires exactly: `'type'`, `'target'`, `'angle'`, `'num_controls'`, `'controls'`.

**How to avoid:** Ensure all optimization transforms preserve the exact dict schema. When merging gates (e.g., combining rotation angles), create new dicts with all required keys.

**Warning signs:** KeyError or TypeError during replay.

### Pitfall 3: Uncomputation of In-Place Returns

**What goes wrong:** When a compiled function returns the same qint it received (in-place modification), setting `operation_type = "COMPILED"` on the caller's qint causes it to be uncomputed when it shouldn't be.

**Why it happens:** `_replay()` detects `return_is_param_index` and returns the caller's qint directly. If you set `operation_type` on the caller's qint, the uncomputation system treats it as an intermediate.

**How to avoid:** Only set uncomputation metadata on NEW qints (when `return_is_param_index is None`). When the return is an in-place modification, the caller's qint retains its original metadata.

**Warning signs:** User-created qints get unexpectedly uncomputed inside with-blocks.

### Pitfall 4: Phase Gate Angle Merging Precision

**What goes wrong:** Merging phase gate angles (e.g., P(pi/4) + P(pi/4) = P(pi/2)) introduces floating-point errors, causing the merged angle to be slightly off, which breaks `gates_are_inverse()` comparison later.

**Why it happens:** IEEE 754 floating-point arithmetic is not exact.

**How to avoid:** Use a tolerance when checking if merged angles sum to zero (for cancellation) or 2*pi (for identity). The C code in `gates_are_inverse()` uses exact equality (`G1->GateValue != -G2->GateValue`), so replicate that behavior but be aware of accumulated error from merging.

**Warning signs:** Merged P gates that should cancel don't; gate count is higher than expected.

### Pitfall 5: Qubit-Saving Mode Interaction with Compiled Functions

**What goes wrong:** When qubit-saving mode is active, intermediates inside the compiled function should be uncomputed before returning, but the compiled function doesn't know about qubit-saving mode.

**Why it happens:** The CONTEXT.md says intermediate qubit handling is tied to existing qubit-saving mode. If the function is captured with qubit-saving off but replayed with it on (or vice versa), behavior may be inconsistent.

**How to avoid:** Capture the qubit-saving state at capture time and store it in the `CompiledBlock`. During replay, respect the captured state (the function was captured under specific conditions). Alternatively, since the cache key already includes classical args and widths, qubit-saving mode could be part of the key to force re-capture when it changes.

**Warning signs:** Qubit counts differ between qubit-saving on/off in unexpected ways.

### Pitfall 6: Optimization Silently Altering Gate Semantics

**What goes wrong:** Incorrect optimization rules cancel or merge gates that should not be combined, producing wrong circuit behavior.

**Why it happens:** The optimizer doesn't verify that cancelled/merged gates truly are inverses or commute.

**How to avoid:** Be conservative. Only implement well-understood rules: (1) adjacent identical self-adjoint gates cancel (X-X, H-H, CX-CX with same controls), (2) adjacent P gates on same qubit with angles summing to zero cancel, (3) adjacent P gates on same qubit merge by adding angles. Add an `optimize=False` escape hatch and test both paths.

**Warning signs:** Circuit simulation produces different results with/without optimization.

## Code Examples

### Gate Inverse Cancellation (Python Port of C Logic)

```python
# Gate type enum values from types.h
X, Y, Z, R, H, Rx, Ry, Rz, P, M = range(10)

# Self-adjoint gates (G*G = I)
SELF_ADJOINT = {X, Y, Z, H}

def _gates_cancel(g1, g2):
    """Check if two gate dicts are inverses (would cancel)."""
    if g1['target'] != g2['target']:
        return False
    if g1['num_controls'] != g2['num_controls']:
        return False
    if g1['type'] != g2['type']:
        return False
    if g1['controls'] != g2['controls']:
        return False

    gate_type = g1['type']

    # Self-adjoint gates: applying twice cancels
    if gate_type in SELF_ADJOINT:
        return True

    # Phase gate: P(t) and P(-t) cancel
    if gate_type == P:
        return g1['angle'] == -g2['angle']

    # Rotation gates: Rx(t) and Rx(-t) cancel, etc.
    if gate_type in (Rx, Ry, Rz, R):
        return g1['angle'] == -g2['angle']

    return False


def _gates_merge(g1, g2):
    """Check if two gates can be merged (same type, same target, same controls)."""
    if g1['target'] != g2['target']:
        return False
    if g1['num_controls'] != g2['num_controls']:
        return False
    if g1['type'] != g2['type']:
        return False
    if g1['controls'] != g2['controls']:
        return False

    # Only rotation/phase gates can be merged (add angles)
    return g1['type'] in (P, Rx, Ry, Rz, R)


def _merged_gate(g1, g2):
    """Create merged gate by adding angles."""
    merged = dict(g1)
    merged['angle'] = g1['angle'] + g2['angle']
    return merged
```

Source: Ported from `c_backend/src/gate.c` lines 445-470 (`gates_are_inverse`).

### Multi-Pass Optimization

```python
def _optimize_gate_list(gates):
    """Optimize gate list with multiple passes until stable."""
    if not gates:
        return gates

    prev_count = len(gates) + 1
    optimized = list(gates)

    # Iterate until no more reductions
    while len(optimized) < prev_count:
        prev_count = len(optimized)
        result = []
        for gate in optimized:
            if result and _gates_cancel(result[-1], gate):
                result.pop()
            elif result and _gates_merge(result[-1], gate):
                result[-1] = _merged_gate(result[-1], gate)
            else:
                result.append(gate)
        optimized = result

    return optimized
```

### Uncomputation Metadata on Replay Result

```python
# In CompiledFunc._replay():
def _replay(self, block, quantum_args):
    # ... existing qubit mapping and injection ...

    start_layer = get_current_layer()
    inject_remapped_gates(block.gates, virtual_to_real)
    end_layer = get_current_layer()

    if block.return_qubit_range is not None:
        if block.return_is_param_index is not None:
            return quantum_args[block.return_is_param_index]
        else:
            result = _build_return_qint(block, virtual_to_real, start_layer, end_layer)
            # Key: operation_type enables uncomputation cascade
            result.operation_type = "COMPILED"
            # _start_layer and _end_layer already set by _build_return_qint
            return result
    return None
```

Source: `src/quantum_language/compile.py` lines 357-391, `src/quantum_language/qint.pyx` lines 359-417.

### Generating Inverse from Optimized Gate List

```python
def _inverse_gate_list(gates):
    """Generate inverse (adjoint) of a gate list.

    Reverses order and negates GateValue for each gate.
    Follows reverse_circuit_range() pattern from execution.c.
    """
    inverse = []
    for gate in reversed(gates):
        inv_gate = dict(gate)
        inv_gate['angle'] = -gate['angle']  # Negate phase
        inverse.append(inv_gate)
    return inverse
```

Source: `c_backend/src/execution.c` lines 57-104.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Whole-circuit optimization via `circuit.optimize()` | Gate-list optimization on captured sequences | Phase 49 | Targeted optimization per compiled function |
| Undecorated functions only in uncomputation | Compiled function outputs participate in uncomputation | Phase 49 | `@ql.compile` compatible with `with` blocks |
| No optimization on compiled functions | Capture-time optimization with cached optimized sequence | Phase 49 | Fewer gates on replay |

## Open Questions

1. **Multi-qubit gate cancellation scope**
   - What we know: The C `add_gate()` already handles CNOT-CNOT cancellation (same target and control). The Python port should match.
   - What's unclear: Whether CCX (Toffoli) and MCX (multi-controlled) gates should also be checked for inverse cancellation. The C code handles them in `gates_are_inverse()`.
   - Recommendation: Include all gate types in cancellation checks -- the logic is the same (same type, same target, same controls = self-adjoint for X-family gates).

2. **SWAP elimination**
   - What we know: CONTEXT.md mentions "redundant SWAP elimination" as an optimization. SWAPs are typically decomposed into 3 CNOTs.
   - What's unclear: Whether SWAP gates appear explicitly in the gate dict format, or only as CNOT sequences.
   - Recommendation: Check if SWAP appears as a distinct gate type in the `Standardgate_t` enum. If not (only X, Y, Z, R, H, Rx, Ry, Rz, P, M are defined in types.h), then SWAP elimination means detecting the CNOT pattern (CX(a,b), CX(b,a), CX(a,b)) and removing all three if immediately followed by the same pattern.
   - Confidence: MEDIUM -- pattern detection for CNOT-based SWAPs adds complexity; may be deferred if gate types don't include explicit SWAP.

3. **QFT-specific optimization**
   - What we know: CONTEXT.md says "Claude's discretion based on research."
   - Assessment: QFT produces a characteristic pattern of H gates and controlled-P gates with decreasing angles (pi/2, pi/4, pi/8, ...). QFT-specific optimization would recognize this pattern and potentially truncate small-angle rotations or merge adjacent QFT/inverse-QFT pairs.
   - Recommendation: Skip QFT-specific optimization for Phase 49. The generic rules (inverse cancellation, rotation merging) already handle QFT-iQFT cancellation when they're adjacent. Pattern recognition for QFT truncation is a significant effort for marginal benefit at this stage.
   - Confidence: HIGH -- generic rules cover the most valuable QFT optimization (adjacent QFT/iQFT cancellation).

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/compile.py` -- CompiledFunc, CompiledBlock, _capture, _replay, _build_return_qint (read in full)
- `src/quantum_language/_core.pyx` -- extract_gate_range, inject_remapped_gates, reverse_instruction_range, circuit.optimize() (read in full)
- `src/quantum_language/_core.pxd` -- Cython declarations, gate_t structure, Standardgate_t enum (read in full)
- `src/quantum_language/qint.pyx` -- _do_uncompute, __enter__, __exit__, _start_layer/_end_layer tracking (read relevant sections)
- `c_backend/src/circuit_optimizer.c` -- circuit_optimize, apply_cancel_inverse (read in full)
- `c_backend/src/optimizer.c` -- add_gate with inline inverse merge (read in full)
- `c_backend/src/execution.c` -- reverse_circuit_range (read in full)
- `c_backend/src/gate.c` -- gates_are_inverse (read relevant section)
- `c_backend/include/types.h` -- Standardgate_t enum (X, Y, Z, R, H, Rx, Ry, Rz, P, M)
- `tests/test_compile.py` -- existing Phase 48 tests (read in full)
- `tests/test_uncomputation.py` -- existing uncomputation tests (read in full)

### Secondary (MEDIUM confidence)
- `.planning/codebase/ARCHITECTURE.md` -- overall codebase architecture
- `.planning/phases/49-optimization-uncomputation/49-CONTEXT.md` -- user decisions for this phase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components exist in codebase, verified by reading source
- Architecture: HIGH -- patterns derived from existing code patterns (compile.py capture/replay, qint uncomputation)
- Pitfalls: HIGH -- identified from actual code paths and data flow analysis
- Optimization rules: MEDIUM -- Python port of C logic, but SWAP elimination and QFT patterns need more investigation

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (stable codebase, internal project)
