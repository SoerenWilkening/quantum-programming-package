# Phase 71: Carry Look-Ahead Adder - Research

**Researched:** 2026-02-15
**Domain:** Quantum arithmetic circuits -- parallel prefix carry look-ahead addition
**Confidence:** HIGH (algorithm details well-established in literature; codebase integration patterns proven by prior phases)

## Summary

This phase implements O(log n) depth addition using carry look-ahead (CLA) prefix trees as an alternative to the existing CDKM ripple-carry adder (RCA). The Draper et al. (2004) quantum CLA paper describes the foundational approach: compute generate/propagate signals for each bit, propagate carries through a parallel prefix tree in O(log n) depth, then compute sums and uncompute ancilla. Two prefix tree variants are required: Kogge-Stone (depth-optimized, ~n*log2(n) ancilla qubits) and Brent-Kung (ancilla-optimized, ~2n-2 ancilla qubits).

The existing codebase already has all necessary infrastructure: gate primitives (ccx, cx, x, mcx), sequence_t caching, hot_path dispatch with arithmetic_mode check, ancilla allocation via allocator_alloc/free, and the qubit_saving option that can select between KS and BK variants. The CLA adder integrates into the existing ToffoliAddition.c as new functions alongside the existing CDKM functions, with dispatch logic added to hot_path_add.c to select RCA vs CLA based on width threshold.

The key design challenge is the prefix tree indexing: both KS and BK trees require careful tracking of which ancilla qubit stores which intermediate generate/propagate value at each tree level. The uncomputation must exactly reverse the prefix tree computation to return all ancilla to |0>. The controlled variants (cQQ, cCQ) require conditioning every gate on the external control, escalating CCX to MCX(3 controls) and CNOT to CCX.

**Primary recommendation:** Implement Brent-Kung first (fewer ancilla, simpler tree structure), then Kogge-Stone. Dispatch CLA for width >= 4 in Toffoli mode. Use the existing `qubit_saving` option to select BK (when true) vs KS (when false/default).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Implement **both** Kogge-Stone and Brent-Kung in Phase 71
- Kogge-Stone is the **default** (depth-optimized, ~n*log(n) ancilla)
- Brent-Kung activates when **qubit-saving option** is enabled (2n-2 ancilla, slightly more depth)
- Each variant is **inline/self-contained** (no shared generate/propagate abstraction)
- **Automatic width threshold**: below threshold use RCA, above use CLA -- transparent to user
- Expose **override option** (e.g., `ql.option('cla', False)`) to force RCA regardless of width
- **Toffoli mode only**: CLA does not get a QFT variant
- **All four variants**: QQ, CQ, cQQ, cCQ all get CLA implementations
- **Subtraction** via reversed gate sequence, same pattern as RCA
- **Mixed-width** supported via zero-extension of shorter operand
- **No ancilla cap**: Kogge-Stone uses whatever it needs
- **Silent fallback to RCA** when ancilla allocation can't satisfy CLA requirements
- **Ancilla reuse** across consecutive additions in multiplication loops

### Claude's Discretion
- Whether CLA propagates into multiplication/division or stays isolated to direct add/sub
- Exact automatic width threshold value
- Internal code structure for controlled CLA variants (CCX/MCX patterns)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core (Existing -- No New Dependencies)

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `ccx()` | `gate.h` / `gate.c` | Toffoli gate for generate computation | Existing primitive, used throughout |
| `cx()` | `gate.h` / `gate.c` | CNOT for propagate computation | Existing primitive |
| `x()` | `gate.h` / `gate.c` | NOT for CQ classical init | Existing primitive |
| `mcx()` | `gate.h` / `gate.c` | Multi-controlled X for controlled CLA | Existing primitive, used in cMAJ/cUMA |
| `allocator_alloc/free` | `qubit_allocator.h` | Ancilla lifecycle | Proven pattern from Phase 66-69 |
| `alloc_sequence()` | `ToffoliAddition.c` | Sequence allocation helper | Reuse existing internal helper |

### Files to Modify

