# Phase 22: Array Class Foundation - Research

**Researched:** 2026-01-29
**Domain:** Cython extension types, Python container protocols, NumPy-style array API
**Confidence:** HIGH

## Summary

Array class implementation involves creating a Cython extension type that wraps a collection of quantum objects (qint or qbool) with NumPy-like semantics. The codebase already has a simple array function that returns Python lists but needs a proper array class with shape tracking, multi-dimensional indexing, view semantics for slices, and immutability constraints.

Based on Phase 21's package structure (src/quantum_language/ with separate .pyx files for each type), the array class should be implemented as `qarray.pyx` with proper `.pxd` declaration files for C-level sharing. The standard approach combines **Cython extension types** with **Python container protocols** (collections.abc.Sequence), **NumPy-inspired API patterns** (shape inference, multi-dimensional indexing), and **view semantics** for memory-efficient slicing.

Key technical challenges: (1) multi-dimensional indexing with tuple unpacking in `__getitem__`, (2) shape validation for jagged arrays, (3) width inference from maximum value using Python's `bit_length()`, (4) immutability enforcement by raising TypeError in `__setitem__`, and (5) view implementation that shares underlying qint objects.

**Primary recommendation:** Create `qarray` Cython extension type inheriting from collections.abc.Sequence, store flattened list of qint/qbool objects with shape tuple, implement `__getitem__` for both indexing and slicing with view returns, use Python's `bit_length()` for width inference with INTEGERSIZE (8) as minimum, validate homogeneity at construction, detect jagged arrays via recursive shape checking, and format repr as compact single-line with truncation for large arrays.

## Standard Stack

The established libraries/tools for Python array-like classes in Cython:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cython | 3.0+ | Extension type implementation | Already in use (Phase 21), standard for Python/C integration |
| collections.abc | stdlib | Container protocol interfaces | Official Python ABCs ensure proper container behavior |
| NumPy | latest | Reference for array API patterns | De facto standard for array semantics, already a dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| reprlib | stdlib | Truncated repr formatting | For large array display (avoid excessive output) |
| typing | stdlib | Type hints for array parameters | Documentation and IDE support |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Cython extension | Pure Python class | Pure Python simpler but loses C-level integration with qint/qbool |
| collections.abc.Sequence | Custom implementation | Sequence ABC provides standard protocol guarantees |
| Flat storage + shape | NumPy ndarray wrapper | NumPy wrapper adds complexity, flat storage sufficient for Phase 22 |

**Installation:**
```bash
# All dependencies already in project (Cython, NumPy in pyproject.toml)
pip install -e .  # Editable install includes new qarray module
```

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
├── __init__.py              # Add: from .qarray import qarray
├── qarray.pyx               # NEW: Array class implementation (~250 lines)
├── qarray.pxd               # NEW: C-level declarations for cimport
├── qint.pyx                 # Existing: qint class
├── qint.pxd                 # Existing: qint declarations
├── qbool.pyx                # Existing: qbool class
└── _core.pyx                # Existing: utilities (remove old array function)
```

### Pattern 1: Cython Extension Type with Container Protocol
**What:** Extension type implementing collections.abc.Sequence for standard Python container behavior
**When to use:** When creating array-like classes that integrate with Python's iteration and indexing protocols

**Example:**
```python
# Source: https://cython.readthedocs.io/en/latest/src/userguide/extension_types.html
# Source: https://docs.python.org/3/library/collections.abc.html

# qarray.pyx
from collections.abc import Sequence

cdef class qarray(Sequence):
    """Immutable quantum array with NumPy-style indexing."""

    cdef list _elements      # Flattened list of qint/qbool objects
    cdef tuple _shape        # Shape tuple (e.g., (3, 4) for 2D)
    cdef object _dtype       # qint or qbool type
    cdef int _width          # Element bit width (for qint arrays)

    def __init__(self, data, width=None, dtype=None):
        # Validate and initialize
        pass

    def __len__(self):
        """Return total element count (flattened)."""
        return len(self._elements)

    def __getitem__(self, key):
        """Support indexing and slicing with views."""
        # Handle int, slice, tuple of indices/slices
        pass

    def __iter__(self):
        """Iterate over flattened elements."""
        return iter(self._elements)

    def __setitem__(self, key, value):
        """Prevent mutation - arrays are immutable."""
        raise TypeError("qarray is immutable")
