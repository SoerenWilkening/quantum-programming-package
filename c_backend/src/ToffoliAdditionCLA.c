/**
 * @file ToffoliAdditionCLA.c
 * @brief Carry Look-Ahead (CLA) adder implementations (Phase 71, 73).
 *
 * Implements the Brent-Kung and Kogge-Stone parallel prefix CLA adders
 * for O(log n) depth carry computation. Also includes controlled variants
 * and CQ (classical-quantum) variants with classical-bit gate simplification.
 *
 * Phase 71: BK and KS CLA stubs and dispatch.
 * Phase 71-05: BK CLA implementation with compute-copy-uncompute pattern.
 * Phase 71-06: BK CQ/cQQ/cCQ CLA via sequence-copy pattern.
 * Phase 73: Inline CQ/cCQ BK CLA with classical-bit gate simplification.
 * Phase 74: Extracted from ToffoliAddition.c during split refactoring.
 *
 * References:
 *   Brent & Kung, "A Regular Layout for Parallel Adders" (1982)
 *   Draper et al., "A logarithmic-depth quantum carry-lookahead adder" (2006)
 */

#include "Integer.h"
#include "execution.h"
#include "gate.h"
#include "toffoli_addition_internal.h"
#include "toffoli_arithmetic_ops.h"
#include "toffoli_sequences.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ============================================================================
// Precompiled caches for CLA Toffoli addition
// ============================================================================
static sequence_t *precompiled_toffoli_QQ_add_bk[65] = {NULL};
static sequence_t *precompiled_toffoli_QQ_add_ks[65] = {NULL};
static sequence_t *precompiled_toffoli_cQQ_add_bk[65] = {NULL};
static sequence_t *precompiled_toffoli_cQQ_add_ks[65] = {NULL};

// ============================================================================
// BK prefix tree merge computation
// ============================================================================

/**
 * @brief Compute BK prefix tree merge list.
 *
 * Generates an ordered list of merge operations for the Brent-Kung parallel
 * prefix tree operating on n_carries carry positions (0..n_carries-1).
 *
 * The merge list consists of:
 * 1. Up-sweep merges: reduce phase, doubling stride at each level.
 * 2. Down-sweep merges: propagate phase, filling gaps between up-sweep positions.
 * 3. Tail merges: chain extension for positions beyond the power-of-2 aligned part.
 *
 * @param n_carries Number of carry positions (bits - 1)
 * @param merges Output array (caller-allocated, max 128 entries)
 * @param max_merges Maximum entries in merges array
 * @return Number of merges written
 */
int bk_compute_merges(int n_carries, bk_merge_t *merges, int max_merges) {
    if (n_carries <= 1)
        return 0;

    int count = 0;
    int up_sweep[128] = {0}; /* 1 if position was an up-sweep merge target */
    int covered[128] = {0};  /* 1 if position has complete prefix coverage */
    covered[0] = 1;          /* position 0 is trivially complete (single generate) */

    /* Track which positions the up-sweep reaches (for coverage simulation) */
    /* We use a simplified prefix tracking: after merge (pos, partner),
     * pos has prefix up to min(partner's leftmost) */
    int leftmost[128]; /* leftmost position in each position's prefix group */
    for (int i = 0; i < n_carries && i < 128; i++)
        leftmost[i] = i;

    /* Up-sweep: reduce phase */
    int max_level = -1;
    int k = 0;
    while (1) {
        int stride = 1 << (k + 1);
        int half = 1 << k;
        int found = 0;
        int pos = stride - 1;
        while (pos < n_carries && count < max_merges) {
            int partner = pos - half;
            if (partner >= 0) {
                merges[count].pos = pos;
                merges[count].partner = partner;
                merges[count].level = k;
                merges[count].is_down = 0;
                count++;
                up_sweep[pos] = 1;
                /* Update coverage: pos now covers down to leftmost[partner] */
                leftmost[pos] = leftmost[partner];
                if (leftmost[pos] == 0)
                    covered[pos] = 1;
                found = 1;
                if (k > max_level)
                    max_level = k;
            }
            pos += stride;
        }
        if (!found)
            break;
        k++;
    }

    /* Down-sweep: propagate phase */
    for (int dk = max_level - 1; dk >= 0; dk--) {
        int half = 1 << dk;
        int stride = half << 1;
        int pos = stride + half - 1; /* first down-sweep position at this level */
        while (pos < n_carries && count < max_merges) {
            if (!up_sweep[pos]) {
                int partner = pos - half;
                if (partner >= 0) {
                    merges[count].pos = pos;
                    merges[count].partner = partner;
                    merges[count].level = dk;
                    merges[count].is_down = 1;
                    count++;
                    up_sweep[pos] = 1; /* mark as covered for tail check */
                    leftmost[pos] = leftmost[partner];
                    if (leftmost[pos] == 0)
                        covered[pos] = 1;
                }
            }
            pos += stride;
        }
    }

    /* Tail merges: chain from last complete position to uncovered positions.
     * These handle positions beyond the power-of-2 aligned BK tree. */
    for (int i = 1; i < n_carries && count < max_merges; i++) {
        if (!covered[i]) {
            /* Find nearest complete position to the left */
            for (int j = i - 1; j >= 0; j--) {
                if (covered[j]) {
                    merges[count].pos = i;
                    merges[count].partner = j;
                    merges[count].level = 0;
                    merges[count].is_down = 1;
                    count++;
                    covered[i] = 1;
                    break;
                }
            }
        }
    }

    return count;
}

