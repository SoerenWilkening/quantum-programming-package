# Phase 43: Copy-Aware Binary Operations - Research

**Researched:** 2026-02-02
**Domain:** Quantum integer and array binary operation internals (Cython/C)
**Confidence:** HIGH

## Summary

This phase modifies existing binary operations in `qint.pyx` and `qarray.pyx` to use quantum copy (`self.copy()` / `self.copy_onto()`) instead of classical value initialization when creating result operands. The core problem is that operations like `__add__` currently do `a = qint(value=self.value, width=result_width)` which creates a new qint with classical X gates based on the Python-side `.value` attribute. This discards quantum state information (superposition, entanglement) and replaces it with a deterministic classical bitstring.

The fix is straightforward: replace the classical initialization pattern with `self.copy()`, which uses CNOT gates to transfer quantum state to fresh qubits. The `copy()` method from Phase 42 is already fully implemented and tested.

**Primary recommendation:** Replace `qint(value=self.value, width=...)` with `self.copy()` in each affected `__add__`, `__radd__`, `__sub__` method. For `__mul__`, `__rmul__`, and bitwise ops that already allocate a zero-initialized result, no copy is needed since the operation itself writes the result. For `__floordiv__` and `__mod__`, the existing `remainder ^= self` pattern is already a valid quantum copy (XOR into |0>). The qarray layer delegates to qint element-wise and needs no direct changes.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| qint.copy() | Phase 42 | Quantum copy via CNOT gates | Already implemented and tested |
| qint.copy_onto() | Phase 42 | XOR-copy into existing target | Already implemented and tested |

No external libraries needed. This phase is purely internal refactoring of existing methods.

## Architecture Patterns

### Pattern 1: Classical Value Initialization (Current - BROKEN for superposition)

**What:** Creates result qint from Python-side `.value` attribute
**When to use:** NEVER for quantum operands (only valid if operand is guaranteed classical)
**Example:**
```python
# CURRENT pattern in __add__ (line 795 of qint.pyx):
a = qint(value=self.value, width=result_width)
a += other
```
**Problem:** `self.value` is the classical value stored at construction time. If `self` is in superposition (e.g., from a prior operation or Hadamard), `self.value` is stale/meaningless. The result will be initialized to a fixed classical state, not a quantum copy.

### Pattern 2: Quantum Copy Initialization (Target - CORRECT)

**What:** Creates result qint via CNOT-based quantum copy
**When to use:** All binary ops that need a copy of the source operand as the starting point for the result
**Example:**
```python
# REPLACEMENT pattern for __add__:
a = self.copy()  # CNOT-based copy preserving quantum state
# Handle width mismatch if needed
a += other
```

### Pattern 3: Zero-Init + Operation (Already Correct)

**What:** Allocates zero qint, then the operation itself writes the result
**When to use:** Operations where the C backend takes both operands as inputs and writes to a separate output register
**Example:**
```python
# CURRENT pattern in __mul__ (line 1058 of qint.pyx) - ALREADY CORRECT:
result = qint(width=result_width)  # zero-initialized result register
self.multiplication_inplace(other, result)  # C backend writes result
```
**Why correct:** The multiplication C function (`CQ_mul`/`QQ_mul`) reads from self and other qubits and writes to the result register. It doesn't need a pre-copied operand.

### Pattern 4: XOR-Copy into Zero (Already Correct)

**What:** Allocates zero qint, then XORs source into it
**When to use:** Division/modulo where `remainder ^= self` serves as copy step
**Example:**
```python
# CURRENT pattern in __floordiv__ (line 2334-2338) - ALREADY CORRECT:
remainder = qint(0, width=self.bits)
remainder ^= self  # quantum copy via XOR into |0>
```
**Why correct:** `^= self` applies CNOT gates from self to remainder. Since remainder starts at |0>, this is equivalent to `self.copy_onto(remainder)`.

