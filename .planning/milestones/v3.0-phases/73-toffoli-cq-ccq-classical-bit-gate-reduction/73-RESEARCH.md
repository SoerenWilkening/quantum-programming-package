# Phase 73: Toffoli CQ/cCQ Classical-Bit Gate Reduction - Research

**Researched:** 2026-02-17
**Domain:** Classical-bit-aware Toffoli gate simplification for CQ/cCQ CDKM and BK CLA adders
**Confidence:** HIGH

## Summary

Phase 73 optimizes the CQ (classical+quantum) and cCQ (controlled classical+quantum) Toffoli adder variants by exploiting known classical bit values to simplify gates at generation time. Currently, both `toffoli_CQ_add()` and `toffoli_cCQ_add()` in `ToffoliAddition.c` use a temp-register approach: they initialize a temp register to the classical value via X/CX gates, run the full QQ/cQQ CDKM adder unchanged, then undo the initialization. This wastes gates because the temp register qubits hold known classical values at the start of each MAJ -- gates controlled on known-|0> qubits can be eliminated entirely, and gates controlled on known-|1> qubits can be simplified (CCX with one known-|1> control becomes CX).

The savings come from two sources: (1) eliminating CX/CCX gates in the MAJ chain where temp qubit values are known, and (2) structural simplification by folding X-init/CX-init into the MAJ chain rather than having separate init/cleanup phases. Per the locked "static simplification only" decision, only the initial known values of each temp[i] qubit and the carry=|0> at position 0 are used -- classical state is NOT propagated through the MAJ chain. The same optimization applies to BK CLA variants (`toffoli_CQ_add_bk`, `toffoli_cCQ_add_bk`).

The cCQ variant benefits MORE than CQ: for each 0-bit in the classical value, two CCX gates in the cMAJ are eliminated (each worth 7T), versus only CX gates (0T) eliminated for CQ. The first cMAJ with bit[0]=0 eliminates 2 CCX + 1 MCX = 21T.

**Primary recommendation:** Write 4 inline generator functions (CDKM CQ, CDKM cCQ, BK CQ, BK cCQ) that emit simplified gates directly based on known classical bit values. Then hardcode value=1 (increment) CQ/cCQ sequences for widths 1-8.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Inline CQ generator: write CQ-specific MAJ/UMA emitters that take the classical bit value as a parameter and emit simplified gates directly
- Static simplification only: use known initial classical bit values (0 or 1) to simplify; do NOT propagate classical state dynamically through the MAJ chain
- Inline cCQ generator: same approach for controlled variants, folding classical bits into the controlled MAJ/UMA chain (saves CX-init/cleanup gates)
- Separate generators for CDKM and CLA (BK) -- no shared simplification logic
- Replace old temp-register CQ/cCQ code entirely once inline version passes tests (no fallback)
- Keep identical layout: [0..N-1] temp, [N..2N-1] self, [2N] carry for CQ; [2N+1] control for cCQ
- No Python-side changes needed -- only the gates emitted on existing qubit positions change
- Add #ifdef DEBUG assertion that temp register qubits are |0> after inline CQ completes
- No caching for inline CQ sequences (value space too large, generator is fast)
- Hardcode CQ and cCQ sequences for value=1 (increment) at widths 1-8
- No generation script changes -- hardcoded value=1 sequences written directly in C
- QQ/cQQ caching and hardcoding unchanged
- CDKM CQ/cCQ: inline generators (primary target)
- CLA BK CQ/cCQ: separate inline generators (also in this phase)
- CQ multiplication: automatically benefits via inline CQ adder calls (no mul-specific changes)
- Division/modulo: verify T-count improvement propagates (no div-specific changes)
- Standalone exhaustive tests against expected arithmetic results (widths 1-4)
- Gate count comparison: verify new CQ sequences have fewer CCX gates than old approach
- T-count reporting verification for CQ operations

### Claude's Discretion
(No explicit discretion areas specified)

