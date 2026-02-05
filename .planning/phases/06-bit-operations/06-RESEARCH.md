# Phase 6: Bit Operations - Research

**Researched:** 2026-01-26
**Domain:** Quantum Bitwise Operations on Variable-Width Integers
**Confidence:** HIGH

## Summary

Phase 6 implements bitwise operations (AND, OR, XOR, NOT) for quantum integers with Python operator overloading. Research reveals that the codebase already contains legacy implementations of these operations for fixed-width (INTEGERSIZE=8) qbool types in LogicOperations.c. The key challenges for this phase are:

1. **Extending to variable-width integers**: Current implementations hardcode INTEGERSIZE, must adapt to 1-64 bit widths
2. **Circuit efficiency**: Bitwise operations on N-bit integers require N Toffoli gates (AND/OR) or N CNOT gates (XOR), leading to O(N) depth
3. **Ancilla management**: AND/OR operations require output ancilla qubits, must track ownership through Phase 3 allocator patterns
4. **Width handling**: Mixed-width operations must zero-extend the smaller operand to match the larger width

The existing LogicOperations.c provides proven gate patterns for qbool (1-bit) operations. These patterns can be generalized to arbitrary widths by iterating over all bits with proper qubit index calculation from the right-aligned q_address array.

**Primary recommendation:** Refactor existing LogicOperations.c functions to accept explicit width parameters and use right-aligned qubit indexing, following the patterns established in Phase 5 for CQ_add/QQ_add.

## Standard Stack

### Core Pattern: Gate-Based Bitwise Operations

Bitwise operations on quantum integers are implemented using fundamental quantum gates:

| Operation | Gate Pattern | Qubits Required | Circuit Depth |
|-----------|--------------|-----------------|---------------|
| AND (a & b) | Toffoli (CCX) per bit | N ancilla (output) | O(N) |
| OR (a \| b) | De Morgan's law + Toffoli | N ancilla (output) | O(N) |
| XOR (a ^ b) | CNOT per bit | 0 (in-place) or N (out-of-place) | O(1) parallel |
| NOT (~a) | X gate per bit | 0 (in-place) | O(1) parallel |

