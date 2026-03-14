/**
 * @file ToffoliAdditionCDKM.c
 * @brief CDKM ripple-carry adder implementation (Phase 66-67, 73).
 *
 * Implements the Cuccaro-Draper-Kutin-Moulton (CDKM) ripple-carry adder
 * using MAJ (Majority) and UMA (UnMajority-and-Add) gate chains.
 *
 * The CDKM adder uses only Toffoli (CCX) and CNOT (CX) gates, making it
 * suitable for fault-tolerant quantum computation where T-gate count matters.
 *
 * Phase 66: Uncontrolled QQ and CQ adders.
 * Phase 67: Controlled variants (cQQ and cCQ) using CCX + MCX gates.
 * Phase 73: Inline CQ/cCQ generators with classical-bit gate simplification.
 *           Exploits known classical bit values (0 or 1) of temp register qubits
 *           to eliminate/simplify gates at generation time. Also applies to
 *           BK CLA CQ/cCQ variants (Phase A/E simplification).
 * Phase 74: Extracted from ToffoliAddition.c during split refactoring.
 *
 * References:
 *   Cuccaro et al., "A new quantum ripple-carry addition circuit" (2004)
 *   arXiv:quant-ph/0410184
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
// Precompiled caches for CDKM Toffoli addition (separate from QFT cache)
// ============================================================================
static sequence_t *precompiled_toffoli_QQ_add[65] = {NULL};
static sequence_t *precompiled_toffoli_cQQ_add[65] = {NULL};

// No cache for CQ/cCQ: value-dependent sequences, generated fresh each call.

// ============================================================================
// MAJ / UMA helper functions
// ============================================================================

/**
 * @brief Emit MAJ (Majority) gate triplet.
 *
 * MAJ(a, b, c):
 *   1. CNOT(target=b, control=c)     -- b ^= c
 *   2. CNOT(target=a, control=c)     -- a ^= c
 *   3. Toffoli(target=c, ctrl=a, ctrl=b) -- c ^= (a AND b)
 *
 * After MAJ: c holds the carry, a and b are in superposition.
 *
 * @param seq   Sequence to emit gates into
 * @param layer Pointer to current layer index (incremented by 3)
 * @param a     Qubit index for 'a' (carry-in / previous carry)
 * @param b     Qubit index for 'b' (source bit)
 * @param c     Qubit index for 'c' (target bit, becomes carry-out)
 */
static void emit_MAJ(sequence_t *seq, int *layer, int a, int b, int c) {
    // Step 1: CNOT(target=b, control=c)
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, c);
    (*layer)++;

    // Step 2: CNOT(target=a, control=c)
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c);
    (*layer)++;

    // Step 3: Toffoli(target=c, ctrl1=a, ctrl2=b)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
    (*layer)++;
}

/**
 * @brief Emit UMA (UnMajority-and-Add) gate triplet.
 *
 * UMA(a, b, c):
 *   1. Toffoli(target=c, ctrl=a, ctrl=b) -- undoes MAJ's Toffoli
 *   2. CNOT(target=a, control=c)          -- restores a
 *   3. CNOT(target=b, control=a)          -- b = sum bit
 *
 * After UMA: a is restored, b holds the sum bit, c is restored.
 *
 * @param seq   Sequence to emit gates into
 * @param layer Pointer to current layer index (incremented by 3)
 * @param a     Qubit index for 'a'
 * @param b     Qubit index for 'b' (becomes sum bit)
 * @param c     Qubit index for 'c'
 */
static void emit_UMA(sequence_t *seq, int *layer, int a, int b, int c) {
    // Step 1: Toffoli(target=c, ctrl1=a, ctrl2=b)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
    (*layer)++;

    // Step 2: CNOT(target=a, control=c)
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c);
    (*layer)++;

    // Step 3: CNOT(target=b, control=a)
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, a);
    (*layer)++;
}

// ============================================================================
// Controlled MAJ / UMA helper functions (Phase 67)
// ============================================================================