/**
 * @brief Compute ancilla count for Brent-Kung CLA adder.
 *
 * For n-bit addition, the BK CLA needs:
 *   - (n-1) generate ancilla g[0..n-2]
 *   - num_merges tree propagate-product ancilla (one per BK tree merge)
 *   - (n-1) carry-copy ancilla c[0..n-2]
 *   Total: 2*(n-1) + num_merges
 *
 * @param bits Width of operands (>= 2)
 * @return Number of ancilla qubits needed (0 for bits < 2)
 */
int bk_cla_ancilla_count(int bits) {
    if (bits < 2)
        return 0;

    int n_carries = bits - 1;
    bk_merge_t merges[128];
    int num_merges = bk_compute_merges(n_carries, merges, 128);

    return 2 * n_carries + num_merges;
}

// ============================================================================
// Kogge-Stone ancilla helper (file-local)
// ============================================================================

/**
 * @brief Compute ancilla count for Kogge-Stone prefix tree.
 *
 * @param bits Width of operands (>= 2)
 * @return Number of ancilla qubits needed
 */
static int ks_ancilla_count(int bits) {
    if (bits < 2)
        return 0;

    /* Count tree levels: ceil(log2(bits)) */
    int levels = 0;
    int tmp = bits;
    while (tmp > 1) {
        levels++;
        tmp = (tmp + 1) >> 1;
    }

    /* n-1 initial generates */
    int count = bits - 1;

    /* Propagate products: at each level k, positions i >= 2^k merge.
     * Each merge needs 1 propagate product ancilla. */
    for (int k = 0; k < levels; k++) {
        int stride = 1 << k;
        for (int i = bits - 2; i >= stride; i--) {
            count++; /* one propagate product ancilla per merge */
        }
    }

    return count;
}

// ============================================================================
// BK CLA QQ Adder
// ============================================================================

/**
 * @brief Brent-Kung CLA QQ adder: b += a (in-place on b-register).
 *
 * Uses the compute-copy-uncompute pattern with a Brent-Kung parallel
 * prefix tree for O(log n) depth carry computation:
 *
 * Phase A: Initialize single-bit generates and propagates
 * Phase B: BK prefix tree (up-sweep + down-sweep) computes group generates
 * Phase C: Copy carries from generate ancilla to carry-copy ancilla
 * Phase D: Reverse Phase B (uncompute tree, restoring generates)
 * Phase E: Uncompute propagates and generates
 * Phase F: Sum extraction using carries
 *
 * Qubit layout:
 *   [0..n-1]              = register a (source, PRESERVED)
 *   [n..2n-1]             = register b (target, gets a+b)
 *   [2n..3n-2]            = generate ancilla g[0..n-2]
 *   [3n-1..3n-2+tree_sz]  = tree propagate-product ancilla
 *   [3n-1+tree_sz..end]   = carry-copy ancilla c[0..n-2]
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 *
 * @param bits Width of operands (2-64; returns NULL for bits < 2)
 * @return Cached sequence, or NULL for bits < 2 or allocation failure
 */
