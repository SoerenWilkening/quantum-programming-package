# Phase 24: Element-wise Operations - Research

**Researched:** 2026-01-29
**Domain:** Quantum array element-wise operations (internal implementation)
**Confidence:** HIGH

## Summary

Phase 24 implements element-wise operators on qarray by applying existing qint/qbool operators pairwise across array elements. The codebase already has all necessary operator overloads (__add__, __sub__, __mul__, __and__, __or__, __xor__, and comparison operators) with established width handling, dependency tracking, and in-place semantics. This phase extends those patterns to arrays with shape validation and scalar broadcasting.

Based on Phase 22 (qarray foundation) and Phase 23 (reductions), element-wise operations follow NumPy's broadcasting semantics but limited to scalar broadcasting only (no shape broadcasting). Operations iterate through flattened elements, apply qint/qbool operators, collect results into new qarray with same shape. In-place operations (+=, -=, *=, &=, |=, ^=) mutate array elements via quantum gates using existing in-place operators. Comparisons return qbool arrays using existing comparison operators.

Key technical patterns: (1) shape validation before operation (exact match or scalar), (2) scalar conversion to qint with array's element width, (3) result width = max(operand widths) following qint precedent, (4) iteration over flattened elements with result reshaping, (5) in-place mutation via element.__iadd__(), element.__iand__(), etc., (6) comparison operators return new qbool array, and (7) operator methods using Python's magic method protocol (__add__, __lt__, etc.).

**Primary recommendation:** Implement operators as qarray methods using existing qint/qbool operator overloads, validate shapes upfront (raise ValueError with clear message showing both shapes), iterate flattened elements applying operations, collect results into new qarray, preserve input shape, support scalar broadcasting by converting int/qint scalar to match array width, and implement in-place variants by mutating elements directly.

## Standard Stack

This phase uses only internal codebase components - no external libraries.

### Core Components
| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| qarray | src/quantum_language/qarray.pyx | Array container with shape metadata | Phase 22 foundation |
| qint | src/quantum_language/qint.pyx | Quantum integer with operators | Core type with all operators implemented |
| qbool | src/quantum_language/qbool.pyx | 1-bit quantum boolean | Comparison result type, inherits from qint |
| qint operators | qint.pyx lines 740-2100 | __add__, __and__, __lt__, etc. | All operators already implemented with width handling |

### Existing Operator Implementations
| Operator | Method | Line | Width Rule | Returns | In-place |
|----------|--------|------|------------|---------|----------|
| + | __add__ | 740 | max(a.width, b.width) | qint | __iadd__ line 801 |
| - | __sub__ | 823 | max(a.width, b.width) | qint | __isub__ line 855 |
| * | __mul__ | 950 | max(a.width, b.width) | qint | __imul__ line 1021 |
| & | __and__ | 1060 | max(a.width, b.width) | qint | __iand__ line 1154 |
| \| | __or__ | 1186 | max(a.width, b.width) | qint | __ior__ line 1280 |
| ^ | __xor__ | 1312 | max(a.width, b.width) | qint | __ixor__ line 1430 |
| == | __eq__ | 1571 | N/A | qbool | N/A |
| != | __ne__ | 1708 | N/A | qbool | N/A |
| < | __lt__ | 1734 | N/A | qbool | N/A |
| <= | __le__ | 1900 | N/A | qbool | N/A |
| > | __gt__ | 1823 | N/A | qbool | N/A |
| >= | __ge__ | 1997 | N/A | qbool | N/A |

**Installation:**
No external dependencies - all internal to quantum_language package.

## Architecture Patterns

### Pattern 1: Element-wise Binary Operation on Arrays
**What:** Apply binary operator between corresponding elements of two arrays
**When to use:** All arithmetic, bitwise, and comparison operations

