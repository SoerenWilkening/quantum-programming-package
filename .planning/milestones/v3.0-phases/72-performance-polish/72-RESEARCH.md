# Phase 72: Performance Polish - Research

**Researched:** 2026-02-16
**Domain:** Toffoli arithmetic optimization (hardcoded sequences, T-count reporting, controlled add-subtract)
**Confidence:** HIGH

## Summary

Phase 72 covers three distinct tasks: (1) hardcoded Toffoli gate sequences for widths 1-8, (2) T-count reporting in circuit statistics, and (3) the controlled add-subtract optimization for multiplication. Each task operates in a well-understood domain with clear precedent in the codebase.

Hardcoded Toffoli sequences follow the exact pattern established in Phases 58-59 for QFT sequences (`add_seq_*.c` files, `generate_seq_all.py`, `sequences.h`). The Toffoli sequences are simpler than QFT because they use only CCX/CX/X gates (no floating-point angles). T-count reporting requires minimal work: the C-side already computes `t_count = 7 * ccx_gates` in `circuit_stats.c` line 68; only the Cython declaration and Python exposure are missing. The controlled add-subtract optimization (MUL-05) is the most significant task, requiring a new multiplication algorithm that replaces expensive controlled adders (MCX/3-control gates) with cheap CNOT-wrapped uncontrolled adders.

**Primary recommendation:** Implement the controlled add-subtract optimization first (it is the most impactful and risk-bearing task), then T-count exposure (trivial), then hardcoded sequences (mechanical but tedious).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INF-03 | Hardcoded Toffoli gate sequences for common widths eliminate generation overhead | Exact pattern exists for QFT sequences (Phases 58-59); Toffoli variants only use CCX/CX/X gates, simpler than QFT (no angles). Script-generated C files with `#ifdef SEQ_WIDTH_N` guards. |
| INF-04 | T-count reporting in circuit statistics (each Toffoli = 7 T gates) | C-side already computes `t_count = 7 * ccx_gates` in `circuit_stats.c`. Only needs Cython pxd declaration + Python dict exposure. |
| MUL-05 | Controlled add-subtract optimization reduces Toffoli count by ~50% in multiplication subroutine | CNOT-wrapping technique from Litinski 2024: replace controlled adders (MCX 3-control gates) with uncontrolled adders + CNOT wrappers. Converts 2n-1 MCX(3-control) to 2n-1 CCX(2-control) + 2n CNOT per iteration. |
</phase_requirements>

## Standard Stack

### Core

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `ToffoliAddition.c` | `c_backend/src/` | CDKM adder sequences (QQ, CQ, cQQ, cCQ, BK CLA) | All Toffoli adder variants, cached per-width |
| `ToffoliMultiplication.c` | `c_backend/src/` | Schoolbook multiplication | Shift-and-add with controlled adders |
| `hot_path_add.c` / `hot_path_mul.c` | `c_backend/src/` | Dispatch logic for Toffoli vs QFT | Mode-aware routing to correct backend |
| `circuit_stats.c/h` | `c_backend/src/` / `c_backend/include/` | Gate counting + T-count | Already computes t_count, needs exposure |
| `_core.pyx` / `_core.pxd` | `src/quantum_language/` | Cython bindings | Python-C bridge for circuit properties |
| `generate_seq_all.py` | `scripts/` | QFT hardcoded sequence generator | Pattern to follow for Toffoli sequences |
| `sequences/add_seq_*.c` | `c_backend/src/sequences/` | QFT hardcoded sequences | Reference implementation pattern |
| `sequences.h` | `c_backend/include/` | Dispatch header for hardcoded sequences | Public API pattern |

### Supporting

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `gate.h` / `gate.c` | `ccx()`, `cx()`, `x()`, `mcx()` gate primitives | When emitting gates into sequences |
| `execution.c` | `run_instruction()` with qubit mapping + inversion | When executing sequences against circuit |
| `qubit_allocator.c` | Ancilla allocation/deallocation | For carry and temp qubits |
| `toffoli_arithmetic_ops.h` | Public header for Toffoli operations | For new function declarations |

## Architecture Patterns

### Recommended Project Structure

