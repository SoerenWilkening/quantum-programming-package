# Phase 13: Equality Comparison - Research

**Researched:** 2026-01-27
**Domain:** Quantum equality comparison circuits and Python operator overloading
**Confidence:** HIGH

## Summary

Equality comparison for quantum integers requires specialized quantum circuits that test if two quantum registers hold the same value, producing a quantum boolean result. The standard approach uses XOR-based algorithms with multi-controlled X gates for classical-quantum comparison (qint == int) and subtract-add-back patterns for quantum-quantum comparison (qint == qint). Phase 12 already implemented the foundational C-level functions `CQ_equal_width` and `cCQ_equal_width`, so Phase 13 primarily focuses on Python-level integration and qint == qint implementation.

Key challenges include managing result qubits without implicit measurement, handling width mismatches through zero-extension, and ensuring proper uncomputation for reversible operations. The existing Python `__eq__` implementation uses Python-level XOR patterns; Phase 13 will refactor to use the optimized C-level circuits from Phase 12.

**Primary recommendation:** Use `CQ_equal_width` from Phase 12 for qint == int comparisons, implement qint == qint via in-place subtract-add-back pattern (a -= b; result = (a == 0); a += b), and wrap result in qbool object that integrates with existing `with qbool:` controlled operation framework.

## Standard Stack

The established approach for quantum equality comparison:

### Core C Functions (Already Implemented in Phase 12)
| Function | Purpose | Status |
|----------|---------|--------|
| `CQ_equal_width(bits, value)` | Classical-quantum equality | ✓ Implemented (Phase 12) |
| `cCQ_equal_width(bits, value)` | Controlled classical-quantum equality | ✓ Implemented (Phase 12) |
| `mcx(gate, target, controls, num)` | Multi-controlled X gate | ✓ Implemented (Phase 12) |

### Python Integration (To Be Implemented in Phase 13)
| Component | Purpose | Approach |
|-----------|---------|----------|
| `qint.__eq__(other)` | Equality operator overload | Call C-level CQ_equal_width or subtract-add pattern |
| `qbool` result | Quantum boolean wrapper | Allocate result qubit, integrate with context manager |
| Width handling | Mismatch resolution | Zero-extend smaller operand conceptually |

### Algorithm Structure

**Classical-Quantum Comparison (qint == int):**
```
1. Convert classical value to binary
2. Apply X gates where classical bit is 0
3. Multi-controlled X to result qubit (all must be |1⟩ = equal)
4. Uncompute: reverse X gates to restore operand state
```

**Quantum-Quantum Comparison (qint == qint):**
```
1. a -= b  (in-place subtraction)
2. result = (a == 0)  (compare to zero using CQ_equal_width)
3. a += b  (restore original value)
```

**Installation/Usage:**
Already integrated in codebase. Python bindings use Cython to call C functions.

## Architecture Patterns

### Pattern 1: XOR-Based Equality (Classical-Quantum)
**What:** Compare quantum register to classical value using bitwise XOR pattern
**When to use:** qint == int comparisons
**Complexity:** O(n) gates vs O(n²) for subtraction-based
**Implementation:**
```c
// Source: Backend/src/IntegerComparison.c (Phase 12 implementation)
// CQ_equal_width algorithm:
// 1. Flip qubits where classical bit is 0
// 2. Multi-controlled X gate (all qubits control result)
// 3. Uncompute flips
```

**Python usage:**
```python
a = qint(5, width=8)
result = a == 5  # Uses CQ_equal_width internally
# result is qbool wrapping result qubit
```

### Pattern 2: Subtract-Add-Back (Quantum-Quantum)
**What:** Compute (a - b) in-place, test if zero, then restore a
**When to use:** qint == qint comparisons
**Why necessary:** Avoids allocating temporary register for a-b result
**Implementation pattern:**
```python
def qint.__eq__(self, other: qint):
    if type(other) == qint:
        # Pattern: (a - b) == 0 with restoration
        self -= other       # In-place subtraction
        result = self == 0  # Compare to zero (uses CQ_equal_width)
        self += other       # Restore original value
        return result
```