sequence_t *toffoli_QQ_add_bk(int bits) {
    if (bits < 2 || bits > 64)
        return NULL;

    /* Check cache */
    if (precompiled_toffoli_QQ_add_bk[bits] != NULL)
        return precompiled_toffoli_QQ_add_bk[bits];

    int n = bits;
    int n_carries = n - 1;

    /* Compute merge list */
    bk_merge_t merges[128];
    int num_merges = bk_compute_merges(n_carries, merges, 128);

    /* Qubit index helpers */
    /* a[i] = i, b[i] = n+i, g[i] = 2*n+i */
    int tree_base = 3 * n - 1;               /* first tree ancilla qubit */
    int carry_base = tree_base + num_merges; /* first carry-copy ancilla */

    /* Track propagate source for each carry position.
     * Initially prop_src[i] = b[i] = n+i. Tree merges update this. */
    int prop_src[128];
    for (int i = 0; i < n_carries && i < 128; i++)
        prop_src[i] = n + i; /* b[i] */

    /* Compute gate count:
     * Phase A: (n-1) CCX + n CX = 2n-1 layers
     * Phase B: 2 gates per merge = 2*num_merges layers
     * Phase C: (n-1) CX layers (copy carries)
     * Phase D: 2*num_merges layers (reverse of Phase B)
     * Phase E: n CX + (n-1) CCX = 2n-1 layers
     * Phase F: n CX + (n-1) CX = 2n-1 layers (sum extraction)
     * Total: 3*(2n-1) + 4*num_merges + (n-1) = 7n - 4 + 4*num_merges
     */
    int num_layers = 7 * n - 4 + 4 * num_merges;

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL)
        return NULL;

    int layer = 0;
    int tree_anc_idx = 0; /* index into tree ancilla (0-based) */

    /* ===== Phase A: Initialize generate and propagate ===== */
    /* For i = 0 to n-2: CCX(target=g[i], ctrl1=a[i], ctrl2=b[i]) */
    for (int i = 0; i < n_carries; i++) {
        ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], 2 * n + i, /* g[i] */
            i,                                                          /* a[i] */
            n + i);                                                     /* b[i] */
        layer++;
    }
    /* For i = 0 to n-1: CX(target=b[i], control=a[i]) */
    for (int i = 0; i < n; i++) {
        cx(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i, /* b[i] */
           i);                                                     /* a[i] */
        layer++;
    }

    /* ===== Phase B: BK prefix tree (up-sweep + down-sweep) ===== */
    /* Record gate arguments for Phase D reversal (3 qubits per CCX gate) */
    int phase_b_gates[512][3]; /* [gate_idx][target, ctrl1, ctrl2] */
    int phase_b_count = 0;

    for (int m = 0; m < num_merges; m++) {
        int pos = merges[m].pos;
        int partner = merges[m].partner;
        int tree_qubit = tree_base + tree_anc_idx;

        /* Step 1: Update group generate */
        /* CCX(target=g[pos], ctrl1=prop_src[pos], ctrl2=g[partner]) */
        int t1 = 2 * n + pos;
        int c1a = prop_src[pos];
        int c1b = 2 * n + partner;
        phase_b_gates[phase_b_count][0] = t1;
        phase_b_gates[phase_b_count][1] = c1a;
        phase_b_gates[phase_b_count][2] = c1b;
        phase_b_count++;
        ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], t1, c1a, c1b);
        layer++;

        /* Step 2: Compute group propagate product */
        /* CCX(target=tree_anc, ctrl1=prop_src[pos], ctrl2=prop_src[partner]) */
        int t2 = tree_qubit;
        int c2a = prop_src[pos];
        int c2b = prop_src[partner];
        phase_b_gates[phase_b_count][0] = t2;
        phase_b_gates[phase_b_count][1] = c2a;
        phase_b_gates[phase_b_count][2] = c2b;
        phase_b_count++;
        ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], t2, c2a, c2b);
        layer++;

        /* Update prop_src[pos] to point to the new tree ancilla */
        prop_src[pos] = tree_qubit;
        tree_anc_idx++;
    }

    /* ===== Phase C: Copy carries ===== */
    /* For i = 0 to n-2: CX(target=c[i], control=g[i]) */
    for (int i = 0; i < n_carries; i++) {
        cx(&seq->seq[layer][seq->gates_per_layer[layer]++], carry_base + i, /* c[i] */
           2 * n + i);                                                      /* g[i] */
        layer++;
    }

    /* ===== Phase D: Reverse BK prefix tree ===== */
    /* Replay every gate from Phase B in reverse order.
     * CCX is self-inverse, so replaying backwards uncomputes the tree. */
    for (int g_idx = phase_b_count - 1; g_idx >= 0; g_idx--) {
        ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], phase_b_gates[g_idx][0], /* target */
            phase_b_gates[g_idx][1],                                                  /* ctrl1 */
            phase_b_gates[g_idx][2]);                                                 /* ctrl2 */
        layer++;
    }

    /* ===== Phase E: Uncompute propagates and generates ===== */
    /* For i = n-1 down to 0: CX(target=b[i], control=a[i]) */
    for (int i = n - 1; i >= 0; i--) {
        cx(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i, /* b[i] */
           i);                                                     /* a[i] */
        layer++;
    }
    /* For i = n-2 down to 0: CCX(target=g[i], ctrl1=a[i], ctrl2=b[i]) */
    for (int i = n_carries - 1; i >= 0; i--) {
        ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], 2 * n + i, /* g[i] */
            i,                                                          /* a[i] */
            n + i);                                                     /* b[i] */
        layer++;
    }

    /* ===== Phase F: Sum extraction ===== */
    /* For i = 0 to n-1: CX(target=b[i], control=a[i]) */
    for (int i = 0; i < n; i++) {
        cx(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i, /* b[i] */
           i);                                                     /* a[i] */
        layer++;
    }
    /* For i = 1 to n-1: CX(target=b[i], control=c[i-1]) */
    for (int i = 1; i < n; i++) {
        cx(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i, /* b[i] */
           carry_base + i - 1);                                    /* c[i-1] */
        layer++;
    }

    seq->used_layer = layer;
    sequence_compute_total_gate_count(seq);

    /* Cache and return */
    precompiled_toffoli_QQ_add_bk[bits] = seq;
    return seq;
}

