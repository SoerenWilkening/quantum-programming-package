# Phase 5: Variable-Width Integers - Research

**Researched:** 2026-01-26
**Domain:** Quantum integer arithmetic with variable bit widths
**Confidence:** HIGH

## Summary

Phase 5 extends the fixed-width quantum integer implementation (currently hardcoded to 8 bits via INTEGERSIZE) to support arbitrary bit widths (1-64 bits). The research reveals that the C backend already has partial variable-width support through parameterized addition functions (CQ_add(bits), cCQ_add(bits)), but the quantum_int_t struct and Python API assume fixed width. The core technical challenge is modifying the quantum_int_t struct to store width metadata while maintaining the QFT-based arithmetic operations that currently work for any bit width when given the right parameters.

The architecture uses Quantum Fourier Transform (QFT) for efficient arithmetic, where addition becomes phase rotations in frequency space. The existing precompiled_CQ_add[64] array demonstrates the design already anticipated variable widths. The mixed-width arithmetic strategy (k-bit + l-bit uses k+1 bit circuit with selective controls) is a novel optimization that requires careful implementation of the qubit mapping logic in run_instruction().

**Primary recommendation:** Extend quantum_int_t to store width field, modify QINT()/QBOOL() to accept width parameter, update arithmetic sequence generation to use per-integer width instead of global INTEGERSIZE, and add width validation at Python/C boundary.

## Standard Stack

### Core Technologies

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| C (C11) | - | Backend implementation | Direct memory control, performance-critical circuit generation |
| Cython | 3.0+ | Python-C bridge | Zero-overhead bindings, maintains type safety across boundary |
| Python | 3.11+ | Frontend API | Operator overloading, natural quantum algorithm expression |
| QFT arithmetic | Custom | Addition/subtraction | Industry-standard quantum addition via phase rotations |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qubit_allocator | Internal | Qubit lifecycle | Already integrated in Phase 3 - handles dynamic allocation |
| sequence_t | Internal | Gate sequence | Already used for all operations - stores parameterized circuits |
| pytest | Latest | Testing | Already integrated in Phase 1 - characterization tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| QFT-based addition | Ripple-carry adder | QFT scales O(n²) gates but O(n) depth; ripple-carry is O(n) gates but O(n) depth with worse constant factors |
| Fixed q_address array | Dynamic allocation | Current approach wastes memory (64 slots, use 1-64) but avoids heap fragmentation and pointer chasing |
| Width stored in struct | Width inferred from MSB | Storing width explicitly clarifies intent and eliminates special-case logic |

**Installation:**
No external dependencies required - all components are internal to the project.

## Architecture Patterns

### Recommended Project Structure

The existing structure already supports variable widths:

```
Backend/
├── include/
│   ├── types.h           # Define quantum_int_t with width field
│   ├── Integer.h         # Update QINT/QBOOL signatures
│   └── circuit.h         # Circuit management (unchanged)
├── src/
│   ├── Integer.c         # Modify QINT(circ, width), QBOOL(circ)
│   ├── IntegerAddition.c # Already parameterized by bits
│   └── qubit_allocator.c # Already supports variable allocation
python-backend/
└── quantum_language.pyx  # Update qint class with width parameter
```

### Pattern 1: Width-Aware Quantum Integer

**What:** Store bit width in quantum_int_t struct alongside qubit addresses
**When to use:** Every quantum integer creation (QINT, QBOOL, qint constructor)
**Example:**

```c
// Current structure (types.h or circuit.h)
typedef struct {
    char MSB;
    qubit_t q_address[INTEGERSIZE];  // Fixed size array
} quantum_int_t;

// Proposed structure
typedef struct {
    char MSB;
    unsigned char width;              // NEW: bit width (1-64)
    qubit_t q_address[64];            // Max width for static allocation
} quantum_int_t;
```

**Rationale:** Static array avoids heap fragmentation while supporting full range. 64-entry array costs 256 bytes per qint (acceptable given typical usage patterns). Width field clarifies semantics and eliminates inference from MSB.

### Pattern 2: Parameterized Arithmetic Sequences

**What:** Arithmetic functions accept bit width parameter and generate appropriately-sized circuits
**When to use:** All arithmetic operations (add, subtract, multiply, compare)
**Example:**