**Why Standard:**
- Toffoli gates (CCX) are universal for classical reversible computing
- CNOT is the fundamental two-qubit gate in quantum computing
- These patterns are used universally across quantum frameworks (Qiskit, Cirq, Q#)

### Existing Codebase Functions

The project already has sequence generators in `LogicOperations.c`:

| Function | Purpose | Current Limitation |
|----------|---------|-------------------|
| `qq_and_seq()` | Quantum-quantum AND | Hardcoded to INTEGERSIZE, qbool only |
| `qq_or_seq()` | Quantum-quantum OR | Hardcoded to INTEGERSIZE, qbool only |
| `qq_xor_seq()` | Quantum-quantum XOR | Hardcoded to INTEGERSIZE, qbool only |
| `q_not_seq()` | Quantum NOT | Hardcoded to INTEGERSIZE, single bit |
| `cq_not_seq()` | Controlled NOT | Hardcoded to INTEGERSIZE, single bit |

**Current Implementation Example (qq_and_seq):**
```c
// From LogicOperations.c:228
sequence_t *qq_and_seq() {
    // Creates ONE Toffoli gate:
    // ccx(&seq->seq[0][0], INTEGERSIZE-1, 2*INTEGERSIZE-1, 3*INTEGERSIZE-1);
    // target: INTEGERSIZE-1, controls: 2*INTEGERSIZE-1, 3*INTEGERSIZE-1
    // This is qbool-only (1-bit)
}
```

**Needed Pattern (variable-width):**
```c
sequence_t *QQ_and(int bits) {
    // For N-bit integers, create N Toffoli gates:
    for (int i = 0; i < bits; i++) {
        // Extract bit i from both operands, store in ancilla output bit i
        ccx(&seq->seq[layer][gate],
            output_base + i,      // target: output bit i (ancilla)
            operand_a_base + i,   // control: a bit i
            operand_b_base + i);  // control: b bit i
    }
}
```

### Supporting Infrastructure

| Component | Location | Purpose |
|-----------|----------|---------|
| Qubit allocator | `qubit_allocator.c/h` | Allocate ancilla for AND/OR results |
| Gate primitives | `gate.c/h` | `cx()`, `ccx()`, `x()` functions |
| Right-aligned arrays | `quantum_int_t` | Indices [64-width] through [63] |
| Sequence builder | `types.h` | `sequence_t` structure for gate lists |

## Architecture Patterns

### Pattern 1: Width-Parameterized Operations (Established in Phase 5)

**What:** Operations accept explicit `int bits` parameter and handle 1-64 bit widths dynamically.

**When to use:** All bitwise operations (AND, OR, XOR, NOT) on quantum integers.

**Example from CQ_add (Phase 5 pattern):**
```c
// From IntegerAddition.c:26
sequence_t *CQ_add(int bits, int64_t value) {
    // Bounds check
    if (bits < 1 || bits > 64) return NULL;

    // Allocate sequence for 'bits' gates
    add->num_layer = 4 * bits - 1;

    // Iterate over all bits
    for (int i = 0; i < bits; ++i) {
        p(&add->seq[start_layer + i][...], i, rotations[bits - i - 1]);
    }

    // Cache by width
    precompiled_CQ_add_width[bits] = add;
    return add;
}
```

**Apply to bitwise ops:**
```c
sequence_t *QQ_and(int bits) {
    if (bits < 1 || bits > 64) return NULL;

    // Create sequence with bits layers (one Toffoli per bit)
    sequence_t *seq = malloc(sizeof(sequence_t));
    seq->num_layer = bits;

    // Generate gate for each bit position
    for (int i = 0; i < bits; i++) {
        ccx(&seq->seq[i][0],
            output_bit(i),    // ancilla output
            operand_a_bit(i), // first input
            operand_b_bit(i)); // second input
    }

    return seq;
}
```

### Pattern 2: Right-Aligned Qubit Indexing (Established in Phase 5)

**What:** Qubits stored right-aligned in 64-element array. For width W, used indices are [64-W] through [63].

**When to use:** All functions accessing qint qubits, especially in Python bindings.

**Example from quantum_language.pyx:**
```python
# From quantum_language.pyx:232 (addition_inplace)
self_offset = 64 - self.bits
qubit_array[:self.bits] = self.qubits[self_offset:64]
```

**Apply to bitwise ops in Python:**
```python
# In qint.__and__(self, other)
def __and__(self, other: qint | int):
    result_width = max(self.bits, other.bits) if isinstance(other, qint) else self.bits
    result = qint(width=result_width)  # Allocates ancilla

    # Extract right-aligned qubits
    self_offset = 64 - self.bits
    result_offset = 64 - result_width

    qubit_array[:result_width] = result.qubits[result_offset:64]
    qubit_array[result_width:2*result_width] = self.qubits[self_offset:64]

    if isinstance(other, qint):
        other_offset = 64 - other.bits
        qubit_array[2*result_width:3*result_width] = other.qubits[other_offset:64]
        seq = QQ_and(result_width)
    else:
        seq = CQ_and(result_width, other)

    run_instruction(seq, &qubit_array[0], False, _circuit)
    return result
```

### Pattern 3: Ancilla-Based Output (For AND/OR)

**What:** Binary bitwise operations that produce new output require allocating ancilla qubits for the result.

**When to use:** AND, OR operations (NOT mutates in-place, XOR can be in-place via CNOT).

**Circuit pattern for AND:**
```
Input A:  |a0⟩ |a1⟩ ... |aN⟩
Input B:  |b0⟩ |b1⟩ ... |bN⟩
Output:   |0⟩  |0⟩  ... |0⟩   (ancilla, initialized to |0⟩)
          ↓    ↓        ↓
        CCX  CCX      CCX   (Toffoli gates)
          ↓    ↓        ↓
Output:   |a0&b0⟩ |a1&b1⟩ ... |aN&bN⟩
```

**Memory management:**
```c
// In C layer
sequence_t *QQ_and(int bits) {
    // Qubit layout expectation:
    // [0, bits-1]: output ancilla (pre-allocated by caller)
    // [bits, 2*bits-1]: operand A
    // [2*bits, 3*bits-1]: operand B

    for (int i = 0; i < bits; i++) {
        ccx(gate,
            i,              // target: output bit i
            bits + i,       // control: A bit i
            2*bits + i);    // control: B bit i
    }
}
```

```python
# In Python layer
def __and__(self, other):
    result = qint(width=result_width)  # QINT() allocates via allocator
    # Now result.qubits contains ancilla from circuit allocator
    # Pass to C sequence generator
    # Return result (caller now owns the qint, must __del__ to free)
```

### Pattern 4: Controlled Operations via Context Manager

**What:** Python `with qbool:` syntax applies control qubit to operations within the block.

**When to use:** All bitwise operations must support controlled variants (cAND, cOR, cXOR, cNOT).

**Example from existing code:**
```python
# From quantum_language.pyx:199
def __enter__(self):
    global _controlled, _control_bool
    if not _controlled:
        _control_bool = self
    _controlled = True
    return self

def __exit__(self, exc_type, exc, tb):
    global _controlled, _control_bool
    _controlled = False
    _control_bool = None
    return False
```

**Apply to bitwise ops:**
```python
def __and__(self, other):
    global _controlled, _control_bool

    result = qint(width=result_width)
    # ... qubit array setup ...

    if _controlled:
        # Add control qubit to layout
        qubit_array[3*result_width] = _control_bool.qubits[63]
        seq = cQQ_and(result_width)
    else:
        seq = QQ_and(result_width)

    run_instruction(seq, &qubit_array[0], False, _circuit)
    return result
```

**Controlled gate pattern (C layer):**
```c
sequence_t *cQQ_and(int bits) {
    // Layout: output[0:N], A[N:2N], B[2N:3N], control[3N]
    // Use 3-control Toffoli (actually C3X, decomposed)
    // Or use auxiliary qubits for multi-control
}
```

### Anti-Patterns to Avoid

- **Hardcoding INTEGERSIZE**: All operations must accept width parameter
- **Global state access**: No references to QPU_state->R0 (eliminated in Phase 4)
- **Mixed classical/quantum in Python**: Classical int & classical int should compute classically, not enter quantum layer
- **Ignoring width mismatches**: Must handle 8-bit & 16-bit by zero-extending to 16-bit

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-control gates | Custom decomposition | Native ccx(), use auxiliary qubits | Toffoli decomposition is well-studied, error-prone |
| Ancilla cleanup | Manual uncomputation | Follow QFT pattern (forward then inverse) | Entanglement cleanup requires careful reversal |
| Width inference | Ad-hoc type checking | Explicit max(a.bits, b.bits) | Clear semantics, no hidden conversions |
| Classical optimization | Classical bitwise in quantum | Check `isinstance(other, int)` in Python | Avoid quantum gates for classical computation |

**Key insight:** Quantum bitwise operations have fundamentally different cost profiles than classical. AND/OR require ancilla and Toffoli gates (expensive), while XOR is just CNOT (cheap). Don't try to optimize circuit depth beyond gate-level parallelism - leave that to hardware-specific transpilers.

## Common Pitfalls

### Pitfall 1: Off-by-One Errors in Right-Aligned Arrays

**What goes wrong:** Forgetting that width=8 uses indices [56:64], not [0:8].

**Why it happens:** Natural instinct is 0-indexed arrays, but right-alignment is necessary for uniform handling.

**How to avoid:**
```python
# WRONG
qubit_array[:width] = qint.qubits[:width]

# RIGHT
offset = 64 - qint.bits
qubit_array[:width] = qint.qubits[offset:64]
```

**Warning signs:** Segfaults when accessing qubits, incorrect gate targets in circuit output.

### Pitfall 2: Ancilla Leaks in Out-of-Place Operations

**What goes wrong:** AND/OR create new qint results with ancilla qubits, but Python __del__ not called if references persist.

**Why it happens:** Python garbage collection is non-deterministic, qubits not freed promptly.

**How to avoid:**
- Document that result qint owns ancilla, caller must manage lifetime
- Consider explicit `.free()` method for critical sections
- Track allocations via allocator_stats for debugging

**Warning signs:** `circuit_stats()` shows `current_in_use` growing without bound.

### Pitfall 3: Width Mismatch Silent Truncation

**What goes wrong:** User expects 16-bit & 8-bit to widen result, but classical int gets truncated.

**Why it happens:** Context doc specifies "NO overflow warning for classical truncation" for bitwise ops.

**How to avoid:**
- Infer width from classical value: `int.bit_length()` in Python
- Document that `qint(8) & 0xFFFF` produces 16-bit result (or widest needed)
- Test with values exceeding current width

**Warning signs:** User reports unexpected wrapping behavior.

### Pitfall 4: XOR Optimization Breaking Semantics

**What goes wrong:** Temptation to optimize XOR by mutating first operand instead of copying.

**Why it happens:** XOR is self-inverse (a ^ b ^ b = a), seems safe to do in-place.

**How to avoid:**
- Context doc specifies: out-of-place (^) must preserve both operands
- Only in-place (^=) may mutate
- Copy qubits to new qint before applying CNOT

**Warning signs:** `a = x ^ y; print(x)` shows x has changed.

### Pitfall 5: Controlled Operations Without Type Checking

**What goes wrong:** User passes qint instead of qbool as control in `with` block.

**Why it happens:** Python duck-typing doesn't enforce qbool type.

**How to avoid:**
```python
def __enter__(self):
    if self.bits != 1:
        raise TypeError("Control must be qbool (width=1)")
    # ... rest of __enter__
```

**Warning signs:** Cryptic circuit errors when multi-bit integer used as control.

## Code Examples

Verified patterns from existing codebase and quantum literature:

### Example 1: Quantum-Quantum XOR (Existing, Generalize)

```c
// From LogicOperations.c:489 (current qbool-only implementation)
sequence_t *qq_xor_seq() {
    int number = QPU_state->Q0->MSB + 1;  // REMOVE: global state

    // Single layer with INTEGERSIZE-number+1 gates (HARDCODED)
    seq->gates_per_layer[0] = INTEGERSIZE - number + 1;
    int counter = 0;
    for (int i = number - 1; i < INTEGERSIZE; ++i)
        cx(&seq->seq[0][counter++], i, INTEGERSIZE + i);

    return seq;
}

// REFACTORED (variable-width):
sequence_t *QQ_xor(int bits) {
    if (bits < 1 || bits > 64) return NULL;

    sequence_t *seq = malloc(sizeof(sequence_t));
    seq->num_layer = 1;  // All CNOTs in parallel
    seq->gates_per_layer = calloc(1, sizeof(num_t));
    seq->seq = calloc(1, sizeof(gate_t *));
    seq->seq[0] = calloc(bits, sizeof(gate_t));
    seq->gates_per_layer[0] = bits;
    seq->used_layer = 1;

    // Qubit layout: [0:bits] = target (modified in-place)
    //               [bits:2*bits] = control (source)
    for (int i = 0; i < bits; i++) {
        cx(&seq->seq[0][i],
           i,        // target bit i
           bits + i); // control bit i
    }

    return seq;
}
```

### Example 2: Python Operator Overloading (AND)

```python
# From quantum_language.pyx:413 (current qbool implementation)
def __and__(self, other):
    a = qbool()  # HARDCODED: always creates 1-bit result
    self.and_functionality(other, a)  # Uses qq_and_seq()
    return a

# REFACTORED (variable-width):
def __and__(self, other: qint | int):
    """Bitwise AND operation.

    Returns NEW qint with width = max(self.width, other.width).
    For qint & int, infers width from classical value.

    Circuit: Uses Toffoli gates (one per bit), requires ancilla for output.
    """
    cdef sequence_t *seq
    cdef unsigned int[:] arr
    cdef int result_bits

    # Determine result width
    if type(other) == int:
        # Infer width from classical value
        classical_width = other.bit_length() if other != 0 else 1
        result_bits = max(self.bits, classical_width)
    elif type(other) == qint:
        result_bits = max(self.bits, (<qint>other).bits)
    else:
        raise TypeError("Operand must be qint or int")

    # Allocate result (ancilla qubits)
    result = qint(width=result_bits)

    # Extract right-aligned qubits
    self_offset = 64 - self.bits
    result_offset = 64 - result_bits

    # Layout: [0:N] = output, [N:2N] = self, [2N:3N] = other (or value)
    qubit_array[:result_bits] = result.qubits[result_offset:64]

    # Zero-extend self if needed
    if self.bits < result_bits:
        qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]
        # Remaining bits implicitly 0 (no gates applied)
    else:
        qubit_array[result_bits:2*result_bits] = self.qubits[self_offset:self_offset+result_bits]

    if type(other) == int:
        # Classical-quantum AND
        seq = CQ_and(result_bits, other)
    else:
        # Quantum-quantum AND
        other_offset = 64 - (<qint>other).bits
        if (<qint>other).bits < result_bits:
            qubit_array[2*result_bits:2*result_bits + (<qint>other).bits] = \
                (<qint>other).qubits[other_offset:64]
        else:
            qubit_array[2*result_bits:3*result_bits] = \
                (<qint>other).qubits[other_offset:other_offset+result_bits]
        seq = QQ_and(result_bits)

    arr = qubit_array
    run_instruction(seq, &arr[0], False, _circuit)
    return result
```

### Example 3: In-Place NOT (Existing, Clean Up)

```c
// From LogicOperations.c:95
sequence_t *q_not_seq() {
    sequence_t *seq = malloc(sizeof(sequence_t));
    // ... allocation boilerplate ...

    seq->gates_per_layer[0] = 1;
    seq->used_layer = 1;
    seq->num_layer = 1;
    int counter = 0;

    // PROBLEM: Loop runs once (INTEGERSIZE-1 to INTEGERSIZE)
    for (int i = INTEGERSIZE - 1; i < INTEGERSIZE; ++i) {
        x(&seq->seq[0][counter++], i);
    }
    return seq;
}

// REFACTORED (variable-width):
sequence_t *Q_not(int bits) {
    if (bits < 1 || bits > 64) return NULL;

    sequence_t *seq = malloc(sizeof(sequence_t));
    seq->num_layer = 1;
    seq->gates_per_layer = calloc(1, sizeof(num_t));
    seq->seq = calloc(1, sizeof(gate_t *));
    seq->seq[0] = calloc(bits, sizeof(gate_t));
    seq->gates_per_layer[0] = bits;
    seq->used_layer = 1;

    // Apply X gate to each bit (all in parallel)
    for (int i = 0; i < bits; i++) {
        x(&seq->seq[0][i], i);
    }

    return seq;
}
```

### Example 4: Controlled XOR (New Pattern)

```c
sequence_t *cQQ_xor(int bits) {
    if (bits < 1 || bits > 64) return NULL;

    sequence_t *seq = malloc(sizeof(sequence_t));
    seq->num_layer = bits;  // Sequential to avoid control conflicts
    seq->gates_per_layer = calloc(bits, sizeof(num_t));
    seq->seq = calloc(bits, sizeof(gate_t *));

    for (int i = 0; i < bits; i++) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
        seq->gates_per_layer[i] = 1;

        // Qubit layout: [0:bits] = target, [bits:2*bits] = source, [2*bits] = control
        // Use Toffoli: control AND source -> target
        ccx(&seq->seq[i][0],
            i,           // target bit i
            2*bits,      // control qubit
            bits + i);   // source bit i (second control)
    }
    seq->used_layer = bits;

    return seq;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed INTEGERSIZE (8-bit) | Variable width (1-64 bits) | Phase 5 (2026-01) | Bitwise ops must adapt to arbitrary widths |
| Global QPU_state->R0 | Explicit value parameters | Phase 4 (2026-01) | CQ_and must take value directly |
| Hardcoded qubit indices | Right-aligned arrays | Phase 5 (2026-01) | Must calculate offsets for each operation |
| Direct qubit allocation | Circuit allocator | Phase 3 (2026-01) | Ancilla for AND/OR tracked automatically |

**Deprecated/outdated:**
- `qq_and_seq()`, `qq_or_seq()`, `qq_xor_seq()`: Replace with width-parameterized versions
- INTEGERSIZE constant in LogicOperations.c: Must become function parameter
- Single-bit-only assumptions: All operations must handle multi-bit integers

## Open Questions

1. **Ancilla cleanup for AND/OR**
   - What we know: AND/OR produce output in ancilla, must eventually be uncomputed or measured
   - What's unclear: Should Phase 6 implement uncomputation, or leave for circuit optimization phase?
   - Recommendation: Phase 6 allocates ancilla, Phase 8 (circuit optimization) handles cleanup via dead-qubit detection

2. **De Morgan's law for OR implementation**
   - What we know: Current `qq_or_seq()` uses multi-stage pattern with X gates
   - What's unclear: Is this implementing OR via `~(~a & ~b)`, or direct OR construction?
   - Recommendation: Document current pattern, verify correctness via tests, don't change unless proven wrong

3. **Classical int width inference**
   - What we know: Context doc says "infer width from classical value"
   - What's unclear: Should `qint(8) & 0xFF` stay 8-bit or widen to 8-bit (value fits)?
   - Recommendation: Use `max(qint.width, classical_value.bit_length())` - always safe, never truncates

4. **Augmented assignment semantics**
   - What we know: Context doc says "requires ancilla, then swap qubit indices"
   - What's unclear: How to swap qubit array indices without copying qubits physically?
   - Recommendation: `a &= b` should allocate result, compute, then swap `a.qubits` array reference (Python-level swap)

## Sources

### Primary (HIGH confidence)

- **Codebase files** (verified by direct reading):
  - `Backend/src/LogicOperations.c` - Existing bitwise operation implementations
  - `Backend/include/LogicOperations.h` - Function signatures
  - `Backend/src/IntegerAddition.c` - Phase 5 width-parameterized pattern
  - `python-backend/quantum_language.pyx` - Python operator overloading structure
  - `.planning/phases/06-bit-operations/06-CONTEXT.md` - User decisions for this phase

- **Quantum computing fundamentals** (established knowledge):
  - Toffoli gate (CCX) for classical AND: Standard in reversible computing literature
  - CNOT for XOR: Direct application of quantum gate definition
  - X gate for NOT: Single-qubit bit flip

### Secondary (MEDIUM confidence)

- **Phase 3/4/5 patterns** (verified by reading prior phase docs):
  - Allocator usage patterns from `.planning/phases/03-memory-architecture/`
  - Global state elimination from `.planning/phases/04-module-separation/`
  - Right-aligned arrays from `.planning/phases/05-variable-width-integers/`

### Tertiary (LOW confidence)

- **De Morgan's law OR optimization**: Current `qq_or_seq()` implementation unclear, needs testing
- **Multi-control gate decomposition**: Assumed from gate.h ccx() signature, actual decomposition not verified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Existing codebase provides proven patterns, just need generalization
- Architecture: HIGH - Phase 5 established clear width-parameterized pattern to follow
- Pitfalls: MEDIUM - Inferred from code structure, not all verified via testing

**Research date:** 2026-01-26
**Valid until:** 2026-02-26 (stable domain, 30 days)

**Key files to reference during planning:**
- `Backend/src/LogicOperations.c` - Current implementations to refactor
- `Backend/src/IntegerAddition.c` - Width-parameterized pattern template
- `python-backend/quantum_language.pyx` - Python binding structure
- `.planning/phases/06-bit-operations/06-CONTEXT.md` - User decisions