// ============================================================================
// KS CLA QQ Adder (Stub)
// ============================================================================

/**
 * @brief Kogge-Stone CLA QQ adder: b += a (in-place on b-register).
 *
 * STUB: Returns NULL to fall through to RCA (CDKM) adder.
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 *
 * @param bits Width of operands (2-64; returns NULL for bits < 2)
 * @return NULL (CLA not yet implemented; falls through to RCA)
 */
sequence_t *toffoli_QQ_add_ks(int bits) {
    (void)bits; // suppress unused parameter warning
    // CLA algorithm not yet implemented -- fall through to RCA
    // Same fundamental ancilla uncomputation issue as Brent-Kung.
    return NULL;
}

// ============================================================================
// BK CLA CQ Adder (Phase 73 - classical-bit gate simplification)
// ============================================================================

/**
 * @brief Brent-Kung CLA CQ adder: self += classical_value.
 *
 * Phase 73: Inline BK CLA CQ generator with classical-bit gate simplification.
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 * NOT cached (value-dependent).
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return Fresh sequence, or NULL for bits < 2 or allocation failure
 */
sequence_t *toffoli_CQ_add_bk(int bits, int64_t value) {
    if (bits < 2 || bits > 64)
        return NULL;

    /* Get cached QQ BK sequence to extract Phases B-D-F gate counts */
    sequence_t *seq_qq = toffoli_QQ_add_bk(bits);
    if (seq_qq == NULL)
        return NULL;

    int n = bits;
    int n_carries = n - 1;

    /* Convert value to binary (MSB-first: bin[0]=MSB, bin[bits-1]=LSB) */
    int *bin = two_complement(value, bits);
    if (bin == NULL)
        return NULL;

    /* Count 1-bits (popcount) */
    int x_count = 0;
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1)
            x_count++;
    }

    /* Compute merge list for BK tree */
    bk_merge_t merges[128];
    int num_merges = bk_compute_merges(n_carries, merges, 128);

    /* Compute layer count for CQ BK */
    int phase_a_layers = 0;
    /* Generate part of Phase A */
    for (int i = 0; i < n_carries; i++) {
        int bit_i = bin[bits - 1 - i]; /* LSB-first */
        if (bit_i == 1) {
            phase_a_layers += 2; /* X-init(temp[i]) + CX(g[i], self[i]) */
        }
        /* bit=0: NOP, 0 layers */
    }
    /* Propagate part of Phase A */
    for (int i = 0; i < n; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            phase_a_layers += 1; /* X(self[i]) instead of CX(self[i], temp[i]) */
        }
        /* bit=0: NOP */
    }
    int phase_e_layers = phase_a_layers; /* Same simplification as Phase A */

    /* Phases B, C, D layer counts from original QQ BK formula */
    int phase_bcd_layers = 4 * num_merges + n_carries;

    /* Phase F (simplified): X(self[i]) for bit[i]=1 + CX(self[i], c[i-1]) for i>=1 */
    int phase_f_layers = x_count + (n - 1);

    int num_layers = phase_a_layers + phase_bcd_layers + phase_e_layers + phase_f_layers;

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    int layer = 0;

    /* Qubit index helpers (same as QQ BK) */
    int tree_base = 3 * n - 1;
    int carry_base = tree_base + num_merges;

    /* ===== Phase A (simplified): Initialize generate and propagate ===== */
    /* For i=0 to n-2: CCX(target=g[i], ctrl1=a[i]=temp[i], ctrl2=b[i]=self[i]) */
    for (int i = 0; i < n_carries; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            /* temp[i]=1: X-init temp[i], then CX(g[i], self[i]) */
            x(&seq->seq[layer][seq->gates_per_layer[layer]++], i); /* X(temp[i]) */
            layer++;
            cx(&seq->seq[layer][seq->gates_per_layer[layer]++], 2 * n + i,
               n + i); /* CX(g[i], self[i]) */
            layer++;
        }
        /* bit=0: CCX with |0> control -> NOP */
    }
    /* For i=0 to n-1: CX(target=b[i]=self[i], control=a[i]=temp[i]) */
    for (int i = 0; i < n; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            /* temp[i]=1: CX(self[i], temp[i]=|1>) -> X(self[i]) */
            x(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i); /* X(self[i]) */
            layer++;
        }
        /* bit=0: CX with |0> control -> NOP */
    }

    /* ===== Phases B, C, D: Copy from cached QQ BK sequence ===== */
    {
        int qq_phase_b_start = 2 * n - 1;
        int qq_phase_d_end = 2 * n - 1 + 4 * num_merges + n_carries; /* exclusive */
        for (int l = qq_phase_b_start; l < qq_phase_d_end; l++) {
            for (num_t g = 0; g < seq_qq->gates_per_layer[l]; g++) {
                gate_t *src = &seq_qq->seq[l][g];
                gate_t *dst = &seq->seq[layer][seq->gates_per_layer[layer]];
                dst->Gate = src->Gate;
                dst->Target = src->Target;
                dst->GateValue = src->GateValue;
                dst->NumControls = src->NumControls;
                dst->NumBasisGates = src->NumBasisGates;
                dst->large_control = NULL;
                if (src->NumControls <= 2) {
                    dst->Control[0] = src->Control[0];
                    dst->Control[1] = src->Control[1];
                } else if (src->large_control != NULL) {
                    dst->large_control = malloc(src->NumControls * sizeof(qubit_t));
                    if (dst->large_control != NULL) {
                        for (num_t c = 0; c < src->NumControls; c++)
                            dst->large_control[c] = src->large_control[c];
                        dst->Control[0] = src->Control[0];
                        dst->Control[1] = src->Control[1];
                    }
                }
                seq->gates_per_layer[layer]++;
            }
            layer++;
        }
    }

    /* ===== Phase E (simplified): Uncompute propagates and generates ===== */
    /* Reverse of Phase A: first CX (propagate uncompute), then CCX (generate uncompute) */
    /* For i=n-1 down to 0: CX(target=self[i], control=temp[i]) */
    for (int i = n - 1; i >= 0; i--) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            /* temp[i]=1: X(self[i]) */
            x(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i);
            layer++;
        }
    }
    /* For i=n-2 down to 0: CCX(target=g[i], ctrl1=temp[i], ctrl2=self[i]) */
    for (int i = n_carries - 1; i >= 0; i--) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            /* temp[i]=1: CX(g[i], self[i]) then X-cleanup(temp[i]) */
            cx(&seq->seq[layer][seq->gates_per_layer[layer]++], 2 * n + i, n + i);
            layer++;
            x(&seq->seq[layer][seq->gates_per_layer[layer]++], i);
            layer++;
        }
    }

    /* ===== Phase F (simplified): Sum extraction ===== */
    for (int i = 0; i < n; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            x(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i);
            layer++;
        }
    }
    for (int i = 1; i < n; i++) {
        cx(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i, carry_base + i - 1);
        layer++;
    }

    seq->used_layer = layer;
    sequence_compute_total_gate_count(seq);