**Example structure:**
```python
# In qarray.pyx
cdef class qarray:
    # ... existing code ...

    def __add__(self, other):
        """Element-wise addition: A + B

        Supports:
        - array + array (shapes must match)
        - array + scalar (broadcasts scalar to all elements)
        - array + qint (broadcasts qint to all elements)

        Returns new array with same shape.
        Result width = max(A.width, B.width).
        """
        # Step 1: Handle scalar broadcasting
        if isinstance(other, (int, qint)):
            # Scalar case - broadcast to all elements
            return self._scalar_op(other, lambda a, b: a + b)

        # Step 2: Validate both are arrays
        if not isinstance(other, qarray):
            return NotImplemented

        # Step 3: Shape validation
        if self._shape != other._shape:
            raise ValueError(
                f"Shape mismatch: cannot perform element-wise operation on arrays "
                f"with shapes {self._shape} and {other._shape}"
            )

        # Step 4: Determine result width (following qint pattern)
        result_width = max(self._width, other._width)

        # Step 5: Apply operation element-wise
        result_elements = []
        for i in range(len(self._elements)):
            elem_result = self._elements[i] + other._elements[i]
            result_elements.append(elem_result)

        # Step 6: Create result array with same shape
        return self._create_view(result_elements, self._shape)

    def _scalar_op(self, scalar, op_func):
        """Helper for scalar broadcasting operations.

        Args:
            scalar: int or qint to broadcast
            op_func: Binary operator (e.g., lambda a, b: a + b)

        Returns:
            New qarray with same shape
        """
        # Convert int scalar to qint with array's width
        if isinstance(scalar, int):
            scalar_qint = qint(scalar, width=self._width)
        else:
            scalar_qint = scalar

        # Apply operation to each element
        result_elements = []
        for elem in self._elements:
            result_elements.append(op_func(elem, scalar_qint))

        return self._create_view(result_elements, self._shape)
```

### Pattern 2: Shape Validation with Clear Error Messages
**What:** Validate array shapes match exactly before element-wise operations
**When to use:** All array-array operations (not needed for scalar broadcasting)

**Example from CONTEXT.md and NumPy patterns:**
```python
def _validate_shapes(self, other):
    """Validate shapes match for element-wise operation.

    Args:
        other: Another qarray

    Raises:
        ValueError: If shapes don't match, with both shapes shown
    """
    if self._shape != other._shape:
        raise ValueError(
            f"Shape mismatch for element-wise operation: "
            f"array with shape {self._shape} cannot operate with "
            f"array with shape {other._shape}. "
            f"Shapes must match exactly (scalar broadcasting is supported)."
        )
```

**Key insight:** Clear error messages showing both shapes help users debug quickly. NumPy-style format: "operands could not be broadcast together with shapes (3,4) (4,3)".

### Pattern 3: Scalar Broadcasting with Width Matching
**What:** Convert scalar (int or qint) to match array's element width for consistent operations
**When to use:** When operand is scalar (not array)

**Example:**
```python
def _prepare_scalar(self, scalar):
    """Convert scalar to qint with array's width.

    Args:
        scalar: int or qint

    Returns:
        qint with width matching self._width
    """
    if isinstance(scalar, int):
        # Convert int to qint with array's width
        return qint(scalar, width=self._width)
    elif isinstance(scalar, qint):
        # If qint already has matching width, use directly
        # Otherwise, width mismatch handled by qint operators
        return scalar
    else:
        raise TypeError(f"Unsupported scalar type: {type(scalar)}")
```

**Rationale from CONTEXT.md:** "Scalar int is auto-converted to qint with width matching the array's element width" ensures consistent operations.

### Pattern 4: In-place Operations via Element Mutation
**What:** Modify array elements in-place using existing qint.__iadd__, __iand__, etc.
**When to use:** In-place operators (+=, -=, *=, &=, |=, ^=)

**Example:**
```python
def __iadd__(self, other):
    """In-place addition: A += B

    Mutates elements via quantum gates (true in-place).

    Args:
        other: qarray, qint, or int

    Returns:
        self (modified)
    """
    # Handle scalar broadcasting
    if isinstance(other, (int, qint)):
        if isinstance(other, int):
            other = qint(other, width=self._width)

        # Apply in-place to each element
        for elem in self._elements:
            elem += other  # Calls qint.__iadd__

        return self

    # Array case - validate shapes
    if not isinstance(other, qarray):
        return NotImplemented

    if self._shape != other._shape:
        raise ValueError(
            f"Shape mismatch: cannot perform in-place operation on arrays "
            f"with shapes {self._shape} and {other._shape}"
        )

    # Apply in-place to corresponding elements
    for i in range(len(self._elements)):
        self._elements[i] += other._elements[i]  # qint.__iadd__

    return self
```