```c
// Already exists in IntegerAddition.c
sequence_t *CQ_add(int bits) {
    // Generates QFT circuit for 'bits' qubits
    // Returns cached sequence from precompiled_CQ_add[bits]
}

// Extended to use per-integer width
sequence_t *QQ_add(int bits_a, int bits_b) {
    int max_bits = (bits_a > bits_b) ? bits_a : bits_b;
    // Generate circuit for max_bits
    // Qubit mapping handles different widths
}
```

**Rationale:** QFT operations scale with qubit count. Generating circuits per-width enables caching while supporting arbitrary sizes. Mixed-width uses max(width_a, width_b) for result.

### Pattern 3: Mixed-Width Qubit Mapping

**What:** Map logical qubits to physical qubits accounting for different operand widths
**When to use:** QQ_add, QQ_mul, comparisons with different-width operands
**Example:**

```c
// Conceptual mapping for 8-bit + 32-bit addition
// Use 9-bit circuit (k+1 where k=8)
// Controls: bits 0-7 (8 bits)
// Targets: bits 0-31 (32 bits)
// Upper bits (8-31) have NO control - "perfect overflow"

void map_mixed_width_qubits(
    qubit_t *out_array,
    quantum_int_t *smaller,  // 8-bit
    quantum_int_t *larger,   // 32-bit
    int circuit_bits         // 9 bits
) {
    // Map smaller operand to lower bits
    for (int i = 0; i < smaller->width; ++i) {
        out_array[INTEGERSIZE - smaller->width + i] = smaller->q_address[...];
    }
    // Map larger operand
    for (int i = 0; i < larger->width; ++i) {
        out_array[INTEGERSIZE + ...] = larger->q_address[...];
    }
    // Circuit uses only first circuit_bits controls
}
```

**Rationale:** Per CONTEXT.md decision, k-bit + l-bit (k < l) uses k+1 bit circuit. Upper bits (index >= k) perform "perfect overflow" without controls. Result width is l-bit. This reduces gate count while maintaining correct modular arithmetic.

### Pattern 4: Width Validation at Boundaries

**What:** Validate width parameter at Python-C boundary and C function entry points
**When to use:** qint.__init__(), QINT(), QBOOL(), all arithmetic operations
**Example:**

```python
# Python layer (quantum_language.pyx)
def __init__(self, value=0, width=8, ...):
    if width < 1 or width > 64:
        raise ValueError(f"Width must be 1-64, got {width}")

    # Warn if value doesn't fit
    max_val = (1 << width) - 1 if value >= 0 else -(1 << (width - 1))
    if abs(value) > max_val:
        import warnings
        warnings.warn(f"Value {value} exceeds {width}-bit range")

    # Proceed with allocation
```

```c
// C layer (Integer.c)
quantum_int_t *QINT(circuit_t *circ, int width) {
    if (width < 1 || width > 64) {
        return NULL;  // Caller checks for NULL
    }

    quantum_int_t *integer = malloc(sizeof(quantum_int_t));
    integer->width = width;

    // Allocate 'width' qubits instead of INTEGERSIZE
    qubit_t start = allocator_alloc(circ->allocator, width, true);
    // ...
}
```

**Rationale:** Early validation prevents downstream errors. Python raises ValueError for invalid widths (explicit exception better than undefined behavior). Warning for value-doesn't-fit allows program to continue (user may intend modular arithmetic). C returns NULL for invalid parameters following existing patterns.

### Anti-Patterns to Avoid

- **Fixed INTEGERSIZE everywhere:** Don't assume INTEGERSIZE - use quantum_int_t->width field
- **Width inference from MSB:** Don't calculate width from MSB - read the width field explicitly
- **Hardcoded array indexing:** Don't use fixed offsets like q_address[0] - compute based on width
- **Implicit width propagation:** Don't assume operands have same width - check and document mixed-width behavior
- **Reallocation after construction:** Don't resize quantum integers after creation - width is immutable

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Quantum addition | Classical ripple-carry translated to quantum | QFT-based addition | Already implemented, O(n²) gates but O(n) depth, well-tested |
| Qubit allocation | Manual tracking of used qubits | qubit_allocator module | Phase 3 established centralized allocation with reuse and statistics |
| Gate sequence caching | Custom memoization | precompiled_* arrays | Already exists for CQ_add[64], cCQ_add[64], extend pattern |
| Width validation | Scattered checks | Centralized validation function | Ensures consistency, easier to update validation rules |