```
c_backend/
  src/
    ToffoliMultiplication.c       # Modified: add-subtract optimization
    circuit_stats.c               # Already done (t_count computed)
    sequences/
      toffoli_add_seq_1.c         # NEW: hardcoded Toffoli QQ/cQQ addition
      toffoli_add_seq_2.c         # NEW
      ...
      toffoli_add_seq_8.c         # NEW
      toffoli_add_seq_dispatch.c  # NEW: dispatch for Toffoli sequences
  include/
    circuit_stats.h               # Already has t_count field
    toffoli_sequences.h           # NEW: public API for Toffoli hardcoded seqs
src/
  quantum_language/
    _core.pxd                     # Modified: add t_count to gate_counts_t
    _core.pyx                     # Modified: expose t_count in gate_counts dict
scripts/
  generate_toffoli_seq.py         # NEW: Toffoli hardcoded sequence generator
```

### Pattern 1: Hardcoded Toffoli Sequences (follows QFT pattern exactly)

**What:** Pre-generated C files containing static const `sequence_t` structs for Toffoli addition at widths 1-8 (QQ and cQQ variants only; CQ/cCQ are value-dependent, not cacheable).

**When to use:** For widths 1-8 where CDKM adder sequences are constant (independent of classical values).

**Key difference from QFT hardcoded sequences:** Toffoli sequences use only X, CX, CCX, MCX gates (integer gate values). No floating-point angles, no phase gates, no Hadamards. This makes them simpler: static const arrays with no template-init pattern needed.

**Generation approach:**
```python
# Generate CDKM adder gate sequence for width N
def generate_toffoli_qq_add(bits):
    """Generate QQ_add Toffoli gate sequence (CCX/CX only)."""
    layers = []
    if bits == 1:
        # Single CX: target=0, control=1
        layers.append([Gate("CX", target=0, control=1)])
        return layers

    ancilla = 2 * bits
    # Forward MAJ sweep
    # MAJ(ancilla, bits+0, 0)
    layers.extend(emit_maj(ancilla, bits, 0))
    for i in range(1, bits):
        layers.extend(emit_maj(i-1, bits+i, i))
    # Reverse UMA sweep
    for i in range(bits-1, 0, -1):
        layers.extend(emit_uma(i-1, bits+i, i))
    layers.extend(emit_uma(ancilla, bits, 0))
    return layers
```

**Dispatch pattern:**
```c
// toffoli_sequences.h
const sequence_t *get_hardcoded_toffoli_QQ_add(int bits);
const sequence_t *get_hardcoded_toffoli_cQQ_add(int bits);

// In ToffoliAddition.c: check hardcoded first, fall back to dynamic
sequence_t *toffoli_QQ_add(int bits) {
    if (precompiled_toffoli_QQ_add[bits] != NULL)
        return precompiled_toffoli_QQ_add[bits];

    // Try hardcoded
    const sequence_t *hc = get_hardcoded_toffoli_QQ_add(bits);
    if (hc != NULL) {
        precompiled_toffoli_QQ_add[bits] = (sequence_t *)hc;
        return (sequence_t *)hc;
    }

    // Dynamic generation (existing code)
    ...
}
```

### Pattern 2: Controlled Add-Subtract via CNOT Wrapping

**What:** Replace controlled adders (which use expensive 3-control MCX gates) with CNOT-wrapped uncontrolled adders in the multiplication loop.

**When to use:** In `toffoli_mul_qq()` and `toffoli_cmul_qq()` for the inner addition loop.

**How it works:**

Current approach in `toffoli_mul_qq()` (Phase 68):
```
For each multiplier bit j:
  controlled_add(ret[j..j+width-1], self[0..width-1], control=other[j])
  // Uses toffoli_cQQ_add which has CCX + MCX(3-control) gates
```

New approach with add-subtract:
```
For each multiplier bit j:
  // CNOT wrap: flip source bits controlled by other[j]
  for i in 0..width-1:
    CX(target=self[i], control=other[j])

  // Uncontrolled add (uses only CCX, CX - much cheaper)
  uncontrolled_add(ret[j..j+width-1], self[0..width-1])

  // CNOT unwrap: restore source bits
  for i in 0..width-1:
    CX(target=self[i], control=other[j])

  // This gives: add when other[j]=1, subtract when other[j]=0
```