#ifdef DEBUG
    if (layer != num_layers) {
        fprintf(stderr, "CQ_add_bk layer mismatch: expected %d, got %d (bits=%d)\n", num_layers,
                layer, bits);
    }
#endif

    free(bin);
    return seq;
}

// ============================================================================
// KS CLA CQ Adder (Stub)
// ============================================================================

/**
 * @brief Kogge-Stone CLA CQ adder: self += classical_value.
 *
 * STUB: Returns NULL to fall through to RCA (CDKM) CQ adder.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return NULL (KS QQ CLA not implemented; falls through to RCA)
 */
sequence_t *toffoli_CQ_add_ks(int bits, int64_t value) {
    (void)bits;
    (void)value;
    // KS QQ CLA not implemented -- fall through to RCA CQ
    return NULL;
}

// ============================================================================
// Controlled BK CLA QQ Adder
// ============================================================================

/**
 * @brief Emit AND-ancilla MCX(3) decomposition into a sequence layer.
 *
 * Replaces MCX(target, [c1, c2, ext_ctrl]) with 3 CCX gates:
 *   CCX(and_anc, c1, c2) -- compute AND
 *   CCX(target, and_anc, ext_ctrl) -- apply
 *   CCX(and_anc, c1, c2) -- uncompute AND
 *
 * Each gate emitted as a separate layer (increments *layer 3 times).
 *
 * @param seq     Sequence to emit into
 * @param layer   Pointer to current layer index
 * @param target  Target qubit
 * @param c1      First control
 * @param c2      Second control
 * @param ext_ctrl Third control (external)
 * @param and_anc AND-ancilla qubit
 */