### Anti-Patterns to Avoid
- **Using `.value` for quantum operand initialization:** The `.value` attribute is a classical snapshot, not quantum state. Never use it to initialize a result that should preserve quantum superposition.
- **Copying both operands:** For `qint + qint`, only one operand needs to be copied (the one that becomes the result base). The other is applied via in-place operation.
- **Modifying `.value` after copy:** The `copy()` method creates a qint with `value=0` (default). The result's `.value` attribute will not match the quantum state. This is expected behavior -- `.value` is only accurate for classically-initialized qints.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Quantum copy | Manual CNOT loops in each operator | `self.copy()` / `self.copy_onto()` | Phase 42 provides tested, layer-tracked copy with dependency registration |
| Width-matched copy | Manual qubit padding after copy | Handle via `copy()` then width adjustment if needed | `copy()` preserves source width; if result needs to be wider, allocate wider and use `copy_onto()` |

**Key insight:** The `copy()` method already handles layer tracking (`_start_layer`, `_end_layer`), dependency registration (`add_dependency`), and operation type tagging (`operation_type = 'COPY'`). Binary ops that use `copy()` get these for free on the copy step, then need to update them for the overall operation.

## Common Pitfalls

### Pitfall 1: Width Mismatch Between Copy and Result
**What goes wrong:** `self.copy()` produces a qint with `self.bits` width, but the result may need `max(self.bits, other.bits)` width.
**Why it happens:** For `qint(4-bit) + qint(8-bit)`, the result should be 8 bits, but `self.copy()` on the 4-bit operand gives a 4-bit copy.
**How to avoid:** After copy, if result_width > copy.bits, either: (a) copy the wider operand instead of the narrower one, or (b) allocate a result with the correct width and use `copy_onto()` for the narrower source (remaining bits stay |0> as zero-extension).
**Warning signs:** Width assertion failures or truncated results in tests with mismatched widths.

### Pitfall 2: Layer Tracking Overlap
**What goes wrong:** The `copy()` call sets its own `_start_layer` and `_end_layer` on the result. Then the binary op overwrites these.
**Why it happens:** Both copy() and the binary op try to set layer tracking on the result qint.
**How to avoid:** Capture `start_layer` before the copy, then after the full operation completes, set `_start_layer` and `_end_layer` on the final result spanning the entire operation (copy + arithmetic). The intermediate copy's layer tracking will be overwritten, which is correct -- the binary op is the logical unit for uncomputation, not the copy step alone.
**Warning signs:** Uncomputation reversing only the copy, not the arithmetic.

### Pitfall 3: Double Dependency Registration
**What goes wrong:** `copy()` registers `self` as a dependency of the result. Then the binary op also registers `self` as a dependency.
**Why it happens:** Both copy() and the binary op call `add_dependency(self)`.
**How to avoid:** The binary op should set dependencies on the final result. Since the copy's result IS the final result object (mutated in-place by `+=`), make sure `add_dependency` is called after the in-place operation, overwriting or supplementing what copy set. Check that `add_dependency` handles duplicates gracefully, or clear dependencies before re-registering.
**Warning signs:** Duplicate entries in `dependency_parents` list.

### Pitfall 4: Forgetting to Update `.value` / `operation_type`
**What goes wrong:** After `copy()`, the result has `operation_type = 'COPY'`. After `result += other`, it should be 'ADD'.
**Why it happens:** `copy()` sets its own metadata; the in-place step doesn't update it.
**How to avoid:** Explicitly set `operation_type` after the full binary operation, as the existing code already does.
**Warning signs:** Uncomputation system treating additions as copies.

### Pitfall 5: Operations That Don't Need Copy Changes
**What goes wrong:** Modifying operations that are already correct wastes time and risks introducing bugs.
**Why it happens:** Not recognizing which operations use the broken `qint(value=...)` pattern vs. the correct zero-init pattern.
**How to avoid:** Carefully audit each operation:
- **Need copy fix:** `__add__`, `__radd__`, `__sub__` (use `qint(value=self.value, ...)`)
- **Already correct (zero-init + operation):** `__mul__`, `__rmul__`, `__and__`, `__or__`, `__xor__`, `__invert__` (use `qint(width=...)` zero-init)
- **Already correct (XOR copy):** `__floordiv__`, `__mod__` (use `remainder ^= self`)
- **Don't exist yet:** `__neg__`, `__abs__`, `__lshift__`, `__rshift__` (must be created with correct pattern from the start)