**Toffoli count comparison (per iteration, width=n):**
- Old (controlled CDKM): 2(n-1) CCX in MAJ/UMA + n-1 MCX(3-control) = lots of Toffoli equiv
- New (CNOT-wrapped): 2(n-1) CCX in MAJ/UMA + 0 Toffoli for CNOTs = 2(n-1) Toffoli

**Complication:** The add-subtract does subtraction when ctrl=0, not identity. This means the multiplication accumulates signed partial products, requiring a correction step at the end to account for the subtractions. The correction is: after all iterations, add back the sum of all "false subtractions" (the terms that were subtracted when they should have been ignored).

**Correction calculation:**
When `other[j]=0`, the circuit subtracts `self << j` instead of doing nothing. The net effect across all zero bits is subtracting `self * (2^n - 1 - other)`. This can be corrected with a single CQ addition of `self * (2^n - 1)` at the end (since `self * other + self * (2^n - 1 - other) = self * (2^n - 1)`, which is known classically modulo 2^n).

Actually, the correction is simpler: at the end, add `self * (2^n - 1)` using a CQ adder. This accounts for all the subtractions from zero-valued multiplier bits. The total is `sum_j(add_or_sub) + correction = self * other`.

### Pattern 3: T-count Exposure

**What:** Expose the existing `t_count` field from `gate_counts_t` through Cython to Python.

**Changes needed:**
1. `_core.pxd`: Add `size_t t_count` to the `gate_counts_t` Cython struct declaration
2. `_core.pyx`: Add `'T': counts.t_count` to the `gate_counts` property dict

```python
# In _core.pyx, gate_counts property:
return {
    'X': counts.x_gates,
    'Y': counts.y_gates,
    'Z': counts.z_gates,
    'H': counts.h_gates,
    'P': counts.p_gates,
    'CNOT': counts.cx_gates,
    'CCX': counts.ccx_gates,
    'other': counts.other_gates,
    'T': counts.t_count,  # NEW: 7 * CCX count
}
```

### Anti-Patterns to Avoid

- **Hand-writing hardcoded C files:** Always generate via script. Manually editing `toffoli_add_seq_N.c` files leads to copy-paste errors. The generation script is the source of truth.
- **Changing the CQ/cCQ sequences to hardcoded:** CQ and cCQ Toffoli sequences are value-dependent (the X-init gates depend on the classical value). They cannot be pre-computed. Only QQ and cQQ are cacheable.
- **Implementing Gidney adders (measurement-based):** The Litinski paper's n-1 Toffoli count specifically requires measurement-based temporary logical-AND uncomputation. This project has no mid-circuit measurement support. Stick with CDKM (2n-1 Toffoli) for the uncontrolled adder.
- **Breaking the precompiled cache contract:** Hardcoded sequences must be treated as cached (DO NOT FREE). The ownership model must match the existing dynamic cache: callers get a pointer they must not free.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| QFT-style sequence gen | Custom per-gate C code | Python generation script | Follows established pattern from Phases 58-59, eliminates human error |
| T-count computation | Custom Python counting | `circuit_stats.c` (already done) | C iterates circuit layers once, computes all counts atomically |
| Controlled add for mul | MCX(3-control) decomposition | CNOT-wrapped uncontrolled add | 50%+ gate reduction, simpler circuit |

## Common Pitfalls

### Pitfall 1: Hardcoded Sequence Ownership Mismatch

**What goes wrong:** Hardcoded sequences use `static const` data. Dynamic sequences use `malloc`-ed data. The `toffoli_sequence_free()` function will crash if called on a hardcoded (static const) sequence.

**Why it happens:** The precompiled cache stores pointers from both sources. CQ/cCQ sequences (caller-owned) must be freed; QQ/cQQ sequences (cached) must NOT be freed.

**How to avoid:** The existing ownership contract is: QQ/cQQ return cached pointers (DO NOT FREE), CQ/cCQ return fresh pointers (caller must free). Hardcoded sequences are just another source of cached pointers. Do not change the ownership model.

**Warning signs:** Segfault in `toffoli_sequence_free()` or double-free crashes.

### Pitfall 2: Add-Subtract Correction Term

**What goes wrong:** The CNOT-wrapped add-subtract adds when ctrl=1 but SUBTRACTS when ctrl=0 (not identity). Without a correction step, the multiplication result is wrong for all inputs except 2^n - 1.