```

### Pattern 2: Multi-Dimensional Indexing with Tuple Unpacking
**What:** Handle NumPy-style indexing like `A[i,j]` which Python passes as tuple `(i, j)` to `__getitem__`
**When to use:** When supporting multi-dimensional array access patterns

**Example:**
```python
# Source: https://medium.com/@beef_and_rice/mastering-pythons-getitem-and-slicing-c94f85415e1c
# Source: https://gaopinghuang0.github.io/2018/11/17/python-slicing

def __getitem__(self, key):
    # Single index: A[0] -> key is int
    if isinstance(key, int):
        if key < 0:
            key += len(self._elements)
        if not 0 <= key < len(self._elements):
            raise IndexError("Index out of bounds")
        return self._elements[key]

    # Single slice: A[1:3] -> key is slice
    elif isinstance(key, slice):
        indices = range(*key.indices(len(self._elements)))
        return self._create_view([self._elements[i] for i in indices])

    # Multi-dimensional: A[i,j] -> key is tuple
    elif isinstance(key, tuple):
        # Convert multi-dimensional index to flat index
        flat_idx = self._multi_to_flat(key)
        if isinstance(flat_idx, int):
            return self._elements[flat_idx]
        else:
            # Slicing in multiple dimensions returns view
            return self._create_view([self._elements[i] for i in flat_idx])

    else:
        raise TypeError(f"Invalid index type: {type(key)}")

def _multi_to_flat(self, indices):
    """Convert (i, j) indices to flat index for row-major storage."""
    # Example: shape (3, 4), index (1, 2) -> flat index 1*4 + 2 = 6
    flat = 0
    stride = 1
    for dim_size in reversed(self._shape):
        flat += indices[-1] * stride
        stride *= dim_size
        indices = indices[:-1]
    return flat
```

### Pattern 3: Shape Detection from Nested Lists
**What:** Recursively detect array shape and validate no jagged arrays (like NumPy's error handling)
**When to use:** During array construction from Python list/NumPy array

**Example:**
```python
# Source: https://numpy.org/devdocs/user/absolute_beginners.html
# Source: https://numpy.org/doc/stable/user/basics.copies.html

def _detect_shape(data):
    """Detect shape from nested lists, raise ValueError for jagged arrays.

    Returns:
        tuple: Shape tuple (e.g., (2, 3) for [[1,2,3], [4,5,6]])

    Raises:
        ValueError: If array is jagged (inconsistent inner lengths)
    """
    if not isinstance(data, (list, tuple)):
        return ()  # Scalar

    if len(data) == 0:
        return (0,)

    # Check first element to determine if nested
    if isinstance(data[0], (list, tuple)):
        # Recursive case: nested structure
        first_inner_shape = _detect_shape(data[0])

        # Validate all inner elements have same shape
        for i, elem in enumerate(data[1:], 1):
            elem_shape = _detect_shape(elem)
            if elem_shape != first_inner_shape:
                raise ValueError(
                    f"Jagged array detected: element 0 has shape {first_inner_shape}, "
                    f"but element {i} has shape {elem_shape}. "
                    f"All sub-arrays must have the same shape."
                )

        return (len(data),) + first_inner_shape
    else:
        # Base case: flat list
        return (len(data),)

def _flatten(data):
    """Flatten nested list structure to 1D list."""
    if not isinstance(data, (list, tuple)):
        return [data]

    result = []
    for elem in data:
        result.extend(_flatten(elem))
    return result
```

### Pattern 4: Width Inference from Maximum Value
**What:** Calculate minimum bits needed to represent largest value, with INTEGERSIZE as floor
**When to use:** When creating array from values without explicit width parameter

**Example:**
```python
# Source: https://python-reference.readthedocs.io/en/latest/docs/ints/bit_length.html
# Source: Existing qint.pyx lines 144-163 (auto-width implementation)

