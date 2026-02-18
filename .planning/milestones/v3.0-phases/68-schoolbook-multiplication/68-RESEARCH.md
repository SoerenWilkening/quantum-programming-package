# Phase 68: Schoolbook Multiplication - Research

**Researched:** 2026-02-15
**Domain:** Toffoli-based quantum multiplication circuits (shift-and-add)
**Confidence:** HIGH

## Summary

Phase 68 implements Toffoli-based schoolbook multiplication using the shift-and-add approach with CDKM ripple-carry adders as subroutines. The existing Toffoli addition infrastructure from Phases 66-67 (`ToffoliAddition.c`) provides all four adder variants (QQ, CQ, cQQ, cCQ), and Phase 68 composes these into multiplication circuits.

The implementation follows the standard schoolbook multiplication algorithm: for each bit b_j of the multiplier, perform a controlled addition of the multiplicand (shifted by j positions) into an accumulator register. For QQ multiplication (`a * b`), each bit of `b` controls whether a shifted copy of `a` is added to the result register. For CQ multiplication (`a * classical_val`), the classical bits determine which shifted additions to perform (no control qubits needed for zero bits).

The key architectural decision is to implement multiplication as a **C-level loop calling the existing CDKM adder** rather than generating a single monolithic sequence. This mirrors the Qiskit HRS cumulative multiplier approach and reuses the proven adder infrastructure. The hot path (`hot_path_mul.c`) needs a Toffoli dispatch branch (like `hot_path_add.c` already has) that builds the shift-and-add loop in C, calling `toffoli_cQQ_add` or `toffoli_QQ_add` for each partial product.

**Primary recommendation:** Implement shift-and-add QQ multiplication using controlled Toffoli adders (one per multiplier bit), with ancilla allocated once per adder call and reused. Start with the simpler plain controlled-addition approach (not the Litinski add-subtract optimization). Verify exhaustively at widths 1-3. Wire into `hot_path_mul.c` with `ARITH_TOFFOLI` dispatch.

## Standard Stack

### Core

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `ToffoliAddition.c` | `c_backend/src/ToffoliAddition.c` | CDKM adder (all 4 variants) | Proven correct, cached, handles 1-64 bits |
| `toffoli_arithmetic_ops.h` | `c_backend/include/toffoli_arithmetic_ops.h` | Public API for Toffoli addition | Consumed by hot paths and Cython |
| `hot_path_mul.c` | `c_backend/src/hot_path_mul.c` | Multiplication dispatch | Already has QFT dispatch, add Toffoli branch |
| `qubit_allocator.c` | `c_backend/src/qubit_allocator.c` | Ancilla allocation/free | Block allocation works for carry qubits |
| `execution.c` | `c_backend/src/execution.c` | `run_instruction()` | Maps abstract to physical qubits |

### Supporting

| Component | Location | Purpose | When to Use |
|-----------|----------|---------|-------------|
| `gate.h` | `c_backend/include/gate.h` | Gate primitives (ccx, cx, x, mcx) | For any direct gate emission |
| `Integer.h` | `c_backend/include/Integer.h` | `two_complement()` utility | For CQ value decomposition |
| `circuit.h` | `c_backend/include/circuit.h` | `arithmetic_mode_t` enum | For Toffoli/QFT dispatch check |
| `alloc_sequence()` | `ToffoliAddition.c` (static) | Sequence allocation | If building monolithic sequence |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain controlled adders per bit | Litinski controlled add-subtract (CAS) | CAS halves Toffoli count (0.5n^2+1.5n vs n^2+n) but requires correction steps; implement CAS as follow-up optimization |
| Monolithic sequence_t per multiplication | Loop calling run_instruction per adder | Loop is simpler, reuses cached adder sequences, easier to debug; monolithic gives better optimizer visibility but harder to implement |
| Separate `ToffoliMultiplication.c` file | Inline in `hot_path_mul.c` | Separate file is cleaner but the multiplication is just a loop of adder calls; recommend separate file for clarity |

## Architecture Patterns

### Recommended Project Structure

```
c_backend/
  src/
    ToffoliMultiplication.c    # NEW: Toffoli multiplication sequence gen
    hot_path_mul.c             # MODIFIED: add ARITH_TOFFOLI dispatch
  include/
    toffoli_arithmetic_ops.h   # MODIFIED: add mul function declarations
tests/
  test_toffoli_multiplication.py  # NEW: exhaustive verification tests
```