### Deferred Ideas (OUT OF SCOPE)
- MCX(3+ controls) decomposition in controlled operations
- CCX-to-native gate decomposition (6 CNOT + 7 T)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADD-02 | Ripple-carry adder (CQ) adds a classical value to a quantum register using only Toffoli/CNOT/X gates | Inline CQ CDKM generator produces optimized CQ sequences; classical bit simplification eliminates unnecessary gates |
| ADD-04 | Controlled ripple-carry adder (cCQ) performs CQ addition conditioned on a control qubit | Inline cCQ CDKM generator eliminates CCX gates at 0-bit positions (up to 14T per position); folded CX-init |
| ADD-05 | Subtraction works via inverse of Toffoli adder (reversed gate sequence) for all 4 variants | Inline CQ/cCQ sequences remain invertible (gate order reversal); no structural change to inversion logic |
| INF-03 | Hardcoded Toffoli gate sequences for common widths eliminate generation overhead | Hardcoded value=1 (increment) CQ/cCQ sequences for widths 1-8 extend existing hardcoded infrastructure |
| INF-04 | T-count reporting in circuit statistics | Fewer CCX/MCX gates in optimized CQ/cCQ directly reduces reported T-count (7T per CCX); verify via gate_counts API |
</phase_requirements>

## Standard Stack

### Core (No New Dependencies)
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `ToffoliAddition.c` | existing | Contains all CQ/cCQ generators to modify | Single file for all Toffoli adder variants |
| `gate.h`: `ccx()`, `cx()`, `x()`, `mcx()` | existing | Gate emitter primitives | Same API, fewer calls per CQ sequence |
| `toffoli_sequences.h` / dispatch | existing | Hardcoded sequence infrastructure | Extended with CQ/cCQ dispatch |
| `alloc_sequence()` | existing | Sequence memory allocation helper | Same helper, smaller layer counts |
| `circuit_stats.c` | existing | T-count = 7 * (CCX + MCX) | No changes needed, automatically reflects fewer gates |

### No New Library Dependencies
All changes are within existing C source files plus new hardcoded sequence files.

## Architecture Patterns

### Recommended File Changes
```
c_backend/
  src/
    ToffoliAddition.c                    # MODIFY: Replace 4 function bodies with inline generators
    sequences/
      toffoli_cq_inc_seq_1.c             # NEW: Hardcoded CQ/cCQ value=1, width 1
      toffoli_cq_inc_seq_2.c             # NEW: width 2
      ...
      toffoli_cq_inc_seq_8.c             # NEW: width 8
      toffoli_add_seq_dispatch.c         # MODIFY: Add CQ/cCQ increment dispatch
  include/
    toffoli_sequences.h                  # MODIFY: Add CQ/cCQ dispatch declarations
tests/
  test_toffoli_cq_reduction.py           # NEW: Gate reduction + correctness tests
```

### Pattern 1: Classical Bit Gate Simplification Rules

Four gate simplification rules applied when a qubit's value is classically known at generation time.

| Gate | Known Qubit Role | Known Value | Simplification |
|------|-----------------|-------------|----------------|
| CX(target, control) | control | 0 | Eliminate (NOP) |
| CX(target, control) | control | 1 | Replace with X(target) |
| CCX(target, ctrl1, ctrl2) | ctrl1 or ctrl2 | 0 | Eliminate (NOP) |
| CCX(target, ctrl1, ctrl2) | ctrl1 or ctrl2 | 1 | Replace with CX(target, other_ctrl) |
| MCX(target, [c1,c2,c3]) | any control | 0 | Eliminate (NOP) |
| MCX(target, [c1,c2,c3]) | any control | 1 | Replace with CCX(target, other two controls) |

**Important:** These rules are only valid when the known qubit has not been modified by any prior gate in the current emission scope. Once a gate writes to a qubit (as target), its value becomes quantum-dependent.

### Pattern 2: CQ CDKM Inline MAJ Emitter

**Static simplification scope per the locked decision:**
- For first MAJ (i=0): carry=|0> AND temp[0]=classical_bit[0] are both known
- For subsequent MAJ (i>=1): only temp[i]=classical_bit[i] is known; the `a` parameter (carry from previous stage) is quantum-modified and unknown

**emit_CQ_MAJ(seq, layer, a, b, c, classical_bit_c):**

Standard MAJ(a, b, c):
```c
// Step 1: CX(target=b, control=c)
// Step 2: CX(target=a, control=c)
// Step 3: CCX(target=c, ctrl1=a, ctrl2=b)
```

If classical_bit_c == 0:
```c
// Step 1: CX(b, c=|0>) -> NOP (skip)
// Step 2: CX(a, c=|0>) -> NOP (skip)
// Step 3: CCX(c, a, b) -> emit as-is (c is target, not simplified)
```