static void emit_mcx3_seq(sequence_t *seq, int *layer, int target, int c1, int c2, int ext_ctrl,
                          int and_anc) {
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, c1, c2);
    (*layer)++;
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], target, and_anc, ext_ctrl);
    (*layer)++;
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, c1, c2);
    (*layer)++;
}

/**
 * @brief Emit recursive AND-ancilla MCX(k) decomposition into a sequence.
 *
 * For k controls, uses recursive pattern:
 * - k==2: CCX (1 layer)
 * - k==3: 3 CCX via AND-ancilla (3 layers)
 * - k>3: 2 CCX (compute/uncompute AND of first 2 controls) + recursive MCX(k-1)
 *
 * Total CCX: 2*(k-2) + 1, total ancilla: k-2 (starting at anc_start).
 *
 * @param seq         Sequence to emit into
 * @param layer       Pointer to current layer index
 * @param target      Target qubit
 * @param controls    Array of control qubits
 * @param num_controls Number of controls (>= 2)
 * @param anc_start   First available AND-ancilla qubit index
 */
static void emit_mcx_recursive_seq(sequence_t *seq, int *layer, int target, const qubit_t *controls,
                                   int num_controls, int anc_start) {
    if (num_controls == 2) {
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], target, controls[0], controls[1]);
        (*layer)++;
    } else if (num_controls == 3) {
        emit_mcx3_seq(seq, layer, target, (int)controls[0], (int)controls[1], (int)controls[2],
                      anc_start);
    } else {
        /* k > 3: peel off 2 controls into AND-ancilla, recurse with k-1 */
        int and_anc = anc_start;

        /* Compute AND of first 2 controls */
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, controls[0], controls[1]);
        (*layer)++;

        /* Build reduced control list: [and_anc, controls[2], ..., controls[k-1]] */
        qubit_t reduced[128];
        reduced[0] = (qubit_t)and_anc;
        for (int i = 2; i < num_controls; i++)
            reduced[i - 1] = controls[i];

        /* Recurse with k-1 controls, next ancilla */
        emit_mcx_recursive_seq(seq, layer, target, reduced, num_controls - 1, anc_start + 1);

        /* Uncompute AND */
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, controls[0], controls[1]);
        (*layer)++;
    }
}

/**
 * @brief Count layers needed for recursive MCX decomposition.
 *
 * @param num_controls Number of controls (>= 2)
 * @return Number of layers (CCX gates)
 */
static int mcx_recursive_layer_count(int num_controls) {
    if (num_controls <= 2)
        return 1;
    if (num_controls == 3)
        return 3;
    /* k > 3: 2 (compute/uncompute AND) + recursive(k-1) */
    return 2 + mcx_recursive_layer_count(num_controls - 1);
}

/**
 * @brief Controlled Brent-Kung CLA QQ adder: b += a, controlled by ext_ctrl.
 *
 * Every gate in the uncontrolled QQ BK sequence gets an additional control
 * qubit (ext_ctrl). Phase 74-03: MCX(3+) gates decomposed via AND-ancilla.
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 *
 * @param bits Width of operands (2-64; returns NULL for bits < 2)
 * @return Cached sequence, or NULL for bits < 2 or allocation failure
 */