**Key insight from CONTEXT.md:** "True in-place mutation: A += B modifies A's quantum elements via gates, no new array allocated." The qint in-place operators already handle quantum gate application.

### Pattern 5: Comparison Operations Returning qbool Arrays
**What:** Element-wise comparisons return new qarray with dtype=qbool
**When to use:** All comparison operators (<, <=, >, >=, ==, !=)

**Example:**
```python
def __lt__(self, other):
    """Element-wise less-than: A < B

    Returns qbool array (not qint 0/1).

    Args:
        other: qarray, qint, or int

    Returns:
        qarray with dtype=qbool, same shape
    """
    # Handle scalar broadcasting
    if isinstance(other, (int, qint)):
        if isinstance(other, int):
            other = qint(other, width=self._width)

        # Compare each element with scalar
        result_elements = []
        for elem in self._elements:
            result_elements.append(elem < other)  # Returns qbool

        # Create qbool array
        result = self._create_view(result_elements, self._shape)
        result._dtype = qbool
        result._width = 1
        return result

    # Array case
    if not isinstance(other, qarray):
        return NotImplemented

    if self._shape != other._shape:
        raise ValueError(
            f"Shape mismatch: cannot compare arrays with shapes "
            f"{self._shape} and {other._shape}"
        )

    # Element-wise comparison
    result_elements = []
    for i in range(len(self._elements)):
        result_elements.append(self._elements[i] < other._elements[i])

    # Create qbool array
    result = self._create_view(result_elements, self._shape)
    result._dtype = qbool
    result._width = 1
    return result
```

**Rationale from CONTEXT.md:** "Comparisons return qbool array (not qint 0/1)" - explicit type for boolean results.

### Pattern 6: Result Width Calculation
**What:** Result width follows max(operand widths) rule from qint operators
**When to use:** Arithmetic and bitwise operations

**Example from existing qint.pyx patterns:**
```python
def __add__(self, other):
    """Element-wise addition."""
    # ... shape validation ...

    # Width calculation following qint precedent (line 765, 976, 1103)
    if isinstance(other, qarray):
        result_width = max(self._width, other._width)
    elif isinstance(other, qint):
        result_width = max(self._width, other.bits)
    else:  # int scalar
        result_width = self._width

    # Apply operations...
    # Note: Individual qint operators will also apply width rules
    # Result elements will automatically have correct width
```

**Key insight:** qint operators already handle width inference internally (lines 765, 976, 1103). Array operators inherit this behavior automatically.

### Pattern 7: Operator Method Organization
**What:** Group operators logically in qarray.pyx following qint.pyx precedent
**When to use:** All operator implementations

**Recommended organization:**
```python
# In qarray.pyx after existing methods:

# ============ Arithmetic Operators ============
def __add__(self, other): ...
def __radd__(self, other): ...  # For int + array
def __iadd__(self, other): ...

def __sub__(self, other): ...
def __rsub__(self, other): ...
def __isub__(self, other): ...

def __mul__(self, other): ...
def __rmul__(self, other): ...
def __imul__(self, other): ...

# ============ Bitwise Operators ============
def __and__(self, other): ...
def __rand__(self, other): ...
def __iand__(self, other): ...

def __or__(self, other): ...
def __ror__(self, other): ...
def __ior__(self, other): ...

def __xor__(self, other): ...
def __rxor__(self, other): ...
def __ixor__(self, other): ...

# ============ Comparison Operators ============
def __eq__(self, other): ...
def __ne__(self, other): ...
def __lt__(self, other): ...
def __le__(self, other): ...
def __gt__(self, other): ...
def __ge__(self, other): ...

# ============ Helper Methods ============
def _validate_shape(self, other): ...
def _prepare_scalar(self, scalar): ...
def _elementwise_op(self, other, op_func, result_dtype=None): ...
```

**Rationale:** qint.pyx organizes operators this way (arithmetic at line 740, bitwise at 1060, comparison at 1571). Following established pattern improves maintainability.