/**
 * @brief Emit controlled MAJ (Majority) gate sequence with AND-ancilla decomposition.
 *
 * cMAJ(a, b, c, ext_ctrl) decomposed:
 *   1. CCX(target=b, ctrl1=c, ctrl2=ext_ctrl)       -- controlled b ^= c
 *   2. CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)       -- controlled a ^= c
 *   3a. CCX(target=and_anc, ctrl1=a, ctrl2=b)       -- compute partial AND
 *   3b. CCX(target=c, ctrl1=and_anc, ctrl2=ext_ctrl) -- apply via AND-ancilla
 *   3c. CCX(target=and_anc, ctrl1=a, ctrl2=b)       -- uncompute AND
 *
 * Replaces MCX(3) with 3 CCX gates. Total: 5 CCX, zero MCX.
 * Phase 74-03: AND-ancilla MCX decomposition.
 *
 * @param seq      Sequence to emit gates into
 * @param layer    Pointer to current layer index (incremented by 5)
 * @param a        Qubit index for 'a' (carry-in / previous carry)
 * @param b        Qubit index for 'b' (source bit)
 * @param c        Qubit index for 'c' (target bit, becomes carry-out)
 * @param ext_ctrl Qubit index for external control qubit
 * @param and_anc  Qubit index for AND-ancilla (reused, starts/ends at |0>)
 */
static void emit_cMAJ(sequence_t *seq, int *layer, int a, int b, int c, int ext_ctrl, int and_anc) {
    // Step 1: CCX(target=b, ctrl1=c, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, c, ext_ctrl);
    (*layer)++;

    // Step 2: CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c, ext_ctrl);
    (*layer)++;

    // Step 3a: CCX(target=and_anc, ctrl1=a, ctrl2=b) -- compute AND
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, a, b);
    (*layer)++;

    // Step 3b: CCX(target=c, ctrl1=and_anc, ctrl2=ext_ctrl) -- apply
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, and_anc, ext_ctrl);
    (*layer)++;

    // Step 3c: CCX(target=and_anc, ctrl1=a, ctrl2=b) -- uncompute AND
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, a, b);
    (*layer)++;
}

/**
 * @brief Emit controlled UMA (UnMajority-and-Add) gate sequence with AND-ancilla decomposition.
 *
 * cUMA(a, b, c, ext_ctrl) decomposed:
 *   1a. CCX(target=and_anc, ctrl1=a, ctrl2=b)       -- compute partial AND
 *   1b. CCX(target=c, ctrl1=and_anc, ctrl2=ext_ctrl) -- apply via AND-ancilla
 *   1c. CCX(target=and_anc, ctrl1=a, ctrl2=b)       -- uncompute AND
 *   2. CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)       -- controlled restore a
 *   3. CCX(target=b, ctrl1=a, ctrl2=ext_ctrl)       -- controlled b = sum bit
 *
 * Replaces MCX(3) with 3 CCX gates. Total: 5 CCX, zero MCX.
 * Phase 74-03: AND-ancilla MCX decomposition.
 *
 * @param seq      Sequence to emit gates into
 * @param layer    Pointer to current layer index (incremented by 5)
 * @param a        Qubit index for 'a'
 * @param b        Qubit index for 'b' (becomes sum bit)
 * @param c        Qubit index for 'c'
 * @param ext_ctrl Qubit index for external control qubit
 * @param and_anc  Qubit index for AND-ancilla (reused, starts/ends at |0>)
 */
static void emit_cUMA(sequence_t *seq, int *layer, int a, int b, int c, int ext_ctrl, int and_anc) {
    // Step 1a: CCX(target=and_anc, ctrl1=a, ctrl2=b) -- compute AND
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, a, b);
    (*layer)++;

    // Step 1b: CCX(target=c, ctrl1=and_anc, ctrl2=ext_ctrl) -- apply
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, and_anc, ext_ctrl);
    (*layer)++;

    // Step 1c: CCX(target=and_anc, ctrl1=a, ctrl2=b) -- uncompute AND
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, a, b);
    (*layer)++;

    // Step 2: CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c, ext_ctrl);
    (*layer)++;

    // Step 3: CCX(target=b, ctrl1=a, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, a, ext_ctrl);
    (*layer)++;
}

// ============================================================================
// CQ MAJ / UMA helper functions (Phase 73 - classical-bit gate simplification)
// ============================================================================