sequence_t *toffoli_cQQ_add_bk(int bits) {
    if (bits < 2 || bits > 64)
        return NULL;

    /* Check cache */
    if (precompiled_toffoli_cQQ_add_bk[bits] != NULL)
        return precompiled_toffoli_cQQ_add_bk[bits];

    /* Get cached QQ BK sequence */
    sequence_t *seq_qq = toffoli_QQ_add_bk(bits);
    if (seq_qq == NULL)
        return NULL;

    /* ext_ctrl qubit index = 2*bits + bk_cla_ancilla_count(bits) */
    int ext_ctrl = 2 * bits + bk_cla_ancilla_count(bits);

    /* Count total layers needed after MCX decomposition.
     * Each gate in QQ sequence becomes:
     *   X -> CX (1 layer)
     *   CX -> CCX (1 layer)
     *   CCX -> MCX(3) decomposed (3 layers)
     * No MCX(n>2) exists in the QQ BK sequence (only X, CX, CCX). */
    int total_layers = 0;
    for (num_t l = 0; l < seq_qq->num_layer; l++) {
        for (num_t g = 0; g < seq_qq->gates_per_layer[l]; g++) {
            gate_t *src = &seq_qq->seq[l][g];
            if (src->NumControls == 2) {
                /* CCX -> MCX(3) decomposed = 3 layers */
                total_layers += 3;
            } else {
                /* X->CX or CX->CCX = 1 layer each */
                total_layers += 1;
            }
        }
    }

    /* AND-ancilla qubit at ext_ctrl + 1 */
    int and_anc = ext_ctrl + 1;

    /* Allocate new sequence */
    sequence_t *seq = alloc_sequence(total_layers);
    if (seq == NULL)
        return NULL;

    int layer = 0;

    /* Copy each gate from QQ sequence, injecting ext_ctrl with MCX decomposition */
    for (num_t l = 0; l < seq_qq->num_layer; l++) {
        for (num_t g = 0; g < seq_qq->gates_per_layer[l]; g++) {
            gate_t *src = &seq_qq->seq[l][g];

            if (src->NumControls == 0) {
                /* X -> CX with ext_ctrl */
                cx(&seq->seq[layer][seq->gates_per_layer[layer]++], src->Target, (qubit_t)ext_ctrl);
                layer++;
            } else if (src->NumControls == 1) {
                /* CX -> CCX with [original_ctrl, ext_ctrl] */
                ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], src->Target, src->Control[0],
                    (qubit_t)ext_ctrl);
                layer++;
            } else if (src->NumControls == 2) {
                /* CCX -> MCX(3) decomposed via AND-ancilla */
                emit_mcx3_seq(seq, &layer, (int)src->Target, (int)src->Control[0],
                              (int)src->Control[1], ext_ctrl, and_anc);
            }
            /* Note: QQ BK sequence has no MCX (only X, CX, CCX) */
        }
    }

    seq->used_layer = layer;
    sequence_compute_total_gate_count(seq);

    /* Cache and return */
    precompiled_toffoli_cQQ_add_bk[bits] = seq;
    return seq;
}

// ============================================================================
// Controlled KS CLA QQ Adder (Stub)
// ============================================================================

/**
 * @brief Controlled Kogge-Stone CLA QQ adder: b += a, controlled by ext_ctrl.
 *
 * STUB: Returns NULL to fall through to controlled RCA (CDKM) adder.
 *
 * @param bits Width of operands (2-64; returns NULL for bits < 2)
 * @return NULL (controlled CLA not yet implemented; falls through to RCA)
 */
sequence_t *toffoli_cQQ_add_ks(int bits) {
    (void)bits; // suppress unused parameter warning
    // Controlled KS CLA not implemented -- fall through to controlled RCA
    return NULL;
}

// ============================================================================
// Controlled BK CLA CQ Adder (Phase 73 - classical-bit gate simplification)
// ============================================================================

/**
 * @brief Controlled Brent-Kung CLA CQ adder: self += classical_value, controlled.
 *
 * Phase 73: Inline BK CLA cCQ generator with classical-bit gate simplification.
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 * NOT cached (value-dependent).
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return Fresh sequence, or NULL for bits < 2 or allocation failure
 */