| File | Change | Rationale |
|------|--------|-----------|
| `c_backend/src/ToffoliAddition.c` | Add CLA functions (KS + BK) | Same file as RCA -- all Toffoli addition lives here |
| `c_backend/include/toffoli_arithmetic_ops.h` | Declare new CLA functions | Public API header for Toffoli arithmetic |
| `c_backend/src/hot_path_add.c` | Add CLA dispatch logic (width threshold + fallback) | Existing dispatch point for Toffoli arithmetic |
| `src/quantum_language/_core.pyx` | Add `cla` option to `option()` | Override mechanism for forcing RCA |
| `c_backend/include/circuit.h` | Add `cla_override` field to `circuit_t` | Store the override flag |

### Files That Do NOT Need Changes

| File | Why |
|------|-----|
| `ToffoliMultiplication.c` | Calls hot_path functions which handle dispatch internally |
| `qint_arithmetic.pxi` | Dispatch happens in C hot-path |
| `qint_division.pxi` | Uses += / -= which dispatch through hot-path |
| `compile.py` | Cache key already includes arithmetic mode; CLA vs RCA is transparent |
| `execution.c` | Gate-type agnostic |
| `qubit_allocator.c` | Already supports multi-qubit ancilla alloc/free |

## Architecture Patterns

### Pattern 1: CLA Algorithm Structure (Brent-Kung variant)

**What:** The CLA adder computes all carry bits in O(log n) depth using a prefix tree, then computes sum bits.

**Algorithm phases for n-bit QQ addition (in-place: b += a):**

```
Phase 1: Compute initial generate and propagate signals
  For each bit i (0 to n-1):
    g[i] = a[i] AND b[i]    -- Toffoli(target=g_ancilla[i], ctrl1=a[i], ctrl2=b[i])
    p[i] = a[i] XOR b[i]    -- CNOT(target=b[i], control=a[i])  [p stored in-place on b]

Phase 2: Prefix tree (Brent-Kung up-sweep)
  For level k = 1 to log2(n):
    For positions where i mod 2^k == 2^k - 1:
      (g[i], p[i]) = (g[i], p[i]) o (g[i-2^(k-1)], p[i-2^(k-1)])
      where (g_h, p_h) o (g_l, p_l) = (g_h XOR (p_h AND g_l), p_h AND p_l)
      Gate decomposition:
        Toffoli(target=g[i], ctrl1=p[i], ctrl2=g[j])   -- g[i] ^= p[i] * g[j]
        Toffoli(target=p[i], ctrl1=p[i_anc], ctrl2=p[j]) -- p[i] = p[i] * p[j] (using ancilla)

Phase 3: Prefix tree (Brent-Kung down-sweep)
  For level k = log2(n)-1 down to 1:
    For positions where carry was not yet computed:
      Apply the same (g,p) o (g,p) merge operation

Phase 4: Compute sum bits
  For each bit i (0 to n-1):
    s[i] = p[i] XOR c[i-1]   -- CNOT(target=b[i], control=carry[i-1])

Phase 5: Uncompute ancilla (reverse of Phases 2-3, then 1)
  Reverse prefix tree merges
  Uncompute generate signals: Toffoli(target=g[i], ctrl1=a[i], ctrl2=b[i])
```

**Depth:** 2*log2(n) + O(1) for Brent-Kung, log2(n) + O(1) for Kogge-Stone

### Pattern 2: Kogge-Stone vs Brent-Kung Prefix Trees

**What:** Two different strategies for the prefix computation in Phase 2/3 above.

**Kogge-Stone (default -- depth-optimized):**
- Depth: log2(n) levels
- Operations: n*log2(n) - n + 1 prefix nodes
- Ancilla: ~n*log2(n) qubits (each prefix node needs ancilla for intermediate values)
- Every position computes its carry in parallel at each level
- Pattern: at level k, position i merges with position i - 2^k

**Brent-Kung (qubit-saving mode):**
- Depth: 2*log2(n) - 2 levels
- Operations: 2n - 2 - log2(n) prefix nodes
- Ancilla: ~2n - 2 qubits
- Up-sweep computes carries at power-of-2 positions; down-sweep fills in the rest
- Pattern: up-sweep like a binary tree, then down-sweep distributes results

### Pattern 3: Dispatch Logic in hot_path_add.c

**What:** Width-based automatic dispatch between RCA and CLA.

