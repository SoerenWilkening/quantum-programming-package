# Phase 23: Array Reductions - Research

**Researched:** 2026-01-29
**Domain:** Quantum array reduction operations (internal implementation)
**Confidence:** HIGH

## Summary

Phase 23 implements reduction operations on qarray using existing quantum operations from the codebase. All operations leverage existing qint operators (&, |, ^, +) that already allocate fresh qubits and handle dependency tracking. The research focused on internal codebase patterns rather than external libraries since this is entirely internal implementation.

Key findings:
- Existing qint operators (&, |, ^, +) already implement out-of-place semantics with fresh qubit allocation
- Operations track dependencies via add_dependency() for proper uncomputation order
- qubit_saving mode is checked via _get_qubit_saving_mode() accessor function
- qarray uses flattened storage with iteration yielding elements in row-major order
- Cython cdef class methods added directly to .pyx file (no includes for methods)
- Module-level functions exposed via __init__.py imports

**Primary recommendation:** Implement reductions as methods on qarray cdef class, using existing qint operators in either tree or linear chain pattern based on qubit_saving mode.

## Standard Stack

This phase uses only internal codebase components - no external libraries.

### Core Components
| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| qarray | src/quantum_language/qarray.pyx | Array container with flattened storage | Phase 22 foundation |
| qint | src/quantum_language/qint.pyx | Quantum integer with &, \|, ^, + operators | Core quantum type |
| qbool | src/quantum_language/qbool.pyx | 1-bit qint subclass | Boolean operations |
| _core.pyx | src/quantum_language/_core.pyx | Global state via accessor functions | State management pattern |

### Existing Operators Used
| Operator | Implementation | Semantics | Dependency Tracking |
|----------|---------------|-----------|---------------------|
| qint.__and__ | qint.pyx:1060 | Allocates fresh result qint, bitwise AND | Yes - result.add_dependency(self/other) |
| qint.__or__ | qint.pyx:1186 | Allocates fresh result qint, bitwise OR | Yes - result.add_dependency(self/other) |
| qint.__xor__ | qint.pyx:1312 | Allocates fresh result qint, bitwise XOR | Yes - result.add_dependency(self/other) |
| qint.__add__ | qint.pyx:740 | Allocates fresh result qint, addition | Yes (via iadd internals) |
| qint.__radd__ | qint.pyx:772 | Reverse addition for int + qint | Same as __add__ |

### Configuration Access
| Option | Accessor | Purpose |
|--------|----------|---------|
| qubit_saving | _get_qubit_saving_mode() | Returns bool - True=linear chain, False=tree |

**Installation:**
No external dependencies - all internal to quantum_language package.

## Architecture Patterns

### Pattern 1: Adding Methods to qarray cdef Class
**What:** Methods added directly to qarray.pyx, no separate include files for cdef classes.
**When to use:** All reduction methods (all(), any(), parity(), sum()).

**Example from existing code:**
```python
# In qarray.pyx (after existing methods)
cdef class qarray:
    # ... existing code ...

    def all(self):
        """AND reduction: reduce array to single value."""
        # Implementation here
        return result
```

**Key insight:** Unlike C includes, Cython cdef class methods must be in the .pyx file directly. The qint.pyx file is ~2400 lines with all methods inline.

### Pattern 2: Reduction Algorithm Structure
**What:** Conditional algorithm based on qubit_saving mode.

**Tree reduction (qubit_saving=False, default):**
```python
from quantum_language._core import _get_qubit_saving_mode

def _reduce_operation(self, op_func):
    """Generic reduction template.

    Args:
        op_func: Binary operator function (e.g., lambda a, b: a & b)
    """
    qubit_saving = _get_qubit_saving_mode()

    if qubit_saving:
        # Linear chain: O(n) depth, minimal qubits
        result = self._elements[0]
        for elem in self._elements[1:]:
            result = op_func(result, elem)
        return result
    else:
        # Pairwise tree: O(log n) depth, fresh qubits per level
        current_level = list(self._elements)
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    # Pair reduction
                    next_level.append(op_func(current_level[i], current_level[i+1]))
                else:
                    # Odd element carries forward
                    next_level.append(current_level[i])
            current_level = next_level
        return current_level[0]
```

**Linear chain (qubit_saving=True):**
- Accumulate sequentially: result = elem[0] op elem[1] op elem[2] ...
- O(n) circuit depth
- Minimal qubit usage (reuse accumulator)