/**
 * @brief Emit CQ-simplified MAJ gate sequence.
 *
 * Applies classical-bit gate simplification rules:
 * - If classical_bit_c == 0: skip CX steps (control is |0>), emit CCX unless
 *   a_known_zero (then entire MAJ is NOP since CCX has |0> control too).
 * - If classical_bit_c == 1: fold X-init (emit X(c)), then X(b) instead of CX,
 *   X(a) instead of CX, then CCX unchanged.
 *
 * @param seq             Sequence to emit gates into
 * @param layer           Pointer to current layer index
 * @param a               Qubit index for 'a' (carry-in / previous carry)
 * @param b               Qubit index for 'b' (source bit)
 * @param c               Qubit index for 'c' (temp bit with known classical value)
 * @param classical_bit_c Known classical value of qubit c (0 or 1)
 * @param a_known_zero    1 if qubit a is known to be |0> (first MAJ only)
 */
static void emit_CQ_MAJ(sequence_t *seq, int *layer, int a, int b, int c, int classical_bit_c,
                        int a_known_zero) {
    if (classical_bit_c == 0) {
        /* temp[i] is known |0>: skip CX steps (control is |0>) */
        /* Step 1: CX(b, c=|0>) -> NOP */
        /* Step 2: CX(a, c=|0>) -> NOP */
        if (a_known_zero) {
            /* First MAJ: carry=|0> AND temp[0]=|0> -> CCX has |0> control -> NOP */
            /* Entire MAJ eliminated */
        } else {
            /* Step 3: CCX(c, a, b) -> emit as-is (c is target, not simplified) */
            ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
            (*layer)++;
        }
    } else {
        /* temp[i] starts at |0>, fold X-init into MAJ */
        /* X(c) to initialize temp to |1> */
        x(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c);
        (*layer)++;
        /* Step 1: CX(b, c=|1>) -> X(b) */
        x(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b);
        (*layer)++;
        /* Step 2: CX(a, c=|1>) -> X(a) */
        x(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a);
        (*layer)++;
        /* Step 3: CCX(c, a, b) -> emit as-is */
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
        (*layer)++;
    }
}

/**
 * @brief Compute layer count for inline CQ CDKM adder.
 *
 * Precisely counts layers based on classical bit values:
 * - First MAJ (i=0): if bit[0]==0, 0 layers (fully eliminated); if bit[0]==1, 4 layers
 * - Subsequent MAJs (i>=1): if bit[i]==0, 1 layer (CCX only); if bit[i]==1, 4 layers
 * - UMA chain: 3*bits layers (unchanged)
 * - Cleanup: popcount(value) X gates
 *
 * @param bits Number of bits
 * @param bin  Binary representation (MSB-first: bin[0]=MSB, bin[bits-1]=LSB)
 * @return Total number of layers needed
 */
static int compute_CQ_layer_count(int bits, int *bin) {
    int layers = 0;

    /* Forward MAJ sweep */
    int bit0 = bin[bits - 1]; /* LSB (bit position 0) */
    if (bit0 == 0) {
        /* First MAJ: entirely eliminated (carry=|0>, temp[0]=|0>) */
        layers += 0;
    } else {
        /* First MAJ: X-init + 2X + 1CCX = 4 gates */
        layers += 4;
    }
    for (int i = 1; i < bits; i++) {
        int bit_i = bin[bits - 1 - i]; /* LSB-first: bit i */
        if (bit_i == 0) {
            /* Skip 2 CX, emit 1 CCX */
            layers += 1;
        } else {
            /* X-init + 2X + 1CCX = 4 gates */
            layers += 4;
        }
    }

    /* Reverse UMA sweep: unchanged, 3 gates per UMA = 3*bits */
    layers += 3 * bits;

    /* Cleanup: 1 X per bit=1 position */
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1)
            layers++;
    }

    return layers;
}

// ============================================================================
// cCQ cMAJ / cUMA helper functions (Phase 73 - classical-bit gate simplification)
// ============================================================================