### Pattern 1: Shift-and-Add QQ Multiplication (Loop Approach)

**What:** For each bit j of the multiplier register `b[j]`, perform a controlled addition of `a` (shifted by j) into the result register, controlled by `b[j]`.

**When to use:** This is the standard approach for QQ multiplication.

**Algorithm (n-bit QQ mul: result = a * b):**

```
// Qubit layout:
//   result[0..n-1] = accumulator (starts at |0>)
//   a[0..n-1]      = multiplicand (preserved)
//   b[0..n-1]      = multiplier (preserved, each bit used as control)
//
// For j = 0 to n-1:
//   Perform controlled addition: result[j..n-1] += a[0..n-1-j], controlled by b[j]
//   This adds a * 2^j to result when b[j] = 1
//
// The shift is implicit: we add a[0..n-1-j] into result[j..n-1]
// For the first iteration (j=0): add full n-bit a into result[0..n-1]
// For j=1: add (n-1)-bit a[0..n-2] into result[1..n-1] (shifted left by 1)
// For j=n-1: add 1-bit a[0] into result[n-1] (shifted left by n-1)
```

**Gate-level detail for each partial product:**
- The controlled CDKM adder `toffoli_cQQ_add(width)` expects:
  - `[0..width-1]` = target (result register, shifted)
  - `[width..2*width-1]` = source (a register, truncated)
  - `[2*width]` = carry ancilla
  - `[2*width+1]` = control qubit (b[j])
- For iteration j, `width = n - j` (progressively smaller additions)
- Ancilla allocated per addition call, freed after

**Toffoli count:** Each controlled addition of width w uses 6w layers (3w MAJ + 3w UMA with CCX/MCX). Total across n iterations: sum_{j=0}^{n-1} (n-j) controlled adder calls. The Toffoli count per controlled adder of width w is approximately 2w (one CCX per MAJ + one per UMA, each promoted to MCX for control). Total: approximately n(n+1)/2 * 2 = n^2 + n Toffoli gates.

### Pattern 2: CQ Multiplication (Classical Shift-and-Add)

**What:** For CQ multiplication (`result = a * classical_val`), iterate over set bits of the classical value. For each set bit j, perform an uncontrolled addition of `a` (shifted by j) into the result register.

**When to use:** When one operand is a classical integer.

**Algorithm (n-bit CQ mul: result = a * val):**

```
// For each bit j where val[j] == 1:
//   result[j..n-1] += a[0..n-1-j]  (uncontrolled addition)
//
// Uses toffoli_QQ_add (uncontrolled) since the classical bit selects
// whether to add at all (compile-time decision, not runtime control).
```

**Key advantage:** No control qubits needed. Each addition uses `toffoli_QQ_add` (uncontrolled, cheaper than controlled). For a classical value with k set bits, only k additions are performed.

### Pattern 3: Hot Path Toffoli Dispatch (Same Pattern as Addition)

**What:** Add `ARITH_TOFFOLI` check in `hot_path_mul_qq` and `hot_path_mul_cq`, dispatch to Toffoli multiplication loop.

**When to use:** This matches the existing pattern in `hot_path_add.c` (lines 51-149).

**Example structure in `hot_path_mul.c`:**

```c
void hot_path_mul_qq(circuit_t *circ, ...) {
    if (circ->arithmetic_mode == ARITH_TOFFOLI) {
        // Toffoli schoolbook multiplication
        toffoli_mul_qq(circ, ret_qubits, ret_bits,
                       self_qubits, self_bits,
                       other_qubits, other_bits);
        return;
    }
    // ... existing QFT path ...
}
```

### Pattern 4: Sequence-Based Approach (Alternative)

**What:** Generate a single `sequence_t` containing all gates for the entire multiplication, similar to how `QQ_mul()` works for QFT.

**When to use:** If the loop approach has integration issues with the layer floor mechanism.

**Tradeoff:** More complex to implement (must compute exact layer count: sum of 6*(n-j) for j=0..n-1 = 3n(n+1) layers), but gives the optimizer a single sequence to work with. The adder sequences cannot be cached since qubit positions change per iteration. Must emit all MAJ/UMA gates directly rather than calling `toffoli_cQQ_add`.

### Anti-Patterns to Avoid