### Anti-Patterns to Avoid
- **Broadcasting beyond scalars:** Don't implement shape broadcasting (e.g., (3,1) + (1,4)) - out of scope per CONTEXT.md
- **Custom width calculation:** Don't override qint's width rules - inherit them automatically
- **Silent shape mismatch:** Don't silently truncate or pad arrays - raise ValueError immediately
- **Copying elements unnecessarily:** Don't create new qint objects when existing operators return them
- **In-place on comparisons:** Don't implement __ilt__, __ieq__ - semantically meaningless per CONTEXT.md

## Don't Hand-Roll

Problems with existing solutions in the codebase:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Quantum addition | Custom adder circuit | qint.__add__() | Handles width, classical/quantum, dependency tracking (line 740) |
| Quantum subtraction | Custom subtractor | qint.__sub__() | Uses addition_inplace(invert=True) pattern (line 875) |
| Quantum multiplication | Custom multiplier | qint.__mul__() | Complex circuit already optimized (line 950) |
| Bitwise AND | Manual CNOT/Toffoli | qint.__and__() | Handles all cases (CQ, QQ, classical) (line 1060) |
| Bitwise OR | Custom circuit | qint.__or__() | Uses CQ_or and Q_or C functions (line 1186) |
| Bitwise XOR | Manual XOR gates | qint.__xor__() | True in-place XOR implementation (line 1312) |
| Comparison operations | Custom comparator | qint.__lt__, __eq__, etc. | Uses subtract-and-check pattern (line 1734) |
| Width inference | Manual bit counting | qint operator result | Operators automatically determine result width (line 765) |
| Dependency tracking | Manual add_dependency | qint operators handle it | All operators register dependencies (line 1113) |
| Shape validation | Custom dimension checking | Simple shape tuple comparison | self._shape != other._shape is sufficient |

**Key insight:** Every quantum operation is already implemented in qint with proper width handling, dependency tracking, and circuit generation. Array operations are just iteration + existing operators - don't reimplement the quantum logic.

## Common Pitfalls

### Pitfall 1: Forgetting Scalar Broadcasting in Reverse Operators
**What goes wrong:** `5 + arr` raises TypeError instead of working like `arr + 5`
**Why it happens:** Python tries int.__add__(qarray) first, fails, then calls qarray.__radd__(int)
**How to avoid:** Implement __radd__, __rsub__, __rmul__, __rand__, __ror__, __rxor__ that delegate to forward operators
**Warning signs:** `arr + 5` works but `5 + arr` raises TypeError

```python
# CORRECT implementation:
def __radd__(self, other):
    """Reverse addition: other + self (for int/qint + array)."""
    return self.__add__(other)  # Delegate to __add__

def __rsub__(self, other):
    """Reverse subtraction: other - self"""
    # Can't just delegate - need to negate result or swap operands
    if isinstance(other, (int, qint)):
        # Broadcast scalar and subtract
        if isinstance(other, int):
            other = qint(other, width=self._width)
        # Create array of scalar, then subtract self
        # OR: negate self and add
        return self._scalar_op(other, lambda a, b: b - a)
    return NotImplemented
```

### Pitfall 2: Width Mismatch in In-place Operations
**What goes wrong:** `A += B` where A.width < B.width causes truncation or error
**Why it happens:** In-place operations modify A's elements which have fixed width
**How to avoid:** Document behavior explicitly in CONTEXT.md ("Claude's Discretion" area)
**Options:**
- Error on width mismatch: `if other._width > self._width: raise ValueError(...)`
- Widen A's elements: Recreate elements with larger width (complex, breaks quantum state)
- Truncate B silently: Let qint.__iadd__ handle it (may surprise users)

**Recommendation for planner:** Choose error approach for safety - clear message prevents unexpected truncation.

```python
def __iadd__(self, other):
    """In-place addition."""
    if isinstance(other, qarray):
        if other._width > self._width:
            raise ValueError(
                f"Cannot perform in-place operation: operand width {other._width} "
                f"exceeds array width {self._width}. Use out-of-place operation (A + B) instead."
            )
```