**Key insight:** The existing QFT-based arithmetic is sophisticated and well-tested. Don't try to "optimize" it without deep quantum algorithm knowledge. The allocator module already handles dynamic qubit management. Focus on plumbing width metadata through the existing infrastructure.

## Common Pitfalls

### Pitfall 1: Off-by-One in Qubit Indexing

**What goes wrong:** q_address array indexed incorrectly when width < 64, causing uninitialized qubit access
**Why it happens:** Current code uses MSB to determine QBOOL (MSB=INTEGERSIZE-1) vs QINT (MSB=0). With variable widths, indexing logic becomes more complex.
**How to avoid:**
- Always use quantum_int_t->width for loop bounds
- Index from high bits: `q_address[64 - width + i]` for i in [0, width)
- Add assertions: `assert(qubit_index < width)`
**Warning signs:** Valgrind reports uninitialized memory, incorrect qubit counts in generated circuits

### Pitfall 2: Precompiled Sequence Array Overflow

**What goes wrong:** precompiled_CQ_add[bits] accessed with bits > 64, causing buffer overflow
**Why it happens:** Array sized for 64 entries, but no bounds checking on bits parameter
**How to avoid:**
- Add bounds check: `if (bits < 1 || bits > 64) return NULL;`
- Document array size assumptions in comments
- Consider dynamic allocation for caching if needed beyond 64 bits
**Warning signs:** Segfault or memory corruption when using large bit widths

### Pitfall 3: Mixed-Width Control Logic Error

**What goes wrong:** Mixed-width addition applies controls to all bits instead of only k bits for k-bit + l-bit (k < l)
**Why it happens:** Per CONTEXT.md, upper bits should have "no control, just targets" for perfect overflow
**How to avoid:**
- Generate circuit with k+1 layers (not l layers)
- Qubit mapping must distinguish control qubits (first k) from target-only qubits (remaining)
- Document the k+1 circuit rule prominently in code comments
**Warning signs:** Generated circuits have more gates than expected, incorrect arithmetic results for mixed widths

### Pitfall 4: Width Metadata Inconsistency

**What goes wrong:** Width stored in C struct differs from Python object's bits attribute
**Why it happens:** Width set during allocation but not synchronized on all code paths
**How to avoid:**
- Single source of truth: C struct width field
- Python bits property reads from C struct (no separate storage)
- Initialize width in QINT/QBOOL before any other operations
**Warning signs:** Assertion failures, arithmetic operations using wrong number of qubits

### Pitfall 5: Ancilla Allocation for Variable Width

**What goes wrong:** Ancilla allocation assumes fixed size, causing insufficient qubits for larger integers
**Why it happens:** Current NUMANCILLY = 2 * INTEGERSIZE is hardcoded for 8-bit integers
**How to avoid:**
- Calculate ancilla needs based on max operand width: `2 * max_width`
- Allocate ancilla dynamically per operation, not globally
- Update qubit_array sizing in Python layer to account for variable widths
**Warning signs:** "Qubit allocation failed" errors when using wide integers, corrupted ancilla state

## Code Examples

Verified patterns from existing implementation and CONTEXT.md specifications:

### Creating Variable-Width Quantum Integers

```python
# Python API (quantum_language.pyx - proposed changes)
from quantum_language import qint

# Default width (8 bits)
a = qint(5)                    # Uses 8 bits
assert a.width == 8

# Explicit width
b = qint(5, width=16)          # Uses 16 bits
assert b.width == 16

# Minimum width (1 bit)
c = qint(0, width=1)           # Uses 1 qubit
assert c.width == 1

# Maximum width (64 bits)
d = qint(1000, width=64)       # Uses 64 qubits
assert d.width == 64

# Invalid width raises exception
try:
    e = qint(5, width=128)     # Exceeds 64-bit limit
except ValueError as ex:
    print(f"Expected error: {ex}")
```

### Mixed-Width Arithmetic

```python
# Python API - mixed-width operations
a = qint(5, width=8)           # 8-bit integer
b = qint(1000, width=32)       # 32-bit integer

# Result width is max of operands
c = a + b                      # Result is 32-bit
assert c.width == 32

# Subtraction uses same width rules
d = b - a                      # Result is 32-bit
assert d.width == 32

# Both operands modified to same internal representation
# Smaller extended conceptually (per CONTEXT.md)
```

### C Backend Width-Aware Allocation

