# Phase 42: Quantum Copy Foundation - Research

**Researched:** 2026-02-02
**Domain:** Quantum state copy via CNOT entanglement (Cython/C backend)
**Confidence:** HIGH

## Summary

Phase 42 adds `.copy()` and `.copy_onto()` methods to `qint` and `qbool` for CNOT-based quantum state copying. The implementation is straightforward because the codebase already has all required infrastructure: qubit allocation, CNOT gate generation via `Q_xor`, layer tracking for uncomputation, and scope-based lifecycle management.

The copy operation is functionally identical to the first half of `__xor__`: allocate fresh |0> qubits, then apply CNOT(source[i], target[i]) for each bit. The `Q_xor(bits)` C function already generates exactly the right circuit (parallel CNOTs with depth O(1)). The main implementation work is wiring up metadata (layer tracking, dependency parents, operation_type, scope registration) and adding the `copy_onto` variant with width validation.

**Primary recommendation:** Implement `copy()` and `copy_onto()` as methods on `qint` (inherited by `qbool`), reusing the existing `Q_xor` C function for CNOT generation, and following the established layer tracking + dependency pattern from Phase 41.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `Q_xor(bits)` | C backend | Generate parallel CNOT gates | Already used for XOR operations; CNOT is the copy primitive |
| `run_instruction` | C backend | Execute gate sequences on circuit | Standard gate execution path |
| `allocator_alloc` | C backend | Allocate fresh |0> qubits | Standard qubit allocation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `reverse_circuit_range` | C backend | Uncompute copy gates | When copy is uncomputed |
| `current_scope_depth` | Python contextvars | Track scope for lifecycle | Scope registration of copies |
| `_get_scope_stack` | Python global | Register copy in active scope | For with-block cleanup |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Q_xor` for CNOT | Manual gate construction | No benefit; Q_xor is already a single parallel layer of CNOTs |
| Method on qint | Standalone function | CONTEXT.md decision: `.copy()` method on types |

## Architecture Patterns

### Pattern 1: Copy Method Implementation (on qint)
**What:** `.copy()` allocates fresh qubits, applies CNOTs, returns new qint with proper metadata
**When to use:** Always for `.copy()`
**Example pattern (derived from existing `__xor__` lines 1510-1519):**
```python
def copy(self):
    # 1. Check not uncomputed
    self._check_not_uncomputed()

    # 2. Capture start layer for uncomputation tracking
    start_layer = circuit.used_layer

    # 3. Allocate fresh qint(0, width=self.bits) -- qubits start in |0>
    result = qint(width=self.bits)

    # 4. Apply CNOTs: result ^= self (CNOT from source to target)
    #    Qubit array: [0:bits] = target (result), [bits:2*bits] = source (self)
    qubit_array[:self.bits] = result.qubits[64-self.bits:64]
    qubit_array[self.bits:2*self.bits] = self.qubits[64-self.bits:64]
    seq = Q_xor(self.bits)
    run_instruction(seq, &arr[0], False, _circuit)

    # 5. Set metadata for uncomputation
    result._start_layer = start_layer
    result._end_layer = circuit.used_layer
    result.operation_type = 'COPY'
    result.add_dependency(self)

    return result
```
**Source:** Derived from existing `__xor__` implementation in qint.pyx lines 1510-1519

### Pattern 2: copy_onto Method
**What:** XOR-copy source bits onto an existing target (target must be same width)
**When to use:** When user already has allocated qubits to copy onto
**Key difference from copy():** Does NOT allocate new qubits; validates target width matches
```python
def copy_onto(self, target):
    # Validate same width
    if target.bits != self.bits:
        raise ValueError(f"Width mismatch: source={self.bits}, target={target.bits}")

    # Apply CNOTs: target ^= self
    # Same CNOT pattern, but uses existing target qubits
    ...
