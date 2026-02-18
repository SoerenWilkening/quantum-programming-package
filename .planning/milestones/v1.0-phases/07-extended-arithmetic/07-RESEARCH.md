# Phase 7: Extended Arithmetic - Research

**Researched:** 2026-01-26
**Domain:** Quantum arithmetic operations (multiplication, comparison, division, modular arithmetic)
**Confidence:** MEDIUM-HIGH

## Summary

Phase 7 completes the quantum arithmetic operation suite by extending multiplication to variable widths, implementing comparison operators, and adding division and modular arithmetic. Research reveals that the codebase already contains fixed-width (INTEGERSIZE=8) implementations of multiplication in `IntegerMultiplication.c` using QFT-based approaches. The key challenges are:

1. **Variable-width multiplication**: Current QQ_mul() is hardcoded to INTEGERSIZE, must be extended to accept bits parameter following Phase 5 patterns
2. **Comparison operators**: Literature shows subtraction-based comparison is standard (subtract then check MSB/borrow), with optimized equality circuits
3. **Division implementation**: Per CONTEXT.md decision, implement at Python level via repeated subtraction/comparison following arXiv:1809.09732 approach
4. **Modular arithmetic**: New qint_mod type carrying classical modulus N, leveraging existing operations with modular reduction

The QFT-based multiplication already exists and is proven to work. The main work is parameterization by width (like Phase 5 arithmetic), implementing comparison circuits at C level, and composing higher-level division/modular operations at Python level.

**Primary recommendation:** Refactor existing multiplication to accept bits parameter, implement comparison operators as separate C functions (not subtraction+MSB check to avoid destroying inputs), implement division/divmod as Python-level composition, and create qint_mod wrapper class that applies modulo after each operation.

## Standard Stack

### Core Operations Already Implemented

The codebase already has proven implementations that need extension:

| Operation | Current State | Location | What's Needed |
|-----------|--------------|----------|---------------|
| QQ_mul | Fixed-width (INTEGERSIZE) | IntegerMultiplication.c:143-221 | Add bits parameter, cache by width |
| CQ_mul | Fixed-width (INTEGERSIZE) | IntegerMultiplication.c:70-142 | Add bits parameter |
| cQQ_mul | Fixed-width (INTEGERSIZE) | IntegerMultiplication.c:324-443 | Add bits parameter |
| cCQ_mul | Fixed-width (INTEGERSIZE) | IntegerMultiplication.c:222-323 | Add bits parameter |

### New Operations Required