**Why it happens:** The CNOT flips all bits of the source operand when ctrl=0, turning addition into two's complement subtraction. In schoolbook multiplication, zero-valued multiplier bits should contribute nothing, not subtract.

**How to avoid:** After all add-subtract iterations, apply a CQ correction: `ret += self * (2^n - 1)`. This compensates for the unwanted subtractions. Verify by comparing gate counts AND functional results against the naive implementation.

**Warning signs:** Multiplication produces correct results for `other = 2^n - 1` (all ones) but wrong results for other inputs.

### Pitfall 3: Build System Not Compiling New Sequence Files

**What goes wrong:** New `toffoli_add_seq_*.c` files are created but not compiled into the shared library. Tests pass because dynamic generation still works; the hardcoded path is silently dead.

**Why it happens:** `setup.py` or `Makefile` needs explicit listing of source files.

**How to avoid:** After creating new C files, verify they are compiled by: (1) adding them to `setup.py`'s `sources` list, (2) adding a test that asserts the hardcoded dispatch returns non-NULL for widths 1-8.

**Warning signs:** `get_hardcoded_toffoli_QQ_add(4)` returns NULL when it should return a valid sequence.

### Pitfall 4: Cython Declaration Mismatch

**What goes wrong:** Adding `t_count` to the Cython `gate_counts_t` struct in `_core.pxd` without matching the exact field name and type from `circuit_stats.h` causes a compilation error or silent memory corruption.

**Why it happens:** Cython generates C code that accesses struct fields by name. If the name in `.pxd` doesn't match the C header exactly, the generated C code references a non-existent field.

**How to avoid:** Copy the field declaration exactly: `size_t t_count` in both `circuit_stats.h` and `_core.pxd`.

### Pitfall 5: Controlled Add-Subtract Modifying Source Register

**What goes wrong:** The CNOT-wrapping technique modifies the source register (`self`) during the add-subtract operation. If `self` is not properly restored, subsequent iterations see corrupted data.

**Why it happens:** The CNOT wrap applies CX(target=self[i], ctrl=other[j]) which flips self bits when other[j]=1. The uncontrolled adder is supposed to preserve the source register (CDKM preserves the a-register). Then the CNOT unwrap restores self. But if the adder does NOT preserve the source, the unwrap fails.

**How to avoid:** The CDKM adder DOES preserve the a-register (source). This is a known property of the MAJ/UMA chain. Verify this property holds by testing with known inputs. Add an assertion or test that self qubits are unchanged after the add-subtract cycle.

## Code Examples

### Example 1: T-count Exposure (Cython pxd)

```cython
# In _core.pxd, inside gate_counts_t declaration:
cdef extern from "circuit_stats.h":
    ctypedef struct gate_counts_t:
        size_t x_gates
        size_t y_gates
        size_t z_gates
        size_t h_gates
        size_t p_gates
        size_t cx_gates
        size_t ccx_gates
        size_t other_gates
        size_t t_count      # NEW: 7 * ccx_gates
```

### Example 2: T-count in Python dict

```cython
# In _core.pyx, gate_counts property:
@property
def gate_counts(self):
    cdef gate_counts_t counts = circuit_gate_counts(<circuit_s*>_circuit)
    return {
        'X': counts.x_gates,
        'Y': counts.y_gates,
        'Z': counts.z_gates,
        'H': counts.h_gates,
        'P': counts.p_gates,
        'CNOT': counts.cx_gates,
        'CCX': counts.ccx_gates,
        'other': counts.other_gates,
        'T': counts.t_count,
    }
```

### Example 3: Controlled Add-Subtract in Multiplication (Pseudocode)