```

### Pattern 3: qbool.copy() Returns qbool (Type Preservation)
**What:** `qbool.copy()` must return `qbool`, not `qint`
**When to use:** When source is qbool
**Implementation:** Override `copy()` in qbool.pyx to call super and wrap result, OR implement copy in qint such that it preserves type by checking `type(self)`

### Pattern 4: Layer Tracking for Uncomputation (Phase 41)
**What:** Every operation that generates gates must record start_layer and end_layer
**When to use:** Always for new operations
**Existing pattern (from every operator in qint.pyx):**
```python
start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
# ... generate gates ...
result._start_layer = start_layer
result._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
result.operation_type = 'COPY'
result.add_dependency(self)
```

### Recommended File Changes
```
src/quantum_language/
├── qint.pyx    # Add copy() and copy_onto() methods
├── qint.pxd    # No changes needed (no new cdef attributes)
├── qbool.pyx   # Add copy() override returning qbool (type preservation)
├── qbool.pxd   # No changes needed
```

### Anti-Patterns to Avoid
- **Allocating qubits manually instead of using qint(width=N):** The qint constructor handles allocation, qubit tracking, scope registration, and creation counter. Use it.
- **Forgetting layer tracking:** Every gate-generating method MUST set `_start_layer`, `_end_layer`, `operation_type`, and call `add_dependency`. Without this, uncomputation breaks.
- **Forgetting scope registration:** The qint constructor already registers in the scope stack, so the fresh result qint created by `copy()` will be automatically registered. No extra work needed.
- **Using `isinstance` instead of `type` for type checks:** The codebase consistently uses `type(other) == qint` for exact type matching and `isinstance` for subclass-inclusive checks. Follow this convention.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CNOT gate generation | Manual gate_t construction | `Q_xor(bits)` from C backend | Already generates exactly parallel CNOTs; handles all widths 1-64 |
| Qubit allocation | Manual allocator calls | `qint(width=N)` constructor | Handles allocation, tracking, scope registration, creation counter |
| Gate execution | Direct circuit manipulation | `run_instruction(seq, arr, invert, circuit)` | Standard execution path with qubit mapping |
| Uncomputation metadata | Custom tracking | Existing `_start_layer`/`_end_layer`/`operation_type`/`add_dependency` pattern | Phase 41 infrastructure already handles this |

**Key insight:** The copy operation is a subset of XOR. The codebase already implements `result ^= self` as "copy self to result" in `__xor__` (line 1518). The `.copy()` method just packages this into a clean API with proper metadata.

## Common Pitfalls

### Pitfall 1: Qubit Array Layout (Right-Aligned Storage)
**What goes wrong:** Qubits are stored right-aligned in a 64-element array. Index 63 is MSB for width-1 qints, but index `64-width` is LSB for wider qints.
**Why it happens:** The qubit storage convention is `self.qubits[64-self.bits:64]` for the actual qubit indices.
**How to avoid:** Always use the pattern `self_offset = 64 - self.bits` and slice `self.qubits[self_offset:64]` to extract actual qubit indices.
**Warning signs:** Wrong qubit indices cause incorrect gate connections, visible as wrong simulation results.

### Pitfall 2: Type Preservation for qbool
**What goes wrong:** `qbool.copy()` returns `qint` instead of `qbool`.
**Why it happens:** The copy method allocates `qint(width=self.bits)` which creates a qint even when `self` is qbool.
**How to avoid:** Either override `copy()` in qbool to construct a qbool result, or use `type(self)(width=self.bits)` in the copy method. The override approach is cleaner and follows the existing codebase pattern (qbool has its own constructor).
**Warning signs:** Type checks fail downstream when copy of qbool is used where qbool is expected.

### Pitfall 3: copy_onto Width Validation
**What goes wrong:** Copying a 4-bit source onto a 3-bit target silently produces wrong results.
**Why it happens:** Q_xor(bits) uses the smaller width and ignores remaining bits.
**How to avoid:** Raise ValueError if `self.bits != target.bits` in `copy_onto`.
**Warning signs:** Silent incorrect results.

### Pitfall 4: Garbage Collection Interaction with Tests
**What goes wrong:** Tests that create qints without keeping references may trigger uncomputation gates before measurement/export.
**Why it happens:** Python's GC runs destructors that add inverse gates to the circuit.
**How to avoid:** In test circuit_builder functions, always return keepalive references: `return (expected, [source, copy_result])`. This is the established pattern in conftest.py.
**Warning signs:** Correct logic but wrong simulation results; extra gates in circuit.

### Pitfall 5: copy_onto Target State Assumption
**What goes wrong:** If target qubits are not in |0> state, copy_onto produces XOR result instead of copy.
**Why it happens:** CNOT(source, target) computes target ^= source. If target is already non-zero, the result is source XOR target, not source.
**How to avoid:** CONTEXT.md says "Claude's discretion" for how to validate target state. Options: (a) document that target must be |0>, (b) add a runtime warning. Since this is quantum, you cannot classically check the target state. Document the precondition.
**Warning signs:** copy_onto on non-zero target gives XOR instead of copy.

## Code Examples

### Example 1: CNOT Copy Pattern (from existing __xor__ in qint.pyx)
```python
# From qint.pyx lines 1510-1519 (existing code, verified in codebase)
# Copy self qubits to result using CNOT pattern
self_offset = 64 - self.bits
result_offset = 64 - result_bits