/**
 * @brief Emit cCQ-simplified controlled MAJ gate sequence with AND-ancilla decomposition.
 *
 * For cCQ, temp initialization uses CX(temp[i], ext_ctrl), which entangles
 * temp[i] with ext_ctrl for bit=1 positions. Therefore:
 * - bit=0 positions: temp[i]=|0> unconditionally -> can simplify
 * - bit=1 positions: temp[i] is entangled -> fold CX-init, emit standard cMAJ
 *
 * Phase 74-03: MCX(3) decomposed to 3 CCX via AND-ancilla.
 *
 * @param seq             Sequence to emit gates into
 * @param layer           Pointer to current layer index
 * @param a               Qubit index for 'a' (carry-in / previous carry)
 * @param b               Qubit index for 'b' (source bit)
 * @param c               Qubit index for 'c' (temp bit)
 * @param classical_bit_c Known classical value of qubit c (0 or 1)
 * @param a_known_zero    1 if qubit a is known to be |0> (first cMAJ only)
 * @param ext_ctrl        External control qubit index
 * @param and_anc         Qubit index for AND-ancilla
 */
static void emit_cCQ_MAJ(sequence_t *seq, int *layer, int a, int b, int c, int classical_bit_c,
                         int a_known_zero, int ext_ctrl, int and_anc) {
    if (classical_bit_c == 0) {
        /* temp[i] unconditionally |0>: skip CCX steps (one control is |0>) */
        /* Step 1: CCX(b, c=|0>, ext_ctrl) -> NOP */
        /* Step 2: CCX(a, c=|0>, ext_ctrl) -> NOP */
        if (a_known_zero) {
            /* First cMAJ: carry=|0> AND temp[0]=|0> -> MCX has |0> control -> NOP */
            /* Entire cMAJ eliminated */
        } else {
            /* Step 3: MCX(c, [a, b, ext_ctrl]) -> AND-ancilla decomposition */
            /* 3a: CCX(and_anc, a, b) -- compute AND */
            ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, a, b);
            (*layer)++;
            /* 3b: CCX(c, and_anc, ext_ctrl) -- apply */
            ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, and_anc, ext_ctrl);
            (*layer)++;
            /* 3c: CCX(and_anc, a, b) -- uncompute AND */
            ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, a, b);
            (*layer)++;
        }
    } else {
        /* temp[i] will be conditionally initialized: fold CX-init */
        /* CX(c, ext_ctrl) to conditionally initialize temp */
        cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, ext_ctrl);
        (*layer)++;
        /* Steps 1-3: emit standard cMAJ with AND-ancilla (temp is entangled, cannot simplify) */
        emit_cMAJ(seq, layer, a, b, c, ext_ctrl, and_anc);
    }
}

/**
 * @brief Compute layer count for inline cCQ CDKM adder.
 *
 * Phase 74-03: MCX(3) replaced with 3 CCX via AND-ancilla.
 * - First cMAJ (i=0): if bit[0]==0, 0 layers; if bit[0]==1, 6 layers (CX-init + 5 cMAJ)
 * - Subsequent cMAJs (i>=1): if bit[i]==0, 3 layers (AND-ancilla decomp); if bit[i]==1, 6 layers
 * - cUMA chain: 5*bits layers (5 gates per cUMA with AND-ancilla)
 * - Cleanup: popcount(value) CX gates
 *
 * @param bits Number of bits
 * @param bin  Binary representation (MSB-first)
 * @return Total number of layers needed
 */
static int compute_cCQ_layer_count(int bits, int *bin) {
    int layers = 0;

    /* Forward cMAJ sweep */
    int bit0 = bin[bits - 1]; /* LSB */
    if (bit0 == 0) {
        /* First cMAJ: entirely eliminated */
        layers += 0;
    } else {
        /* First cMAJ: CX-init + 5 decomposed cMAJ gates = 6 layers */
        layers += 6;
    }
    for (int i = 1; i < bits; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 0) {
            /* Skip 2 CCX, emit 3 CCX (AND-ancilla decomposition of MCX(3)) */
            layers += 3;
        } else {
            /* CX-init + 5 decomposed cMAJ gates = 6 layers */
            layers += 6;
        }
    }

    /* Reverse cUMA sweep: 5 gates per decomposed cUMA = 5*bits */
    layers += 5 * bits;

    /* Cleanup: 1 CX per bit=1 position */
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1)
            layers++;
    }

    return layers;
}