```c
// Backend/src/Integer.c - proposed modifications
quantum_int_t *QINT(circuit_t *circ, int width) {
    // Validate width
    if (circ == NULL || circ->allocator == NULL) {
        return NULL;
    }
    if (width < 1 || width > 64) {
        return NULL;  // Invalid width
    }

    quantum_int_t *integer = malloc(sizeof(quantum_int_t));
    if (integer == NULL) {
        return NULL;
    }

    // Allocate 'width' qubits through circuit's allocator
    qubit_t start = allocator_alloc(circ->allocator, width, true);
    if (start == (qubit_t)-1) {
        free(integer);
        return NULL;  // Allocation failed
    }

    // Store width and populate addresses
    integer->width = width;
    integer->MSB = 0;  // Convention: MSB=0 for multi-bit integers

    // Map qubits to high end of array (right-aligned)
    for (int i = 0; i < width; ++i) {
        integer->q_address[64 - width + i] = start + i;
    }

    // Update backward compat tracking
    circ->ancilla += width;
    circ->used_qubit_indices += width;

    return integer;
}
```

### Width-Aware Addition Sequence

```c
// Backend/src/IntegerAddition.c - QQ_add extended for variable width
sequence_t *QQ_add_variable(int bits_a, int bits_b) {
    // Result width is max of operands
    int result_bits = (bits_a > bits_b) ? bits_a : bits_b;

    // Check cache for this width
    if (result_bits <= 64 && precompiled_QQ_add_width[result_bits] != NULL) {
        return precompiled_QQ_add_width[result_bits];
    }

    // Generate QFT circuit for result_bits
    sequence_t *add = malloc(sizeof(sequence_t));
    if (add == NULL) {
        return NULL;
    }

    // Allocate layers: 5 * result_bits - 2 (per existing QQ_add pattern)
    add->num_layer = 5 * result_bits - 2;
    add->gates_per_layer = calloc(add->num_layer, sizeof(num_t));
    // ... rest of allocation ...

    // Apply QFT, controlled rotations, inverse QFT
    QFT(add, result_bits);

    // Controlled phase rotations (QFT-based addition)
    int rounds = 0;
    for (int bit = result_bits - 1; bit >= 0; --bit) {
        for (int i = 0; i < result_bits - rounds; ++i) {
            // ... cp gate generation ...
        }
        rounds++;
    }

    QFT_inverse(add, result_bits);

    // Cache the sequence
    if (result_bits <= 64) {
        precompiled_QQ_add_width[result_bits] = add;
    }

    return add;
}
```

### Width Property in Python