# First, copy self to result by XORing self into result (result starts at 0)
qubit_array[:self.bits] = result.qubits[result_offset:result_offset + self.bits]
qubit_array[self.bits:2*self.bits] = self.qubits[self_offset:64]
arr = qubit_array
seq = Q_xor(self.bits)  # XOR self into result (copying self to result)
run_instruction(seq, &arr[0], False, _circuit)
```

### Example 2: Layer Tracking Pattern (from __add__ in qint.pyx)
```python
# From qint.pyx lines 788-806 (existing code, verified in codebase)
start_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0

# ... operations ...

a._start_layer = start_layer
a._end_layer = (<circuit_s*>_circ).used_layer if _circ_init else 0
a.operation_type = 'ADD'
a.add_dependency(self)
```

### Example 3: Test Pattern (from conftest.py)
```python
# Standard verification test pattern (from tests/conftest.py)
def test_copy_value(verify_circuit):
    def build():
        a = ql.qint(5, width=4)
        b = a.copy()
        return (5, [a, b])  # Keep both alive

    actual, expected = verify_circuit(build, width=4)
    assert actual == expected
```

### Example 4: Q_xor C Implementation (from LogicOperations.c)
```c
// From LogicOperations.c lines 260-308 (existing code, verified in codebase)
// Q_xor generates parallel CNOTs: target[i] ^= source[i] for all i
// Single layer, O(1) depth
seq->gates_per_layer[0] = bits;
for (int i = 0; i < bits; ++i) {
    cx(&seq->seq[0][i], i, bits + i);  // CNOT: target=i, control=bits+i
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual qubit management | Allocator-based allocation | Phase 3 | copy() uses qint constructor which handles allocation |
| No uncomputation | Layer tracking + reverse_circuit_range | Phase 17-18, refined in Phase 41 | copy() must set _start_layer/_end_layer |
| No scope management | Scope stack + current_scope_depth | Phase 19 | copy results auto-register in active scope |

**No deprecated patterns relevant to this phase.**

## Open Questions

1. **qbool.copy() Implementation Strategy**
   - What we know: qbool is a subclass of qint with width=1. CONTEXT.md says copy preserves type.
   - What's unclear: Whether to override copy() in qbool or use type(self) dispatch in qint.copy()
   - Recommendation: Override in qbool.pyx (simpler, follows existing pattern where qbool has its own constructor). The override calls the same CNOT logic but wraps result as qbool.

2. **copy_onto Target State Validation**
   - What we know: CONTEXT.md puts this under "Claude's Discretion." CNOT-copy only works correctly on |0> targets.
   - What's unclear: Whether to validate, warn, or just document.
   - Recommendation: Document the precondition in docstring. Quantum states cannot be classically inspected, so runtime validation is not possible. The method name "copy_onto" already implies the target should be fresh.

3. **copy() Return Type for qint Subclasses (qint_mod)**
   - What we know: qint_mod is a subclass with a `_modulus` attribute. CONTEXT.md only mentions qint and qbool.
   - What's unclear: Whether qint_mod.copy() should preserve modulus.
   - Recommendation: Defer qint_mod.copy() to a later phase if needed. The base qint.copy() will work for qint_mod but return qint (not qint_mod). This is acceptable for Phase 42.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/qint.pyx` - Full qint implementation including XOR copy pattern (lines 1510-1519), layer tracking, dependency management
- `src/quantum_language/qbool.pyx` - qbool as qint subclass with width=1
- `src/quantum_language/_core.pyx` - Circuit initialization, global state, allocator access
- `src/quantum_language/_core.pxd` - C function declarations including Q_xor, run_instruction, allocator functions
- `src/quantum_language/qint.pxd` - qint cdef attribute declarations
- `c_backend/include/bitwise_ops.h` - Q_xor documentation and qubit layout specification
- `c_backend/src/LogicOperations.c` - Q_xor C implementation (parallel CNOTs)
- `tests/conftest.py` - Standard verification test fixture pattern
- `tests/test_uncomputation.py` - Uncomputation test patterns with EAGER mode
- Phase 42 CONTEXT.md - User decisions on API surface and semantics

### Secondary (MEDIUM confidence)
- `src/quantum_language/qint_mod.pyx` - Pattern for extending qint with additional methods and _wrap_result

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All required C functions and Python infrastructure verified in codebase
- Architecture: HIGH - Implementation pattern directly derived from existing __xor__ code
- Pitfalls: HIGH - Identified from actual codebase patterns and established test conventions

**Research date:** 2026-02-02
**Valid until:** 2026-03-04 (stable internal codebase, no external dependencies for this phase)