### Pattern 3: Type-Specific Return Values
**What:** Return type varies by input dtype and operation.

**Implementation pattern:**
```python
def all(self):
    """AND reduction."""
    if len(self._elements) == 0:
        raise ValueError("cannot reduce empty array")
    if len(self._elements) == 1:
        return self._elements[0]  # Single element - no operations

    # Use generic reduction with AND operator
    return self._reduce_operation(lambda a, b: a & b)

def sum(self, width=None):
    """Sum reduction with optional width override."""
    if len(self._elements) == 0:
        raise ValueError("cannot reduce empty array")
    if len(self._elements) == 1:
        return self._elements[0]

    # For qbool arrays: popcount with special width calculation
    if self._dtype == qbool:
        import math
        if width is None:
            width = math.ceil(math.log2(len(self._elements) + 1))
        # Convert each qbool to qint, then sum
        # (qbool inherits from qint, so addition works)
    else:
        # For qint arrays: default width = element width
        if width is None:
            width = self._width

    # Perform reduction with addition
    result = self._reduce_operation(lambda a, b: a + b)

    # Ensure result has correct width (may need to resize)
    if result.bits != width:
        # Create new qint with desired width
        from quantum_language.qint import qint
        resized = qint(width=width)
        # Copy value (implementation detail for planner)

    return result
```

### Pattern 4: Module-Level Function Exposure
**What:** Expose reduction operations both as methods and module-level functions.

**In __init__.py:**
```python
# After existing imports
from quantum_language.qarray import qarray

# Module-level reduction functions
def all(arr):
    """AND reduction of array.

    Equivalent to arr.all()
    """
    if not isinstance(arr, qarray):
        raise TypeError("all() requires qarray argument")
    return arr.all()

def any(arr):
    """OR reduction of array."""
    if not isinstance(arr, qarray):
        raise TypeError("any() requires qarray argument")
    return arr.any()

def parity(arr):
    """XOR reduction of array."""
    if not isinstance(arr, qarray):
        raise TypeError("parity() requires qarray argument")
    return arr.parity()

# sum() not needed - Python built-in sum() works via __radd__
# But expose as module function for consistency
def sum(arr, width=None):
    """Sum reduction of array."""
    if not isinstance(arr, qarray):
        raise TypeError("sum() requires qarray argument")
    return arr.sum(width=width)

# Update __all__
__all__ = [
    # ... existing exports ...
    "all", "any", "parity", "sum",
]
```

### Pattern 5: Python sum() Built-in Support
**What:** Python's built-in sum() works via __radd__ protocol.

**How it works:**
```python
# Python's sum() does:
# sum(iterable, start=0)
# => start + elem[0] + elem[1] + ...
# => 0.__add__(elem[0])  # int has no qint overload, fails
# => elem[0].__radd__(0)  # qint has __radd__, succeeds
# => result + elem[1]
# => etc.

# qint already has __radd__ (line 772 in qint.pyx)
# So sum(arr) where arr is qarray works automatically via iteration
```

**Implementation:**
```python
# In qarray.pyx, add __radd__ method:
def __radd__(self, other):
    """Support sum(arr) via Python's built-in sum().

    When sum() is called on qarray, it iterates elements.
    For sum to work: sum([a,b,c]) = 0 + a + b + c
    But 0.__add__(qint) fails, so qint.__radd__(0) is called.

    For qarray, we redirect to arr.sum() method.
    """
    if other == 0:
        # sum() starting with 0
        return self.sum()
    else:
        return NotImplemented
```

### Anti-Patterns to Avoid
- **Don't manually manage qubits:** Use existing qint operators that handle allocation/tracking.
- **Don't build custom AND/OR/XOR circuits:** Operators already exist and are optimized.
- **Don't ignore qubit_saving mode:** Users expect depth/qubit tradeoff to be respected.
- **Don't modify input array elements:** All reductions must allocate fresh result qubits.

## Don't Hand-Roll

Problems with existing solutions in the codebase:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bitwise AND operation | Custom CNOT/Toffoli circuit | qint.__and__() | Already handles width mismatch, classical/quantum, dependency tracking, layer tracking |
| Bitwise OR operation | Custom circuit | qint.__or__() | Handles CQ_or vs Q_or, width inference, qubit allocation |
| Bitwise XOR operation | Custom CNOT chain | qint.__xor__() | Handles copy semantics (target ^= source), multiple XOR applications |
| Quantum addition | Custom adder circuit | qint.__add__() | Handles width inference, classical constants, modular wrap |
| Dependency tracking | Manual weakref management | result.add_dependency(parent) | Established pattern with cycle detection (line 317-335) |
| Qubit allocation | Direct allocator_alloc calls | Let qint() constructor handle it | Automatic tracking, uncomputation support |
| Global state access | Direct module variable import | _get_qubit_saving_mode() accessor | Cython cdef module variables cannot be cimported |

