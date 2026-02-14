# Phase 66: CDKM Ripple-Carry Adder - Research

**Researched:** 2026-02-14
**Domain:** Toffoli-based quantum arithmetic (CDKM ripple-carry addition)
**Confidence:** HIGH

## Summary

Phase 66 implements the CDKM (Cuccaro-Draper-Kutin-Moulton, 2004) ripple-carry adder as the project's first Toffoli-based arithmetic operation. The algorithm uses two primitive 3-qubit sub-circuits -- MAJ (majority) and UMA (unmajority-and-add) -- chained in a forward/reverse sweep to perform n-bit in-place addition using exactly 1 ancilla qubit, O(n) Toffoli gates, and O(n) CNOT gates. This is architecturally significant: it is the foundation for all subsequent Toffoli-based operations (multiplication, division, comparison) and is the first arithmetic operation in this codebase to require ancilla qubit allocation.

The existing codebase has complete infrastructure for this phase. The gate primitives (`ccx()`, `cx()`, `x()` in `gate.c`) already exist and are used by comparison/bitwise operations. The `sequence_t` pipeline (`run_instruction()`, `add_gate()`) is gate-type agnostic. The `qubit_allocator` (Phase 65) supports ancilla alloc/free with block reuse and lifecycle assertions. The `run_instruction()` inversion logic (Phase 65) correctly handles self-inverse gates (X, CX, CCX) by not negating `GateValue`. The hot path pattern (`hot_path_add.c`) provides the exact dispatch template to extend.

The phase scope is constrained to four requirements: QQ addition (ADD-01), CQ addition (ADD-02), subtraction via inverse (ADD-05), and mixed-width via zero-extension (ADD-07). Controlled variants (cQQ, cCQ) are NOT in the success criteria and should be deferred. The focus is on getting the foundational adder correct and verified for widths 1-4 with exhaustive input testing.

**Primary recommendation:** Implement `ToffoliAddition.c` with `toffoli_QQ_add(bits)` and `toffoli_CQ_add(bits, val)` using the MAJ/UMA chain algorithm, wire into `hot_path_add.c` via a new `arithmetic_mode` field on `circuit_t`, and verify exhaustively against classical computation for all input pairs at widths 1-4.

## Standard Stack

### Core

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `ccx()` | `c_backend/src/gate.c:200` | Toffoli gate primitive | Already exists, used by IntegerComparison.c |
| `cx()` | `c_backend/src/gate.c:193` | CNOT gate primitive | Already exists, used everywhere |
| `x()` | `c_backend/src/gate.c:187` | NOT gate primitive | Already exists |
| `sequence_t` | `c_backend/include/types.h:77` | Gate sequence container | Standard container for all arithmetic sequences |
| `run_instruction()` | `c_backend/src/execution.c:14` | Execute sequence with qubit mapping + inversion | Phase 65 fixed self-inverse gate handling |
| `allocator_alloc/free` | `c_backend/src/qubit_allocator.c:124,241` | Ancilla qubit lifecycle | Phase 65 added block reuse + coalescing + DEBUG assertions |
| `hot_path_add_qq/cq` | `c_backend/src/hot_path_add.c` | C hot path for addition dispatch | Phase 60 pattern, extends cleanly |

### New Files Required

| File | Purpose | Estimated Lines |
|------|---------|-----------------|
| `c_backend/src/ToffoliAddition.c` | CDKM adder: `toffoli_QQ_add()`, `toffoli_CQ_add()` + MAJ/UMA helpers | ~300 |
| `c_backend/include/toffoli_arithmetic_ops.h` | Public API header for Toffoli arithmetic | ~40 |

### Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `c_backend/include/types.h` | Add `arithmetic_mode_t` enum | ~2 |
| `c_backend/include/circuit.h` | Add `arithmetic_mode` field to `circuit_t` | ~1 |
| `c_backend/src/circuit_allocations.c` | Initialize `arithmetic_mode = ARITH_QFT` in `init_circuit()` | ~1 |
| `c_backend/src/hot_path_add.c` | Add Toffoli dispatch path with ancilla alloc/free | ~40 |
| `src/quantum_language/_core.pxd` | Declare Toffoli C functions + extend `circuit_s` struct | ~15 |
| `src/quantum_language/_core.pyx` | Add `fault_tolerant` to `option()` function | ~15 |
| `setup.py` | Add `ToffoliAddition.c` to `c_sources` | ~1 |