def _infer_width(values, default_width=8):
    """Infer minimum bit width from values.

    Args:
        values: List of integer values
        default_width: Minimum width (INTEGERSIZE = 8)

    Returns:
        int: Bit width (>= default_width)

    Examples:
        >>> _infer_width([1, 2, 3])  # max=3 -> 2 bits, but returns 8 (default)
        8
        >>> _infer_width([0, 255, 100])  # max=255 -> 8 bits
        8
        >>> _infer_width([0, 1000])  # max=1000 -> 10 bits
        10
    """
    if not values:
        return default_width

    max_val = max(abs(v) for v in values)

    if max_val == 0:
        required_bits = 1
    else:
        # Python's bit_length() returns minimum bits for unsigned representation
        required_bits = max_val.bit_length()

    # Never go below default width (consistency with qint scalar behavior)
    return max(required_bits, default_width)
```

### Pattern 5: Immutability via __setitem__ Prevention
**What:** Raise TypeError when attempting element assignment to enforce immutability
**When to use:** When creating immutable array-like containers (like tuples)

**Example:**
```python
# Source: https://realpython.com/python-mutable-vs-immutable-types/
# Source: https://docs.python.org/3/reference/datamodel.html

def __setitem__(self, key, value):
    """Prevent mutation - arrays are immutable.

    Raises:
        TypeError: Always (arrays cannot be modified after creation)

    Examples:
        >>> arr = qarray([1, 2, 3])
        >>> arr[0] = 5  # Raises TypeError
        TypeError: 'qarray' object does not support item assignment
    """
    raise TypeError("'qarray' object does not support item assignment")

def __delitem__(self, key):
    """Prevent deletion - arrays are immutable."""
    raise TypeError("'qarray' object does not support item deletion")
```

### Pattern 6: View Semantics for Slicing
**What:** Return lightweight view object that shares underlying qint objects (not deep copy)
**When to use:** For memory-efficient slicing (NumPy-style views vs copies)

**Example:**
```python
# Source: https://numpy.org/doc/stable/user/basics.copies.html
# Source: https://cython-guidelines.readthedocs.io/en/latest/articles/memoryviews_are_views_not_arrays.html

def __getitem__(self, key):
    if isinstance(key, slice):
        # Create view that shares elements (not copies)
        indices = range(*key.indices(len(self._elements)))
        view_elements = [self._elements[i] for i in indices]

        # Return new qarray that shares same qint objects
        return qarray._from_elements(
            view_elements,
            shape=(len(view_elements),),
            dtype=self._dtype,
            width=self._width
        )
    # ... handle other cases

@classmethod
def _from_elements(cls, elements, shape, dtype, width):
    """Internal constructor for creating views.

    Shares qint/qbool objects from parent array (not deep copy).
    """
    arr = cls.__new__(cls)
    arr._elements = elements  # Shared reference
    arr._shape = shape
    arr._dtype = dtype
    arr._width = width
    return arr
```

### Pattern 7: Compact repr with Truncation
**What:** Format array representation with type info and truncation for large arrays
**When to use:** For readable output that doesn't flood terminal with thousands of elements

**Example:**
```python
# Source: https://numpy.org/doc/stable/reference/generated/numpy.array_repr.html
# Source: https://docs.python.org/3/library/reprlib.html

def __repr__(self):
    """Compact format: ql.array<qint:8, shape=(3,)>[1, 2, 3]

    Truncates large arrays with ellipsis (...) NumPy-style.
    """
    dtype_name = self._dtype.__name__  # "qint" or "qbool"

    # Format type info
    if dtype_name == "qint":
        type_info = f"<qint:{self._width}, shape={self._shape}>"
    else:
        type_info = f"<qbool, shape={self._shape}>"

    # Format elements with truncation
    threshold = 6  # Show first 3 and last 3 if len > threshold

    if len(self._elements) <= threshold:
        # Small array: show all elements
        elem_str = ", ".join(str(e) for e in self._elements)
    else:
        # Large array: truncate with ellipsis
        first = ", ".join(str(e) for e in self._elements[:3])
        last = ", ".join(str(e) for e in self._elements[-3:])
        elem_str = f"{first}, ..., {last}"

    # Multi-dimensional: use nested brackets
    if len(self._shape) > 1:
        elem_str = self._format_nested(self._elements, self._shape)

    return f"ql.array{type_info}[{elem_str}]"