```c
// In hot_path_add.c, within the ARITH_TOFFOLI block:
if (circ->cla_override == 0 && result_bits >= CLA_THRESHOLD) {
    // Try CLA first
    int ancilla_needed;
    if (qubit_saving_mode) {
        ancilla_needed = 2 * result_bits - 2;  // Brent-Kung
    } else {
        ancilla_needed = result_bits * log2_ceil(result_bits);  // Kogge-Stone (approx)
    }

    qubit_t cla_ancilla = allocator_alloc(circ->allocator, ancilla_needed, true);
    if (cla_ancilla != (qubit_t)-1) {
        // CLA path: build qubit array with ancilla
        if (qubit_saving_mode) {
            toff_seq = toffoli_QQ_add_bk(result_bits);
        } else {
            toff_seq = toffoli_QQ_add_ks(result_bits);
        }
        // ... run_instruction, then free ancilla
    } else {
        // Silent fallback to RCA (ancilla allocation failed)
        // ... existing RCA path (1 ancilla)
    }
} else {
    // RCA path (below threshold or override active)
    // ... existing CDKM code
}
```

### Pattern 4: CLA Function Naming Convention

**What:** Parallel naming to existing CDKM functions with variant suffix.

| Existing RCA | New CLA (Kogge-Stone) | New CLA (Brent-Kung) |
|-------------|----------------------|---------------------|
| `toffoli_QQ_add(bits)` | `toffoli_QQ_add_ks(bits)` | `toffoli_QQ_add_bk(bits)` |
| `toffoli_CQ_add(bits, val)` | `toffoli_CQ_add_ks(bits, val)` | `toffoli_CQ_add_bk(bits, val)` |
| `toffoli_cQQ_add(bits)` | `toffoli_cQQ_add_ks(bits)` | `toffoli_cQQ_add_bk(bits)` |
| `toffoli_cCQ_add(bits, val)` | `toffoli_cCQ_add_ks(bits, val)` | `toffoli_cCQ_add_bk(bits, val)` |

### Pattern 5: Qubit Layout for CLA Operations

**What:** The qubit_array mapping for CLA operations, which is different from RCA.

```
RCA (CDKM) qubit layout -- toffoli_QQ_add(n):
  [0..n-1]       = register a (source, preserved)
  [n..2n-1]      = register b (target, gets a+b)
  [2n]           = 1 ancilla carry qubit
  Total: 2n+1 qubits

CLA (Brent-Kung) qubit layout -- toffoli_QQ_add_bk(n):
  [0..n-1]       = register a (source, preserved)
  [n..2n-1]      = register b (target, gets a+b)
  [2n..4n-3]     = 2n-2 ancilla qubits (generate + propagate intermediates)
  Total: 4n-2 qubits

CLA (Kogge-Stone) qubit layout -- toffoli_QQ_add_ks(n):
  [0..n-1]       = register a (source, preserved)
  [n..2n-1]      = register b (target, gets a+b)
  [2n..]         = ~n*log2(n) ancilla qubits
  Total: 2n + n*ceil(log2(n)) qubits (approx)
```

### Anti-Patterns to Avoid

- **Shared generate/propagate abstraction:** User decision explicitly requires each variant to be inline/self-contained. Do NOT create a shared `prefix_tree.h` with abstract tree traversal -- each CLA variant should have its own complete implementation.

- **Exposing CLA/RCA choice at the Python API level:** The dispatch is automatic and transparent. The user sees `a += b` regardless. Only the `ql.option('cla', False)` override is exposed.

- **Allocating ancilla in Python:** CLA ancilla count depends on the variant and width -- allocate in C hot path where the decision is made.

- **Modifying multiplication to directly call CLA functions:** Multiplication calls the hot_path functions which handle CLA dispatch. Do not bypass the hot path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sequence allocation | Custom malloc patterns | `alloc_sequence()` helper | Already handles error cleanup, used throughout ToffoliAddition.c |
| Ancilla lifecycle | Manual qubit tracking | `allocator_alloc()` + `allocator_free()` | Block-based reuse, coalescing, DEBUG leak detection |
| Subtraction | Separate subtraction functions | `run_instruction(seq, qa, /*invert=*/1, circ)` | Gate reversal for self-inverse gates is automatic |
| Qubit saving mode detection | New option plumbing | `_get_qubit_saving_mode()` | Already exists, already threaded through compile cache key |
| Controlled variant gates | Manual CCX decomposition | `mcx()` for 3+ controls | Existing MCX handles arbitrary control counts |