If classical_bit_c == 1:
```c
// Fold init: emit X(c) to initialize temp to |1>
x(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c);
(*layer)++;
// Step 1: CX(b, c=|1>) -> X(b)
x(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b);
(*layer)++;
// Step 2: CX(a, c=|1>) -> X(a)
x(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a);
(*layer)++;
// Step 3: CCX(c, a, b) -> emit as-is
ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
(*layer)++;
```

**Special case: first MAJ (i=0) where carry=|0>:**

If classical_bit[0] == 0 AND carry=|0>:
```c
// Step 1: CX(self[0], temp[0]=|0>) -> NOP
// Step 2: CX(carry=|0>, temp[0]=|0>) -> NOP
// Step 3: CCX(temp[0], carry=|0>, self[0]) -> NOP (one control is |0>)
// ENTIRE FIRST MAJ ELIMINATED -- 3 gates saved including 1 CCX (7T)
```

If classical_bit[0] == 1 AND carry=|0>:
```c
// Fold init: X(temp[0])
// Step 1: CX(self[0], temp[0]=|1>) -> X(self[0])
// Step 2: CX(carry=|0>, temp[0]=|1>) -> X(carry)
// Step 3: CCX(temp[0], carry, self[0]) -> emit as-is (carry was flipped by step 2)
// Net: 3 X + 1 CCX (was 1 X + 2 CX + 1 CCX)
```

### Pattern 3: CQ CDKM Inline UMA Emitter

**emit_CQ_UMA(seq, layer, a, b, c, classical_bit_c):**

The UMA chain runs after the MAJ chain. After CDKM, the temp register is restored to its initial classical values. However, DURING the UMA chain, the temp qubits hold intermediate carry values and are NOT known classically. Therefore, **no static simplification applies to UMA gates** in the general case.

The UMA is emitted identically to the standard `emit_UMA()` regardless of classical bit values.

After the entire UMA chain completes, temp[i] is back to classical_bit[i]. For bit=1 positions, emit X(temp[i]) as cleanup (same as old approach). For bit=0 positions, no cleanup needed.

### Pattern 4: cCQ CDKM Inline cMAJ Emitter

**Key difference from CQ:** In cCQ, temp initialization uses CX(temp[i], ext_ctrl) for bit=1 positions. This puts temp[i] in a superposition entangled with ext_ctrl, so we CANNOT simplify based on "temp[i]=|1>" for bit=1 positions. However, for bit=0 positions, temp[i]=|0> unconditionally.

**emit_cCQ_MAJ(seq, layer, a, b, c, classical_bit_c, ext_ctrl):**

Standard cMAJ(a, b, c, ext_ctrl):
```c
// Step 1: CCX(target=b, ctrl1=c, ctrl2=ext_ctrl)
// Step 2: CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)
// Step 3: MCX(target=c, controls=[a, b, ext_ctrl])
```

If classical_bit_c == 0 (temp[i] unconditionally |0>):
```c
// Step 1: CCX(b, c=|0>, ext_ctrl) -> NOP (one control is |0>)
// Step 2: CCX(a, c=|0>, ext_ctrl) -> NOP (one control is |0>)
// Step 3: MCX(c, [a, b, ext_ctrl]) -> emit as-is (c is target)
// SAVES: 2 CCX = 14T per zero-bit position
```

If classical_bit_c == 1:
```c
// Fold init: CX(c, ext_ctrl) to conditionally initialize temp
cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, ext_ctrl);
(*layer)++;
// Steps 1-3: emit as-is (temp[i] is entangled, cannot simplify)
// Same as standard cMAJ
emit_cMAJ(seq, layer, a, b, c, ext_ctrl);
```

**Special case: first cMAJ (i=0) where carry=|0>:**

If classical_bit[0] == 0 AND carry=|0>:
```c
// Step 1: CCX(self[0], temp[0]=|0>, ext_ctrl) -> NOP
// Step 2: CCX(carry=|0>, temp[0]=|0>, ext_ctrl) -> NOP
// Step 3: MCX(temp[0], [carry=|0>, self[0], ext_ctrl]) -> NOP (one control is |0>)
// ENTIRE FIRST cMAJ ELIMINATED -- 2 CCX + 1 MCX = 21T saved
```

### Pattern 5: BK CLA CQ/cCQ Inline Generator

The BK CLA variants (`toffoli_CQ_add_bk`, `toffoli_cCQ_add_bk`) currently use the "copy QQ/cQQ sequence and wrap with X/CX init/cleanup" pattern. The inline approach replaces this with direct BK CLA generation that applies classical bit simplification to Phase A (generate initialization):