### Files NOT Changed

| File | Why No Change |
|------|---------------|
| `qint_arithmetic.pxi` | Dispatch is in C hot path; Cython layer is transparent |
| `IntegerAddition.c` | QFT code stays as-is; Toffoli lives in separate file |
| `execution.c` | Already handles self-inverse gates correctly (Phase 65) |
| `qubit_allocator.c` | Already supports ancilla alloc/free with block reuse (Phase 65) |

## Architecture Patterns

### Recommended Project Structure

```
c_backend/
  include/
    toffoli_arithmetic_ops.h    # New: Public API for Toffoli arithmetic
    types.h                     # Modified: arithmetic_mode_t enum
    circuit.h                   # Modified: arithmetic_mode field
  src/
    ToffoliAddition.c           # New: CDKM adder implementation
    hot_path_add.c              # Modified: Toffoli dispatch
```

### Pattern 1: MAJ/UMA Gate Composition

**What:** The CDKM adder is built from two primitive 3-qubit gate sequences. MAJ computes carry; UMA uncomputes carry and writes sum.

**When to use:** For all CDKM ripple-carry addition circuits.

**MAJ gate decomposition (verified from Cuccaro et al. 2004, Section 3):**
```c
// MAJ(a, b, c): computes majority = carry-out into c
// Input:  a = carry_in,  b = b_i,  c = a_i
// Output: a = a_i XOR carry_in,  b = a_i XOR b_i,  c = carry_out
//
// Gate sequence:
//   CNOT(target=b, control=c)       -- b ^= c  => b = b_i XOR a_i
//   CNOT(target=a, control=c)       -- a ^= c  => a = carry_in XOR a_i
//   Toffoli(target=c, ctrl1=a, ctrl2=b)  -- c ^= (a AND b)
//     After substitution: c = a_i XOR ((carry_in XOR a_i) AND (b_i XOR a_i))
//     Which simplifies to: c = MAJ(carry_in, a_i, b_i) = carry_out
static void emit_MAJ(sequence_t *seq, num_t *layer,
                     qubit_t a, qubit_t b, qubit_t c) {
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, c);
    (*layer)++;
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c);
    (*layer)++;
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
    (*layer)++;
}
```

**UMA gate decomposition (verified from Cuccaro et al. 2004, Section 3):**
```c
// UMA(a, b, c): uncomputes carry and writes sum bit
// Input:  a = carry_in XOR a_i,  b = a_i XOR b_i,  c = carry_out
// Output: a = carry_in,  b = sum_i = carry_in XOR a_i XOR b_i,  c = a_i
//
// Gate sequence:
//   Toffoli(target=c, ctrl1=a, ctrl2=b)  -- undoes MAJ's Toffoli
//   CNOT(target=a, control=c)            -- restores a = carry_in
//   CNOT(target=b, control=a)            -- b = sum = carry_in XOR a_i XOR b_i
static void emit_UMA(sequence_t *seq, num_t *layer,
                     qubit_t a, qubit_t b, qubit_t c) {
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
    (*layer)++;
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c);
    (*layer)++;
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, a);
    (*layer)++;
}
```

### Pattern 2: Full n-bit CDKM Adder Construction

**What:** Chain MAJ gates forward (carry propagation) then UMA gates backward (sum computation + carry uncomputation).

**Qubit layout (virtual indices in sequence_t):**
```
[0..n-1]     : register a (target, modified to hold a+b)
[n..2n-1]    : register b (source, preserved)
[2n]         : ancilla carry qubit (starts at |0>, ends at |0>)
```