def _format_nested(self, elements, shape):
    """Format multi-dimensional array with nested brackets."""
    if len(shape) == 1:
        return ", ".join(str(e) for e in elements)

    # Recursive formatting for each dimension
    stride = 1
    for s in shape[1:]:
        stride *= s

    chunks = []
    for i in range(0, len(elements), stride):
        chunk = elements[i:i+stride]
        chunks.append("[" + self._format_nested(chunk, shape[1:]) + "]")

    return ", ".join(chunks)
```

### Anti-Patterns to Avoid
- **Deep copying on slice:** Violates NumPy semantics and wastes memory - use views instead
- **Mutable arrays:** Adds complexity to quantum circuit semantics - keep immutable
- **Shape-per-dimension storage:** Complicates indexing - use flat storage with shape tuple
- **Custom indexing syntax:** Break Python conventions - stick to `__getitem__` protocol
- **Silent type coercion:** Mixed qint/qbool should error loudly at construction - validate early

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Container protocols | Custom iteration/indexing | collections.abc.Sequence | Ensures standard Python behavior, __contains__, __reversed__ free |
| Shape validation | Ad-hoc list checking | NumPy's approach (recursive shape detection) | Handles edge cases (jagged arrays, empty arrays) correctly |
| Multi-dimensional indexing | Custom tuple parsing | Standard __getitem__ with tuple key | Python passes `A[i,j]` as tuple automatically |
| Width calculation | Manual bit counting | Python's int.bit_length() | Built-in, optimized, handles all integer sizes |
| Repr truncation | String slicing | reprlib (optional) or threshold-based approach | NumPy's established pattern familiar to users |

**Key insight:** Python's container protocols (collections.abc) provide most boilerplate methods for free if you implement core methods (`__len__`, `__getitem__`, `__iter__`). NumPy's API patterns are familiar to scientific Python users - don't reinvent.

## Common Pitfalls

### Pitfall 1: Forgetting Negative Index Handling
**What goes wrong:** `arr[-1]` raises IndexError or returns wrong element
**Why it happens:** `__getitem__` receives negative indices directly from Python
**How to avoid:** Always normalize negative indices: `if key < 0: key += len(self._elements)`
**Warning signs:** Unit tests with `arr[-1]` failing unexpectedly

### Pitfall 2: Slice.indices() Misunderstanding
**What goes wrong:** Slices with step or out-of-bounds indices behave incorrectly
**Why it happens:** Manual slice handling doesn't cover edge cases (negative step, None values)
**How to avoid:** Always use `slice.indices(length)` which returns normalized (start, stop, step)
**Warning signs:** `arr[::2]` or `arr[::-1]` not working as expected

```python
# WRONG: Manual slice handling
start = key.start if key.start is not None else 0
stop = key.stop if key.stop is not None else len(self._elements)

# RIGHT: Use slice.indices()
start, stop, step = key.indices(len(self._elements))
indices = range(start, stop, step)
```

### Pitfall 3: Reference Counting with Cython Objects
**What goes wrong:** Returning qint from `__getitem__` causes reference count issues or crashes
**Why it happens:** Cython extension types need proper reference management
**How to avoid:** Return Python objects directly - Cython handles refcounting automatically for extension types
**Warning signs:** Segfaults when accessing array elements, memory leaks

```python
# CORRECT for Cython extension types
def __getitem__(self, int idx):
    return self._elements[idx]  # Cython auto-increments refcount
```

### Pitfall 4: Jagged Array Silent Acceptance
**What goes wrong:** `qarray([[1,2], [3]])` creates array without error, later indexing fails
**Why it happens:** Not validating consistent sub-array shapes during construction
**How to avoid:** Validate shape recursively during `__init__`, raise ValueError immediately
**Warning signs:** Multi-dimensional indexing crashes or returns wrong elements

### Pitfall 5: Width Inference Narrower Than qint Default
**What goes wrong:** `qarray([1, 2])` creates 2-bit array, inconsistent with `qint(1)` (8-bit default)
**Why it happens:** Using `max_value.bit_length()` directly without minimum constraint
**How to avoid:** Floor width at INTEGERSIZE (8): `width = max(inferred_width, 8)`
**Warning signs:** Array elements have different width than standalone qint scalars

### Pitfall 6: Forgetting collections.abc Import
**What goes wrong:** Code compiles but `isinstance(arr, Sequence)` returns False
**Why it happens:** Inheritance from collections.abc.Sequence not registered
**How to avoid:** Import and inherit: `from collections.abc import Sequence; class qarray(Sequence):`
**Warning signs:** Standard library functions expecting sequences reject qarray instances

## Code Examples

Verified patterns from official sources:

### Example 1: Basic qarray Construction
```python
# From requirements ARR-04, ARR-05, ARR-06
import quantum_language as ql
import numpy as np