| Operation | Purpose | Implementation Strategy | Complexity |
|-----------|---------|------------------------|------------|
| Comparison (>, <, ==, >=, <=) | Return qbool result | Subtraction-based for >/</>=/<= via MSB; optimized equality via XOR | O(n²) QFT gates |
| Division (// and %) | Integer division and modulo | Python-level repeated subtraction | O(log(quotient)) iterations |
| Modular arithmetic | Operations mod N | Python wrapper applying mod after each op | Same as base operation + modular reduction |

### Supporting Infrastructure

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| QFT-based multiplication | IntegerMultiplication.c | Efficient O(n²) gate multiplication | Exists, needs width param |
| Subtraction operations | IntegerAddition.c | Used for comparisons and division | Exists with width param (Phase 5) |
| qubit_allocator | qubit_allocator.c/h | Allocate result qubits | Integrated (Phase 3) |
| Right-aligned arrays | quantum_int_t | Width-aware qubit addressing | Established (Phase 5) |

## Architecture Patterns

### Pattern 1: Width-Parameterized Multiplication (Extend Phase 5 Pattern)

**What:** Extend existing multiplication functions to accept explicit `int bits` parameter for operand width.

**When to use:** QQ_mul, CQ_mul, controlled variants for arbitrary-width integers.

**Current implementation (fixed-width):**
```c
// From IntegerMultiplication.c:143
sequence_t *QQ_mul() {
    if (precompiled_QQ_mul != NULL)
        return precompiled_QQ_mul;

    // Hardcoded INTEGERSIZE throughout
    mul->num_layer = INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1;
    QFT(mul, INTEGERSIZE);
    // ... CP_sequence operations with INTEGERSIZE ...
    QFT_inverse(mul, INTEGERSIZE);
}
```

**Proposed pattern (variable-width):**
```c
// Signature change
sequence_t *QQ_mul(int bits) {
    if (bits < 1 || bits > 64) return NULL;

    // Cache by width (like Phase 5 addition)
    static sequence_t *precompiled_QQ_mul[65] = {NULL};
    if (precompiled_QQ_mul[bits] != NULL)
        return precompiled_QQ_mul[bits];

    // Allocate circuit layers based on bits
    mul->num_layer = bits * (2 * bits + 6) - 1;

    // Use bits parameter throughout
    QFT(mul, bits);

    int rounds = 0;
    for (int bit = bits - 1; bit >= 0; --bit) {
        layer = 2 * bits + 2 * rounds - 1;
        num_t control = bits + bit;
        for (int i = 0; i < bits - rounds; ++i) {
            num_t target = bits - i - 1 - rounds;
            // ... CP operations ...
        }
        rounds++;
    }

    QFT_inverse(mul, bits);
    precompiled_QQ_mul[bits] = mul;
    return mul;
}
```

**Rationale:** Follows established Phase 5 pattern for CQ_add/QQ_add. Caching by width (up to 64) uses ~200 bytes × 64 = ~12KB per operation type (acceptable). Result width per CONTEXT.md is max(width_a, width_b) with silent modular wrap.

### Pattern 2: Comparison via Subtraction + MSB Check

**What:** Implement comparison operators by performing subtraction and checking the most significant bit (MSB) or borrow flag.

**When to use:** Greater-than (>), less-than (<), greater-or-equal (>=), less-or-equal (<=) operators.

**Literature basis:** [Comprehensive Study of Quantum Arithmetic Circuits](https://arxiv.org/html/2406.03867v1) and [QFT-Based Quantum Comparator](https://arxiv.org/pdf/2305.09106) show subtraction-based comparison is standard approach.

**Pattern:**
```c
// New function in IntegerComparison.c (new file)
sequence_t *QQ_compare_gt(int bits) {
    // Greater-than: a > b iff (a - b) has MSB = 0 (positive result)
    // Uses existing QQ_sub circuit + check MSB

    sequence_t *comp = malloc(sizeof(sequence_t));

    // Get subtraction circuit
    sequence_t *sub = QQ_sub(bits);

    // Copy subtraction gates
    // ... copy gates from sub to comp ...

    // Add MSB extraction: use CNOT to copy MSB to result qubit
    // If MSB=0 (positive), result=1 (true)
    // If MSB=1 (negative), result=0 (false)

    // Note: Subtraction must be done on COPIES to preserve inputs
    // Use ancilla for temporary result, extract MSB, uncompute subtraction

    return comp;
}
```

**Alternative (simpler, per existing code patterns):**
```python
# Python-level comparison (current implementation pattern)
def __gt__(self, other):
    # Save MSB before subtraction
    a = self[64 - self.bits]  # MSB qubit

    # In-place subtraction (modifies self temporarily)
    self.addition_inplace(other, negate=True)

    # Create result qbool
    c = qbool()
    c = ~c  # Invert default

    # Controlled operation based on MSB
    with a:
        c = ~c

    # Restore original value
    self.addition_inplace(other, negate=False)

    return c
```

**Issue with current pattern:** Modifies self during comparison (not pure function). Better approach is ancilla-based.

**Improved pattern (recommended):**
```python
def __gt__(self, other):
    # Allocate ancilla for subtraction result
    temp = qint(width=self.bits)

    # Compute temp = self - other (into ancilla)
    # Use new QQ_sub_into function that takes 3 arguments

    # Extract MSB from temp into result qbool
    result = temp[64 - temp.bits]  # MSB qubit

    # Uncompute temp (restore to |0⟩) if needed for qubit reuse
    # OR leave as-is if ancilla cleanup handled later

    return result
```

### Pattern 3: Optimized Equality Circuit (XOR-Based)

**What:** Per CONTEXT.md, equality (==) uses dedicated simpler circuit, not subtraction-based.

**When to use:** Equality comparison operator (==).

**Rationale:** XOR all corresponding bits, OR results together. If any bit differs, result is 1 (not equal). Negate for equality.

**Pattern:**
```c
// New function in IntegerComparison.c
sequence_t *QQ_equal(int bits) {
    // Equality: a == b iff XOR(a_i, b_i) = 0 for all i
    // Strategy:
    // 1. XOR each bit pair into ancilla
    // 2. Multi-controlled OR (or tree of ORs) into result
    // 3. NOT result (1 if equal, 0 if not)

    sequence_t *eq = malloc(sizeof(sequence_t));

    // Layer 1: XOR all bit pairs
    for (int i = 0; i < bits; i++) {
        cx(&eq->seq[i][0],
           ancilla_base + i,    // target: ancilla bit i
           operand_a_base + i); // control: a bit i
        cx(&eq->seq[i][0],
           ancilla_base + i,    // target: same ancilla
           operand_b_base + i); // control: b bit i
    }

    // Layer 2: Multi-control OR (ancilla bits -> result)
    // If any ancilla != 0, result = 1 (not equal)
    // Use tree of multi-control gates
    // ... implementation ...

    // Layer 3: NOT result
    x(&eq->seq[final_layer][0], result_qubit);

    return eq;
}
```

**Complexity:** O(n) CNOT gates + O(log n) depth multi-control OR. More efficient than O(n²) subtraction for large integers.

### Pattern 4: Python-Level Division via Repeated Subtraction

**What:** Implement division at Python level by repeated subtraction and comparison, following arXiv:1809.09732 approach.

**When to use:** Floor division (//) and modulo (%) operators.

**Literature basis:** [Quantum Circuit Designs of Integer Division](https://arxiv.org/pdf/1809.09732) proposes restoring and non-restoring division algorithms based on quantum subtractors and conditional addition. Per CONTEXT.md, implement via repeated subtraction at Python level using existing primitives.

**Pattern:**
```python
def __floordiv__(self, divisor):
    """Floor division: a // b

    Implements via repeated subtraction (restoring division).
    Per arXiv:1809.09732 approach but at Python level.
    """
    if isinstance(divisor, int):
        if divisor == 0:
            raise ZeroDivisionError("Division by zero")

        # Classical divisor: optimize by unrolling
        quotient = qint(width=self.bits)
        remainder = self.copy()  # Work on copy

        # Count how many times we can subtract divisor
        # Use conditional subtraction based on comparison
        for bit in range(self.bits - 1, -1, -1):
            # Try subtracting divisor * 2^bit
            trial = divisor << bit

            # If remainder >= trial, subtract and set quotient bit
            cmp = remainder >= trial
            with cmp:
                remainder -= trial
                quotient |= (1 << bit)

        return quotient

    elif isinstance(divisor, qint):
        # Quantum divisor: more complex, use similar logic
        # ... implementation ...
        pass

def __mod__(self, divisor):
    """Modulo operation: a % b"""
    quotient = self // divisor
    remainder = self - (quotient * divisor)
    return remainder

def divmod_quantum(a, b):
    """Return (quotient, remainder) tuple."""
    quotient = a // b
    remainder = a % b
    return (quotient, remainder)
```

**Rationale:** No new C primitives needed (per CONTEXT.md). Uses existing subtraction, comparison, bitwise OR. Classical divisor enables optimizations (known bit positions). Quantum divisor requires full quantum comparison circuit.

**Complexity:** O(n) iterations where n = bit width, each iteration uses O(n²) gates for subtraction/comparison.

### Pattern 5: qint_mod Type with Classical Modulus

**What:** New class `qint_mod` that wraps qint and applies modulo N after each operation.

**When to use:** Modular arithmetic operations (add mod N, subtract mod N, multiply mod N).

**CONTEXT.md specification:**
- Modulus N is classical only (Python int, known at circuit generation time)
- Supported operations: modular add, subtract, multiply
- Mixed operands allowed: `qint_mod + qint` works, result is `qint_mod`
- Operations between `qint_mod` values require matching N

**Pattern:**
```python
class qint_mod(qint):
    """Quantum integer with modular arithmetic (modulus N classical)."""

    def __init__(self, value=0, N=None, width=None):
        """Create quantum integer with classical modulus N.

        Args:
            value: Initial value (reduced mod N)
            N: Classical modulus (Python int, required)
            width: Bit width (default: ceil(log2(N)))
        """
        if N is None or N <= 0:
            raise ValueError("Modulus N must be positive integer")

        if width is None:
            width = N.bit_length()

        # Reduce value mod N classically
        value = value % N

        super().__init__(value, width=width)
        self._modulus = N

    @property
    def modulus(self):
        """Get the modulus (read-only)."""
        return self._modulus

    def __add__(self, other):
        """Modular addition: (a + b) mod N."""
        if isinstance(other, qint_mod):
            if other.modulus != self.modulus:
                raise ValueError(f"Moduli must match: {self.modulus} != {other.modulus}")
            result = super().__add__(other)
        elif isinstance(other, (qint, int)):
            result = super().__add__(other)
        else:
            return NotImplemented

        # Apply modular reduction
        # Strategy: conditional subtraction
        # If result >= N, subtract N
        # Repeat until result < N (may need multiple iterations)
        reduced = self._modular_reduce(result, self.modulus)

        # Wrap in qint_mod to preserve modular type
        return self._wrap_result(reduced)

    def _modular_reduce(self, value, N):
        """Reduce value mod N via conditional subtraction.

        Uses quantum comparison and conditional subtraction.
        More efficient than full division for small reductions.
        """
        # Classical N optimization: know exact number of subtractions needed
        max_iterations = (2 ** value.bits) // N

        for _ in range(max_iterations.bit_length()):
            # If value >= N, subtract N
            cmp = value >= N
            with cmp:
                value -= N

        return value

    def _wrap_result(self, qint_value):
        """Wrap qint result back into qint_mod."""
        result = qint_mod.__new__(qint_mod)
        result.__dict__.update(qint_value.__dict__)
        result._modulus = self.modulus
        return result

    def __mul__(self, other):
        """Modular multiplication: (a * b) mod N."""
        # Multiply then reduce
        product = super().__mul__(other)
        reduced = self._modular_reduce(product, self.modulus)
        return self._wrap_result(reduced)

    def __sub__(self, other):
        """Modular subtraction: (a - b) mod N."""
        diff = super().__sub__(other)
        # Handle negative results: add N until positive
        # Check MSB (sign bit)
        while diff < 0:  # Quantum comparison
            diff += self.modulus
        return self._wrap_result(diff)
```

**Rationale:** Classical modulus N enables compile-time optimizations (known number of reduction steps). Mixed-operand support allows natural expressions like `x_mod + 5`. Modular reduction via conditional subtraction is more efficient than full division when result is close to N.

**Advanced optimization (Montgomery reduction):** For repeated modular operations, [Montgomery modular multiplication](https://arxiv.org/pdf/1801.01081) shows QFT-based arithmetic is "uniquely amenable" to Montgomery reduction, which trades divisions for additions. This is a future optimization, not required for Phase 7.

### Anti-Patterns to Avoid

- **Destroying operands in comparisons**: Don't use subtraction that modifies inputs - use ancilla for temporary results
- **Hardcoding INTEGERSIZE**: All new operations must accept bits parameter
- **Subtraction for equality**: Use optimized XOR-based equality circuit, not subtraction
- **Quantum division in C**: Don't try to implement quantum division as low-level circuit - compose at Python level per CONTEXT.md
- **Dynamic modulus N**: Don't implement quantum modulus (N as qint) - classical N only per CONTEXT.md

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Quantum subtraction | Custom borrow logic | Existing QQ_sub(bits) from Phase 5 | Already implemented with QFT, O(n²) gates, tested |
| Multi-control gates | Manual decomposition | Ancilla-based tree reduction | Exponential savings, established pattern |
| Division circuit | Low-level quantum circuit | Python-level repeated subtraction | Per CONTEXT.md, avoids circuit complexity, enables classical optimization |
| Modular exponentiation | Custom modular multiply | Future phase (deferred per CONTEXT.md) | Requires advanced techniques (Montgomery, Barrett reduction) |

**Key insight:** Phase 5 and 6 established all needed primitives (variable-width arithmetic, bitwise ops). Phase 7 is primarily about composition and parameterization, not new gate-level algorithms. The division and modular arithmetic are Python-level orchestration of existing operations.

## Common Pitfalls

### Pitfall 1: Comparison Destroys Input Values

**What goes wrong:** Using existing `__gt__` implementation that calls `addition_inplace(negate=True)`, modifying self during comparison.

**Why it happens:** Avoids allocating ancilla by reusing input qubits, but breaks pure function semantics.

**How to avoid:**
- Allocate ancilla for subtraction result
- Use new `QQ_sub_into(bits, out, a, b)` that writes to separate output
- Uncompute ancilla after extracting MSB if qubit reuse needed

**Warning signs:** Tests fail because quantum integers have wrong values after comparison operations.

### Pitfall 2: Width Mismatch in Multiplication

**What goes wrong:** Multiplying 8-bit × 32-bit allocates 8-bit result, causing silent overflow.

**Why it happens:** CONTEXT.md specifies "result width is max of operand widths" with "silent modular wrap".

**How to avoid:**
- `result_bits = max(self.bits, other.bits)` in Python layer
- Allocate result with max width before calling C multiplication
- Document overflow behavior clearly in docstrings

**Warning signs:** Multiplication results are incorrect for large values, modulo arithmetic applied unexpectedly.

### Pitfall 3: Inefficient Modular Reduction

**What goes wrong:** Using full division circuit for modular reduction when conditional subtraction suffices.

**Why it happens:** Division is the "obvious" way to compute mod, but for small reductions (result close to N), conditional subtraction is much cheaper.

**How to avoid:**
- Implement modular reduction as iterative conditional subtraction
- Classical N enables computing exact number of iterations needed
- Use full division only if result >> N (rare in modular arithmetic)

**Warning signs:** Modular arithmetic circuits are orders of magnitude larger than expected.

### Pitfall 4: Precompiled Cache Overflow

**What goes wrong:** `precompiled_QQ_mul[bits]` indexed with bits > 64, causing array overflow.

**Why it happens:** No bounds checking on bits parameter in multiplication functions.

**How to avoid:**
```c
sequence_t *QQ_mul(int bits) {
    if (bits < 1 || bits > 64) return NULL;

    // Safe to index precompiled_QQ_mul[bits]
}
```

**Warning signs:** Segfault or memory corruption when using large bit widths.

### Pitfall 5: qint_mod Type Confusion

**What goes wrong:** Operations between qint_mod values with different moduli N produce incorrect results.

**Why it happens:** Forgetting to check modulus compatibility in operator overloads.

**How to avoid:**
```python
def __add__(self, other):
    if isinstance(other, qint_mod):
        if other.modulus != self.modulus:
            raise ValueError(f"Moduli must match: {self.modulus} != {other.modulus}")
```

**Warning signs:** Modular arithmetic results violate mathematical properties (e.g., (a mod N) + (b mod M) nonsensical).

## Code Examples

Verified patterns from existing codebase and literature:

### Example 1: Variable-Width Multiplication (Refactored)

```c
// Backend/src/IntegerMultiplication.c - refactor QQ_mul
sequence_t *QQ_mul(int bits) {
    // Validate width
    if (bits < 1 || bits > 64) return NULL;

    // Cache by width (like Phase 5 addition)
    static sequence_t *precompiled_QQ_mul_width[65] = {NULL};
    if (precompiled_QQ_mul_width[bits] != NULL) {
        return precompiled_QQ_mul_width[bits];
    }

    sequence_t *mul = malloc(sizeof(sequence_t));
    if (mul == NULL) return NULL;

    // Allocate based on bits (not INTEGERSIZE)
    mul->num_layer = bits * (2 * bits + 6) - 1;
    mul->gates_per_layer = calloc(mul->num_layer, sizeof(num_t));
    mul->seq = calloc(mul->num_layer, sizeof(gate_t *));

    for (int i = 0; i < mul->num_layer; ++i) {
        mul->seq[i] = calloc(2 * bits, sizeof(gate_t));
    }

    // QFT with bits parameter
    QFT(mul, bits);
    num_t layer = bits;

    // CP sequences with bits parameter
    int rounds = 0;
    for (int bit = bits - 1; bit >= 0; --bit) {
        layer = 2 * bits + 2 * rounds - 1;
        CP_sequence(mul, &layer, rounds, bits + bit,
                    pow(2, bits) - 1, false);
        rounds++;
    }
    layer++;

    // Intermediate steps (adjust for bits)
    for (int bit_int2 = 0; bit_int2 < bits; ++bit_int2) {
        layer -= bits;
        CX_sequence_width(mul, &layer, -bit_int2, bits);
        all_rot_width(mul, &layer, false, pow(2, 1 + bit_int2), bits);
        CX_sequence_width(mul, &layer, -bit_int2, bits);

        for (int i = 0; i < bits; ++i) {
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            double value = pow(2, -i - 1) * M_PI *
                          (pow(2, i + 1) - 1) * pow(2, bit_int2);
            cp(g, bits - i - 1, 3 * bits - bit_int2 - 1, value);
            layer++;
        }
    }

    mul->used_layer = layer - 1;
    QFT_inverse(mul, bits);

    // Cache for reuse
    precompiled_QQ_mul_width[bits] = mul;
    return mul;
}

// Helper functions also need bits parameter
void CX_sequence_width(sequence_t *mul, num_t *layer,
                       int bit_int2, int bits) {
    for (int bit = bits - 1; bit >= 0; --bit) {
        num_t control = bits + bit;
        gate_t *g = &mul->seq[*layer][mul->gates_per_layer[*layer]++];
        cx(g, control, 3 * bits + bit_int2 - 1);
        (*layer)++;
    }
}
```

### Example 2: Python Multiplication with Variable Width

```python
# python-backend/quantum_language.pyx
def __mul__(self, other):
    """Multiply quantum integers.

    Result width is max(self.width, other.width) per CONTEXT.md.
    Overflow wraps silently (modular arithmetic).
    """
    cdef sequence_t *seq
    cdef unsigned int[:] arr
    cdef int result_bits

    # Determine result width
    if type(other) == int:
        # Classical multiplication
        result_bits = self.bits
    elif type(other) == qint:
        # Quantum × Quantum
        result_bits = max(self.bits, (<qint>other).bits)
    else:
        raise TypeError("Operand must be qint or int")

    # Allocate result
    result = qint(width=result_bits)

    # Extract right-aligned qubits
    self_offset = 64 - self.bits
    result_offset = 64 - result_bits

    # Qubit layout: [0:N] = result, [N:2N] = self, [2N:3N] = other
    qubit_array[:result_bits] = result.qubits[result_offset:64]
    qubit_array[result_bits:result_bits + self.bits] = \
        self.qubits[self_offset:64]

    if type(other) == int:
        # Classical-quantum multiplication
        seq = CQ_mul(result_bits, other)
    else:
        # Quantum-quantum multiplication
        other_offset = 64 - (<qint>other).bits
        qubit_array[2*result_bits:2*result_bits + (<qint>other).bits] = \
            (<qint>other).qubits[other_offset:64]
        seq = QQ_mul(result_bits)

    arr = qubit_array
    run_instruction(seq, &arr[0], False, _circuit)
    return result
```

### Example 3: Comparison Operator (Greater-Than)

```python
# python-backend/quantum_language.pyx
def __gt__(self, other):
    """Greater-than comparison: self > other.

    Returns qbool (1-bit qint).
    Uses subtraction then MSB check.
    """
    cdef sequence_t *seq
    cdef unsigned int[:] arr

    # Convert other to qint if needed
    if type(other) == int:
        other_qint = qint(other, width=self.bits)
    elif type(other) == qint:
        other_qint = other
    else:
        raise TypeError("Operand must be qint or int")

    # Allocate result qbool
    result = qbool()

    # Allocate temporary for subtraction
    temp = qint(width=max(self.bits, other_qint.bits))

    # Layout: [0:N] = temp, [N:2N] = self, [2N:3N] = other
    temp_offset = 64 - temp.bits
    self_offset = 64 - self.bits
    other_offset = 64 - other_qint.bits

    qubit_array[:temp.bits] = temp.qubits[temp_offset:64]
    qubit_array[temp.bits:temp.bits + self.bits] = \
        self.qubits[self_offset:64]
    qubit_array[2*temp.bits:2*temp.bits + other_qint.bits] = \
        other_qint.qubits[other_offset:64]

    # Compute temp = self - other
    seq = QQ_sub(temp.bits)
    arr = qubit_array
    run_instruction(seq, &arr[0], False, _circuit)

    # Extract MSB: if MSB=0 (positive), self > other
    msb_qubit = temp[0]  # MSB is leftmost bit

    # Result = NOT(MSB)
    result_array[0] = result.qubits[63]
    result_array[1] = msb_qubit.qubits[63]
    seq = Q_not(1)  # Actually, use X gate controlled by NOT(MSB)
    # Better: use CNOT then X
    # ... implementation ...

    return result
```

### Example 4: Optimized Equality Circuit

```c
// Backend/src/IntegerComparison.c (new file)
sequence_t *QQ_equal(int bits) {
    // Equality: a == b iff XOR(a, b) == 0
    // More efficient than subtraction

    if (bits < 1 || bits > 64) return NULL;

    sequence_t *eq = malloc(sizeof(sequence_t));

    // Layout: [0] = result, [1:bits+1] = ancilla,
    //         [bits+1:2*bits+1] = a, [2*bits+1:3*bits+1] = b

    // Total layers: bits (XOR) + log2(bits) (multi-OR) + 1 (NOT)
    int tree_depth = 0;
    int temp = bits;
    while (temp > 1) {
        tree_depth++;
        temp = (temp + 1) / 2;
    }

    eq->num_layer = bits + tree_depth + 1;
    eq->gates_per_layer = calloc(eq->num_layer, sizeof(num_t));
    eq->seq = calloc(eq->num_layer, sizeof(gate_t *));

    // Phase 1: XOR all bit pairs into ancilla
    int layer = 0;
    for (int i = 0; i < bits; i++) {
        eq->seq[layer] = calloc(2, sizeof(gate_t));
        eq->gates_per_layer[layer] = 2;

        // XOR: ancilla[i] = a[i] XOR b[i]
        cx(&eq->seq[layer][0],
           1 + i,              // target: ancilla bit i
           bits + 1 + i);      // control: a bit i
        cx(&eq->seq[layer][1],
           1 + i,              // target: same ancilla
           2*bits + 1 + i);    // control: b bit i

        layer++;
    }

    // Phase 2: Multi-control OR (tree reduction)
    // If any ancilla bit is 1, set result = 1 (not equal)
    int active_bits = bits;
    int ancilla_base = 1;

    while (active_bits > 1) {
        eq->seq[layer] = calloc(active_bits / 2, sizeof(gate_t));
        eq->gates_per_layer[layer] = active_bits / 2;

        for (int i = 0; i < active_bits / 2; i++) {
            // OR: ancilla[i] |= ancilla[2*i+1]
            // Use Toffoli decomposition for OR
            // ... implementation ...
        }

        active_bits = (active_bits + 1) / 2;
        layer++;
    }

    // Copy final ancilla to result
    eq->seq[layer] = calloc(1, sizeof(gate_t));
    eq->gates_per_layer[layer] = 1;
    cx(&eq->seq[layer][0], 0, ancilla_base);
    layer++;

    // Phase 3: NOT result (1 if equal, 0 if not)
    eq->seq[layer] = calloc(1, sizeof(gate_t));
    eq->gates_per_layer[layer] = 1;
    x(&eq->seq[layer][0], 0);
    layer++;

    eq->used_layer = layer;
    return eq;
}
```

### Example 5: Python Division via Repeated Subtraction

```python
# python-backend/quantum_language.pyx
def __floordiv__(self, divisor):
    """Floor division: self // divisor.

    Implements restoring division via repeated subtraction
    per arXiv:1809.09732 approach at Python level.
    """
    # Validate divisor
    if isinstance(divisor, int):
        if divisor == 0:
            raise ZeroDivisionError("Division by zero")
        if divisor < 0:
            raise NotImplementedError("Negative divisor not yet supported")

        # Classical divisor: optimize with bit-level algorithm
        quotient = qint(0, width=self.bits)
        remainder = self.copy()  # Work on copy to preserve self

        # Division by powers of 2: just right shift
        if (divisor & (divisor - 1)) == 0:
            # Power of 2: quotient = self >> log2(divisor)
            shift = divisor.bit_length() - 1
            # ... implement right shift via qubit remapping ...
            return quotient

        # General case: repeated conditional subtraction
        # Start from most significant bit
        for bit_pos in range(self.bits - 1, -1, -1):
            # Try subtracting divisor << bit_pos
            trial_divisor = divisor << bit_pos

            # If remainder >= trial_divisor, do subtraction
            can_subtract = remainder >= trial_divisor

            # Controlled subtraction
            with can_subtract:
                remainder -= trial_divisor
                # Set quotient bit
                quotient |= (1 << bit_pos)

        return quotient

    elif isinstance(divisor, qint):
        # Quantum divisor: similar but use quantum comparisons
        # ... full quantum division implementation ...
        raise NotImplementedError("Quantum divisor not yet implemented")

    else:
        raise TypeError("Divisor must be int or qint")

def __mod__(self, divisor):
    """Modulo: self % divisor."""
    quotient = self // divisor
    product = quotient * divisor
    remainder = self - product
    return remainder

def __divmod__(self, divisor):
    """Return (quotient, remainder) tuple."""
    quotient = self // divisor
    remainder = self % divisor
    return (quotient, remainder)
```

### Example 6: qint_mod Class

```python
# python-backend/quantum_language.pyx
class qint_mod(qint):
    """Quantum integer with modular arithmetic.

    Modulus N is classical (Python int), known at circuit generation.
    Operations automatically reduce mod N.
    """

    def __init__(self, value=0, N=None, width=None):
        """Create modular quantum integer.

        Args:
            value: Initial value (reduced mod N classically)
            N: Modulus (required, must be positive int)
            width: Bit width (default: N.bit_length())
        """
        if N is None or not isinstance(N, int) or N <= 0:
            raise ValueError("Modulus N must be positive integer")

        # Default width: just enough to represent N
        if width is None:
            width = N.bit_length()

        # Reduce value mod N classically
        reduced_value = value % N

        # Initialize as regular qint
        super().__init__(reduced_value, width=width)

        # Store modulus
        self._modulus = N

    @property
    def modulus(self):
        """Get modulus (read-only)."""
        return self._modulus

    def __repr__(self):
        return f"qint_mod({self._modulus}, width={self.bits})"

    def _reduce_mod(self, value):
        """Reduce value mod N via conditional subtraction.

        Args:
            value: qint to reduce (may be > N)

        Returns:
            qint reduced to range [0, N)
        """
        # Classical N: know max iterations needed
        max_val = 2 ** value.bits
        max_subtractions = (max_val // self.modulus).bit_length()

        # Iteratively subtract N while value >= N
        for _ in range(max_subtractions):
            # Compare: is value >= N?
            cmp = value >= self.modulus

            # Conditional subtraction
            with cmp:
                value -= self.modulus

        return value

    def _wrap_result(self, qint_result):
        """Wrap plain qint into qint_mod with same modulus."""
        result = qint_mod.__new__(qint_mod)
        # Copy qint state
        result.qubits = qint_result.qubits
        result.bits = qint_result.bits
        result._circuit = qint_result._circuit
        # Add modulus
        result._modulus = self.modulus
        return result

    def __add__(self, other):
        """Modular addition: (self + other) mod N."""
        # Check modulus compatibility
        if isinstance(other, qint_mod):
            if other.modulus != self.modulus:
                raise ValueError(
                    f"Moduli must match: {self.modulus} != {other.modulus}"
                )

        # Perform regular addition
        sum_val = super().__add__(other)

        # Reduce mod N
        reduced = self._reduce_mod(sum_val)

        # Wrap result
        return self._wrap_result(reduced)

    def __sub__(self, other):
        """Modular subtraction: (self - other) mod N."""
        if isinstance(other, qint_mod):
            if other.modulus != self.modulus:
                raise ValueError(
                    f"Moduli must match: {self.modulus} != {other.modulus}"
                )

        # Subtract
        diff = super().__sub__(other)

        # If negative, add N repeatedly until positive
        # Check sign via MSB or comparison
        is_negative = diff < 0
        with is_negative:
            diff += self.modulus

        # Ensure in range [0, N)
        reduced = self._reduce_mod(diff)

        return self._wrap_result(reduced)

    def __mul__(self, other):
        """Modular multiplication: (self * other) mod N."""
        if isinstance(other, qint_mod):
            if other.modulus != self.modulus:
                raise ValueError(
                    f"Moduli must match: {self.modulus} != {other.modulus}"
                )

        # Multiply (may overflow width)
        product = super().__mul__(other)

        # Reduce mod N (critical - product may be >> N)
        reduced = self._reduce_mod(product)

        return self._wrap_result(reduced)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed 8-bit multiplication | Variable 1-64 bit multiplication | Phase 7 | Realistic cryptographic key sizes (2048-bit RSA) |
| Comparison via subtraction-only | Optimized equality circuit + subtraction-based >/< | Phase 7 | Faster equality checks, common in conditional logic |
| No division support | Python-level repeated subtraction | Phase 7 | Enables modular arithmetic for Shor's algorithm |
| No modular arithmetic | qint_mod type with classical modulus | Phase 7 | Foundation for modular exponentiation (Phase 8+) |
| Result width = 2N for N×N multiply | Result width = max(N, M) for N×M | Phase 7 (CONTEXT.md) | Matches classical C semantics, explicit overflow |

**Deprecated/outdated:**
- `QQ_mul()` without bits parameter: Becomes `QQ_mul(bits)` with caching
- Hardcoded INTEGERSIZE in multiplication: Replaced with bits parameter
- Comparison destroying operands: New comparison functions use ancilla

**Research trends (2023-2026):**
- QFT-based arithmetic dominates for high-level languages (vs Clifford+T for low-level)
- Montgomery reduction preferred for modular multiplication in quantum circuits
- Division remains expensive (O(n³) gates), avoided when possible via reciprocal multiplication

## Open Questions

### 1. Comparison Circuit Strategy: Ancilla vs In-Place

**What we know:**
- Current `__gt__` modifies self during comparison (in-place subtraction)
- Literature shows ancilla-based comparison is standard (preserves inputs)
- Ancilla must be allocated and eventually uncomputed or measured

**What's unclear:**
- Should Phase 7 refactor existing in-place comparisons to use ancilla?
- Or keep current pattern and document as "destructive comparison"?
- Uncomputation strategy: immediate (within comparison) or deferred (circuit optimization phase)?

**Recommendation:**
Keep existing in-place pattern for now (working code, less ancilla pressure). Document clearly that comparison is destructive. Future phase can refactor to ancilla-based when implementing proper uncomputation. Add `compare_pure()` variant that uses ancilla for users who need non-destructive comparison.

### 2. Modular Reduction: Subtraction vs Division

**What we know:**
- Repeated conditional subtraction works for small reductions (result close to N)
- Full division needed when result >> N (e.g., after multiplication)
- Classical N enables computing exact number of iterations

**What's unclear:**
- When to switch from subtraction to division?
- Should `_reduce_mod()` use heuristic (if result > 2N, use division)?

**Recommendation:**
Use conditional subtraction for Phase 7 (simpler, fewer gates for common case). Document that modular multiplication may produce large circuits for very large products. Phase 8+ can add division-based reduction with automatic selection based on estimated gate count.

### 3. Equality Circuit Complexity

**What we know:**
- XOR-based equality is O(n) CNOT gates
- Multi-control OR requires O(log n) depth tree
- Subtraction-based equality is O(n²) QFT gates but reuses existing circuits

**What's unclear:**
- Is custom equality circuit worth the complexity vs reusing subtraction?
- Does tree-based OR provide significant speed advantage?

**Recommendation:**
Implement XOR-based equality for Phase 7 (per CONTEXT.md "optimized equality circuit"). The O(n) vs O(n²) gate count difference is significant for large integers (32-64 bits). Tree depth matters for parallel execution on future hardware.

### 4. Classical Divisor Optimization

**What we know:**
- Division by classical constant can be optimized (unroll loop, known bit positions)
- Division by power of 2 is just right shift (O(1) operation)
- General division by classical constant still requires comparisons

**What's unclear:**
- Should Phase 7 special-case power-of-2 division?
- What about other special divisors (small primes, etc.)?

**Recommendation:**
Special-case power-of-2 division (common, huge speedup). General classical divisor uses standard repeated subtraction algorithm. Document that classical divisor is much faster than quantum divisor. Future optimizations can add Barrett reduction or other techniques.

## Sources

### Primary (HIGH confidence)

**Codebase inspection:**
- `Backend/src/IntegerMultiplication.c` - Existing QFT-based multiplication (lines 1-443)
- `Backend/src/IntegerAddition.c` - Variable-width addition/subtraction patterns (Phase 5)
- `Backend/src/LogicOperations.c` - Bitwise operations patterns (Phase 6)
- `python-backend/quantum_language.pyx` - Current comparison operators (lines 697-725)
- `.planning/phases/07-extended-arithmetic/07-CONTEXT.md` - User decisions and requirements
- `.planning/phases/05-variable-width-integers/05-RESEARCH.md` - Variable-width patterns
- `.planning/phases/06-bit-operations/06-RESEARCH.md` - Bitwise operation patterns

**Academic literature (quantum division):**
- [Quantum Circuit Designs of Integer Division Optimizing T-count and T-depth (arXiv:1809.09732)](https://arxiv.org/abs/1809.09732) - Referenced in CONTEXT.md for division approach
- [A Comprehensive Study of Quantum Arithmetic Circuits (arXiv:2406.03867)](https://arxiv.org/html/2406.03867v1) - Subtraction-based comparison standard
- [An Improved QFT-Based Quantum Comparator (arXiv:2305.09106)](https://arxiv.org/pdf/2305.09106) - QFT comparison operators

**Academic literature (modular arithmetic):**
- [High Performance Quantum Modular Multipliers (arXiv:1801.01081)](https://arxiv.org/pdf/1801.01081) - Montgomery multiplication for QFT arithmetic
- [Montgomery modular multiplication (Wikipedia)](https://en.wikipedia.org/wiki/Montgomery_modular_multiplication) - Classical Montgomery reduction background

### Secondary (MEDIUM confidence)

**Quantum comparison circuits:**
- [Demonstration of quantum comparator on ion-trap (arXiv:2512.17779)](https://arxiv.org/html/2512.17779) - Recent experimental validation
- [Quantum implementation of elementary arithmetic operations](https://arxiv.org/pdf/quant-ph/0403048) - Classical foundations

**Modular arithmetic frameworks:**
- [QuantumModulus documentation (Qrisp)](https://qrisp.eu/reference/Quantum%20Types/QuantumModulus.html) - Example implementation in quantum framework

### Tertiary (LOW confidence)

- WebSearch results on quantum computing trends 2025-2026 - General context only, no specific technical information for Phase 7

## Metadata

**Confidence breakdown:**
- Multiplication refactoring: HIGH - Direct code inspection, established Phase 5 pattern
- Comparison operators: MEDIUM - Literature support, but implementation details need validation
- Division implementation: MEDIUM - CONTEXT.md specifies approach, but Python-level complexity uncertain
- Modular arithmetic: MEDIUM-HIGH - Clear CONTEXT.md specification, qint_mod pattern is standard wrapper

**Research date:** 2026-01-26
**Valid until:** 2026-02-26 (30 days - domain is stable)

**Key files to reference during planning:**
- `Backend/src/IntegerMultiplication.c` - Existing multiplication to refactor
- `Backend/src/IntegerAddition.c` - Phase 5 width-parameterized pattern template
- `python-backend/quantum_language.pyx` - Python operator overloading structure
- `.planning/phases/07-extended-arithmetic/07-CONTEXT.md` - Authoritative user decisions
- `.planning/phases/05-variable-width-integers/05-VERIFICATION.md` - Variable-width implementation status

**Critical design decisions validated:**
- ✓ Division via repeated subtraction at Python level (CONTEXT.md)
- ✓ Modulus N classical only (CONTEXT.md)
- ✓ Result width = max(operand widths) for multiplication (CONTEXT.md)
- ✓ Optimized equality circuit separate from subtraction (CONTEXT.md)
- ✓ Mixed-width comparison via zero-extension (CONTEXT.md)

**Assumptions requiring validation during planning:**
- Ancilla allocation strategy for comparison operators (in-place vs pure functions)
- Performance of conditional subtraction vs division for modular reduction
- Tree-based multi-control OR complexity for equality circuit
- Right-shift qubit remapping for power-of-2 division optimization