**Phase A of BK CLA (initialize single-bit generates):**
```c
// For i=0 to n-2: CCX(target=g[i], ctrl1=a[i], ctrl2=b[i])
// For i=0 to n-1: CX(target=b[i], control=a[i])
```

When a[i]=temp[i] has a known classical value:
- If temp[i]=0: CCX(g[i], temp[i]=|0>, self[i]) -> NOP (7T saved per zero-bit)
- If temp[i]=0: CX(self[i], temp[i]=|0>) -> NOP
- If temp[i]=1: CCX(g[i], temp[i]=|1>, self[i]) -> CX(g[i], self[i])
- If temp[i]=1: CX(self[i], temp[i]=|1>) -> X(self[i])

**Phase E of BK CLA (uncompute, same as Phase A reversed):**
Same simplifications apply for Phase E since temp qubits are restored by Phase D.

**Phases B, C, D, F:** No simplification (intermediate values are quantum-dependent).

### Pattern 6: Hardcoded Value=1 (Increment) Sequences

The increment operation (CQ add value=1) is the most common CQ operation (used in loops, counters). For value=1 (binary: 1 followed by 0s), classical bits are: bit[0]=1, bit[1..N-1]=0.

For CDKM increment:
- First MAJ: bit[0]=1, carry=|0> -> folded init + simplified steps (3 X + 1 CCX)
- Remaining MAJs: bit[i]=0 -> 2 CX eliminated, 1 CCX remains per position
- UMA chain: unchanged
- Cleanup: only X(temp[0])

Total gates for N-bit CDKM CQ increment:
- Forward: (3X + 1CCX) + (N-1)(1CCX) = 3X + N*CCX
- Reverse: N UMA = N*CCX + 2N*CX
- Cleanup: 1X
- Total: 4X + 2N*CCX + 2N*CX (vs old: 2X + 2N*CCX + 4N*CX)
- **Net saving: 2(N-1) CX gates** (Clifford savings, no T savings)

For cCQ increment with ext_ctrl:
- bit[0]=1: CX-init folded, no further simplification (entangled)
- bit[i]=0 (i>=1): 2 CCX eliminated per position = 14T per position
- For N-bit: (N-1)*14T = **14(N-1) T-gates saved**

These are significant enough to warrant hardcoding.

### Anti-Patterns to Avoid

- **Dynamic classical propagation through MAJ chain:** Tracking how carry values evolve through the MAJ chain given initial classical bits. This breaks the "static simplification only" decision and adds complexity. Keep it simple: only use initial known values.

- **Shared simplification logic between CDKM and BK CLA:** The gate structures are fundamentally different (MAJ/UMA chain vs generate/propagate tree). Separate emitters are clearer and less error-prone.

- **Trying to simplify UMA gates in CQ:** After the MAJ chain, temp qubits hold quantum carry values. UMA must be emitted unchanged.

- **Simplifying bit=1 positions in cCQ:** The CX-init entangles temp[i] with ext_ctrl, making temp[i] a quantum superposition. Only bit=0 positions (where temp[i]=|0> unconditionally) can be simplified.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sequence allocation | Custom allocator | Existing `alloc_sequence()` | Already handles all malloc/free patterns |
| Gate emission | Direct struct filling | `ccx()`, `cx()`, `x()`, `mcx()` from `gate.h` | Consistent initialization, handles large_control |
| Qubit layout mapping | New layout scheme | Same [temp, self, carry, ext_ctrl] layout | Python-C contract is tested and proven |
| Sequence freeing | Manual free | `toffoli_sequence_free()` | Handles large_control arrays for MCX gates |

## Common Pitfalls

### Pitfall 1: Incorrect Layer Count Calculation
**What goes wrong:** The inline CQ generator computes a different number of layers than the old temp-register approach. If the allocation is wrong, array out-of-bounds occurs.
**Why it happens:** The number of emitted gates varies based on the classical value (more 0-bits = fewer gates).
**How to avoid:** Count gates precisely: for each MAJ, count actual emitted gates based on classical bit value. Compute total before calling `alloc_sequence()`.
**Warning signs:** Segfault in sequence generation, `layer > num_layers` assertion.