- **Anti-pattern: Generating the entire mul as one sequence_t by calling toffoli_cQQ_add internally.** The cached adder sequences use abstract qubit indices (0, 1, 2, ...) that must be remapped per iteration. You cannot compose two `sequence_t` objects; you must either (a) emit gates directly or (b) call `run_instruction` per adder.

- **Anti-pattern: Allocating ancilla once for all iterations.** Each adder call needs its own ancilla allocation/free cycle because the CDKM adder guarantees ancilla returns to |0> only after the full MAJ-UMA sequence. Keeping ancilla allocated across iterations is fine as long as the same qubit is reused (it is |0> after each adder call).

- **Anti-pattern: Using the QFT mul qubit layout for Toffoli mul.** QFT QQ_mul layout is `[result, self, other]` with no ancilla. Toffoli QQ_mul needs ancilla for each adder call. The hot path must build a different qubit array.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CDKM adder circuit | Custom adder for multiplication | `toffoli_QQ_add`, `toffoli_cQQ_add` from ToffoliAddition.c | Adder is proven correct and cached; reimplementing introduces bugs |
| Qubit allocation | Manual qubit index tracking | `allocator_alloc` / `allocator_free` | Centralized allocation handles reuse, stats, and debugging |
| Gate emission | Direct gate_t manipulation | `ccx()`, `cx()`, `x()` from gate.h | Gate primitives handle Control/large_control setup correctly |
| Subtraction | Separate subtraction circuit | `run_instruction(add_seq, qa, /*invert=*/1, circ)` | CDKM gates are self-inverse; running in reverse = subtraction |

**Key insight:** The multiplication is fundamentally a loop of adder calls. The hard work (CDKM correctness, controlled variants, ancilla management) was done in Phases 66-67. Phase 68 composes these into multiplication.

## Common Pitfalls

### Pitfall 1: Qubit Array Layout Mismatch Between Adder and Multiplier

**What goes wrong:** The CDKM adder `toffoli_cQQ_add(width)` expects a specific qubit layout: `[target 0..w-1, source w..2w-1, ancilla 2w, control 2w+1]`. In the multiplication loop, the "target" is a shifted slice of the result register, and the "source" is a truncated slice of `a`. If the qubit array maps these incorrectly, the adder operates on wrong qubits.

**Why it happens:** Each iteration has different width (n-j) and different target offset (starting at result[j]). The qubit array must be rebuilt for each iteration with the correct physical qubit indices.

**How to avoid:** Build a fresh `tqa[]` array for each iteration. Map: `tqa[0..w-1] = result[j..n-1]`, `tqa[w..2w-1] = a[0..n-1-j]`, `tqa[2w] = ancilla`, `tqa[2w+1] = b[j]`. Document the mapping at the top of the loop.

**Warning signs:** Multiplication works for width 1 but fails for width 2+. Or works when a=0 or b=0 but fails for non-trivial inputs.

### Pitfall 2: Register Swap (a-register vs b-register in CDKM)

**What goes wrong:** The CDKM adder computes `a[i] = a[i] + b[i]`, where the a-register is modified and the b-register is preserved. In `hot_path_add.c`, the registers are swapped for the Toffoli path (lines 72-77): other goes to a-register, self goes to b-register. The multiplication must apply the same swap: the result register (which accumulates the sum) must be in the b-register position (gets modified), and the multiplicand `a` must be in the a-register position (preserved).

**Why it happens:** Confusion about which register is target vs source in the CDKM convention. The CDKM paper uses "a" for the register that receives the sum, but `toffoli_QQ_add` in the codebase uses `[0..n-1]` as the target that gets `a += b`.

**How to avoid:** Look at `toffoli_QQ_add` documentation: "register a (target, modified in place: a += b)". So in the qubit array: position [0..w-1] = the register to be modified (result slice), position [w..2w-1] = the source (a slice). For the hot path, this means `tqa[i] = result[j+i]` and `tqa[w+i] = a[i]`.

**Warning signs:** Multiplicand `a` is corrupted after multiplication. Or result contains wrong values but `a` and `b` are unchanged.

### Pitfall 3: Ancilla Leaked Across Multiplier Iterations

**What goes wrong:** If ancilla is allocated but not freed between adder calls in the multiplication loop, qubit count grows by 1 per iteration (n total leaked ancilla for n-bit multiplication).

**Why it happens:** Each `toffoli_cQQ_add` call needs 1 ancilla qubit (for carry). The allocator should return the same qubit each time if it was freed after the previous call. But if the free is skipped or the allocator cannot reuse (e.g., contiguous block mismatch), fresh ancilla are allocated each time.