**Key insight:** The existing codebase provides all the building blocks. The CLA implementation is purely algorithmic -- translating prefix tree logic into sequences of ccx/cx/x calls using the existing patterns.

## Common Pitfalls

### Pitfall 1: Prefix Tree Index Off-by-One Errors

**What goes wrong:** The prefix tree merge operations reference wrong ancilla positions, computing incorrect carries. This is especially dangerous because incorrect carries produce wrong sums for some but not all inputs -- can pass many tests but fail on specific bit patterns.

**Why it happens:** Brent-Kung and Kogge-Stone use different indexing schemes. In Brent-Kung, only positions at powers-of-2 boundaries participate in the up-sweep; in Kogge-Stone, every position participates at every level. Mapping these abstract tree positions to concrete qubit indices requires careful bookkeeping.

**How to avoid:**
1. Write the prefix tree as two nested loops with explicit position calculations
2. Pre-compute a `tree_map[]` array that lists (source_pos, dest_pos, level) for each merge operation
3. Verify the tree_map against known examples (n=4, n=8) before generating gates
4. Test exhaustively for n=4 (2^8=256 input pairs) -- this catches all indexing bugs

**Warning signs:** Tests pass for n=1,2,3 but fail for n=4 or above. Some input values produce correct results while others don't.

### Pitfall 2: Uncomputation Order Mismatch

**What goes wrong:** Ancilla qubits are not returned to |0> after the CLA operation, causing the allocator_free to release dirty qubits that contaminate subsequent operations.

**Why it happens:** The uncomputation must exactly reverse the prefix tree computation. If the forward computation does operations in order A, B, C, the uncomputation must do C_inv, B_inv, A_inv. Since Toffoli and CNOT are self-inverse, the gates are the same but the ORDER must be exactly reversed.

**How to avoid:**
1. Build the forward pass as a list of (gate_type, target, controls) tuples
2. Generate the uncomputation by iterating the list in reverse
3. Verify ancilla state with simulation for small widths

**Warning signs:** Ancilla leak warnings in DEBUG mode. Statevector has non-zero amplitude on ancilla qubits after the operation.

### Pitfall 3: Qubit Array Layout Mismatch Between Sequence and Hot Path

**What goes wrong:** The sequence's virtual qubit indices don't align with the hot path's physical qubit mapping. This is the exact bug class (BUG-CQQ-ARITH) that caused weeks of debugging in Phase 66.

**Why it happens:** The CLA sequence uses many more ancilla than the RCA (2n-2 vs 1), and the hot path must map ALL of them correctly. If the sequence expects generate[0] at virtual index 2n but the hot path places it at 2n+1, every gate referencing that ancilla is wrong.

**How to avoid:**
1. Document the qubit layout at the top of BOTH the sequence function AND the hot path function
2. Use a single source of truth for layout constants (e.g., `#define CLA_BK_ANCILLA_START(n) (2*(n))`)
3. Write a test that verifies gate qubit indices match expected physical qubits

**Warning signs:** Circuit produces wrong results only for multi-bit widths. Single-bit special cases work fine.

### Pitfall 4: CQ Variant Ancilla Double-Count

**What goes wrong:** The CQ (classical-quantum) CLA variant needs BOTH the classical value temp register AND the CLA ancilla. If the hot path doesn't account for both, ancilla indices overlap.

**Why it happens:** RCA CQ needs n+1 ancilla (n temp + 1 carry). CLA CQ needs n temp + (2n-2 for BK or n*log(n) for KS) ancilla. The hot path must allocate ALL of these as a single contiguous block.

**How to avoid:**
1. Calculate total ancilla = temp_count + cla_ancilla_count
2. Allocate all at once via `allocator_alloc(circ->allocator, total, true)`
3. Map temp register to first n indices, CLA ancilla to remaining indices