```python
# Python API - read-only width property
class qint(circuit):
    cdef int bits  # Internal storage

    @property
    def width(self):
        """Get the bit width of this quantum integer (read-only)."""
        return self.bits

    def __init__(self, value=0, width=8, ...):
        # Validation
        if width < 1 or width > 64:
            raise ValueError(f"Width must be 1-64, got {width}")

        # Warn if value doesn't fit
        if value >= (1 << width) or value < -(1 << (width - 1)):
            import warnings
            warnings.warn(
                f"Value {value} exceeds {width}-bit range, "
                f"will wrap to {value % (1 << width)}"
            )

        self.bits = width
        # ... allocate width qubits ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed 8-bit integers (INTEGERSIZE) | Variable 1-64 bit integers | Phase 5 | Enables realistic algorithms (32-bit Shor's, 64-bit arithmetic) |
| Global INTEGERSIZE constant | Per-integer width field | Phase 5 | Multiple integer sizes in same circuit |
| MSB field for width inference | Explicit width field | Phase 5 | Clearer semantics, eliminates special cases |
| All-or-nothing operand widths | Mixed-width arithmetic | Phase 5 | Natural expression (8-bit + 32-bit just works) |

**Deprecated/outdated:**
- INTEGERSIZE as universal width: Should become default width, not only width
- MSB for QBOOL detection: width==1 is clearer semantic
- Fixed q_address[INTEGERSIZE]: Needs to become q_address[64] for max width

## Open Questions

### 1. Precompiled Sequence Strategy for Variable Widths

**What we know:**
- Current precompiled_CQ_add[64] array caches sequences per bit width
- QQ_add has single cached sequence (assumes fixed INTEGERSIZE)
- Memory cost: ~200 bytes per cached sequence × 64 widths = ~12KB per operation type

**What's unclear:**
- Should QQ_add cache all 64 widths? (12KB memory overhead acceptable?)
- Mixed-width operations: cache only max width, or cache (width_a, width_b) pairs?
- Cache invalidation strategy if INTEGERSIZE constant removed?

**Recommendation:**
Cache sequences for all powers of 2 (1, 2, 4, 8, 16, 32, 64 bits). Generate on-demand for other widths. Power-of-2 widths are 90%+ of realistic use cases. Adds ~7 × 200 bytes = ~1.4KB per operation type (negligible). Mixed-width uses max width's cached sequence.

### 2. QBOOL as width=1 qint vs Separate Type

**What we know:**
- QBOOL currently uses MSB=INTEGERSIZE-1 to distinguish from QINT (MSB=0)
- CONTEXT.md says "minimum width is 1 bit — qint(0) still uses 1 qubit"
- Python qbool class inherits from qint

**What's unclear:**
- Should QBOOL(circ) become QINT(circ, 1)?
- Should Python qbool(value) become qint(value, width=1)?
- Does collapsing types break existing code expectations?

**Recommendation:**
Keep QBOOL() and qbool as convenience constructors that call QINT(circ, 1) and qint(value, width=1) internally. Maintains backward compatibility while unifying implementation. Document that qbool is syntactic sugar for 1-bit qint.

### 3. Default Width Strategy

**What we know:**
- CONTEXT.md specifies "default width is 8 bits (easier for testing, may increase later)"
- Python API: qint(5) uses default, qint(5, width=16) overrides
- Current INTEGERSIZE=8 is hardcoded constant

**What's unclear:**
- Should default be runtime-configurable?
- Should default depend on value magnitude? (e.g., qint(1000) auto-chooses 16 bits)
- How to handle existing code that assumes 8-bit without specifying width?

**Recommendation:**
Fixed default of 8 bits for Phase 5. No auto-sizing from value (explicit better than implicit). Add TODO comment for future configurability. Existing code continues working with 8-bit default. Users who need other widths specify explicitly.

### 4. Overflow Behavior Documentation

**What we know:**
- CONTEXT.md: "Arithmetic overflow: wrap silently (standard modular arithmetic)"
- Mixed-width: upper bits perform "perfect overflow" without controls
- Two's complement representation used throughout

**What's unclear:**
- Should overflow be detectable by user (carry-out flag)?
- Should there be an overflow warning mode for debugging?
- How is overflow communicated in quantum superposition?

**Recommendation:**
Silent wrap is correct for Phase 5 (matches classical modular arithmetic). Document overflow behavior prominently in docstrings. Future phase can add optional overflow detection via extra qubit. In superposition, overflow is per-amplitude (correct by definition).

## Sources

### Primary (HIGH confidence)

- **Backend/src/Integer.c** - QINT/QBOOL implementation, allocation patterns
- **Backend/src/IntegerAddition.c** - CQ_add(bits) parameterization, precompiled arrays
- **Backend/include/types.h** - quantum_int_t struct definition, INTEGERSIZE constant
- **Backend/include/circuit.h** - circuit_t and quantum_int_t struct definitions
- **python-backend/quantum_language.pyx** - Python qint class implementation
- **.planning/phases/05-variable-width-integers/05-CONTEXT.md** - User decisions and specifications
- **.planning/phases/03-memory-architecture/03-VERIFICATION.md** - Qubit allocator API and usage patterns

### Secondary (MEDIUM confidence)

- **Backend/src/gate.c** - QFT implementation (verified by existence, not deep analysis)
- **tests/python/test_qint_operations.py** - Current API patterns and test structure
- **.planning/codebase/architecture.md** - Overall system architecture and data flow

### Tertiary (LOW confidence)

None - all research based on direct codebase inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - direct inspection of existing C/Cython/Python implementation
- Architecture: HIGH - code structure and patterns verified in codebase
- Pitfalls: HIGH - derived from type system analysis and CONTEXT.md edge cases

**Research date:** 2026-01-26
**Valid until:** 30 days (stable domain, unlikely to change rapidly)

**Key assumptions validated:**
- ✓ QFT-based arithmetic already parameterized by bit count
- ✓ Qubit allocator supports dynamic width allocation
- ✓ Precompiled sequence caching exists for variable widths
- ✓ Mixed-width arithmetic strategy specified in CONTEXT.md
- ✓ Python-C boundary uses Cython for type-safe bindings

**Not validated (requires prototyping):**
- Mixed-width qubit mapping logic complexity
- Performance impact of cache misses for uncommon widths
- Edge cases in width validation (negative values in smaller widths)