```c
// NEW: toffoli_mul_qq with CNOT-wrapped add-subtract
void toffoli_mul_qq_addsub(circuit_t *circ,
    const unsigned int *ret_qubits, int ret_bits,
    const unsigned int *self_qubits, int self_bits,
    const unsigned int *other_qubits, int other_bits)
{
    int n = ret_bits;
    qubit_t carry = allocator_alloc(circ->allocator, 1, true);

    for (int j = 0; j < n; j++) {
        int width = n - j;
        if (width < 1) break;

        // Step 1: CNOT wrap - flip self bits controlled by other[j]
        for (int i = 0; i < width && i < self_bits; i++) {
            gate_t g; memset(&g, 0, sizeof(g));
            cx(&g, self_qubits[i], other_qubits[j]);
            add_gate(circ, &g);
        }

        // Step 2: Uncontrolled addition (uses CDKM: only CCX+CX)
        if (width == 1) {
            unsigned int tqa[2];
            tqa[0] = ret_qubits[n - 1];
            tqa[1] = self_qubits[0];
            sequence_t *seq = toffoli_QQ_add(1);
            if (seq) run_instruction(seq, tqa, 0, circ);
        } else {
            unsigned int tqa[256];
            for (int i = 0; i < width; i++) tqa[i] = self_qubits[i];
            for (int i = 0; i < width; i++) tqa[width + i] = ret_qubits[j + i];
            tqa[2 * width] = carry;
            sequence_t *seq = toffoli_QQ_add(width);
            if (seq) run_instruction(seq, tqa, 0, circ);
        }

        // Step 3: CNOT unwrap - restore self bits
        for (int i = 0; i < width && i < self_bits; i++) {
            gate_t g; memset(&g, 0, sizeof(g));
            cx(&g, self_qubits[i], other_qubits[j]);
            add_gate(circ, &g);
        }
    }

    // Step 4: Correction - add self * (2^n - 1) via CQ adder
    // This compensates for subtractions when other[j] = 0
    // ... (CQ addition with classical value = 2^n - 1, applied to self * constant)

    allocator_free(circ->allocator, carry, 1);
}
```

### Example 4: Toffoli Hardcoded Sequence (Static Const)