**Algorithm:**
```c
sequence_t *toffoli_QQ_add(int bits) {
    if (bits < 1 || bits > 64) return NULL;
    if (precompiled[bits] != NULL) return precompiled[bits];

    int ancilla = 2 * bits;  // Virtual index for ancilla qubit

    // Special case: 1-bit addition is just a CNOT
    if (bits == 1) {
        // a[0] += b[0]  =>  CNOT(target=a[0], control=b[0])
        // No ancilla needed for 1-bit add
        // Allocate 1-layer sequence...
        cx(&seq->seq[0][0], 0, bits);  // a[0] ^= b[0]
        return seq;
    }

    // General case: n >= 2
    // Layer count: 3 gates per MAJ * n + 3 gates per UMA * n - 3
    //   = 6n - 3 layers (each layer holds 1 gate for sequential execution)
    int num_layers = 6 * bits - 3;

    // Forward sweep: MAJ chain
    num_t layer = 0;
    emit_MAJ(seq, &layer, ancilla, bits + 0, 0);     // MAJ(anc, b[0], a[0])
    for (int i = 1; i < bits; i++) {
        emit_MAJ(seq, &layer, i - 1, bits + i, i);   // MAJ(a[i-1], b[i], a[i])
    }

    // Reverse sweep: UMA chain
    for (int i = bits - 1; i >= 1; i--) {
        emit_UMA(seq, &layer, i - 1, bits + i, i);   // UMA(a[i-1], b[i], a[i])
    }
    emit_UMA(seq, &layer, ancilla, bits + 0, 0);     // UMA(anc, b[0], a[0])

    seq->used_layer = layer;
    precompiled[bits] = seq;
    return seq;
}
```

**Gate counts for n-bit addition (n >= 2):**
- Toffoli (CCX) gates: 2n - 2 (one per MAJ except first shares with UMA)
- CNOT (CX) gates: 4n - 2
- Total gates: 6n - 4
- Ancilla: 1 qubit
- Depth: 6n - 3 (sequential)

Note: The exact gate count depends on whether n=1 special case uses 0 or 1 ancilla. For n=1, a single CNOT suffices (no ancilla).

### Pattern 3: CQ Addition (Classical + Quantum)

**What:** When adding a classical value, bits where the classical value is 0 allow gate simplification.

**When to use:** For `toffoli_CQ_add(bits, value)`.

**Algorithm:**
```c
sequence_t *toffoli_CQ_add(int bits, int64_t value) {
    // Convert value to binary representation
    int *bin = two_complement(value, bits);

    // For each bit position i:
    //   If classical bit b[i] = 1: full MAJ/UMA (Toffoli + 2 CNOT)
    //   If classical bit b[i] = 0: simplified carry propagation (CNOT only)
    //
    // When b[i] = 0:
    //   MAJ(carry, 0, a[i]) simplifies to: CNOT(a,carry), carry stays
    //   UMA(carry, 0, a[i]) simplifies to: CNOT(a,carry)
    //
    // This means: fewer Toffoli gates for sparse classical values.
    // Worst case (all bits 1): same as QQ add.
    // Best case (all bits 0): only CNOT gates.

    // Qubit layout:
    // [0..n-1] : target register a (modified in-place)
    // [n]      : ancilla carry qubit
    // No b-register needed (classical value is a parameter)
}
```

**Key difference from QQ:** CQ uses only n+1 qubits (target + ancilla), not 2n+1. The qubit layout in the hot path is different.

### Pattern 4: Hot Path Dispatch with Arithmetic Mode

**What:** Extend `hot_path_add.c` to dispatch to Toffoli or QFT based on `circuit_t.arithmetic_mode`.

**Implementation:**
```c
// In hot_path_add.c (modified):
void hot_path_add_qq(circuit_t *circ, ...) {
    unsigned int qa[256];
    // ... existing qubit array setup ...

    sequence_t *seq;
    if (circ->arithmetic_mode == ARITH_TOFFOLI) {
        // Toffoli path: allocate 1 ancilla qubit
        qubit_t ancilla_qubit = allocator_alloc(circ->allocator, 1, true);
        if (ancilla_qubit == (qubit_t)-1) return;  // allocation failed

        // Ancilla goes at position 2*result_bits (after both registers)
        qa[2 * result_bits] = ancilla_qubit;

        seq = toffoli_QQ_add(result_bits);
        if (seq == NULL) {
            allocator_free(circ->allocator, ancilla_qubit, 1);
            return;
        }
        run_instruction(seq, qa, invert, circ);

        // Free ancilla (CDKM guarantees it returns to |0>)
        allocator_free(circ->allocator, ancilla_qubit, 1);
    } else {
        // QFT path: existing behavior (no ancilla for addition)
        if (controlled) {
            qa[2 * result_bits] = control_qubit;
            seq = cQQ_add(result_bits);
        } else {
            seq = QQ_add(result_bits);
        }
        if (seq == NULL) return;
        run_instruction(seq, qa, invert, circ);
    }
}
```

### Pattern 5: Subtraction via Inversion

**What:** Subtraction `a -= b` is computed by running the adder in reverse gate order.