**Key insight:** The quantum operators already implement out-of-place semantics with fresh qubit allocation. Reductions are just applying these operators in tree or linear patterns - don't rebuild the operators.

## Common Pitfalls

### Pitfall 1: Attempting to Modify Array Elements In-Place
**What goes wrong:** Trying to use in-place operators (&=, |=, ^=, +=) to reduce without allocating result.
**Why it happens:** Tempting to think "accumulate into first element" saves qubits.
**How to avoid:** Always use out-of-place operators (a & b, not a &= b) to get fresh result qubits. Linear chain mode already minimizes qubits via sequential operations.
**Warning signs:** Tests fail with "qubits modified unexpectedly" or dependency tracking breaks.

### Pitfall 2: Ignoring Single-Element and Empty Array Edge Cases
**What goes wrong:** Tree reduction logic fails for n=0 or n=1 arrays.
**Why it happens:** Reduction algorithms assume pairs of elements.
**How to avoid:** Check length upfront:
```python
if len(self._elements) == 0:
    raise ValueError("cannot reduce empty array")
if len(self._elements) == 1:
    return self._elements[0]  # No operations needed
```
**Warning signs:** IndexError or returning wrong result for single-element arrays.

### Pitfall 3: Width Mismatch in sum() for qbool Arrays
**What goes wrong:** Summing qbool array without width parameter produces wrong result width.
**Why it happens:** qbool inherits from qint with width=1, but popcount needs log2(n) bits.
**How to avoid:** Special-case qbool arrays:
```python
if self._dtype == qbool:
    import math
    if width is None:
        width = math.ceil(math.log2(len(self._elements) + 1))
```
**Warning signs:** sum() result overflows for large qbool arrays.

### Pitfall 4: Assuming Cython Include Works for cdef Class Methods
**What goes wrong:** Attempting to use include "qarray_methods.pxi" for reduction methods fails.
**Why it happens:** Misunderstanding of Cython include semantics - includes are textual, work for module-level code, not class methods.
**How to avoid:** Add all methods directly to qarray.pyx. The qint.pyx precedent (2400+ lines, all inline) confirms this pattern.
**Warning signs:** Cython compilation errors "cdef class methods cannot be in included files".

### Pitfall 5: Forgetting Dependency Tracking for Tree Intermediate Results
**What goes wrong:** Intermediate tree level results get garbage collected before reduction completes.
**Why it happens:** Tree creates temporary qints at each level that must stay alive until final result is computed.
**How to avoid:** Operators automatically call add_dependency(). Just ensure intermediate results are referenced in next_level list until consumed.
**Warning signs:** Uncomputation happens prematurely, breaking circuit correctness.

## Code Examples

Verified patterns from the codebase:

### Using Existing qint Operators for Reduction
```python
# Source: src/quantum_language/qint.pyx:1060-1152 (__and__)
# Pattern: Operators allocate fresh result with dependency tracking

# In qarray reduction:
def all(self):
    """AND reduction using existing qint.__and__."""
    if len(self._elements) == 0:
        raise ValueError("cannot reduce empty array")
    if len(self._elements) == 1:
        return self._elements[0]

    # Tree reduction
    current_level = list(self._elements)
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            if i + 1 < len(current_level):
                # qint.__and__ allocates result, tracks dependencies
                next_level.append(current_level[i] & current_level[i+1])
            else:
                next_level.append(current_level[i])
        current_level = next_level
    return current_level[0]
```

### Checking qubit_saving Mode
```python
# Source: src/quantum_language/_core.pyx:122-129
# Accessor pattern for global state

from quantum_language._core import _get_qubit_saving_mode

def _reduce_with_op(self, op_func):
    """Generic reduction respecting qubit_saving mode."""
    if _get_qubit_saving_mode():
        # Linear chain: O(n) depth
        result = self._elements[0]
        for elem in self._elements[1:]:
            result = op_func(result, elem)
        return result
    else:
        # Tree: O(log n) depth
        # ... tree implementation ...
```