```c
// toffoli_add_seq_2.c (width=2 QQ addition: 12 layers)
#include "toffoli_sequences.h"

#ifdef TOFFOLI_SEQ_WIDTH_2

// MAJ(ancilla=4, b[0]=2, a[0]=0): CX(2,4), CX(0,4), CCX(4,0,2)
static const gate_t TOF_QQ_ADD_2_L0[] = {{.Gate=X, .Target=2, .NumControls=1, .Control={4}, .GateValue=1}};
static const gate_t TOF_QQ_ADD_2_L1[] = {{.Gate=X, .Target=0, .NumControls=1, .Control={4}, .GateValue=1}};
static const gate_t TOF_QQ_ADD_2_L2[] = {{.Gate=X, .Target=4, .NumControls=2, .Control={0,2}, .GateValue=1}};
// ... (9 more layers for MAJ + UMA chain)

static const gate_t *TOF_QQ_ADD_2_LAYERS[] = {
    TOF_QQ_ADD_2_L0, TOF_QQ_ADD_2_L1, TOF_QQ_ADD_2_L2, /* ... */
};
static const num_t TOF_QQ_ADD_2_GPL[] = {1, 1, 1, /* ... */};

static const sequence_t HARDCODED_TOF_QQ_ADD_2 = {
    .seq = (gate_t **)TOF_QQ_ADD_2_LAYERS,
    .num_layer = 12,
    .used_layer = 12,
    .gates_per_layer = (num_t *)TOF_QQ_ADD_2_GPL
};
#endif
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Dynamic-only Toffoli sequence gen | Add hardcoded for widths 1-8 | Phase 72 | Eliminates malloc/build overhead for common widths |
| Controlled multiplication via cQQ_add | CNOT-wrapped uncontrolled add-subtract | Phase 72 | ~50% fewer Toffoli-equivalent gates |
| No T-count in Python API | `gate_counts['T']` available | Phase 72 | Users can assess fault-tolerant circuit cost |
| T-count only in C struct | Exposed through Cython to Python | Phase 72 | Full stack visibility |

**Important note on Gidney vs CDKM:**
The Litinski 2024 paper (arXiv:2410.00899) reports n^2 + 4n + 3 Toffoli count using Gidney adders (n-1 Toffoli per uncontrolled add, requires measurement). Since this project uses CDKM adders (2n-1 Toffoli per uncontrolled add, no measurement needed), the Toffoli count with CNOT-wrapping will be higher than Litinski's formula. The improvement is still significant: replacing 3-control MCX gates with 2-control CCX gates plus cheap CNOTs.

**Expected Toffoli count for n-bit multiplication:**
- Naive controlled (current): n iterations of cQQ_add, each with 2(n-j)-1 MCX(3-control) in cMAJ/cUMA = expensive
- CNOT-wrapped add-subtract: n iterations of QQ_add, each with 2(n-j)-1 CCX(2-control) + 2(n-j) CNOT = much cheaper
- The CCX count alone: sum_{j=0}^{n-1} 2(n-j)-1 = n(2n-1) - n(n-1) = n^2 Toffoli for the adder parts

## Open Questions

1. **Exact correction term for add-subtract multiplication**
   - What we know: After CNOT-wrapped iterations, wrong partial products accumulate when multiplier bits are 0.
   - What's unclear: The exact classical value to add as correction, accounting for modular arithmetic and carry behavior.
   - Recommendation: Implement and test empirically. Compare output of add-subtract multiplication against naive multiplication for all input pairs at width 2-4. The correction formula derivation should be: `correction = self * sum_{j: other[j]=0} 2^j = self * (2^n - 1 - other)`. But since `other` is quantum, this correction must be applied as another add-subtract or handled differently. This needs careful analysis during implementation.

   **Alternative approach:** Instead of a single correction at the end, adjust the algorithm to use the add-subtract's natural behavior. In Litinski's formulation, the intermediate result is signed and the algorithm is specifically designed for this. An implementation-time deep-dive into the paper's Section 2 is recommended.

2. **Hardcoded sequence width range**
   - What we know: Phase description says widths 1-8. QFT hardcoded covers 1-16.
   - What's unclear: Whether 1-8 is sufficient or should match QFT's 1-16.
   - Recommendation: Start with 1-8 as specified. The Toffoli sequences are simpler (fewer gates per layer, no angles) so 8 widths is a reasonable starting point. Can extend later.

3. **BK CLA hardcoded sequences**
   - What we know: Only CDKM (RCA) sequences are planned for hardcoding.
   - What's unclear: Whether BK CLA sequences should also be hardcoded.
   - Recommendation: Do not hardcode BK CLA. The BK sequence generation involves a tree computation that varies with width. The CDKM sequences are the primary dispatch target for most operations (BK is only used for forward, non-inverted additions). Keep BK as dynamic-only.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis**: `circuit_stats.c` (t_count computation, line 68), `_core.pxd` (missing t_count field, line 161-168), `_core.pyx` (gate_counts dict, missing T entry)
- **Codebase analysis**: `ToffoliAddition.c` (CDKM adder implementation, precompiled cache pattern, sequence structure)
- **Codebase analysis**: `ToffoliMultiplication.c` (current schoolbook multiplication using toffoli_cQQ_add)
- **Codebase analysis**: `generate_seq_all.py` (QFT hardcoded sequence generation script, 1317 lines, well-documented)
- **Codebase analysis**: `sequences/add_seq_dispatch.c` and `sequences.h` (dispatch infrastructure pattern)

### Secondary (MEDIUM confidence)
- [Litinski 2024 - Quantum schoolbook multiplication with fewer Toffoli gates](https://arxiv.org/abs/2410.00899) -- Controlled add-subtract technique, n^2+4n+3 Toffoli count (with Gidney adders)
- [Gidney 2018 - Halving the cost of quantum addition](https://quantum-journal.org/papers/q-2018-06-18-74/) -- n-1 Toffoli adder (requires measurement, not applicable to this project's current infrastructure)
- [Cuccaro et al. 2004 - CDKM ripple-carry adder](https://arxiv.org/abs/quant-ph/0410184) -- 2n-1 Toffoli, 5n-3 CNOT, 1 ancilla, used in current implementation

### Tertiary (LOW confidence)
- The exact Toffoli count improvement for CNOT-wrapped CDKM (vs Litinski's Gidney-based formula) has not been independently verified. The ~50% improvement claim is based on replacing MCX(3-control) with CCX(2-control), which is analytically sound but the exact count reduction depends on MCX decomposition strategy.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all infrastructure exists, patterns well-established
- Architecture (hardcoded sequences): HIGH - exact pattern from Phases 58-59
- Architecture (T-count exposure): HIGH - 3-line change, field already computed in C
- Architecture (add-subtract optimization): MEDIUM - technique is sound but correction term for CDKM-based version needs implementation-time validation
- Pitfalls: HIGH - based on direct codebase analysis of ownership contracts and known bug patterns

**Research date:** 2026-02-16
**Valid until:** 2026-03-16 (stable domain, no external dependencies changing)