**Trade-offs:**
- Pro: No additional register allocation
- Pro: Reuses existing subtraction circuits
- Con: 2x gate count vs direct comparison (if it existed)
- Con: Temporary modification of operand (reversible)

### Pattern 3: Result Qubit Management
**What:** Allocate dedicated qubit for comparison result, integrate with circuit allocator
**When to use:** All comparison operations
**Implementation:**
```python
class qbool:
    """Quantum boolean wrapping a single result qubit"""
    # Already exists, used for comparison results
    # Integrates with 'with qbool:' context manager for controlled ops
```

**Memory lifecycle:**
- Result qubit allocated via circuit allocator
- Auto-freed when qbool object destroyed
- Multiple comparisons can be active simultaneously

### Pattern 4: Width Mismatch Handling
**What:** Handle qint operands of different bit widths
**Approach:** Conceptual zero-extension (treat missing high bits as |0⟩)
**Implementation:**
```python
def qint.__eq__(self, other):
    if type(other) == int:
        # Classical overflow check
        if other doesn't fit in self.bits:
            return qbool(False)  # Definitely not equal
        # Use CQ_equal_width(self.bits, other)
    elif type(other) == qint:
        # Use max width for comparison
        comp_width = max(self.bits, other.bits)
        # Subtract-add pattern handles zero-extension naturally
```

### Anti-Patterns to Avoid

- **Implicit Measurement:** Never use comparison result in classical boolean context (if/while) - raises error instead
- **Allocating Temp Registers for a-b:** Use in-place subtract-add-back pattern instead
- **Manual Gate Construction:** Always use Phase 12 C functions, not Python-level gate-by-gate construction
- **Forgetting Uncomputation:** Subtract-add pattern must always restore operand

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Classical-quantum comparison | Python loop comparing each bit | `CQ_equal_width(bits, value)` | Phase 12 C implementation handles overflow, uses optimized mcx() for multi-bit |
| Multi-controlled X gate | Cascaded CCX gates manually | `mcx()` from Phase 12 | Handles n>2 controls using large_control array, proper memory management |
| Result qubit allocation | Manual qubit tracking | Circuit allocator via `allocator_alloc()` | Automatic memory management, prevents qubit conflicts |
| Width mismatch | Manual zero-padding qubits | Conceptual extension in comparison logic | Physical padding wastes qubits; treat missing bits as |0⟩ in algorithm |
| Quantum-quantum comparison direct | Custom n-qubit comparator circuit | Subtract-add-back pattern | Reuses existing subtraction circuits, no new primitives needed |

**Key insight:** Phase 12 already provides optimized comparison primitives. Phase 13 is primarily Python glue code, not circuit design.

## Common Pitfalls

### Pitfall 1: Implicit Measurement in Classical Context
**What goes wrong:** Using comparison result in `if` statement or `while` loop
**Why it happens:** Python's bool coercion mechanism tries to convert qbool to classical bool
**How to avoid:**
```python
# WRONG:
if a == b:  # Raises error - can't use qbool as classical bool
    ...

# RIGHT:
result = a == b  # Get qbool
with result:      # Use as quantum control
    ...
```
**Warning signs:** TypeError or AttributeError when using comparison in classical control flow

### Pitfall 2: Forgetting to Restore in Subtract-Add Pattern
**What goes wrong:** Operand left in modified state after comparison
**Why it happens:** Subtraction is in-place, easy to forget restoration step
**How to avoid:** Always pair subtract with add-back:
```python
# Pattern template:
self -= other
result = self == 0
self += other  # MUST restore
return result
```
**Warning signs:** Subsequent operations on operand produce wrong results

### Pitfall 3: Classical Overflow Not Handled
**What goes wrong:** Comparing qint to classical value that doesn't fit in width
**Why it happens:** Forgetting to check value range before generating circuit
**How to avoid:**
```python
if type(other) == int:
    max_val = (1 << self.bits) - 1
    if other < 0 or other > max_val:
        # Return "definitely not equal" without circuit generation
        return qbool(False)
```
**Warning signs:** C function returns empty sequence (num_layer=0), incorrect results