### Pitfall 2: Forgetting X-init for bit=1 in CQ
**What goes wrong:** The classical bit simplification for bit=1 assumes the temp qubit has been flipped to |1>, but the X gate was omitted.
**Why it happens:** When folding init into MAJ, the X(temp[i]) gate must be emitted BEFORE the simplified MAJ gates.
**How to avoid:** Always emit X(temp[i]) as the first gate in the MAJ block for bit=1 positions. Pair with X(temp[i]) cleanup after UMA.

### Pitfall 3: Incorrect cCQ Simplification for bit=1
**What goes wrong:** Trying to simplify cMAJ gates when temp[i] was conditionally initialized (CX from ext_ctrl), treating temp[i] as known-|1> when it's actually entangled.
**Why it happens:** Confusion between CQ (unconditional init, X gate) and cCQ (conditional init, CX gate).
**How to avoid:** Only simplify bit=0 positions in cCQ. For bit=1, fold the CX-init and emit standard cMAJ/cUMA unchanged.

### Pitfall 4: Subtraction Breaks After Replacement
**What goes wrong:** The old CQ function was run with `invert=1` for subtraction. The new inline version produces a different gate structure that doesn't invert correctly.
**Why it happens:** `run_instruction()` reverses gate order for inversion. If the inline CQ sequence has a different structure, the reversal must still produce correct subtraction.
**How to avoid:** The inline approach produces a valid `sequence_t` that inverts the same way (gate reversal). Since all gates are self-inverse (X, CX, CCX), reversing order is sufficient. Test subtraction explicitly for all values at small widths.

### Pitfall 5: BK CLA Sequence Copy After CQ Change
**What goes wrong:** The BK CLA CQ variant (`toffoli_CQ_add_bk`) currently copies gates from the cached QQ BK sequence. If we change it to an inline generator, the `seq_qq` gate-by-gate copy pattern becomes obsolete but leftover code remains.
**Why it happens:** The old and new approaches are fundamentally different (copy+wrap vs. generate inline).
**How to avoid:** For BK CLA, the inline approach regenerates the BK sequence with classical bit knowledge applied to Phase A and Phase E. The function body is completely replaced, not modified.

### Pitfall 6: Hardcoded Sequence Qubit Layout Mismatch
**What goes wrong:** Hardcoded CQ value=1 sequences use different qubit indices than the dynamic generator.
**Why it happens:** CQ layout [0..N-1]=temp, [N..2N-1]=self differs from QQ layout [0..N-1]=a, [N..2N-1]=b. Copy-paste from QQ hardcoded sequences with wrong indices.
**How to avoid:** Verify: in CQ, temp[i]=i, self[i]=N+i, carry=2N. Write a unit test that compares dynamic inline CQ(value=1) output against the hardcoded version gate-by-gate.

## Code Examples

### Example 1: CQ CDKM Inline Generator Skeleton

```c
// Source: Derived from existing ToffoliAddition.c patterns

static void emit_CQ_MAJ(sequence_t *seq, int *layer,
                         int a, int b, int c,
                         int classical_bit_c, int a_known_zero) {
    if (classical_bit_c == 0) {
        // temp[i] is known |0>: skip CX steps (control is |0>)
        // Step 1: CX(b, c=|0>) -> NOP
        // Step 2: CX(a, c=|0>) -> NOP
        if (a_known_zero) {
            // First MAJ: carry=|0> AND temp=|0> -> CCX has |0> control -> NOP
            // Entire MAJ eliminated
        } else {
            // Step 3: CCX(c, a, b) -> emit as-is
            ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
            (*layer)++;
        }
    } else {
        // temp[i] starts at |0>, fold X-init into MAJ
        // X(c) to initialize temp to |1>
        x(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c);
        (*layer)++;
        // Step 1: CX(b, c=|1>) -> X(b)
        x(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b);
        (*layer)++;
        // Step 2: CX(a, c=|1>) -> X(a)
        x(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a);
        (*layer)++;
        // Step 3: CCX(c, a, b) -> emit as-is
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
        (*layer)++;
    }
}
```

### Example 2: Layer Count Calculation for CQ CDKM

