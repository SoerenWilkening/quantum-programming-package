# Phase 44: Array Mutability - Research

**Researched:** 2026-02-03
**Domain:** Cython/Python augmented assignment protocol for quantum array element mutation
**Confidence:** HIGH

## Summary

This phase enables `qarray[i] += x` and similar augmented assignment patterns on individual array elements. The core mechanism is Python's augmented assignment protocol, which decomposes `container[i] op= value` into three steps: `__getitem__`, the in-place operator on the element, and `__setitem__`. The current `qarray.__setitem__` unconditionally raises `TypeError` to enforce immutability -- this must be changed to permit element-level augmented assignment.

The existing codebase already has all the building blocks: `qint` implements `__iadd__`, `__isub__`, `__ixor__` (truly in-place), and `__imul__`, `__iand__`, `__ior__` (ancilla+swap). Three operators that qint supports in non-augmented form (`__lshift__`, `__rshift__`, `__floordiv__`) do NOT yet have `__ilshift__`, `__irshift__`, `__ifloordiv__` methods on qint -- these must be added. The qarray already has whole-array in-place ops via `_inplace_binary_op` which delegates to qint's `__iXXX__` methods.

**Primary recommendation:** Implement `__setitem__` on qarray to store elements by index (int, tuple, or slice), add missing `__ilshift__`/`__irshift__`/`__ifloordiv__` methods to qint using the existing ancilla+swap pattern, and add corresponding `__ilshift__`/`__irshift__`/`__ifloordiv__` to qarray.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cython | (project's current) | `cdef class` extension types with `__setitem__` | Already used for all quantum types |
| Python augmented assignment protocol | 3.x | `__getitem__` + `__iXXX__` + `__setitem__` sequence | Language-level mechanism, cannot be customized |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | (project's current) | Verification tests | Testing all augmented assignment patterns |
| qiskit-aer | (project's current) | Simulation verification | End-to-end correctness checks via conftest's `verify_circuit` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `__setitem__` allowing mutation | Proxy/wrapper objects returned by `__getitem__` that intercept `__iadd__` | Far more complex, fragile, violates Python semantics. Not recommended. |
| Adding `__ilshift__`/`__irshift__`/`__ifloordiv__` to qint | Only supporting ops that already have `__iXXX__` | Would leave gaps in the operator coverage per CONTEXT.md decision |

## Architecture Patterns

### Pattern 1: Python Augmented Assignment Protocol (CRITICAL)
**What:** When Python evaluates `qarray[i] += x`, it executes:
1. `temp = qarray.__getitem__(i)` -- returns reference to `self._elements[i]`
2. `temp = temp.__iadd__(x)` -- calls qint's in-place add, returns `self` (same object)
3. `qarray.__setitem__(i, temp)` -- writes element back into the array

**When to use:** This is how ALL `container[key] op= value` expressions work in Python. No alternative.
**Confidence:** HIGH (Python language specification)

**Key insight:** For all existing qint in-place operators, `__iXXX__` returns `self`. This means `temp` in step 2 is the SAME Python object as `self._elements[i]`. Step 3 therefore writes the same object reference back. However, `__setitem__` MUST still be called (Python requires it), so it cannot raise TypeError.

```python
# In qarray.pyx - replace the current __setitem__ that raises TypeError
def __setitem__(self, key, value):
    if isinstance(key, int):
        if key < 0:
            key += len(self._elements)
        if not 0 <= key < len(self._elements):
            raise IndexError(f"Index {key} out of bounds")
        self._elements[key] = value
    elif isinstance(key, tuple):
        # Multi-dimensional: resolve to flat index
        flat_idx = self._multi_to_flat(key)
        self._elements[flat_idx] = value
    elif isinstance(key, slice):
        # Slice assignment for qarray[1:3] += x
        start, stop, step = key.indices(len(self._elements))
        indices = range(start, stop, step)
        if isinstance(value, qarray):
            if len(value) != len(indices):
                raise ValueError("Slice length mismatch")
            for i, idx in enumerate(indices):
                self._elements[idx] = value._elements[i]
        else:
            # Single element broadcast to slice
            for idx in indices:
                self._elements[idx] = value
    else:
        raise TypeError(f"Unsupported index type: {type(key).__name__}")
```

### Pattern 2: Ancilla+Swap for Non-Reversible In-Place Ops on qint
**What:** Operations like `*=`, `//=`, `<<=`, `>>=`, `&=`, `|=` cannot be done truly in-place on qubits. Instead:
1. Compute result on fresh ancilla qubits: `result = self OP other`
2. SWAP qubit references: `self.qubits, result.qubits = result.qubits, self.qubits`
3. Release old qubits (now on `result`) -- dirty release, no uncomputation

**When to use:** Any qint in-place operator that isn't truly reversible (only `+=`, `-=`, `^=` are truly in-place).

**Existing examples in codebase:**
```python
# From qint.__iand__ (line 1453-1460)
result = self & other
result_qint = <qint>result
self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
self.bits = result_qint.bits
return self

# Same pattern used by __imul__, __ior__
```

### Pattern 3: Missing qint In-Place Operators (Must Be Added)
**What:** qint has `__lshift__`, `__rshift__`, `__floordiv__` but NOT `__ilshift__`, `__irshift__`, `__ifloordiv__`. These must be added using the ancilla+swap pattern.

**Implementation template:**
```python
# In qint.pyx
def __ilshift__(self, int other):
    """In-place left shift: self <<= other"""
    result = self << other
    cdef qint result_qint = <qint>result
    self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
    self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
    self.bits = result_qint.bits
    return self

def __irshift__(self, int other):
    """In-place right shift: self >>= other"""
    result = self >> other
    cdef qint result_qint = <qint>result
    self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
    self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
    self.bits = result_qint.bits
    return self

def __ifloordiv__(self, other):
    """In-place floor division: self //= other"""
    result = self // other
    cdef qint result_qint = <qint>result
    self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
    self.allocated_start, result_qint.allocated_start = result_qint.allocated_start, self.allocated_start
    self.bits = result_qint.bits
    return self
```

### Pattern 4: Slice-Based Augmented Assignment
**What:** `qarray[1:3] += x` must work. Python decomposes this as:
1. `temp = qarray.__getitem__(slice(1,3))` -- returns a qarray VIEW (shared element refs)
2. `temp = temp.__iadd__(x)` -- calls qarray's whole-array `__iadd__`, which calls qint `__iadd__` on each element
3. `qarray.__setitem__(slice(1,3), temp)` -- writes elements back

**Critical insight:** Because `_create_view` returns a qarray whose `_elements` list shares references to the same qint objects, step 2 already modifies the original array's elements in-place. Step 3 writes the same references back. This means slice augmented assignment works naturally once `__setitem__` supports slices.

### Anti-Patterns to Avoid
- **Proxy objects for intercepting augmented assignment:** Don't create special wrapper objects returned by `__getitem__` -- this breaks the type contract (users expect qint, not a proxy) and is fragile.
- **Duplicating qint operator logic in qarray:** Don't reimplement the quantum gate logic. Always delegate to qint's existing `__iXXX__` methods.
- **Trying to skip `__setitem__`:** Python's augmented assignment protocol ALWAYS calls `__setitem__` for subscript operations. There is no way to avoid it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| In-place quantum addition | Custom QFT-based code in qarray | `qint.__iadd__` | Already implemented and tested |
| Ancilla+swap pattern | New swap logic | Copy existing `__iand__` pattern from qint | Proven pattern, handles allocated_start correctly |
| Multi-dimensional index resolution | New flat index calculation | Existing `qarray._multi_to_flat()` | Already handles negative indices, bounds checking |
| Slice index range computation | Custom slice logic | Python's `slice.indices()` | Standard library, handles all edge cases |

**Key insight:** This phase is almost entirely plumbing -- connecting existing qint in-place operators to qarray's subscript operations via `__setitem__`. The quantum gate logic already exists.

## Common Pitfalls

### Pitfall 1: Forgetting `allocated_start` Swap in Ancilla+Swap Pattern
**What goes wrong:** Only swapping `qubits` without swapping `allocated_start` corrupts qubit deallocation tracking.
**Why it happens:** Easy to forget the second swap line.
**How to avoid:** Always use the complete 3-line swap pattern from `__iand__`: qubits swap, allocated_start swap, bits update.
**Warning signs:** Segfaults or incorrect circuit output after `//=`, `<<=`, `>>=` on qint.

### Pitfall 2: `x = qarray[i]; x += 1` Should NOT Modify Array Element
**What goes wrong:** Users might expect `x = qarray[i]; x += 1` to modify the array, but Python's augmented assignment on a local variable does NOT call `__setitem__`.
**Why it happens:** `x += 1` calls `x.__iadd__(1)` which returns `self` (same qint object). The qint IS the same object as `qarray._elements[i]`, so the qubits ARE modified.
**How to avoid:** This is actually a semantic subtlety. For truly in-place ops (`+=`, `-=`, `^=`), `x = arr[i]; x += 1` DOES modify the array element because qint `__iadd__` modifies the actual qubits of the same object. This is different from Python ints. The CONTEXT.md says "modifies local copy only" but for qint that IS the same object. Documenting this behavior is important. For swap-based ops (`*=`, `&=`, etc.), the same applies -- the object's internal qubit references are swapped in-place.
**Warning signs:** User confusion about mutation semantics.

### Pitfall 3: `__setitem__` with Slice Must Handle Length Mismatch
**What goes wrong:** `qarray[0:2] += qarray([1,2,3])` -- the slice selects 2 elements but the operand has 3.
**Why it happens:** Shape validation happens in qarray's `__iadd__` which compares full shapes, but the view has shape (2,) while the operand has shape (3,).
**How to avoid:** The existing `_inplace_binary_op` already validates shapes. This will naturally raise ValueError because the view qarray has shape (2,) and the operand has shape (3,). No extra handling needed in `__setitem__`.
**Warning signs:** Silent data corruption if shapes aren't validated.

### Pitfall 4: Cython `cdef class` `__setitem__` Signature
**What goes wrong:** Cython has specific requirements for `__setitem__` in `cdef class` -- the method signature must match Python's expectations exactly.
**Why it happens:** Cython extension types handle special methods differently than regular Python classes.
**How to avoid:** Use `def __setitem__(self, key, value):` exactly as in the current code (just change the body). Cython handles the `sq_ass_item` / `mp_ass_subscript` slot mapping automatically.
**Warning signs:** Compilation errors if signature is wrong.

### Pitfall 5: View Semantics and `__getitem__` for Slices
**What goes wrong:** `qarray.__getitem__` with a slice returns a view via `_create_view` which shares element references. This means the view's `_elements` list contains the SAME qint objects as the original array. Augmented assignment on the view modifies the originals.
**Why it happens:** `_create_view` copies the list of references, not the qint objects themselves.
**How to avoid:** This is actually the DESIRED behavior for augmented assignment -- we WANT `qarray[1:3] += x` to modify the original array's elements.
**Warning signs:** None -- this is correct behavior.

## Code Examples

### Example 1: Minimal `__setitem__` Implementation
```python
# Source: qarray.pyx analysis (current codebase)
def __setitem__(self, key, value):
    """Set element(s) by index, enabling augmented assignment."""
    if isinstance(key, int):
        # Handle negative indices
        if key < 0:
            key += self._shape[0] if len(self._shape) == 1 else self._shape[0]
        if len(self._shape) > 1:
            # Multi-dim: single int selects sub-array (row)
            # For now, only support full element assignment for 1D
            raise NotImplementedError("Row assignment not yet supported")
        if not 0 <= key < len(self._elements):
            raise IndexError(
                f"Index {key} out of bounds for array "
                f"with {len(self._elements)} elements"
            )
        self._elements[key] = value

    elif isinstance(key, tuple):
        if all(isinstance(k, int) for k in key):
            flat_idx = self._multi_to_flat(key)
            self._elements[flat_idx] = value
        else:
            raise NotImplementedError(
                "Slice-based multi-dim setitem not yet supported"
            )

    elif isinstance(key, slice):
        start, stop, step = key.indices(len(self._elements))
        indices = list(range(start, stop, step))
        if hasattr(value, '_elements'):
            # qarray value
            if len(value._elements) != len(indices):
                raise ValueError(
                    f"Cannot assign {len(value._elements)} elements "
                    f"to slice of length {len(indices)}"
                )
            for i, idx in enumerate(indices):
                self._elements[idx] = value._elements[i]
        else:
            # Single element -- broadcast
            for idx in indices:
                self._elements[idx] = value

    else:
        raise TypeError(f"Unsupported index type: {type(key).__name__}")
```

### Example 2: Adding `__ilshift__` to qint
```python
# Source: Pattern from qint.__iand__ (line 1453-1460)
def __ilshift__(self, int other):
    """In-place left shift: self <<= other."""
    result = self << other
    cdef qint result_qint = <qint>result
    self.qubits, result_qint.qubits = result_qint.qubits, self.qubits
    self.allocated_start, result_qint.allocated_start = (
        result_qint.allocated_start, self.allocated_start
    )
    self.bits = result_qint.bits
    return self
```

### Example 3: Adding `__ilshift__` to qarray
```python
# Source: Pattern from qarray.__iadd__ (line 900-902)
def __ilshift__(self, other):
    """In-place element-wise left shift."""
    return self._inplace_binary_op(other, "__ilshift__")
```

### Example 4: End-to-End Usage (What Tests Should Verify)
```python
# 1D element augmented assignment
_c = ql.circuit()
arr = ql.array([1, 2, 3])
arr[0] += 10     # Element 0 modified in-place
arr[1] -= 1      # Element 1 modified in-place
arr[2] ^= 5      # Element 2 modified in-place

# Multi-dimensional
arr2d = ql.array([[1, 2], [3, 4]])
arr2d[0, 1] += 10  # Element at row 0, col 1 modified

# Slice-based
arr = ql.array([1, 2, 3, 4])
arr[1:3] += 10     # Elements 1 and 2 each get += 10
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `__setitem__` raises TypeError (immutable) | `__setitem__` stores elements (mutable for augmented assignment) | This phase | Enables `qarray[i] += x` syntax |
| No `__ilshift__`/`__irshift__`/`__ifloordiv__` on qint | Ancilla+swap pattern added | This phase | Enables `qint <<= n`, `qint >>= n`, `qint //= n` |
| qarray is fully immutable | qarray elements are mutable via indexed assignment | This phase | Changes the "immutable" contract to "mutable elements, immutable shape" |

**Deprecated/outdated:**
- `__setitem__` raising TypeError: Will be replaced by element storage logic
- The docstring "Immutable quantum array" should be updated to reflect mutability

## Open Questions

1. **Should direct assignment `qarray[i] = new_qint` be allowed?**
   - What we know: The CONTEXT.md focuses on augmented assignment, not direct assignment
   - What's unclear: Whether `__setitem__` should also permit `arr[i] = qint(5, width=8)` (replacing an element entirely)
   - Recommendation: Allow it -- `__setitem__` needs to work anyway, and there's no reason to restrict it to only augmented assignment. Restricting it would require complex detection logic and provide no benefit.

2. **What about `__delitem__`?**
   - What we know: Currently raises TypeError
   - What's unclear: Whether deletion should also be enabled
   - Recommendation: Keep `__delitem__` raising TypeError. Deletion changes array shape, which is not in scope.

3. **qbool elements and augmented assignment**
   - What we know: qbool has limited in-place operators (mainly `^=` via `__ixor__`)
   - What's unclear: Which augmented assignments make sense for qbool arrays
   - Recommendation: Allow whatever qbool's existing `__iXXX__` methods support. Don't add new qbool operators.

4. **Interaction with uncomputation (Phase 41)**
   - What we know: Phase 41 dependency tracking is in qint operators. Swap-based ops create intermediate qint objects that may trigger uncomputation on GC.
   - What's unclear: Whether augmented assignment on array elements could interfere with uncomputation of the intermediate results.
   - Recommendation: Test carefully. The intermediate qint from swap-based ops (the one holding old qubits) must be released correctly. Since it's a local variable in `__iXXX__`, Python GC will handle it. But verify with the `verify_circuit` fixture.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis**: `qarray.pyx` (lines 160-1071) - full qarray implementation
- **Codebase analysis**: `qint.pyx` (lines 855-876, 926-946, 1282-1315, 1434-1460, 1578-1604, 1713-1768) - all existing `__iXXX__` methods
- **Codebase analysis**: `qint.pyx` (lines 1019-1105) - `__lshift__`, `__rshift__` (no `__ilshift__`, `__irshift__`)
- **Codebase analysis**: `qint.pyx` (lines 2447-2521) - `__floordiv__` (no `__ifloordiv__`)
- **Python Data Model**: augmented assignment protocol (`__getitem__` + `__iXXX__` + `__setitem__`)
- **Test patterns**: `test_qarray_elementwise.py`, `conftest.py` verify_circuit fixture

### Secondary (MEDIUM confidence)
- **Cython documentation**: `cdef class` special method handling for `__setitem__` -- matches standard Python slot mapping

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All based on existing codebase patterns and Python language spec
- Architecture: HIGH - Direct analysis of qarray.pyx and qint.pyx reveals exact implementation path
- Pitfalls: HIGH - Based on specific code patterns found in the codebase

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (stable -- internal project, no external dependency changes expected)