### Pitfall 5: Threshold Too Low Causes Regression

**What goes wrong:** If the CLA threshold is set too low (e.g., width >= 2), very small additions use CLA which wastes ancilla for negligible depth benefit.

**Why it happens:** For small n (1-3), the CLA prefix tree has minimal depth advantage over RCA, but uses significantly more ancilla. The overhead of compute/uncompute for generate/propagate signals can even make CLA slower in total gate count.

**How to avoid:** Set threshold at width >= 4. At n=4, RCA depth is 24 layers while BK CLA depth is ~10 layers -- a clear win. Below n=4, the difference is negligible.

## Code Examples

### Example 1: Brent-Kung Up-Sweep (4-bit addition)

```c
// 4-bit Brent-Kung CLA: up-sweep phase
// Positions: 0, 1, 2, 3
// Ancilla: g[0..3] at indices 2n..2n+3, p stored in-place on b register

// Level 1: merge adjacent pairs
// Position 1: (g[1],p[1]) o (g[0],p[0])
//   Toffoli(target=g[1], ctrl1=p[1], ctrl2=g[0])   -- g[1] ^= p[1]*g[0]
//   Toffoli(target=p_anc[1], ctrl1=p[1], ctrl2=p[0])  -- p[1] &= p[0]
ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], g_idx[1], p_idx[1], g_idx[0]);
layer++;
// ... (p merge using ancilla)

// Position 3: (g[3],p[3]) o (g[2],p[2])
ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], g_idx[3], p_idx[3], g_idx[2]);
layer++;

// Level 2: merge position 3 with position 1
// Position 3: (g[3],p[3]) o (g[1],p[1])
ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], g_idx[3], p_idx[3], g_idx[1]);
layer++;
```

### Example 2: Generate/Propagate Initialization

```c
// Compute g[i] and p[i] for each bit position
// g[i] = a[i] AND b[i] -- stored in ancilla g_qubit[i]
// p[i] = a[i] XOR b[i] -- stored in-place on b[i]

for (int i = 0; i < bits; i++) {
    int a_i = i;             // a-register index
    int b_i = bits + i;      // b-register index
    int g_i = 2 * bits + i;  // generate ancilla index

    // g[i] = a[i] AND b[i]: Toffoli(target=g[i], ctrl1=a[i], ctrl2=b[i])
    ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], g_i, a_i, b_i);
    // Note: all g[i] computations are independent and CAN be on the same layer
}
layer++;

for (int i = 0; i < bits; i++) {
    int a_i = i;
    int b_i = bits + i;

    // p[i] = a[i] XOR b[i]: CNOT(target=b[i], control=a[i])
    cx(&seq->seq[layer][seq->gates_per_layer[layer]++], b_i, a_i);
    // Note: all p[i] computations are independent and CAN be on the same layer
}
layer++;
```

### Example 3: Sum Computation

```c
// After carries are computed, sum[i] = p[i] XOR carry[i-1]
// p[i] is stored in b[i], carry[i-1] is in g[i-1] (after prefix tree)

// For i = 0: sum[0] = p[0] XOR carry_in (carry_in = 0 for unsigned add)
// Result: b[0] already holds p[0] = a[0] XOR b[0] = correct sum bit 0

// For i = 1..n-1: sum[i] = p[i] XOR carry[i-1]
for (int i = 1; i < bits; i++) {
    int b_i = bits + i;
    int carry_i_minus_1 = 2 * bits + i - 1;  // g[i-1] holds carry[i-1]

    cx(&seq->seq[layer][seq->gates_per_layer[layer]++], b_i, carry_i_minus_1);
}
layer++;
```

### Example 4: Silent Fallback to RCA