**When to use:** When `invert=1` is passed to `run_instruction()`.

**Why it works:** All gates in CDKM are self-inverse (CCX and CX). `run_instruction()` with `invert=1` iterates layers in reverse order. Phase 65 ensured that self-inverse gate GateValues are NOT negated during inversion. Therefore, running the CDKM adder backwards correctly computes `a = a - b` instead of `a = a + b`.

**Verification:** For n-bit registers, `(a + b) mod 2^n` followed by `(result - b) mod 2^n` should yield `a`. Test this property exhaustively.

### Pattern 6: Mixed-Width via Zero-Extension

**What:** When operands have different widths, the shorter one is zero-extended.

**How it already works:** The existing `hot_path_add_qq()` receives `self_bits` and `other_bits` separately. It computes `result_bits = max(self_bits, other_bits)`. For the QFT path, `QQ_add(result_bits)` handles width mismatch internally. For the Toffoli path, the same `result_bits` is used. The shorter register's upper qubits are uninitialized in `qa[]` -- they point to existing qubits that are in |0> state (from the qint's allocated block, which extends to `result_bits`).

**Key contract:** The Cython layer already handles width extension in `addition_inplace()` by calling `hot_path_add_qq` with `self_bits` and `other_bits`. The `toffoli_QQ_add(result_bits)` sequence operates on `result_bits` virtual qubits for each register. The hot path maps the shorter register's excess positions to actual allocated-but-zero qubits. No algorithm change needed -- just ensure `qa[]` is populated correctly for both registers up to `result_bits`.

### Anti-Patterns to Avoid

- **Anti-Pattern 1: Allocating ancilla in Python/Cython.** Ancilla count is an implementation detail of the adder algorithm. Allocate in the C hot path using `allocator_alloc()`.

- **Anti-Pattern 2: Separate subtraction function.** Subtraction is the inverse of addition. Use `run_instruction(seq, qa, /*invert=*/1, circ)`, not a separate `toffoli_QQ_sub()`.

- **Anti-Pattern 3: Mixed qubit layouts between sequence and hot path.** The `sequence_t` uses virtual indices [0..2n]; the hot path maps them to physical indices. Document the layout contract at both ends. BUG-CQQ-ARITH was exactly this class of bug.

- **Anti-Pattern 4: Using MAXLAYERINSEQUENCE.** Compute exact layer count from `bits`: `6*bits - 3` for n >= 2. Do not over-allocate.

- **Anti-Pattern 5: Attempting controlled variants in this phase.** The success criteria do NOT require cQQ or cCQ Toffoli variants. Controlled Toffoli addition adds significant complexity (CCX becomes C3X, needs decomposition). Defer to a later phase.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sequence allocation boilerplate | Custom allocation for each function | Follow `CQ_equal_width()` pattern in `IntegerComparison.c` | Proven pattern with proper cleanup on failure |
| Ancilla allocation | Manual qubit tracking | `allocator_alloc(circ->allocator, 1, true)` + `allocator_free()` | Phase 65 built exactly this infrastructure |
| Gate inversion for subtraction | Separate subtraction circuit | `run_instruction(seq, qa, /*invert=*/1, circ)` | Phase 65 fixed self-inverse handling |
| Two's complement conversion | Manual binary conversion | `two_complement(value, bits)` from `Integer.c` | Already handles negative values correctly |
| Qubit reuse after free | Custom pool | Block-based free-list in `qubit_allocator.c` | Phase 65 added sorted array + coalescing |

**Key insight:** Phase 65 was specifically designed to prepare infrastructure for Phase 66. Every infrastructure component needed by the CDKM adder was built or fixed in Phase 65.

## Common Pitfalls

### Pitfall 1: Ancilla Qubit Not Returned to |0>

**What goes wrong:** If the CDKM uncomputation (UMA sweep) has a bug, the ancilla qubit remains entangled with data registers. Subsequent operations that reuse this qubit via `allocator_alloc()` get a dirty qubit, producing silently wrong results.

**Why it happens:** The UMA sweep must exactly undo the MAJ sweep's carry computation. Any off-by-one error in the sweep loop leaves the ancilla dirty.

**How to avoid:** Test with two sequential additions using the same width. If the second addition gives correct results, the ancilla was properly cleaned. In DEBUG mode, the Phase 65 ancilla lifecycle assertions will detect the leak.