### Pitfall 3: Forgetting dtype Consistency for Comparisons
**What goes wrong:** Comparison result has dtype=qint instead of dtype=qbool
**Why it happens:** Using _create_view without setting _dtype
**How to avoid:** Explicitly set result._dtype = qbool and result._width = 1 after creating comparison result
**Warning signs:** isinstance(result[0], qbool) fails, result has wrong width

```python
# WRONG:
def __lt__(self, other):
    result_elements = [self._elements[i] < other._elements[i] for i in range(len(self))]
    return self._create_view(result_elements, self._shape)  # dtype=qint!

# CORRECT:
def __lt__(self, other):
    result_elements = [self._elements[i] < other._elements[i] for i in range(len(self))]
    result = self._create_view(result_elements, self._shape)
    result._dtype = qbool
    result._width = 1
    return result
```

### Pitfall 4: Inefficient Operator Dispatch Pattern
**What goes wrong:** Duplicating shape validation and scalar handling in every operator
**Why it happens:** Copy-paste between operator methods
**How to avoid:** Extract common logic to helper method (_elementwise_op or similar)
**Warning signs:** 20+ lines duplicated across 18+ operators

```python
# BETTER: Generic helper method
def _elementwise_binary_op(self, other, op_func, result_dtype=None):
    """Generic element-wise binary operation.

    Args:
        other: qarray, qint, or int
        op_func: Binary operator function (e.g., lambda a, b: a + b)
        result_dtype: Optional dtype override (for comparisons)

    Returns:
        New qarray with same shape
    """
    # Handle scalar broadcasting
    if isinstance(other, (int, qint)):
        if isinstance(other, int):
            other = qint(other, width=self._width)
        result_elements = [op_func(elem, other) for elem in self._elements]
    elif isinstance(other, qarray):
        # Validate shapes
        if self._shape != other._shape:
            raise ValueError(
                f"Shape mismatch: {self._shape} vs {other._shape}"
            )
        # Apply element-wise
        result_elements = [
            op_func(self._elements[i], other._elements[i])
            for i in range(len(self._elements))
        ]
    else:
        return NotImplemented

    # Create result
    result = self._create_view(result_elements, self._shape)
    if result_dtype is not None:
        result._dtype = result_dtype
        result._width = 1 if result_dtype == qbool else result._width
    return result

# Then operators become one-liners:
def __add__(self, other):
    """Element-wise addition."""
    return self._elementwise_binary_op(other, lambda a, b: a + b)

def __lt__(self, other):
    """Element-wise less-than."""
    return self._elementwise_binary_op(other, lambda a, b: a < b, result_dtype=qbool)
```

### Pitfall 5: Mixed dtype Operations Not Handled
**What goes wrong:** `qint_array + qbool_array` raises unclear error or produces wrong dtype
**Why it happens:** Not checking dtype compatibility upfront
**How to avoid:** Follow CONTEXT.md: "Mixed dtype result is always qint (qint dominates over qbool)"
**Warning signs:** Operations between qint and qbool arrays produce qbool results

```python
def _elementwise_binary_op(self, other, op_func, result_dtype=None):
    """Generic element-wise operation."""
    # ... scalar handling ...

    # Array case
    if isinstance(other, qarray):
        # Shape validation
        if self._shape != other._shape:
            raise ValueError(...)

        # dtype handling per CONTEXT.md
        if result_dtype is None:
            # For arithmetic/bitwise: qint dominates
            if self._dtype == qint or other._dtype == qint:
                result_dtype = qint
            else:
                result_dtype = qbool

        # ... rest of operation ...
```

### Pitfall 6: Error Messages Not Showing Shapes
**What goes wrong:** `ValueError: Shape mismatch` without showing actual shapes
**Why it happens:** Lazy error message formatting
**How to avoid:** Always include both shapes in error message for quick debugging
**Warning signs:** Users have to add print statements to debug shape mismatches

```python
# WRONG:
if self._shape != other._shape:
    raise ValueError("Shape mismatch")

# CORRECT (per CONTEXT.md):
if self._shape != other._shape:
    raise ValueError(
        f"Shape mismatch for element-wise operation: "
        f"cannot operate on arrays with shapes {self._shape} and {other._shape}"
    )
```

## Code Examples

Verified patterns from the codebase:

### Existing qint Operator Pattern (Template for Array Operators)
```python
# Source: src/quantum_language/qint.pyx:740-770
# Pattern: Out-of-place operation with width inference

def __add__(self, other: qint | int):
    """Add quantum integers: self + other

    Result width is max(self.width, other.width). Overflow wraps (modular).
    """
    # Determine result width
    if type(other) == qint:
        result_width = max(self.bits, (<qint>other).bits)
    else:
        result_width = self.bits

    # Create new result with correct width
    a = qint(value=self.value, width=result_width)
    a += other  # Use in-place operation
    return a

# Array version follows same pattern:
def __add__(self, other):
    """Element-wise addition: A + B"""
    # ... shape/scalar handling ...
    result_elements = [
        self._elements[i] + other._elements[i]  # qint.__add__
        for i in range(len(self._elements))
    ]
    return self._create_view(result_elements, self._shape)
```

### In-place Operation Pattern
```python
# Source: src/quantum_language/qint.pyx:801-821
# Pattern: In-place mutation via gate application

def __iadd__(self, other: qint | int):
    """In-place addition: self += other

    Returns self (modified in-place via quantum gates).
    """
    return self.addition_inplace(other)

# Array version applies to each element:
def __iadd__(self, other):
    """In-place element-wise addition: A += B"""
    if isinstance(other, (int, qint)):
        # Scalar broadcast
        if isinstance(other, int):
            other = qint(other, width=self._width)
        for elem in self._elements:
            elem += other  # qint.__iadd__
    elif isinstance(other, qarray):
        if self._shape != other._shape:
            raise ValueError(...)
        for i in range(len(self._elements)):
            self._elements[i] += other._elements[i]
    else:
        return NotImplemented
    return self
```

### Comparison Operator Returning qbool
```python
# Source: src/quantum_language/qint.pyx:1734-1755
# Pattern: Comparison returns qbool

def __lt__(self, other):
    """Less-than comparison: self < other

    Returns qbool indicating self < other.
    """
    # ... implementation details ...
    result = qbool()  # Allocate result
    # ... comparison logic ...
    return result

# Array version returns qbool array:
def __lt__(self, other):
    """Element-wise less-than: A < B"""
    # ... shape/scalar handling ...
    result_elements = [
        self._elements[i] < other._elements[i]  # Returns qbool
        for i in range(len(self._elements))
    ]
    result = self._create_view(result_elements, self._shape)
    result._dtype = qbool
    result._width = 1
    return result
```

### Shape Validation from Existing Code
```python
# Source: src/quantum_language/qarray.pyx:71-74
# Pattern: Clear ValueError with details

if item_shape != first_shape:
    raise ValueError(
        f"Jagged array detected: element 0 has shape {first_shape}, "
        f"but element {i} has shape {item_shape}"
    )

# Apply to element-wise operations:
def _validate_shape(self, other):
    """Validate shapes match for element-wise operation."""
    if self._shape != other._shape:
        raise ValueError(
            f"Shape mismatch for element-wise operation: "
            f"array with shape {self._shape} cannot operate with "
            f"array with shape {other._shape}"
        )
```

### Scalar Conversion Pattern
```python
# Source: src/quantum_language/qarray.pyx:298-305
# Pattern: Create qint with specific width

q = qint(self._width)
q.value = value
self._elements.append(q)

# Apply for scalar broadcasting:
def _prepare_scalar(self, scalar):
    """Convert scalar to qint with array width."""
    if isinstance(scalar, int):
        return qint(scalar, width=self._width)
    elif isinstance(scalar, qint):
        return scalar  # Use as-is, width mismatch handled by qint ops
    else:
        raise TypeError(f"Unsupported scalar type: {type(scalar)}")
```