```c
// Source: Analysis of gate simplification rules

static int compute_CQ_layer_count(int bits, int *bin) {
    if (bits == 1) return (bin[0] == 1) ? 1 : 0;

    int layers = 0;

    // Forward MAJ sweep
    int bit0 = bin[bits - 1]; // LSB (bit[0])
    if (bit0 == 0) {
        // First MAJ: entirely eliminated (carry=|0>, temp[0]=|0>)
        layers += 0;
    } else {
        // First MAJ: X-init + 2 X + 1 CCX = 4 gates
        layers += 4;
    }
    for (int i = 1; i < bits; i++) {
        int bit_i = bin[bits - 1 - i]; // LSB-first
        if (bit_i == 0) {
            // Skip 2 CX, emit 1 CCX
            layers += 1;
        } else {
            // X-init + 2 X + 1 CCX = 4 gates
            layers += 4;
        }
    }

    // Reverse UMA sweep: unchanged, 3 gates per UMA = 3*bits
    layers += 3 * bits;

    // Cleanup: 1 X per bit=1 position
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) layers++;
    }

    return layers;
}
```

### Example 3: cCQ Gate Savings Verification Test

```python
# Source: Test pattern from test_toffoli_hardcoded.py

def test_ccq_gate_reduction_for_even_value():
    """cCQ with even value saves 21T at first position."""
    ql.circuit()
    a = ql.qint(0, width=4)
    with ql.control(ql.qint(1, width=1)):
        a += 2  # Even value: bit[0]=0

    counts = ql.gate_counts()
    ccx_old = 8 * 4  # Old cCQ: 2*N cMAJ steps * 2 CCX + N MCX
    # New: first cMAJ eliminated (3 gates * 7T = 21T saved)
    assert counts['t_count'] < ccx_old * 7
```

### Example 4: Hardcoded CQ Increment Width 2

```c
// Source: Generated from inline CQ analysis for value=1, width=2

// CQ add value=1, width=2 inline sequence:
// Layout: [0,1]=temp, [2,3]=self, [4]=carry
//
// First MAJ(carry=|0>, self[0]=q2, temp[0]=bit[0]=1):
//   X(temp[0])=X(0)        -- init
//   X(self[0])=X(2)        -- CX simplified
//   X(carry)=X(4)          -- CX simplified
//   CCX(0, 4, 2)           -- unchanged
//
// Second MAJ(temp[0]=q0, self[1]=q3, temp[1]=bit[1]=0):
//   CX -> NOP (x2)
//   CCX(1, 0, 3)           -- unchanged
//
// UMA(temp[0], self[1], temp[1]):
//   CCX(1, 0, 3)
//   CX(0, 1)
//   CX(3, 0)
//
// UMA(carry, self[0], temp[0]):
//   CCX(0, 4, 2)
//   CX(4, 0)
//   CX(2, 4)
//
// Cleanup:
//   X(0)                   -- restore temp[0] from |1> to |0>
//
// Total: 4X + 4CCX + 4CX = 12 gates
// Old:   2X + 4CCX + 8CX = 14 gates
// Savings: 2 gates (4 CX eliminated, 2 X added)
```

## State of the Art

| Old Approach | New Approach | Impact |
|--------------|--------------|--------|
| X-init + QQ CDKM + X-cleanup | Inline CQ MAJ/UMA with classical simplification | Eliminates 2*CX per 0-bit in MAJ; saves 7T at first position if bit[0]=0 |
| CX-init + cQQ CDKM + CX-cleanup | Inline cCQ cMAJ/cUMA with 0-bit elimination | Eliminates 2*CCX per 0-bit = 14T per position; up to 21T at first position |
| Gate-copy from cached QQ BK sequence | Inline BK CLA with Phase A/E simplification | Eliminates CCX per 0-bit in generate computation |
| Dynamic generation only for CQ/cCQ | Hardcoded value=1 for widths 1-8 | Zero generation overhead for most common CQ operation (increment) |

## Gate Count Analysis

### CDKM CQ Savings (N-bit, value with k set bits out of N)

| Component | Old Gate Count | New Gate Count | Saved |
|-----------|---------------|----------------|-------|
| Init X gates | k | k (folded into MAJ) | 0 (moved, not eliminated) |
| MAJ CX gates | 2N | 2k (only bit=1 positions emit CX-as-X) | 2(N-k) CX |
| MAJ CCX gates | N | N or N-1 (if bit[0]=0) | 0 or 1 CCX (7T) |
| UMA gates | 3N | 3N (unchanged) | 0 |
| Cleanup X gates | k | k | 0 |
| **Total** | **2k + 4N CX + 2N CCX** | **4k X + 2k CX + (2N or 2N-1) CCX + 2N CX** | **2(N-k) CX + (0 or 7T)** |