**Warning signs:** Test passes for single operations but fails for sequential operations. Results depend on operation order.

### Pitfall 2: MAJ/UMA Parameter Order Mismatch

**What goes wrong:** The MAJ gate takes parameters (carry_in, b_bit, a_bit) where carry_in is the PREVIOUS carry (or ancilla for bit 0), b_bit is from the source register, and a_bit is from the target register. Swapping any two parameters produces a circuit that computes the wrong function.

**Why it happens:** Different sources use different conventions for parameter naming and ordering. The original Cuccaro paper uses (c, b, a) where c is carry-in. The qubit layout maps a[i] to virtual index i, b[i] to virtual index n+i, and ancilla to virtual index 2n. These must be passed to MAJ/UMA in the correct order.

**How to avoid:** Write a standalone test that verifies the 1-bit MAJ output matches the classical majority function for all 8 input combinations (3 bits = 8 states). Similarly verify UMA. Then test the full adder against classical addition.

**Warning signs:** Addition works for some input pairs but not others. Carry does not propagate correctly past bit 0.

### Pitfall 3: CQ Qubit Layout Differs From QQ

**What goes wrong:** QQ addition uses 2n+1 qubits (a-register, b-register, ancilla). CQ addition uses only n+1 qubits (a-register, ancilla) since the classical value is a parameter. If the hot path builds the `qa[]` array using the QQ layout for CQ dispatch, the ancilla position is wrong.

**Why it happens:** The existing hot path already handles QQ vs CQ layout differences for QFT (see `hot_path_add_qq` vs `hot_path_add_cq`). The Toffoli path must follow the same pattern but with the ancilla at position `n` (after target register) for CQ, not position `2n`.

**How to avoid:** The Toffoli CQ path should be in `hot_path_add_cq()`, not `hot_path_add_qq()`. The CQ sequence expects: `[0..n-1] = target, [n] = ancilla`. The hot path maps: `qa[0..n-1] = self_qubits[0..n-1]`, `qa[n] = ancilla_qubit`.

**Warning signs:** CQ addition with Toffoli mode segfaults or produces garbage for all inputs.

### Pitfall 4: 1-Bit Addition Edge Case

**What goes wrong:** For n=1, the CDKM adder degenerates. A 1-bit addition is `a[0] = a[0] XOR b[0]`, which is a single CNOT with no carry propagation and no ancilla needed. If the code tries to allocate an ancilla for n=1, it wastes a qubit. If it tries to run MAJ/UMA with n=1, it may access out-of-bounds indices.

**Why it happens:** The MAJ/UMA loop iterates from i=1 to n-1. For n=1, this loop body never executes, leaving only the first MAJ and last UMA calls -- which for 1-bit may not form a valid adder.

**How to avoid:** Handle n=1 as a special case: emit a single CNOT, no ancilla. The hot path should skip ancilla allocation for 1-bit Toffoli addition. Test 1-bit exhaustively: all 4 input combinations (0+0, 0+1, 1+0, 1+1) must give correct results.

**Warning signs:** 1-bit addition fails or ancilla statistics show unexpected allocations for 1-bit operations.

### Pitfall 5: Sequence Cache Collision Between QFT and Toffoli

**What goes wrong:** If `toffoli_QQ_add(bits)` accidentally writes to the same cache array as `QQ_add(bits)`, switching arithmetic modes produces wrong gate sequences.

**Why it happens:** Copy-paste from `IntegerAddition.c` code using `precompiled_QQ_add_width[bits]`.

**How to avoid:** Toffoli sequences MUST use separate cache arrays: `precompiled_toffoli_QQ_add[65]`. Name them distinctly. Never share cache between QFT and Toffoli variants.

### Pitfall 6: Mixed-Width Addition With Uninitialized Qubits

**What goes wrong:** For mixed-width addition (e.g., 2-bit + 3-bit), the shorter register needs zero-extension. The hot path must populate `qa[]` entries for the extended bits with qubits that are genuinely in |0> state.

**Why it happens:** The existing QFT path handles this because `qint` objects are right-aligned in a 64-element array, with unused high bits pointing to allocated-but-zero qubits. The Toffoli path needs the same guarantee.

**How to avoid:** The Cython `addition_inplace()` already handles width matching before calling the hot path. Verify that `self_qubits` has `result_bits` entries (not just `self_bits`) when `result_bits > self_bits`. If not, the hot path must zero-pad the shorter array.