// ============================================================================
// Public API
// ============================================================================

sequence_t *toffoli_QQ_add(int bits) {
    // OWNERSHIP: Returns cached sequence - DO NOT FREE
    //
    // Qubit layout for toffoli_QQ_add(bits):
    //   [0..bits-1]       = register a (target, modified in place: a += b)
    //   [bits..2*bits-1]   = register b (source, unchanged)
    //   [2*bits]           = ancilla carry (bits >= 2 only)

    // Bounds check
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Check cache
    if (precompiled_toffoli_QQ_add[bits] != NULL) {
        return precompiled_toffoli_QQ_add[bits];
    }

    // Use hardcoded sequences for widths 1-8
    if (bits <= TOFFOLI_HARDCODED_MAX_WIDTH) {
        const sequence_t *hardcoded = get_hardcoded_toffoli_QQ_add(bits);
        if (hardcoded != NULL) {
            // Copy into mutable memory so total_gate_count can be computed
            sequence_t *copy = copy_hardcoded_sequence(hardcoded);
            if (copy != NULL) {
                sequence_compute_total_gate_count(copy);
                precompiled_toffoli_QQ_add[bits] = copy;
                return copy;
            }
        }
    }

    // 1-bit special case: single CNOT, no ancilla
    if (bits == 1) {
        sequence_t *seq = alloc_sequence(1);
        if (seq == NULL)
            return NULL;

        // a[0] ^= b[0]: CNOT(target=0, control=1)
        cx(&seq->seq[0][seq->gates_per_layer[0]++], 0, 1);
        seq->used_layer = 1;
        sequence_compute_total_gate_count(seq);

        precompiled_toffoli_QQ_add[bits] = seq;
        return seq;
    }

    // General case (bits >= 2): CDKM ripple-carry adder
    // Forward sweep: n MAJ calls (3n layers)
    // Reverse sweep: n UMA calls (3n layers)
    // Total: 6n layers
    int num_layers = 6 * bits;

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL)
        return NULL;

    int layer = 0;
    int ancilla = 2 * bits; // ancilla carry qubit index

    // Forward MAJ sweep
    // First: MAJ(ancilla, b[0], a[0])
    emit_MAJ(seq, &layer, ancilla, bits + 0, 0);

    // Remaining: MAJ(a[i-1], b[i], a[i]) for i = 1..bits-1
    for (int i = 1; i < bits; i++) {
        emit_MAJ(seq, &layer, i - 1, bits + i, i);
    }

    // Reverse UMA sweep
    // First (innermost): UMA(a[bits-2], b[bits-1], a[bits-1])
    for (int i = bits - 1; i >= 1; i--) {
        emit_UMA(seq, &layer, i - 1, bits + i, i);
    }

    // Last: UMA(ancilla, b[0], a[0])
    emit_UMA(seq, &layer, ancilla, bits + 0, 0);

    seq->used_layer = layer;
    sequence_compute_total_gate_count(seq);

    // Cache and return
    precompiled_toffoli_QQ_add[bits] = seq;
    return seq;
}