```c
// In hot_path_add.c, CLA dispatch with silent fallback:
int cla_ancilla_count;
bool use_bk = /* check qubit_saving_mode */;

if (use_bk) {
    cla_ancilla_count = 2 * result_bits - 2;
} else {
    // Kogge-Stone: n * ceil(log2(n)) approximate
    int log_n = 0;
    int tmp = result_bits;
    while (tmp > 1) { log_n++; tmp >>= 1; }
    cla_ancilla_count = result_bits * log_n;
}

qubit_t cla_ancilla = allocator_alloc(circ->allocator, cla_ancilla_count, true);
if (cla_ancilla == (qubit_t)-1) {
    // Silent fallback to RCA -- no warning, no error
    // Allocate just 1 ancilla for RCA
    qubit_t rca_ancilla = allocator_alloc(circ->allocator, 1, true);
    if (rca_ancilla == (qubit_t)-1) return;

    tqa[2 * result_bits] = rca_ancilla;
    toff_seq = toffoli_QQ_add(result_bits);  // existing RCA
    // ... run_instruction, free rca_ancilla
} else {
    // CLA path
    for (int i = 0; i < cla_ancilla_count; i++) {
        tqa[2 * result_bits + i] = cla_ancilla + i;
    }
    toff_seq = use_bk ? toffoli_QQ_add_bk(result_bits)
                      : toffoli_QQ_add_ks(result_bits);
    // ... run_instruction, free cla_ancilla
}
```

## Depth and Resource Analysis

### RCA vs CLA Depth Comparison

| Width (n) | RCA Depth (6n) | BK CLA Depth (~4*log2(n)+6) | KS CLA Depth (~2*log2(n)+4) | BK Ancilla (2n-2) | KS Ancilla (~n*log2(n)) |
|-----------|---------------|---------------------------|---------------------------|-------------------|----------------------|
| 1 | 1 (CNOT) | N/A (use RCA) | N/A (use RCA) | 0 | 0 |
| 2 | 12 | ~10 | ~6 | 2 | 2 |
| 3 | 18 | ~12 | ~8 | 4 | ~5 |
| 4 | 24 | ~14 | ~8 | 6 | ~8 |
| 8 | 48 | ~18 | ~10 | 14 | ~24 |
| 16 | 96 | ~22 | ~12 | 30 | ~64 |
| 32 | 192 | ~26 | ~14 | 62 | ~160 |
| 64 | 384 | ~30 | ~16 | 126 | ~384 |

### Recommended Width Threshold: 4

**Rationale:**
- At n=4, RCA depth is 24 while BK CLA depth is ~14 (1.7x improvement) and KS CLA depth is ~8 (3x improvement)
- At n=3, the improvement is marginal and extra ancilla are not worth it
- At n=2, BK CLA depth is comparable to RCA but uses 2 extra ancilla
- At n=1, RCA is a single CNOT -- no tree possible

The threshold of 4 provides clear depth wins while avoiding wasteful ancilla allocation for tiny widths.

### CLA Propagation into Multiplication/Division (Claude's Discretion)

**Recommendation: YES, propagate CLA into multiplication and division.**

**Rationale:**
1. Multiplication calls `toffoli_cQQ_add` internally via the hot path. If the hot path dispatches to CLA when width >= threshold, multiplication automatically benefits from O(log n) depth per addition step, reducing total multiplication depth from O(n^2) to O(n * log n).
2. The ancilla reuse pattern (allocate once, reuse for loop iterations) works naturally because the hot path allocates/frees ancilla per call, and `allocator_free` -> `allocator_alloc` reuses the same physical qubits.
3. Division similarly benefits: each trial subtraction uses the adder, so CLA reduces division depth.
4. No code changes needed in `ToffoliMultiplication.c` -- the hot path handles it transparently.
5. The silent fallback ensures safety: if ancilla can't be allocated for CLA, multiplication silently uses RCA.

## State of the Art

| Aspect | Current Approach (RCA) | New Approach (CLA) | Impact |
|--------|----------------------|-------------------|--------|
| Addition depth | O(n) -- linear | O(log n) -- logarithmic | Major improvement for large widths |
| Addition ancilla | 1 qubit | 2n-2 (BK) or n*log(n) (KS) | Moderate ancilla cost |
| Multiplication depth | O(n^2) | O(n * log n) | Significant improvement |
| Subtraction | Inverted adder | Inverted CLA adder | Same pattern, automatic |

**Recent developments (2024-2025):**
- Optimal Toffoli-depth quantum adders using Sklansky trees achieve log(n)+1 Toffoli-depth with Gidney's logical-AND optimization (arXiv:2405.02523)
- Ancilla-free sublinear-depth adders exist but use more complex gate sets
- Higher-radix CLA architectures reduce depth further for very large widths