### Flattened Iteration from qarray
```python
# Source: src/quantum_language/qarray.pyx:270-285
# qarray.__iter__ yields flattened elements in row-major order

def sum(self):
    """Sum reduction using iteration."""
    elements = list(self)  # Flattened iteration
    # Now reduce elements...
```

### Module-Level Function Pattern
```python
# Source: src/quantum_language/__init__.py:55-84
# Pattern: Wrapper function that delegates to class method

def array(data=None, *, width=None, dtype=None, dim=None):
    """Wrapper function for qarray construction."""
    if dtype is None:
        dtype = qint
    return qarray(data, width=width, dtype=dtype, dim=dim)

# Apply same pattern for reductions:
def all(arr):
    """Module-level all() delegates to qarray.all()."""
    if not isinstance(arr, qarray):
        raise TypeError("all() requires qarray")
    return arr.all()
```

### Supporting Python's sum() Built-in
```python
# Source: qint.pyx:772-799 (__radd__)
# Pattern exists for qint - adapt for qarray

# In qarray.pyx:
def __radd__(self, other):
    """Support sum(arr) via built-in sum()."""
    if other == 0:
        # sum() starts with 0, redirect to our sum()
        return self.sum()
    else:
        return NotImplemented
```

### Width Calculation for qbool Popcount
```python
# Manual verification shows correct formula:
# For n qbools, sum range is 0..n
# Minimum bits = ceil(log2(n+1))

import math

def sum(self, width=None):
    """Sum with automatic width for qbool popcount."""
    if self._dtype == qbool:
        if width is None:
            n = len(self._elements)
            width = math.ceil(math.log2(n + 1))
        # Now perform sum with this width...
```

## State of the Art

No version changes - this is internal implementation using stable quantum operations.

| Component | Current State | Notes |
|-----------|---------------|-------|
| qint operators | Stable since Phase 6 (bitwise) | Out-of-place semantics established |
| qarray | Phase 22 (current) | Flattened storage, iteration working |
| qubit_saving | Established pattern | Boolean flag via _get_qubit_saving_mode() |
| Dependency tracking | Phase 18 pattern | add_dependency() with cycle detection |

**Deprecated/outdated:**
- None - all patterns are current.

## Open Questions

Things that couldn't be fully resolved:

1. **Width adjustment for sum() result**
   - What we know: qint constructor accepts width parameter, operators preserve width
   - What's unclear: How to resize qint result width after reduction (if needed)
   - Recommendation: sum() implementation should construct final qint with target width upfront, or accept width mismatch (result.bits may differ from requested width). Planner should investigate if width adjustment is needed or if width parameter just ensures adequate bits during reduction.

2. **Optimal tree vs chain threshold**
   - What we know: User can set qubit_saving mode globally
   - What's unclear: If there's an optimal array size where linear chain becomes better even without qubit_saving
   - Recommendation: Always respect qubit_saving mode as documented. Don't add auto-detection logic this phase.

3. **Multi-dimensional array flattening verification**
   - What we know: qarray.__iter__ yields flattened elements (line 270-285)
   - What's unclear: Whether order is guaranteed row-major (stated in CONTEXT but not explicitly tested)
   - Recommendation: Trust Phase 22 implementation - CONTEXT.md states "flatten before reduction (row-major order, matching iteration order)". Tests verify iteration order implicitly.

## Sources

### Primary (HIGH confidence)
- src/quantum_language/qint.pyx - Lines 740-799 (__add__, __radd__), 1060-1428 (__and__, __or__, __xor__)
- src/quantum_language/qarray.pyx - Lines 1-634 (complete implementation)
- src/quantum_language/_core.pyx - Lines 122-129 (_get_qubit_saving_mode accessor)
- src/quantum_language/__init__.py - Lines 55-84 (module-level function pattern)
- .planning/phases/23-array-reductions/23-CONTEXT.md - User decisions and requirements
- .planning/phases/22-array-class-foundation/22-CONTEXT.md - qarray design decisions

### Secondary (MEDIUM confidence)
- tests/test_qarray.py - Test patterns for qarray validation
- qint.pyx lines 317-335 - Dependency tracking implementation (add_dependency)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components verified in codebase
- Architecture: HIGH - Patterns extracted from existing implementations
- Pitfalls: HIGH - Based on Cython limitations and quantum operation semantics

**Research date:** 2026-01-29
**Valid until:** 90+ days (stable internal codebase, no external dependencies)