sequence_t *toffoli_cCQ_add_bk(int bits, int64_t value) {
    /* BUG: Phase F sum extraction produces incorrect results for the
     * controlled CQ BK CLA path.  Disabled until fixed — falls through
     * to the working CDKM (RCA) implementation.  See test_cla_bk_algorithm
     * TestBKControlledCQAdd for the failing test case. */
    return NULL;
    if (bits < 2 || bits > 64)
        return NULL;

    /* Get cached controlled QQ BK sequence */
    sequence_t *seq_cqq = toffoli_cQQ_add_bk(bits);
    if (seq_cqq == NULL)
        return NULL;

    int n = bits;
    int n_carries = n - 1;

    /* ext_ctrl qubit index (same position as in cQQ) */
    int ext_ctrl = 2 * bits + bk_cla_ancilla_count(bits);

    /* Convert value to binary (MSB-first: bin[0]=MSB, bin[bits-1]=LSB) */
    int *bin = two_complement(value, bits);
    if (bin == NULL)
        return NULL;

    /* Count number of 1-bits in classical value */
    int x_count = 0;
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1)
            x_count++;
    }

    /* Compute merge list for BK tree */
    bk_merge_t merges[128];
    int num_merges = bk_compute_merges(n_carries, merges, 128);
    (void)merges; /* Used only for count */

    /* Compute layer count for cCQ BK */
    int phase_a_layers = 0;
    for (int i = 0; i < n_carries; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            phase_a_layers += 2; /* CX-init + CCX(g[i], self[i], ext_ctrl) */
        }
    }
    for (int i = 0; i < n; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            phase_a_layers += 1; /* CX(self[i], ext_ctrl) */
        }
    }
    int phase_e_layers = phase_a_layers;

    /* Phases B, C, D: same gate count as cQQ BK */
    int phase_bcd_layers = 4 * num_merges + n_carries;

    /* Phase F (simplified) */
    int phase_f_layers = x_count + (n - 1);

    int num_layers = phase_a_layers + phase_bcd_layers + phase_e_layers + phase_f_layers;

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    int layer = 0;

    /* Qubit index helpers (same as CQ BK / QQ BK) */
    int tree_base = 3 * n - 1;
    int carry_base = tree_base + num_merges;

    /* ===== Phase A (simplified): Initialize generate and propagate ===== */
    /* Generates: in cQQ BK, Phase A generate is MCX(g[i], [temp[i], self[i], ext_ctrl]) */
    for (int i = 0; i < n_carries; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            /* CX-init: CX(temp[i], ext_ctrl) */
            cx(&seq->seq[layer][seq->gates_per_layer[layer]++], i, (qubit_t)ext_ctrl);
            layer++;
            /* CCX(g[i], self[i], ext_ctrl) -- temp[i]=|1> when ext_ctrl=|1> */
            ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], 2 * n + i, n + i,
                (qubit_t)ext_ctrl);
            layer++;
        }
        /* bit=0: MCX with |0> control -> NOP */
    }
    /* Propagates: in cQQ BK, Phase A propagate is CCX(self[i], temp[i], ext_ctrl) */
    for (int i = 0; i < n; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            cx(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i, (qubit_t)ext_ctrl);
            layer++;
        }
        /* bit=0: CCX with |0> control -> NOP */
    }

    /* ===== Phases B, C, D: Copy from cached cQQ BK sequence ===== */
    {
        int cqq_phase_b_start = 2 * n - 1;
        int cqq_phase_d_end = 2 * n - 1 + 4 * num_merges + n_carries;
        for (int l = cqq_phase_b_start; l < cqq_phase_d_end; l++) {
            for (num_t g = 0; g < seq_cqq->gates_per_layer[l]; g++) {
                gate_t *src = &seq_cqq->seq[l][g];
                gate_t *dst = &seq->seq[layer][seq->gates_per_layer[layer]];
                dst->Gate = src->Gate;
                dst->Target = src->Target;
                dst->GateValue = src->GateValue;
                dst->NumControls = src->NumControls;
                dst->NumBasisGates = src->NumBasisGates;
                dst->large_control = NULL;
                if (src->NumControls <= 2) {
                    dst->Control[0] = src->Control[0];
                    dst->Control[1] = src->Control[1];
                } else if (src->large_control != NULL) {
                    dst->large_control = malloc(src->NumControls * sizeof(qubit_t));
                    if (dst->large_control != NULL) {
                        for (num_t c = 0; c < src->NumControls; c++)
                            dst->large_control[c] = src->large_control[c];
                        dst->Control[0] = src->Control[0];
                        dst->Control[1] = src->Control[1];
                    }
                }
                seq->gates_per_layer[layer]++;
            }
            layer++;
        }
    }

    /* ===== Phase E (simplified): Uncompute propagates and generates ===== */
    /* Propagate uncompute (reverse order) */
    for (int i = n - 1; i >= 0; i--) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            cx(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i, (qubit_t)ext_ctrl);
            layer++;
        }
    }
    /* Generate uncompute (reverse order) */
    for (int i = n_carries - 1; i >= 0; i--) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], 2 * n + i, n + i,
                (qubit_t)ext_ctrl);
            layer++;
            /* CX-cleanup: CX(temp[i], ext_ctrl) */
            cx(&seq->seq[layer][seq->gates_per_layer[layer]++], i, (qubit_t)ext_ctrl);
            layer++;
        }
    }

    /* ===== Phase F (simplified): Sum extraction ===== */
    for (int i = 0; i < n; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 1) {
            cx(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i, (qubit_t)ext_ctrl);
            layer++;
        }
    }
    for (int i = 1; i < n; i++) {
        ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], n + i, carry_base + i - 1,
            (qubit_t)ext_ctrl);
        layer++;
    }

    seq->used_layer = layer;
    sequence_compute_total_gate_count(seq);

#ifdef DEBUG
    if (layer != num_layers) {
        fprintf(stderr, "cCQ_add_bk layer mismatch: expected %d, got %d (bits=%d)\n", num_layers,
                layer, bits);
    }
#endif

    free(bin);
    return seq;
}

// ============================================================================
// Controlled KS CLA CQ Adder (Stub)
// ============================================================================

/**
 * @brief Controlled Kogge-Stone CLA CQ adder: self += classical_value, controlled.
 *
 * STUB: Returns NULL to fall through to controlled RCA (CDKM) CQ adder.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return NULL (controlled KS CLA not implemented; falls through to RCA)
 */
sequence_t *toffoli_cCQ_add_ks(int bits, int64_t value) {
    (void)bits;
    (void)value;
    // Controlled KS CLA CQ not implemented -- fall through to controlled RCA CQ
    return NULL;
}