**For this project:** Standard Brent-Kung and Kogge-Stone are appropriate. The Sklansky optimization is a potential future enhancement but adds complexity for marginal benefit at the widths this project targets (1-64 bits).

## Open Questions

1. **Exact Kogge-Stone ancilla formula**
   - What we know: ~n*log2(n) ancilla, exact count depends on how fan-out copies are handled in the quantum domain
   - What's unclear: Whether copy qubits can be shared across levels or must be separate. The quantum no-cloning theorem prevents direct fan-out, so each fan-out requires a CNOT to copy into an ancilla.
   - Recommendation: During implementation, compute exact ancilla count by building the tree structure and counting unique intermediate qubits. For n <= 64, the qa[256] buffer is sufficient for any reasonable count.

2. **CQ CLA variant efficiency**
   - What we know: Classical bits being known at compile time can simplify some prefix tree operations (if g[i]=0 because classical bit is 0, the Toffoli becomes identity)
   - What's unclear: How much simplification is practical to implement vs just using the temp-register approach (init temp with X gates, run QQ CLA, cleanup)
   - Recommendation: Use the temp-register approach (same as CQ RCA), which is proven correct and simpler to implement. Optimization of CQ CLA with classical bit knowledge is a future enhancement.

3. **Controlled CLA gate overhead**
   - What we know: Controlled RCA uses CCX + MCX(3 controls) in place of CNOT + Toffoli. Controlled CLA would similarly need each Toffoli replaced by MCX(3 controls) and each CNOT replaced by CCX.
   - What's unclear: Whether MCX(3 controls) decomposition overhead makes controlled CLA slower than controlled RCA for small widths
   - Recommendation: Implement controlled CLA using the same cMAJ/cUMA pattern (replace each gate with its controlled version). The threshold for controlled CLA may need to be higher than for uncontrolled CLA.

## Sources

### Primary (HIGH confidence)
- **Draper et al. (2004)** "A logarithmic-depth quantum carry-lookahead adder" [arXiv:quant-ph/0406142](https://arxiv.org/abs/quant-ph/0406142) -- Foundational CLA paper, defines the quantum prefix tree approach
- **Cuccaro et al. (2004)** "A new quantum ripple-carry addition circuit" [arXiv:quant-ph/0410184](https://arxiv.org/abs/quant-ph/0410184) -- CDKM RCA (existing implementation reference)
- **Existing codebase** `ToffoliAddition.c`, `hot_path_add.c`, `qubit_allocator.c` -- Verified directly, all patterns confirmed

### Secondary (MEDIUM confidence)
- **"Optimal Toffoli-Depth Quantum Adder"** [arXiv:2405.02523](https://arxiv.org/html/2405.02523v1) -- Compares prefix tree variants (KS, BK, Sklansky) for quantum; Sklansky slightly better but KS is standard
- **"A Higher radix architecture for quantum carry-lookahead adder"** [Nature Scientific Reports](https://www.nature.com/articles/s41598-023-41122-4) -- Higher-radix CLA using Brent-Kung structure, confirms BK as standard for quantum CLA
- **Classical prefix adder theory** -- Kogge-Stone: n*log2(n)-n+1 nodes, log2(n) depth; Brent-Kung: 2n-2-log2(n) nodes, 2*log2(n)-2 depth

### Tertiary (LOW confidence)
- Depth numbers in the comparison table are approximate (computed from formulas, not measured from actual gate-level implementation). Exact depths should be verified during implementation by counting actual layers in generated sequences.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- existing codebase provides all needed infrastructure
- Architecture patterns: HIGH for Brent-Kung (well-understood tree structure), MEDIUM for Kogge-Stone (quantum-specific fan-out handling needs careful implementation)
- Pitfalls: HIGH -- based on lessons learned from BUG-CQQ-ARITH and Phase 66/67 experience
- Depth analysis: MEDIUM -- formulas are from literature but exact layer counts need implementation verification
- Threshold recommendation: MEDIUM -- based on analytical comparison, should be validated with benchmarks

**Research date:** 2026-02-15
**Valid until:** 2026-04-15 (stable algorithms, no fast-moving dependencies)