## Code Examples

### Example 1: Fixing `__add__` (the core change)

Current code (qint.pyx line 790-806):
```python
def __add__(self, other):
    # ...layer capture...
    if type(other) == qint:
        result_width = max(self.bits, (<qint>other).bits)
    else:
        result_width = self.bits
    a = qint(value = self.value, width = result_width)  # BUG: classical init
    a += other
    # ...layer tracking...
    return a
```

Fixed code:
```python
def __add__(self, other):
    # ...layer capture...
    if type(other) == qint:
        result_width = max(self.bits, (<qint>other).bits)
    else:
        result_width = self.bits

    # Quantum copy self as the result base
    if self.bits == result_width:
        a = self.copy()
    else:
        # Width mismatch: allocate wider result, copy_onto it
        a = qint(width=result_width)
        self.copy_onto_padded(a)  # or manual approach
    a += other

    # ...layer tracking, dependencies...
    return a
```

Note: `copy_onto()` requires matching widths. For the width-mismatch case, the simplest approach is to copy the wider operand. For `__add__` specifically: if `self` is narrower, consider copying `other` and adding `self` to it (addition is commutative). For non-commutative ops like `__sub__`, we need the subtraction order preserved.

### Example 2: Width Mismatch Resolution Strategy

For commutative ops (`+`, `*`, `&`, `|`, `^`):
```python
# Always copy the wider operand as the result base
if type(other) == qint and (<qint>other).bits > self.bits:
    a = (<qint>other).copy()
    a += self  # add narrower into wider copy
else:
    a = self.copy()
    a += other
```

For non-commutative ops (`-`):
```python
# Must copy self (the left operand), handle width padding
if type(other) == qint:
    result_width = max(self.bits, (<qint>other).bits)
else:
    result_width = self.bits

# For now, simplest approach: allocate zero result, XOR self into it, then subtract
a = qint(width=result_width)
# XOR self into lower bits of result (same pattern as floordiv/mod)
a ^= self  # quantum copy via XOR into |0> -- equivalent to copy_onto
a -= other
```

### Example 3: qarray Operations (No Changes Needed)

The qarray `_elementwise_binary_op` method (line 804-850) delegates to qint operators:
```python
result_elements = [op_func(elem, other) for elem in self._elements]
```
Where `op_func = lambda a, b: a + b`. This calls `qint.__add__` on each element. So fixing `qint.__add__` automatically fixes `qarray.__add__` -- no separate qarray changes needed for the copy-aware behavior.

However, the qarray's `_elementwise_binary_op` constructs a view from the results. The elements in the result are the qint objects returned by `qint.__add__`, which will now be copy-based. This is correct.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `qint(value=self.value, width=W)` | `self.copy()` (CNOT-based) | Phase 43 (this phase) | Preserves quantum state in binary ops |

**Why this matters now:** Prior phases may have worked because tests only used classically-initialized qints. Once users create qints in superposition (e.g., via Hadamard gates or conditional operations), the classical initialization bug would produce incorrect results.

## Operation-by-Operation Audit

### Operations Needing Copy Fix (Classical Init Bug)
| Method | Line | Current Pattern | Fix |
|--------|------|----------------|-----|
| `__add__` | 795 | `qint(value=self.value, width=W)` | Replace with `self.copy()` or XOR-copy |
| `__radd__` | 840 | `qint(value=self.value, width=W)` | Replace with `self.copy()` or XOR-copy |
| `__sub__` | 910 | `qint(value=self.value, width=W)` | Replace with `self.copy()` or XOR-copy |

### Operations Already Correct (Zero-Init + Backend Writes Result)
| Method | Line | Current Pattern | Why Correct |
|--------|------|----------------|-------------|
| `__mul__` | 1058 | `qint(width=W)` then `multiplication_inplace` | C backend reads both operands, writes output |
| `__rmul__` | 1107 | `qint(width=W)` then `multiplication_inplace` | Same as __mul__ |
| `__and__` | 1219 | `qint(width=W)` then Q_and | C backend reads both operands, writes output |
| `__or__` | ~1360 | `qint(width=W)` then Q_or | Same as __and__ |
| `__xor__` | 1498 | `qint(width=W)` then CNOT sequence | Uses explicit CNOT copy of self + XOR other |
| `__invert__` | 1612 | Modifies self in-place | No result allocation needed |