# Auto-width from Python list (uses max value)
arr1 = ql.array([1, 2, 3])           # width=8 (default floor)
arr2 = ql.array([0, 255, 100])       # width=8 (fits in 8 bits)
arr3 = ql.array([0, 1000])           # width=10 (1000 needs 10 bits)

# Explicit width parameter
arr4 = ql.array([1, 2, 3], width=16) # width=16 (explicit)

# From NumPy array (respects dtype)
np_arr = np.array([1, 2, 3], dtype=np.int32)
arr5 = ql.array(np_arr)              # width=32 (from NumPy dtype)

# From dimensions with dtype
arr6 = ql.array(dim=(3, 3), dtype=ql.qint)  # 3x3 array of qint
arr7 = ql.array(dim=5, dtype=ql.qbool)      # 1D array of 5 qbool
```

### Example 2: Multi-Dimensional Indexing
```python
# From requirements PYI-03, PYI-04
A = ql.array([[1, 2, 3], [4, 5, 6]])  # shape=(2, 3)

# Single element access
elem = A[0, 1]      # Returns qint with value 2
elem = A[1, 2]      # Returns qint with value 6

# Row/column access (returns view)
row = A[0]          # Returns qarray([1, 2, 3]), shape=(3,)
col = A[:, 1]       # Returns qarray([2, 5]), shape=(2,) - column slice

# Slicing (returns view)
sub = A[0:1, 1:3]   # Returns qarray([[2, 3]]), shape=(1, 2)
```

### Example 3: Iteration and len()
```python
# From requirements PYI-01, PYI-02
arr = ql.array([[1, 2], [3, 4]])

# len() returns flattened length
assert len(arr) == 4

# Iteration over flattened elements
for x in arr:
    print(x)  # Prints: qint(1), qint(2), qint(3), qint(4)

# Enumerate also works (collections.abc.Sequence provides it)
for i, x in enumerate(arr):
    print(f"Index {i}: {x}")
```

### Example 4: Immutability Enforcement
```python
# From CONTEXT.md: arrays are immutable
arr = ql.array([1, 2, 3])

# Assignment raises TypeError
try:
    arr[0] = 5
except TypeError as e:
    print(e)  # "'qarray' object does not support item assignment"

# Indexing returns shared reference (view semantics)
elem = arr[0]       # elem is the actual qint object
slice_view = arr[1:3]  # slice_view shares qint objects with arr
```

### Example 5: Homogeneity Validation
```python
# From requirement ARR-08: validate homogeneity
import quantum_language as ql

# Mixed types raise ValueError at construction
try:
    mixed = ql.array([ql.qint(1), ql.qbool(True)])
except ValueError as e:
    print(e)  # "Array must be homogeneous: cannot mix qint and qbool"

# Nested list validation (jagged arrays)
try:
    jagged = ql.array([[1, 2], [3]])  # Inconsistent inner lengths
except ValueError as e:
    print(e)  # "Jagged array detected: element 0 has shape (2,), ..."
```

### Example 6: Compact repr Format
```python
# From CONTEXT.md: compact format with shape and dtype
arr1 = ql.array([1, 2, 3])
print(repr(arr1))
# Output: ql.array<qint:8, shape=(3,)>[1, 2, 3]

arr2 = ql.array([[1, 2], [3, 4]], width=16)
print(repr(arr2))
# Output: ql.array<qint:16, shape=(2, 2)>[[1, 2], [3, 4]]