### CDKM cCQ Savings (N-bit, value with k set bits, N-k zero bits)

| Component | Old Gate Count | New Gate Count | Saved |
|-----------|---------------|----------------|-------|
| Init CX gates | k | k (folded) | 0 |
| cMAJ CCX gates | 2N | 2k (zero-bit positions: 2 CCX eliminated each) | 2(N-k) CCX = **14(N-k) T** |
| cMAJ MCX gates | N | N or N-1 (if bit[0]=0, MCX also eliminated) | 0 or 1 MCX (7T) |
| cUMA gates | same | same | 0 |
| Cleanup CX gates | k | k | 0 |
| **Total T savings** | -- | -- | **14(N-k) + (0 or 7) T** |

For N=4, value=2 (k=1, N-k=3): saves 14*3 + 7 = **49T** (from 112T to 63T for the cMAJ phase alone).

### BK CLA CQ Savings (N-bit)

Phase A generates: N-1 CCX gates. For each 0-bit position: 1 CCX eliminated = 7T.
Phase A propagates: N CX gates. For each 0-bit: 1 CX eliminated.
Phase E (uncompute): Same savings as Phase A (mirror).

Total Phase A+E savings: 2*(N-k-1) CCX = **14(N-k-1) T** (position 0 to N-2 only have generates).

## Open Questions

1. **Layer counting edge cases for 1-bit CQ**
   - What we know: 1-bit CQ is a special case (single X or NOP). The inline approach doesn't change this.
   - What's unclear: Whether the 1-bit case should be routed through the inline generator or kept as a separate path.
   - Recommendation: Keep the existing 1-bit special case unchanged.

2. **Hardcoded sequence format for CQ (value-dependent)**
   - What we know: QQ/cQQ hardcoded sequences are width-dependent only (cacheable). CQ sequences are both width AND value dependent.
   - What's unclear: How to organize hardcoded files: one file per (width, value) pair? Or one file per width with value=1 only?
   - Recommendation: One file per width, containing both CQ and cCQ for value=1 only. Use the naming pattern `toffoli_cq_inc_seq_N.c`.

3. **MCX elimination in first cMAJ**
   - What we know: MCX(target, [carry=|0>, self[0], ext_ctrl]) has one control at |0>, making it NOP.
   - What's unclear: Whether the MCX function handles this gracefully when the gate is simply not emitted.
   - Recommendation: Just don't emit the gate. The MCX was never executed (it would have been a NOP at runtime).

## Sources

### Primary (HIGH confidence)
- **Codebase analysis:** `ToffoliAddition.c` (lines 301-622) - Current CQ/cCQ implementation with temp-register approach
- **Codebase analysis:** `ToffoliAddition.c` (lines 58-100) - MAJ/UMA gate decomposition (reference for simplification)
- **Codebase analysis:** `ToffoliAddition.c` (lines 123-172) - cMAJ/cUMA gate decomposition (reference for controlled simplification)
- **Codebase analysis:** `hot_path_add.c` - Dispatch logic showing how CQ/cCQ sequences are invoked
- **Codebase analysis:** `toffoli_add_seq_2.c` - Hardcoded sequence pattern (reference for new CQ hardcoded files)
- **Codebase analysis:** `circuit_stats.c` - T-count calculation: `7 * (ccx_gates + mcx_gates)`

### Secondary (MEDIUM confidence)
- **Phase 73 CONTEXT.md** - User decisions on scope, layout, and simplification approach
- **ARCHITECTURE-TOFFOLI-ARITHMETIC.md** - Prior research on CDKM adder structure and MAJ/UMA chain
- **Cuccaro et al., arXiv:quant-ph/0410184** - CDKM adder paper confirming MAJ/UMA structure and a-register preservation

### Tertiary (LOW confidence)
- Gate savings for BK CLA Phase A/E are derived from analysis, not empirically verified. Should be validated by gate count comparison tests.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, all within existing C codebase
- Architecture (CDKM CQ/cCQ): HIGH - Gate simplification rules are mathematically exact, traced through concrete examples
- Architecture (BK CLA CQ/cCQ): MEDIUM - Same principles apply but BK has more phases; simplification limited to Phase A/E
- Pitfalls: HIGH - Based on direct analysis of existing code patterns and known failure modes
- Gate count analysis: HIGH for CQ (modest savings), HIGH for cCQ (significant CCX elimination)

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable domain, no external dependency changes expected)