### Pitfall 4: Width Mismatch Causes Incorrect Comparison
**What goes wrong:** Comparing qints of different widths produces wrong result
**Why it happens:** Not handling conceptual zero-extension of smaller operand
**How to avoid:** Use max width for comparison logic:
```python
comp_width = max(self.bits, other.bits)
# Subtract-add pattern naturally handles this via max-width arithmetic
```
**Warning signs:** Equality tests fail for values that should be equal

### Pitfall 5: Result Qubit Not Integrated with Allocator
**What goes wrong:** Result qubit leaks or conflicts with other allocations
**Why it happens:** Manual qubit index assignment instead of using allocator
**How to avoid:** Always allocate result through circuit allocator:
```python
result = qbool()  # Allocates via allocator_alloc()
# Auto-freed when result goes out of scope
```
**Warning signs:** Qubit count grows without bound, allocation errors

## Code Examples

Verified patterns from Phase 12 and existing implementation:

### Classical-Quantum Equality (qint == int)
```python
# Source: Planned implementation using Phase 12 CQ_equal_width
def qint.__eq__(self, other):
    if type(other) == int:
        # Check overflow
        max_val = (1 << self.bits) - 1
        if other < 0 or other > max_val:
            # Classical value doesn't fit - definitely not equal
            result = qbool(False)
            return result

        # Use Phase 12 C function
        seq = CQ_equal_width(self.bits, other)

        # Allocate result qubit
        result = qbool()

        # Build qubit array: [0] = result, [1:bits+1] = self operand
        qubit_array[0] = result.qubits[63]  # Result qubit
        qubit_array[1:self.bits+1] = self.qubits[64-self.bits:64]

        # Run comparison circuit
        run_instruction(seq, qubit_array, False, _circuit)

        return result
```

### Quantum-Quantum Equality (qint == qint)
```python
# Source: CONTEXT.md decision - subtract-add-back pattern
def qint.__eq__(self, other):
    if type(other) == qint:
        # Self-comparison optimization
        if self is other:
            return qbool(True)

        # Subtract-add-back pattern
        self -= other       # In-place: self = self - other
        result = self == 0  # Compare to zero (uses CQ_equal_width)
        self += other       # Restore: self = self + other

        return result
```

### Inequality Operator
```python
# Source: CONTEXT.md decision
def qint.__ne__(self, other):
    # Not-equal is just inverted equality
    result = self == other
    ~result  # Apply X gate to result qubit
    return result
```

### Using Comparison Results
```python
# Source: Existing qbool context manager pattern
a = qint(5, width=8)
b = qint(3, width=8)

# Get comparison result
is_equal = (a == b)  # qbool object

# Use in controlled operation
result = qint(0, width=8)
with is_equal:
    result += 1  # Only adds if a == b
```

### Current Python-Level Implementation (to be replaced)
```python
# Source: python-backend/quantum_language.pyx lines 1379-1438
# Current __eq__ uses Python-level XOR pattern
def __eq__(self, other):
    # XOR self and other into temp
    temp = self ^ other_qint

    # Check if temp is all zeros via loop
    result = qbool(True)
    for i in range(comp_bits):
        bit = temp[bit_index]
        with bit:
            result = ~result  # Flip result if any bit is 1

    return result
```
**Phase 13 will replace this with C-level CQ_equal_width calls.**

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python-level XOR loop | C-level CQ_equal_width | Phase 12-13 (2026-01) | Cleaner code, leverages optimized C circuits |
| Manual CCX cascades | mcx() with large_control | Phase 12 (2026-01) | Handles n>2 controls correctly |
| Subtraction-based comparison | XOR-based for CQ, subtract-add for QQ | Phase 7-13 | O(n) vs O(n²) gate count for CQ |
| Global QPU state registers | Explicit parameter passing | Phase 11 (2025) | Clean function signatures, no global state |
| Manual qubit allocation | Circuit allocator | Phase 9 (2025) | Automatic memory management |

**Deprecated/outdated:**
- `CQ_equal()` without width parameter - replaced by `CQ_equal_width(bits, value)` in Phase 11
- Manual qubit index tracking - replaced by allocator in Phase 9
- Python-level gate-by-gate construction - replaced by C-level sequence generation in Phase 12