# Large array truncation
arr3 = ql.array(list(range(100)))
print(repr(arr3))
# Output: ql.array<qint:8, shape=(100,)>[0, 1, 2, ..., 97, 98, 99]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python list of qints | qarray class with shape | Phase 22 (v1.3) | Proper array semantics, NumPy-style indexing |
| Manual array creation | Auto-width inference | Phase 22 (v1.3) | Easier API, consistent with qint scalar behavior |
| Deep copy on slice | View semantics | Phase 22 (v1.3) | Memory efficient, matches NumPy expectations |
| Mutable array elements | Immutable arrays | Phase 22 (v1.3) | Simpler quantum semantics, no mutation complexity |

**Deprecated/outdated:**
- `_core.array()` function: Returns plain Python lists, no shape tracking - replace with qarray class
- Manual array indexing: `arr._elements[i]` direct access - use `arr[i]` protocol instead

## Open Questions

Things that couldn't be fully resolved:

1. **NumPy dtype mapping for explicit width**
   - What we know: NumPy arrays have dtype (int8, int32, etc.) that could map to qint width
   - What's unclear: How to handle NumPy uint vs int dtypes (qint uses signed representation)
   - Recommendation: For Phase 22, use dtype.itemsize * 8 as width; defer signed/unsigned distinction to future phase

2. **View tracking for circular references**
   - What we know: Views share qint objects with parent array
   - What's unclear: Whether parent array needs to track child views (for lifecycle management)
   - Recommendation: Don't track - Python's refcounting handles object lifetime; views keep references to shared qints

3. **Column slice implementation efficiency**
   - What we know: `A[:, j]` column access requires non-contiguous memory access
   - What's unclear: Whether to create new qint objects or return view with stride information
   - Recommendation: Create new qarray with selected elements (simple, correct); optimize later if needed

4. **Explicit width truncation vs error**
   - What we know: CONTEXT.md says "warn then truncate" when value doesn't fit explicit width
   - What's unclear: Whether to use warnings.warn() or UserWarning, and exact message format
   - Recommendation: Use `warnings.warn(f"Value {value} truncated to {width} bits", UserWarning)`

## Sources

### Primary (HIGH confidence)
- [Cython Extension Types](https://cython.readthedocs.io/en/latest/src/userguide/extension_types.html) - Official Cython docs
- [Cython Typed Memoryviews](https://cython.readthedocs.io/en/latest/src/userguide/memoryviews.html) - Array access patterns
- [Python collections.abc](https://docs.python.org/3/library/collections.abc.html) - Container ABCs (updated 2026-01-28)
- [NumPy Copies and Views](https://numpy.org/doc/stable/user/basics.copies.html) - View vs copy semantics
- [Python Data Model](https://docs.python.org/3/reference/datamodel.html) - __getitem__, __setitem__ protocols
- [Python int.bit_length()](https://python-reference.readthedocs.io/en/latest/docs/ints/bit_length.html) - Width calculation
- Existing qint.pyx (lines 144-163) - Auto-width implementation already in codebase
- Phase 21 RESEARCH.md - Package structure patterns

### Secondary (MEDIUM confidence)
- [Implementing slicing in __getitem__](https://gaopinghuang0.github.io/2018/11/17/python-slicing) - Multi-dimensional indexing
- [Mastering __getitem__ and slicing](https://medium.com/@beef_and_rice/mastering-pythons-getitem-and-slicing-c94f85415e1c) - Practical patterns
- [NumPy array_repr](https://numpy.org/doc/stable/reference/generated/numpy.array_repr.html) - Repr formatting
- [Python reprlib](https://docs.python.org/3/library/reprlib.html) - Truncated representations
- [Awkward Array docs](https://awkward-array.org/doc/main/getting-started/jagged-ragged-awkward-arrays.html) - Jagged array handling

### Tertiary (LOW confidence)
- None - all findings verified with official documentation or existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Cython and collections.abc already in use, NumPy is established dependency
- Architecture: HIGH - Patterns drawn from official docs and existing qint implementation
- Pitfalls: HIGH - Based on common Cython/Python container implementation issues, verified with docs

**Research date:** 2026-01-29
**Valid until:** 90 days (stable domain - Cython and Python protocols change slowly)