sequence_t *toffoli_CQ_add(int bits, int64_t value) {
    // OWNERSHIP: Caller owns returned sequence, must free via toffoli_sequence_free()
    //
    // Qubit layout for toffoli_CQ_add(bits, value):
    //   [0..bits-1]       = temp register (initialized to classical value, cleaned to |0>)
    //   [bits..2*bits-1]  = self register (target, modified: self += value)
    //   [2*bits]          = carry ancilla (bits >= 2 only)
    //
    // Phase 73: Inline CQ generator with classical-bit gate simplification.
    // Instead of X-init + full QQ CDKM + X-cleanup, we emit simplified MAJ gates
    // directly based on known classical bit values, then standard UMA gates,
    // then X-cleanup for bit=1 positions.

    // Bounds check
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Use hardcoded increment sequence for value=1, widths 1-8
    if (value == 1 && bits <= TOFFOLI_HARDCODED_MAX_WIDTH) {
        const sequence_t *hardcoded = get_hardcoded_toffoli_CQ_inc(bits);
        if (hardcoded != NULL) {
            sequence_t *copy = copy_hardcoded_sequence(hardcoded);
            if (copy != NULL)
                sequence_compute_total_gate_count(copy);
            return copy;
        }
    }

    // Convert value to binary (MSB-first: bin[0]=MSB, bin[bits-1]=LSB)
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    // 1-bit special case (unchanged)
    if (bits == 1) {
        if (bin[0] == 1) {
            // X(target=0)
            sequence_t *seq = alloc_sequence(1);
            if (seq == NULL) {
                free(bin);
                return NULL;
            }
            x(&seq->seq[0][seq->gates_per_layer[0]++], 0);
            seq->used_layer = 1;
            sequence_compute_total_gate_count(seq);
            free(bin);
            return seq;
        } else {
            // Identity: 0-layer sequence
            sequence_t *seq = malloc(sizeof(sequence_t));
            if (seq == NULL) {
                free(bin);
                return NULL;
            }
            seq->num_layer = 0;
            seq->used_layer = 0;
            seq->total_gate_count = 0;
            seq->gates_per_layer = NULL;
            seq->seq = NULL;
            free(bin);
            return seq;
        }
    }

    // General case (bits >= 2): Inline CQ CDKM with classical-bit simplification
    //
    // Forward sweep: emit_CQ_MAJ for each position (simplified based on classical bits)
    // Reverse sweep: emit_UMA for each position (standard, no simplification)
    // Cleanup: X(temp[i]) for each bit=1 position

    int num_layers = compute_CQ_layer_count(bits, bin);

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    int layer = 0;
    int carry = 2 * bits; // carry ancilla qubit index

    // Forward CQ MAJ sweep with classical-bit simplification
    // First MAJ: a=carry (known |0>), b=self[0], c=temp[0]
    emit_CQ_MAJ(seq, &layer, carry, bits + 0, 0, bin[bits - 1], /* classical bit[0] (LSB) */
                1); /* a_known_zero = 1 (carry starts at |0>) */

    // Remaining MAJs: a=temp[i-1] (quantum after MAJ), b=self[i], c=temp[i]
    for (int i = 1; i < bits; i++) {
        emit_CQ_MAJ(seq, &layer, i - 1, bits + i, i, bin[bits - 1 - i], /* classical bit[i] */
                    0);                                                 /* a_known_zero = 0 */
    }

    // Reverse UMA sweep (standard, no simplification)
    for (int i = bits - 1; i >= 1; i--) {
        emit_UMA(seq, &layer, i - 1, bits + i, i);
    }
    emit_UMA(seq, &layer, carry, bits + 0, 0);

    // Cleanup: X(temp[i]) for each bit=1 position
    // CDKM preserves temp register, so temp[i] still holds classical_bit[i].
    // For bit=1 positions, temp[i]=|1> and needs X to restore to |0>.
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) {
            x(&seq->seq[layer][seq->gates_per_layer[layer]++], i);
            layer++;
        }
    }

    seq->used_layer = layer;
    sequence_compute_total_gate_count(seq);

#ifdef DEBUG
    /* Assertion: verify layer count matches expectation */
    if (layer != num_layers) {
        fprintf(stderr, "CQ_add layer mismatch: expected %d, got %d (bits=%d, value=%ld)\n",
                num_layers, layer, bits, (long)value);
    }
#endif

    free(bin);
    return seq;
}