### Operations Already Correct (XOR Copy)
| Method | Line | Current Pattern | Why Correct |
|--------|------|----------------|-------------|
| `__floordiv__` | 2334-2338 | `qint(0, width=W)` then `^= self` | XOR into |0> is quantum copy |
| `__mod__` | 2434-2435 | `qint(0, width=W)` then `^= self` | XOR into |0> is quantum copy |

### Operations That Don't Exist Yet
| Method | Required By Phase? | Notes |
|--------|-------------------|-------|
| `__neg__` | Yes (CONTEXT.md lists unary ops) | Implement as `result = qint(width=W); result -= self` or `~self + 1` |
| `__abs__` | Yes (CONTEXT.md lists unary ops) | Implement using conditional negation |
| `__lshift__` | Yes (CONTEXT.md lists bitwise ops) | Implement with qubit remapping or repeated doubling |
| `__rshift__` | Yes (CONTEXT.md lists bitwise ops) | Implement with qubit remapping or repeated halving |
| `__rsub__` | Implied by reverse ops | Implement as `other_copy - self` |

### qarray Operations
| Method | Needs Direct Fix? | Why |
|--------|------------------|-----|
| All arithmetic/bitwise | No | Delegates to qint ops via `_elementwise_binary_op` |
| Missing: `__floordiv__`, `__mod__`, `__neg__`, `__abs__`, `__lshift__`, `__rshift__`, `__invert__` | Yes - need to be added | Not currently in qarray.pyx |

## Open Questions

1. **Width mismatch strategy for copy**
   - What we know: `copy()` produces same-width result; `copy_onto()` requires matching widths.
   - What's unclear: Best pattern for when result_width > self.bits. Options: (a) XOR-copy into zero-initialized wider qint (already used by floordiv/mod), (b) copy wider operand for commutative ops, (c) allocate wider result and manually CNOT partial bits.
   - Recommendation: Use the XOR-into-zero pattern (`result = qint(width=W); result ^= self`) since it's already proven in floordiv/mod and handles width padding naturally (upper bits stay |0>). This is equivalent to `copy_onto` but without the width-match constraint.

2. **Missing operations (__neg__, __abs__, __lshift__, __rshift__)**
   - What we know: CONTEXT.md lists these as in scope. They don't exist in qint.pyx.
   - What's unclear: Whether implementing them is required for Phase 43 success criteria or deferred.
   - Recommendation: Phase 43 CONTEXT.md says "All arithmetic ops: +, -, *, //, %" and "All bitwise ops: &, |, ^, ~, <<, >>" and "Unary ops: __neg__, __abs__". These should be implemented as part of Phase 43 since they're listed in the operation scope. However, the success criteria focus on copy-awareness, so implementing them with correct copy-aware patterns from the start satisfies both concerns.

3. **qarray missing operations**
   - What we know: qarray has +, -, *, &, |, ^, comparisons, and in-place variants. Missing: //, %, ~, <<, >>, neg, abs.
   - What's unclear: Whether adding these to qarray is in Phase 43 scope.
   - Recommendation: The CONTEXT.md says "qarray supports the same full set of operations as qint -- all arithmetic + bitwise + unary, element-wise." This implies adding missing operations to qarray is in scope.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/qint.pyx` - Direct code analysis of all binary operations
- `src/quantum_language/qarray.pyx` - Direct code analysis of element-wise delegation pattern
- `src/quantum_language/qint.pxd` - Class attribute declarations
- `tests/test_copy.py` - Phase 42 verification tests showing copy() usage
- `tests/conftest.py` - Test fixture pattern (verify_circuit)
- `tests/verify_helpers.py` - Test data generation helpers
- `.planning/phases/43-copy-aware-binary-operations/43-CONTEXT.md` - Phase decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All code is internal, no external dependencies
- Architecture: HIGH - Direct code analysis of every affected method
- Pitfalls: HIGH - Identified from actual code patterns and tested behaviors

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (internal codebase, stable patterns)