**How to avoid:** Explicitly `allocator_alloc` before and `allocator_free` after each adder call in the loop. Alternatively, allocate one ancilla before the loop and reuse it for all iterations (since it's guaranteed |0> after each CDKM call).

**Warning signs:** `allocator_stats.ancilla_allocations` is much higher than expected. Circuit qubit count grows with multiplication width.

### Pitfall 4: Off-by-One in Shifted Addition Width

**What goes wrong:** For iteration j, the addition width should be `n - j` (adding a truncated multiplicand into a shifted result slice). Getting this as `n - j - 1` or `n - j + 1` produces wrong products, but only for certain input values.

**Why it happens:** The shift amount and the truncation must be coordinated. Bit j of the multiplier has weight 2^j, so the partial product `a * 2^j` contributes to result bits j through n-1 (a total of n-j bits). The multiplicand bits used are a[0] through a[n-1-j] (the low n-j bits of a, since higher bits would overflow the n-bit result).

**How to avoid:** Write a clear comment documenting the width calculation. Test with `a = 1, b = 1` (should give 1), `a = 1, b = 2` (should give 2), `a = 2, b = 2` (should give 4 for width >= 3), exhaustively for all pairs at widths 1-3.

### Pitfall 5: 1-bit Width Special Case

**What goes wrong:** For width 1, multiplication is just AND (1-bit multiply is `a AND b`). The controlled CDKM adder at width 1 is a single CCX. But the multiplication loop with j=0 calls `toffoli_cQQ_add(1)`, which expects qubits `[target, source, control]` (3 qubits). If the loop doesn't handle width 1 specially, the qubit array may be wrong.

**Why it happens:** Width 1 is always a special case in this codebase (both QFT and Toffoli adders have 1-bit special paths). For 1-bit multiplication: `a * b = a AND b`. This can be implemented as a single CCX(target=result[0], ctrl1=a[0], ctrl2=b[0]). The general loop would call `toffoli_cQQ_add(1)` which is a CCX(target=0, ctrl1=1, ctrl2=2), with qubit array mapping to the correct physical qubits. This should work if the qubit array is `[result[0], a[0], b[0]]`.

**How to avoid:** Test width 1 exhaustively first (only 4 input pairs: 0*0, 0*1, 1*0, 1*1). Verify the CCX truth table matches AND.

## Code Examples

### QQ Multiplication - Loop in hot_path_mul.c

```c
// Toffoli schoolbook QQ multiplication: result = self * other
// Uses controlled CDKM adder per multiplier bit
static void toffoli_mul_qq(circuit_t *circ,
                           const unsigned int *ret_qubits, int ret_bits,
                           const unsigned int *self_qubits, int self_bits,
                           const unsigned int *other_qubits, int other_bits) {
    int n = ret_bits;  // = max(self_bits, other_bits)

    for (int j = 0; j < n; j++) {
        int width = n - j;  // Addition width for this iteration
        if (width < 1) break;

        unsigned int tqa[256];
        sequence_t *toff_seq;

        if (width == 1) {
            // 1-bit controlled addition: CCX(result[n-1], self[0], other[j])
            tqa[0] = ret_qubits[n - 1];    // target = result[j] for 1-bit
            tqa[1] = self_qubits[0];        // source = a[0]
            tqa[2] = other_qubits[j];       // control = b[j]

            toff_seq = toffoli_cQQ_add(1);
            if (toff_seq == NULL) return;
            run_instruction(toff_seq, tqa, 0, circ);
        } else {
            // General case: controlled addition of width bits
            // Allocate 1 ancilla for carry
            qubit_t ancilla = allocator_alloc(circ->allocator, 1, true);
            if (ancilla == (qubit_t)-1) return;

            // CDKM convention: a-register = source (preserved), b-register = target (modified)
            // For cQQ_add: [a 0..w-1, b w..2w-1, ancilla 2w, control 2w+1]
            // But toffoli_cQQ_add uses: [0..w-1]=target, [w..2w-1]=source
            // Need to swap: a-register (indices 0..w-1) = self (source, preserved)
            //               b-register (indices w..2w-1) = result slice (target, gets sum)

            // a-register = self[0..width-1] (multiplicand, preserved)
            for (int i = 0; i < width; i++) {
                tqa[i] = self_qubits[i];
            }
            // b-register = result[j..j+width-1] (accumulator, modified)
            for (int i = 0; i < width; i++) {
                tqa[width + i] = ret_qubits[j + i];
            }
            // ancilla carry
            tqa[2 * width] = ancilla;
            // control qubit = other[j] (bit j of multiplier)
            tqa[2 * width + 1] = other_qubits[j];

            toff_seq = toffoli_cQQ_add(width);
            if (toff_seq == NULL) {
                allocator_free(circ->allocator, ancilla, 1);
                return;
            }
            run_instruction(toff_seq, tqa, 0, circ);
            allocator_free(circ->allocator, ancilla, 1);
        }
    }
}
```

### CQ Multiplication - Classical Shift-and-Add

```c
// Toffoli schoolbook CQ multiplication: result = self * classical_value
// Only adds for set bits of classical value (uncontrolled additions)
static void toffoli_mul_cq(circuit_t *circ,
                           const unsigned int *ret_qubits, int ret_bits,
                           const unsigned int *self_qubits, int self_bits,
                           int64_t classical_value) {
    int n = ret_bits;
    int *bin = two_complement(classical_value, n);
    if (bin == NULL) return;

    for (int j = 0; j < n; j++) {
        // bin is MSB-first: bin[0]=MSB, bin[n-1]=LSB
        // Bit j (weight 2^j) is at bin[n-1-j]
        if (bin[n - 1 - j] == 0) continue;  // Skip zero bits

        int width = n - j;
        if (width < 1) break;

        unsigned int tqa[256];
        sequence_t *toff_seq;

        if (width == 1) {
            // 1-bit uncontrolled: CNOT(result[n-1], self[0])
            tqa[0] = ret_qubits[n - 1];
            tqa[1] = self_qubits[0];

            toff_seq = toffoli_QQ_add(1);
            if (toff_seq == NULL) { free(bin); return; }
            run_instruction(toff_seq, tqa, 0, circ);
        } else {
            qubit_t ancilla = allocator_alloc(circ->allocator, 1, true);
            if (ancilla == (qubit_t)-1) { free(bin); return; }

            // a-register = self[0..width-1] (source, preserved)
            for (int i = 0; i < width; i++) {
                tqa[i] = self_qubits[i];
            }
            // b-register = result[j..j+width-1] (target, accumulates)
            for (int i = 0; i < width; i++) {
                tqa[width + i] = ret_qubits[j + i];
            }
            // ancilla carry
            tqa[2 * width] = ancilla;

            toff_seq = toffoli_QQ_add(width);
            if (toff_seq == NULL) {
                allocator_free(circ->allocator, ancilla, 1);
                free(bin);
                return;
            }
            run_instruction(toff_seq, tqa, 0, circ);
            allocator_free(circ->allocator, ancilla, 1);
        }
    }

    free(bin);
}
```

### Test Pattern (from existing test_toffoli_addition.py)

```python
# Follows same pattern as TestToffoliQQAddition in test_toffoli_addition.py

class TestToffoliQQMultiplication:
    @pytest.mark.parametrize("width", [1, 2, 3])
    def test_qq_mul_exhaustive(self, width):
        failures = []
        for a in range(1 << width):
            for b in range(1 << width):
                def circuit_builder(a=a, b=b, w=width):
                    _enable_toffoli()
                    qa = ql.qint(a, width=w)
                    qb = ql.qint(b, width=w)
                    qc = qa * qb
                    return ((a * b) % (1 << w), [qa, qb, qc])

                actual, expected = _verify_toffoli_mul(circuit_builder, width)
                if actual != expected:
                    failures.append(format_failure_message(
                        "toffoli_qq_mul", [a, b], width, expected, actual))

        assert not failures, f"{len(failures)} failures at width {width}:\n" + "\n".join(failures[:10])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| QFT-based multiplication (QQ_mul in IntegerMultiplication.c) using CCP decomposition | Toffoli-based shift-and-add with CDKM adders | Phase 68 (new) | Fault-tolerant: O(n^2) Toffoli vs O(n^3 log n) T-gates for QFT approach |
| Litinski CAS (controlled add-subtract) | Plain controlled adders | Phase 68 decision | CAS reduces Toffoli count by ~50% but adds complexity; defer to future optimization |
| Monolithic sequence generation | Hot-path loop calling adder | Phase 68 decision | Simpler implementation, reuses proven adder, easier to debug |

**Deprecated/outdated:**
- QFT multiplication remains available via `ql.option('fault_tolerant', False)` but is no longer the default (Phase 67-03 made Toffoli default)

## Open Questions

1. **Register swap convention for controlled adder in multiplication context**
   - What we know: `hot_path_add.c` swaps registers for Toffoli QQ addition (lines 72-77): `other` goes to a-register position (preserved), `self` goes to b-register (target). The CDKM adder convention is `a[0..n-1]` is modified, `b[n..2n-1]` is preserved.
   - What's unclear: The documentation in `toffoli_QQ_add` says "[0..bits-1] = register a (target, modified in place: a += b)" and "[bits..2*bits-1] = register b (source, unchanged)". But `hot_path_add.c` places `other` (source) at indices 0..n-1 and `self` (target) at indices n..2n-1. This means `other` maps to register a (which is supposedly the target), which seems backwards. Investigation reveals this is because the CDKM paper convention has `b` as the register that gets the sum bit, not `a`. The `emit_UMA` function writes the sum to the `b` parameter. So `toffoli_QQ_add` actually modifies the b-register at positions [bits..2*bits-1], not the a-register. The documentation comment says "register a (target, modified)" but the actual modification is to b via UMA. **Resolution:** The hot_path_add.c swap is correct. For multiplication, follow the same pattern: `self_qubits` (multiplicand, preserved) at a-register positions [0..w-1], `result_slice` (target, gets sum) at b-register positions [w..2w-1].
   - Recommendation: Verify by tracing through the MAJ/UMA sequence for a 2-bit example. The code example above uses this convention.

2. **MAXLAYERINSEQUENCE limit for Toffoli multiplication**
   - What we know: The loop approach calls `run_instruction` multiple times (once per adder), so no single sequence exceeds the CDKM adder size (6n layers for n-bit adder). This sidesteps the MAXLAYERINSEQUENCE=10000 limit entirely.
   - What's unclear: If a monolithic sequence approach is ever needed, the limit would be hit for n > ~40 (total layers = 3n(n+1)).
   - Recommendation: Use the loop approach. No MAXLAYERINSEQUENCE issue.

3. **Operator dispatch for `a * b` and `a *= b`**
   - What we know: `__mul__` calls `multiplication_inplace(self, other, result)` which calls `hot_path_mul_qq`. `__imul__` calls `__mul__` then swaps qubit references. The Cython layer passes `ret_qubits`, `self_qubits`, `other_qubits` to the hot path.
   - What's unclear: The current hot_path_mul.c QFT path passes all three register arrays plus ancilla. The Toffoli path does not need the ancilla array from Python (it allocates ancilla internally). The function signature already accepts ancilla but the Toffoli path can ignore them.
   - Recommendation: Keep the same function signature. In the Toffoli branch, ignore the `ancilla` and `num_ancilla` parameters (same pattern as `hot_path_add.c`).

4. **Controlled multiplication (cQQ_mul_toffoli, cCQ_mul_toffoli)**
   - What we know: Success criteria 4 says `a * b` operators must dispatch to Toffoli when fault_tolerant is active. The existing `hot_path_mul_qq` has a `controlled` parameter. For controlled Toffoli multiplication, each controlled addition becomes doubly-controlled (MCX with 2 external controls: multiplier bit + outer control).
   - What's unclear: Whether controlled Toffoli multiplication is needed in Phase 68 or deferred. The success criteria mention `QQ_mul_toffoli` and `CQ_mul_toffoli` but not `cQQ_mul_toffoli` or `cCQ_mul_toffoli`.
   - Recommendation: Phase 68 scope is uncontrolled QQ and CQ Toffoli multiplication. Controlled variants are not listed in the success criteria and can be deferred. The `controlled` flag in the hot path should fall through to the QFT path for controlled multiplication until a future phase implements it.

## Detailed Implementation Plan Guidance

### Step 1: Create ToffoliMultiplication.c (or extend hot_path_mul.c)

Two static functions: `toffoli_mul_qq` and `toffoli_mul_cq`. These are called from `hot_path_mul_qq` and `hot_path_mul_cq` when `arithmetic_mode == ARITH_TOFFOLI`.

### Step 2: Wire into hot_path_mul.c

Add `ARITH_TOFFOLI` check at the top of both `hot_path_mul_qq` and `hot_path_mul_cq`, before the existing QFT path. For controlled operations, fall through to QFT (not implemented in Toffoli for Phase 68).

### Step 3: Add to setup.py

Add `ToffoliMultiplication.c` to the C source files list (if using a separate file).

### Step 4: Write exhaustive tests

Following the pattern in `test_toffoli_addition.py`:
- QQ mul exhaustive for widths 1-3 (all input pairs)
- CQ mul exhaustive for widths 1-3
- Gate purity check (no CP/H gates in Toffoli mode)
- Ancilla lifecycle verification

### Step 5: Verify operator dispatch

Ensure `a * b` and `a *= b` use Toffoli multiplication when `fault_tolerant` is active.

### Qubit Budget

For n-bit QQ multiplication:
- Input: n (self/a) + n (other/b) = 2n qubits
- Output: n (result) = n qubits
- Ancilla: 1 carry (reused per adder call)
- Total: 3n + 1 qubits (vs 3n for QFT QQ_mul)

For n-bit CQ multiplication:
- Input: n (self/a) qubits
- Output: n (result) = n qubits (note: result is separate from self in `multiplication_inplace`)
- Ancilla: 1 carry (reused per adder call)
- Total: 2n + 1 qubits (vs 2n for QFT CQ_mul)

### Gate Count Estimates

For n-bit QQ multiplication (controlled adder per bit):
- Each iteration j: 1 controlled CDKM adder of width (n-j)
  - Controlled CDKM: 6*(n-j) layers, each MAJ/UMA uses CCX+MCX (2-3 controls)
- Total Toffoli/MCX gates: approx 2 * sum_{j=0}^{n-1}(n-j) = n(n+1) gates
- For n=3: ~12 Toffoli/MCX gates

For n-bit CQ multiplication (uncontrolled adder per set bit):
- Each set bit j: 1 uncontrolled CDKM adder of width (n-j)
- Total Toffoli gates: approx 2 * sum over set bits j of (n-j)
- Best case (val=1): 2*(n) = 2n Toffoli gates
- Worst case (val=2^n-1, all bits set): same as QQ

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `c_backend/src/ToffoliAddition.c` -- all 4 CDKM adder variants with qubit layouts
- Codebase inspection: `c_backend/src/hot_path_add.c` -- Toffoli dispatch pattern (lines 51-149)
- Codebase inspection: `c_backend/src/hot_path_mul.c` -- current QFT multiplication dispatch
- Codebase inspection: `c_backend/src/IntegerMultiplication.c` -- QFT QQ_mul/CQ_mul qubit layouts
- Codebase inspection: `src/quantum_language/qint_arithmetic.pxi` -- Python operator overloading
- Codebase inspection: `tests/test_toffoli_addition.py` -- exhaustive verification test pattern
- Codebase inspection: `tests/test_mul.py` -- existing multiplication test pattern

### Secondary (MEDIUM confidence)
- [Litinski 2024, "Quantum schoolbook multiplication with fewer Toffoli gates"](https://arxiv.org/abs/2410.00899) -- n^2+4n+3 Toffoli count with CAS (deferred optimization)
- [Cuccaro et al. 2004, "A new quantum ripple-carry addition circuit"](https://arxiv.org/abs/quant-ph/0410184) -- CDKM adder foundation
- [Haner et al. 2018, "Optimizing Quantum Circuits for Arithmetic"](https://arxiv.org/abs/1805.12445) -- HRS cumulative multiplier (Qiskit reference implementation)
- `.planning/research/ARCHITECTURE-TOFFOLI-ARITHMETIC.md` -- prior research on Toffoli architecture
- `.planning/research/PITFALLS-TOFFOLI-ARITHMETIC.md` -- pitfalls catalogue from Phase 66 research
- `.planning/research/FEATURES-TOFFOLI-ARITHMETIC.md` -- feature landscape and resource counts

### Tertiary (LOW confidence)
- Litinski modular variant (0.5n^2+1.5n Toffoli) -- described in paper but deferred; may be relevant for future optimization

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components already exist and are proven
- Architecture: HIGH -- follows exact same pattern as Toffoli addition dispatch (Phase 66-67)
- Pitfalls: HIGH -- identified from prior codebase experience (BUG-CQQ-ARITH, register swap issues)
- Algorithm: HIGH -- schoolbook multiplication is standard textbook algorithm; composition with CDKM adder is straightforward

**Research date:** 2026-02-15
**Valid until:** 2026-03-15 (stable domain, no external dependencies changing)