sequence_t *toffoli_cQQ_add(int bits) {
    // OWNERSHIP: Returns cached sequence - DO NOT FREE
    //
    // Qubit layout for toffoli_cQQ_add(bits):
    //   [0..bits-1]       = register a (target, modified in place: a += b)
    //   [bits..2*bits-1]   = register b (source, unchanged)
    //   [2*bits]           = ancilla carry (bits >= 2 only)
    //   [2*bits+1]         = external control qubit
    //   [2*bits+2]         = AND-ancilla for MCX decomposition (bits >= 2 only)
    //
    // For bits == 1: no ancilla. [0]=a, [1]=b, [2]=ext_control.
    //   Single CCX(target=0, ctrl1=1, ctrl2=2). Total qubits: 3.
    // For bits >= 2: Total qubits: 2*bits + 3 (Phase 74-03: +1 for AND-ancilla).

    // Bounds check
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Check cache
    if (precompiled_toffoli_cQQ_add[bits] != NULL) {
        return precompiled_toffoli_cQQ_add[bits];
    }

    // Phase 74-05: Use MCX-decomposed hardcoded cQQ sequences for widths 1-8.
    // These contain only CCX (max 2 controls) via AND-ancilla decomposition.
    // Copy into mutable memory so total_gate_count can be computed.
    if (bits <= TOFFOLI_HARDCODED_MAX_WIDTH) {
        const sequence_t *hardcoded = get_hardcoded_toffoli_decomp_cQQ_add(bits);
        if (hardcoded != NULL) {
            sequence_t *copy = copy_hardcoded_sequence(hardcoded);
            if (copy != NULL) {
                sequence_compute_total_gate_count(copy);
                precompiled_toffoli_cQQ_add[bits] = copy;
                return copy;
            }
        }
    }

    // 1-bit special case: single CCX, no ancilla
    if (bits == 1) {
        sequence_t *seq = alloc_sequence(1);
        if (seq == NULL)
            return NULL;

        // controlled a[0] ^= b[0]: CCX(target=0, ctrl1=1, ctrl2=2)
        ccx(&seq->seq[0][seq->gates_per_layer[0]++], 0, 1, 2);
        seq->used_layer = 1;
        sequence_compute_total_gate_count(seq);

        precompiled_toffoli_cQQ_add[bits] = seq;
        return seq;
    }

    // General case (bits >= 2): controlled CDKM ripple-carry adder
    // Phase 74-03: MCX(3) decomposed via AND-ancilla.
    // Forward sweep: n decomposed cMAJ calls (5n layers)
    // Reverse sweep: n decomposed cUMA calls (5n layers)
    // Total: 10n layers
    int num_layers = 10 * bits;

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL)
        return NULL;

    int layer = 0;
    int ancilla = 2 * bits;      // ancilla carry qubit index
    int ext_ctrl = 2 * bits + 1; // external control qubit
    int and_anc = 2 * bits + 2;  // AND-ancilla for MCX decomposition

    // Forward cMAJ sweep
    // First: cMAJ(ancilla, b[0], a[0], ext_ctrl, and_anc)
    emit_cMAJ(seq, &layer, ancilla, bits + 0, 0, ext_ctrl, and_anc);

    // Remaining: cMAJ(a[i-1], b[i], a[i], ext_ctrl, and_anc) for i = 1..bits-1
    for (int i = 1; i < bits; i++) {
        emit_cMAJ(seq, &layer, i - 1, bits + i, i, ext_ctrl, and_anc);
    }

    // Reverse cUMA sweep
    for (int i = bits - 1; i >= 1; i--) {
        emit_cUMA(seq, &layer, i - 1, bits + i, i, ext_ctrl, and_anc);
    }

    // Last: cUMA(ancilla, b[0], a[0], ext_ctrl, and_anc)
    emit_cUMA(seq, &layer, ancilla, bits + 0, 0, ext_ctrl, and_anc);

    seq->used_layer = layer;
    sequence_compute_total_gate_count(seq);

    // Cache and return
    precompiled_toffoli_cQQ_add[bits] = seq;
    return seq;
}