**Recent advances (2024-2026):**
- Automated uncomputation synthesis (Modular Synthesis paper, 2024) - reduces ancilla by up to 96%
- Conditionally clean ancilla qubits (arXiv:2407.17966) - bridge between clean and dirty ancilla
- Reqomp space-constrained uncomputation (Quantum journal 2024) - optimizes ancilla reuse under hardware constraints

## Open Questions

Things that couldn't be fully resolved:

1. **Uncomputation Tracking Integration**
   - What we know: qbool results should support automatic uncomputation
   - What's unclear: How to track computation history for automatic add-back in qint == qint
   - Recommendation: For Phase 13, manual add-back is sufficient; defer automatic uncomputation to future optimization phase

2. **Multiple Simultaneous Comparisons Memory**
   - What we know: Multiple comparison results can be active (each allocates result qubit)
   - What's unclear: Memory pressure strategy when many comparisons active
   - Recommendation: Rely on circuit allocator's existing memory management; add warning if allocation fails

3. **Comparison Result Lifetime**
   - What we know: Result qubit freed when qbool object destroyed
   - What's unclear: If result is used in controlled operation, can it be freed safely?
   - Recommendation: Current Python reference counting is sufficient; result stays alive while referenced

4. **Width Mismatch Semantics for Signed Values**
   - What we know: qint is unsigned, but supports negative classical values via two's complement
   - What's unclear: Zero-extend vs sign-extend when comparing different widths
   - Recommendation: Always zero-extend (treat as unsigned) since qint arithmetic is modular

## Sources

### Primary (HIGH confidence)
- Backend/src/IntegerComparison.c - CQ_equal_width and cCQ_equal_width implementations (Phase 12)
- Backend/include/comparison_ops.h - Function declarations and specifications
- python-backend/quantum_language.pyx - Current Python-level __eq__ implementation (lines 1379-1461)
- .planning/phases/12-comparison-function-refactoring/12-VERIFICATION.md - Phase 12 verification results
- .planning/phases/13-equality-comparison/13-CONTEXT.md - User decisions for Phase 13

### Secondary (MEDIUM confidence)
- [Quantum bit string comparator paper](https://www.researchgate.net/publication/228574906_Quantum_bit_string_comparator_Circuits_and_applications) - Quantum comparison circuit theory
- [Modular Synthesis of Efficient Quantum Uncomputation (2024)](https://arxiv.org/pdf/2406.14227) - Automated uncomputation techniques
- [Reqomp: Space-constrained Uncomputation (Quantum 2024)](https://quantum-journal.org/papers/q-2024-02-19-1258/) - Ancilla optimization under constraints
- [Scalable Memory Recycling (2026)](https://ar5iv.labs.arxiv.org/html/2503.00822) - Qubit reuse and topological sorting
- [Rise of conditionally clean ancillae (2024)](https://arxiv.org/abs/2407.17966) - New ancilla qubit paradigm

### Tertiary (LOW confidence - general context)
- [IBM Quantum advantage predictions for 2026](https://www.ibm.com/quantum/blog/qdc-2025) - Industry context
- [Toffoli gate Wikipedia](https://en.wikipedia.org/wiki/Toffoli_gate) - Multi-controlled gate background
- [Python operator overloading documentation](https://docs.python.org/3/reference/datamodel.html) - __eq__ semantics
- [Quantum decoherence overview](https://www.bluequbit.io/quantum-decoherence) - General quantum computing challenges

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Phase 12 C functions already implemented and verified
- Architecture: HIGH - Subtract-add pattern is standard reversible computing technique, user decisions provide clear guidance
- Pitfalls: HIGH - Identified from existing code (e.g., current Python __eq__ pattern to avoid)
- Code examples: HIGH - Based on actual Phase 12 implementation and existing Python patterns

**Research date:** 2026-01-27
**Valid until:** 60 days (stable domain - comparison algorithms are well-established)

**Key uncertainties:** Uncomputation tracking integration (deferred to future phase), exact memory management strategy for multiple simultaneous comparisons (rely on existing allocator)