## Code Examples

### Complete Sequence Allocation Pattern (from IntegerComparison.c)

```c
// Source: c_backend/src/IntegerComparison.c, CQ_equal_width function
// This is the established pattern for allocating sequence_t in this codebase:

sequence_t *seq = malloc(sizeof(sequence_t));
if (seq == NULL) return NULL;

seq->num_layer = num_layers;  // Compute exactly from algorithm
seq->used_layer = 0;
seq->gates_per_layer = calloc(num_layers, sizeof(num_t));
if (seq->gates_per_layer == NULL) {
    free(seq);
    return NULL;
}
seq->seq = calloc(num_layers, sizeof(gate_t *));
if (seq->seq == NULL) {
    free(seq->gates_per_layer);
    free(seq);
    return NULL;
}
for (int i = 0; i < num_layers; i++) {
    seq->seq[i] = calloc(max_gates_per_layer, sizeof(gate_t));
    if (seq->seq[i] == NULL) {
        for (int j = 0; j < i; j++) free(seq->seq[j]);
        free(seq->seq);
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
}
```

### Gate Emission Pattern (from IntegerComparison.c)

```c
// Source: c_backend/src/IntegerComparison.c:148-153
// This is how gates are added to layers in this codebase:

// X gate on qubit i+1 at current_layer
x(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], i + 1);
seq->gates_per_layer[current_layer]++;
current_layer++;
seq->used_layer++;

// CX gate: target=b, control=c
cx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], b, c);
seq->gates_per_layer[current_layer]++;
current_layer++;

// CCX gate: target=c, control1=a, control2=b
ccx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], c, a, b);
seq->gates_per_layer[current_layer]++;
current_layer++;
```

### Hot Path Ancilla Lifecycle Pattern

```c
// Source: Architecture research - recommended pattern for Toffoli hot path
// Matches allocator_alloc/free from c_backend/src/qubit_allocator.c

// Allocate ancilla
qubit_t ancilla = allocator_alloc(circ->allocator, 1, /*is_ancilla=*/true);
if (ancilla == (qubit_t)-1) return;  // allocation failed

// Map ancilla to qubit array position
qa[2 * result_bits] = ancilla;

// Generate and execute sequence
sequence_t *seq = toffoli_QQ_add(result_bits);
if (seq == NULL) {
    allocator_free(circ->allocator, ancilla, 1);
    return;
}
run_instruction(seq, qa, invert, circ);

// Free ancilla (CDKM guarantees return to |0>)
allocator_free(circ->allocator, ancilla, 1);
```

### Arithmetic Mode Enum and Circuit Field

```c
// In types.h:
typedef enum { ARITH_QFT = 0, ARITH_TOFFOLI = 1 } arithmetic_mode_t;

// In circuit.h (add to circuit_t struct):
arithmetic_mode_t arithmetic_mode;  // Default: ARITH_QFT (0 = backward compatible)

// In circuit_allocations.c init_circuit():
circ->arithmetic_mode = ARITH_QFT;  // 0, backward compatible via memset
```

### Python Option Wiring