sequence_t *toffoli_cCQ_add(int bits, int64_t value) {
    // OWNERSHIP: Caller owns returned sequence, must free via toffoli_sequence_free()
    //
    // Qubit layout for toffoli_cCQ_add(bits, value):
    //   [0..bits-1]       = temp register (controlled init to classical value, controlled cleanup)
    //   [bits..2*bits-1]  = self register (target, modified: self += value)
    //   [2*bits]          = carry ancilla (bits >= 2 only)
    //   [2*bits+1]        = external control qubit
    //   [2*bits+2]        = AND-ancilla for MCX decomposition (bits >= 2 only)
    //
    // Phase 73: Inline cCQ generator with classical-bit gate simplification.
    // Phase 74-03: MCX(3) decomposed via AND-ancilla.
    // For bit=0 positions, temp[i]=|0> unconditionally -> eliminate CCX gates.
    // For bit=1 positions, CX-init entangles temp[i] -> fold init, emit standard cMAJ.
    // NOT cached (value-dependent).

    // Bounds check
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Phase 74-03: Skip hardcoded cCQ sequences (they contain MCX gates).
    // Dynamic generator now produces MCX-free sequences via AND-ancilla decomposition.

    // Convert value to binary (MSB-first: bin[0]=MSB, bin[bits-1]=LSB)
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    // 1-bit special case (unchanged)
    if (bits == 1) {
        if (bin[0] == 1) {
            // CX(target=0, control=1) where [0]=self, [1]=ext_control
            sequence_t *seq = alloc_sequence(1);
            if (seq == NULL) {
                free(bin);
                return NULL;
            }
            cx(&seq->seq[0][seq->gates_per_layer[0]++], 0, 1);
            seq->used_layer = 1;
            sequence_compute_total_gate_count(seq);
            free(bin);
            return seq;
        } else {
            // Identity: 0-layer sequence
            sequence_t *seq = malloc(sizeof(sequence_t));
            if (seq == NULL) {
                free(bin);
                return NULL;
            }
            seq->num_layer = 0;
            seq->used_layer = 0;
            seq->total_gate_count = 0;
            seq->gates_per_layer = NULL;
            seq->seq = NULL;
            free(bin);
            return seq;
        }
    }

    // General case (bits >= 2): Inline cCQ CDKM with classical-bit simplification
    // Phase 74-03: MCX(3) decomposed via AND-ancilla.
    //
    // Forward sweep: emit_cCQ_MAJ for each position (simplified based on classical bits)
    // Reverse sweep: emit_cUMA for each position (with AND-ancilla decomposition)
    // Cleanup: CX(temp[i], ext_ctrl) for each bit=1 position

    int num_layers = compute_cCQ_layer_count(bits, bin);
    int ext_ctrl = 2 * bits + 1; // external control qubit
    int and_anc = 2 * bits + 2;  // AND-ancilla for MCX decomposition

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    int layer = 0;
    int carry = 2 * bits; // carry ancilla qubit index

    // Forward cCQ MAJ sweep with classical-bit simplification
    // First cMAJ: a=carry (known |0>), b=self[0], c=temp[0]
    emit_cCQ_MAJ(seq, &layer, carry, bits + 0, 0, bin[bits - 1], /* classical bit[0] (LSB) */
                 1,                                              /* a_known_zero = 1 */
                 ext_ctrl, and_anc);

    // Remaining cMAJs: a=temp[i-1] (quantum after cMAJ), b=self[i], c=temp[i]
    for (int i = 1; i < bits; i++) {
        emit_cCQ_MAJ(seq, &layer, i - 1, bits + i, i, bin[bits - 1 - i], /* classical bit[i] */
                     0,                                                  /* a_known_zero = 0 */
                     ext_ctrl, and_anc);
    }

    // Reverse cUMA sweep (with AND-ancilla decomposition)
    for (int i = bits - 1; i >= 1; i--) {
        emit_cUMA(seq, &layer, i - 1, bits + i, i, ext_ctrl, and_anc);
    }
    emit_cUMA(seq, &layer, carry, bits + 0, 0, ext_ctrl, and_anc);

    // Cleanup: CX(temp[i], ext_ctrl) for each bit=1 position
    // CDKM preserves temp register, so temp[i] is still entangled with ext_ctrl.
    // CX undoes the conditional initialization.
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) {
            cx(&seq->seq[layer][seq->gates_per_layer[layer]++], i, ext_ctrl);
            layer++;
        }
    }

    seq->used_layer = layer;
    sequence_compute_total_gate_count(seq);

#ifdef DEBUG
    /* Assertion: verify layer count matches expectation */
    if (layer != num_layers) {
        fprintf(stderr, "cCQ_add layer mismatch: expected %d, got %d (bits=%d, value=%ld)\n",
                num_layers, layer, bits, (long)value);
    }
#endif

    free(bin);
    return seq;
}