### Reverse Operator Pattern
```python
# Source: src/quantum_language/qint.pyx:772-799
# Pattern: __radd__ for int + qint

def __radd__(self, other: qint | int):
    """Reverse addition: other + self (for int + qint).

    Addition is commutative, so delegate to __add__.
    """
    if type(other) == qint:
        result_width = max(self.bits, (<qint>other).bits)
    else:
        result_width = self.bits
    a = qint(value=self.value, width=result_width)
    a += other
    return a

# Array version:
def __radd__(self, other):
    """Reverse addition: other + array (for int/qint + array)."""
    return self.__add__(other)  # Addition is commutative

def __rsub__(self, other):
    """Reverse subtraction: other - array"""
    # Subtraction NOT commutative - need to flip operands
    if isinstance(other, (int, qint)):
        if isinstance(other, int):
            other = qint(other, width=self._width)
        # Broadcast: other - elem for each elem
        result_elements = [other - elem for elem in self._elements]
        return self._create_view(result_elements, self._shape)
    return NotImplemented
```

## State of the Art

No version changes - this is internal implementation using stable quantum operations.

| Component | Current State | Notes |
|-----------|---------------|-------|
| qint operators | Stable since Phase 6-7 | All operators with width inference established |
| qarray foundation | Phase 22 (current) | Flattened storage, shape tracking, indexing complete |
| Operator overloading | Python standard | __add__, __iadd__, __lt__ protocol well-defined |
| NumPy broadcasting | Reference API | Scalar broadcasting only (shape broadcasting out of scope) |

**Deprecated/outdated:**
- None - all patterns are current

## Open Questions

Things that couldn't be fully resolved:

1. **In-place operation width mismatch behavior**
   - What we know: In-place ops modify existing elements with fixed width
   - What's unclear: Should `A += B` where B.width > A.width error, widen A, or truncate B?
   - Recommendation: Error with clear message (safest). Document in CONTEXT.md "Claude's Discretion" as: "Width mismatch in in-place operations raises ValueError to prevent unexpected truncation"

2. **Mixed dtype bitwise operations**
   - What we know: CONTEXT.md says "qbool promoted to qint(width=1) for mixed-type bitwise operations"
   - What's unclear: Whether promotion happens at array level or element level
   - Recommendation: Let element-level qint/qbool operators handle promotion automatically. qbool inherits from qint, so `qint & qbool` already works (line 1060 handles isinstance(other, qint) which includes qbool)

3. **Comparison of qbool arrays**
   - What we know: CONTEXT.md says "qbool array comparisons supported: bool_arr == other_bool_arr returns qbool array"
   - What's unclear: Whether all 6 comparison operators should work on qbool arrays
   - Recommendation: Support all 6 comparisons - qbool inherits qint's comparison operators (lines 1571-2100), so element-wise comparison works automatically

4. **Error vs NotImplemented for unsupported types**
   - What we know: Python protocol suggests NotImplemented for type incompatibility
   - What's unclear: When to return NotImplemented vs raise TypeError
   - Recommendation: Return NotImplemented for unknown types (allows Python to try reverse operator), raise TypeError only for explicitly forbidden operations

## Sources

### Primary (HIGH confidence)
- src/quantum_language/qint.pyx - Lines 740-2100 (all operator implementations)
- src/quantum_language/qarray.pyx - Lines 1-809 (complete qarray implementation)
- src/quantum_language/qbool.pyx - Lines 1-55 (qbool as qint subclass)
- .planning/phases/24-element-wise-operations/24-CONTEXT.md - User decisions and requirements
- .planning/phases/22-array-class-foundation/22-RESEARCH.md - qarray design patterns
- .planning/phases/23-array-reductions/23-RESEARCH.md - Array operation patterns
- .planning/STATE.md - Prior decisions (width inference, operator patterns)
- [Python Data Model](https://docs.python.org/3/reference/datamodel.html) - Operator overloading protocol
- [NumPy Broadcasting](https://numpy.org/doc/stable/user/basics.broadcasting.html) - Reference semantics

### Secondary (MEDIUM confidence)
- NumPy testing (manual verification) - Scalar broadcasting behavior confirmed
- qint.pyx lines 317-335 - Dependency tracking pattern (add_dependency)

### Tertiary (LOW confidence)
- None - all findings verified with codebase or official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components verified in codebase
- Architecture: HIGH - Patterns extracted from existing qint/qarray implementations
- Pitfalls: HIGH - Based on Python operator protocol and quantum operation semantics

**Research date:** 2026-01-29
**Valid until:** 90+ days (stable internal codebase, no external dependencies)