```python
# In _core.pyx option() function:
elif key == 'fault_tolerant':
    cdef circuit_t *_circuit = <circuit_t*><unsigned long long>_get_circuit()
    if value is None:
        return (<circuit_s*>_circuit).arithmetic_mode == 1
    if not isinstance(value, bool):
        raise ValueError("fault_tolerant option requires bool value")
    (<circuit_s*>_circuit).arithmetic_mode = 1 if value else 0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `reverse_circuit_range()` negated all GateValues | Self-inverse gates (X, CX, CCX) preserve GateValue | Phase 65-01 | Enables correct Toffoli circuit inversion |
| `allocator_alloc()` only reused count=1 blocks | Block-based free-list with first-fit + coalescing | Phase 65-02 | Enables efficient ancilla reuse |
| No ancilla lifecycle tracking | DEBUG-mode ancilla bitmap with leak assertions | Phase 65-03 | Catches ancilla leaks at destroy time |

**Phase 65 was explicitly designed as Phase 66 infrastructure.** All three Phase 65 tasks directly enable Phase 66.

## Open Questions

1. **1-bit CQ addition: does it need ancilla?**
   - What we know: 1-bit QQ addition is a single CNOT (no ancilla). 1-bit CQ addition with value 0 is identity; with value 1 is a single X gate.
   - What's unclear: Whether the unified code path can handle the no-ancilla case without branching.
   - Recommendation: Handle n=1 as explicit special case in both `toffoli_QQ_add` and `toffoli_CQ_add`. Skip ancilla allocation in the hot path when `bits == 1`.

2. **Should `toffoli_CQ_add` be cached per (bits, value)?**
   - What we know: QFT `CQ_add` caches the sequence per `bits` and MUTATES the cached sequence's rotation values for each call. The Toffoli `CQ_add` generates a different gate pattern for each classical value.
   - What's unclear: Whether the CQ path should be cached at all, or generated fresh each call.
   - Recommendation: Do NOT cache `toffoli_CQ_add` per value. Cache only the `toffoli_QQ_add` (width-only). CQ sequences are fast to generate (O(n) gates) and value-dependent, making caching impractical for the full value space. Alternatively, cache per `bits` with a template that is parameterized, similar to the QFT approach -- but this is more complex and can be deferred.

3. **How should the controlled operation path work when arithmetic_mode is TOFFOLI?**
   - What we know: The success criteria do NOT include controlled Toffoli addition. But the existing code paths handle controlled operations.
   - What's unclear: Whether to fall back to QFT for controlled operations or error out.
   - Recommendation: For Phase 66, if `controlled && arithmetic_mode == ARITH_TOFFOLI`, fall back to QFT path. Log a warning if DEBUG is enabled. Implement Toffoli controlled variants in a later phase.

4. **Should `circuit_s` struct in `_core.pxd` be updated to expose `arithmetic_mode`?**
   - What we know: The Cython `circuit_s` struct mirrors a subset of `circuit_t` fields. The `option()` function needs to read/write `arithmetic_mode`.
   - Recommendation: Yes, add `unsigned int arithmetic_mode` to the `circuit_s` struct in `_core.pxd`. Use `unsigned int` (not the enum type) for Cython compatibility.

## Sources

### Primary (HIGH confidence)
- Cuccaro, Draper, Kutin, Moulton: [A new quantum ripple-carry addition circuit](https://arxiv.org/abs/quant-ph/0410184) (2004) -- Algorithm definition, MAJ/UMA decomposition, 1-ancilla property
- Existing codebase: `gate.c` (gate primitives), `execution.c` (run_instruction with Phase 65 fix), `qubit_allocator.c` (Phase 65 block-based allocator), `hot_path_add.c` (dispatch pattern), `IntegerAddition.c` (QQ_add, CQ_add as reference), `IntegerComparison.c` (CCX sequence construction pattern)
- Prior research: `.planning/research/ARCHITECTURE-TOFFOLI-ARITHMETIC.md` -- Comprehensive codebase analysis for Toffoli arithmetic integration

### Secondary (MEDIUM confidence)
- [IBM Quantum CDKMRippleCarryAdder docs](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.CDKMRippleCarryAdder) -- Qubit layout and variant documentation
- [Qiskit CDKMRippleCarryAdder source](https://github.com/Qiskit/qiskit/blob/main/qiskit/circuit/library/arithmetic/adders/cdkm_ripple_carry_adder.py) -- Reference implementation structure
- [Optimizing T and CNOT Gates in Quantum Ripple-Carry Adders (2024)](https://arxiv.org/abs/2401.17921) -- T-depth 3n optimization (future reference)

### Tertiary (LOW confidence)
- Gate count formulas: 2n-2 Toffoli, 4n-2 CNOT for n >= 2 -- derived from algorithm analysis but exact counts should be verified by testing against n=2,3,4

## Metadata

**Confidence breakdown:**
- Algorithm (MAJ/UMA decomposition): HIGH -- from original paper, consistent across multiple sources, verified in prior research
- Codebase integration (hot path, allocator): HIGH -- directly inspected all relevant source files
- Gate counts: MEDIUM -- derived from algorithm analysis, need verification by counting gates in generated sequences
- CQ variant: MEDIUM -- optimization logic (skip Toffoli when classical bit = 0) is well-understood but implementation details for the sequence template need validation
- Mixed-width handling: MEDIUM -- existing pattern works for QFT but Toffoli qubit layout differences need testing

**Research date:** 2026-02-14
**Valid until:** 2026-04-14 (stable algorithms, stable codebase -- 60-day validity)
