/**
 * @file ToffoliAddition.c
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
 *
 * References:
 *   Cuccaro et al., "A new quantum ripple-carry addition circuit" (2004)
 *   arXiv:quant-ph/0410184
 */

#include "Integer.h"
#include "gate.h"
#include "toffoli_arithmetic_ops.h"
#include "toffoli_sequences.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

// ============================================================================
// Precompiled caches for Toffoli addition (separate from QFT cache)
// ============================================================================
static sequence_t *precompiled_toffoli_QQ_add[65] = {NULL};
static sequence_t *precompiled_toffoli_cQQ_add[65] = {NULL};
static sequence_t *precompiled_toffoli_QQ_add_bk[65] = {NULL};
static sequence_t *precompiled_toffoli_QQ_add_ks[65] = {NULL};
static sequence_t *precompiled_toffoli_cQQ_add_bk[65] = {NULL};
static sequence_t *precompiled_toffoli_cQQ_add_ks[65] = {NULL};

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
 * @brief Emit controlled MAJ (Majority) gate triplet.
 *
 * cMAJ(a, b, c, ext_ctrl):
 *   1. CCX(target=b, ctrl1=c, ctrl2=ext_ctrl)     -- controlled b ^= c
 *   2. CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)     -- controlled a ^= c
 *   3. MCX(target=c, controls=[a, b, ext_ctrl])   -- controlled c ^= (a AND b)
 *
 * Each operation conditioned on ext_ctrl being |1>.
 *
 * @param seq      Sequence to emit gates into
 * @param layer    Pointer to current layer index (incremented by 3)
 * @param a        Qubit index for 'a' (carry-in / previous carry)
 * @param b        Qubit index for 'b' (source bit)
 * @param c        Qubit index for 'c' (target bit, becomes carry-out)
 * @param ext_ctrl Qubit index for external control qubit
 */
static void emit_cMAJ(sequence_t *seq, int *layer, int a, int b, int c, int ext_ctrl) {
    // Step 1: CCX(target=b, ctrl1=c, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, c, ext_ctrl);
    (*layer)++;

    // Step 2: CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c, ext_ctrl);
    (*layer)++;

    // Step 3: MCX(target=c, controls=[a, b, ext_ctrl]) -- 3 controls
    {
        qubit_t ctrls[3] = {(qubit_t)a, (qubit_t)b, (qubit_t)ext_ctrl};
        mcx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, ctrls, 3);
    }
    (*layer)++;
}

/**
 * @brief Emit controlled UMA (UnMajority-and-Add) gate triplet.
 *
 * cUMA(a, b, c, ext_ctrl):
 *   1. MCX(target=c, controls=[a, b, ext_ctrl])   -- undoes cMAJ's MCX
 *   2. CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)     -- controlled restore a
 *   3. CCX(target=b, ctrl1=a, ctrl2=ext_ctrl)     -- controlled b = sum bit
 *
 * Each operation conditioned on ext_ctrl being |1>.
 *
 * @param seq      Sequence to emit gates into
 * @param layer    Pointer to current layer index (incremented by 3)
 * @param a        Qubit index for 'a'
 * @param b        Qubit index for 'b' (becomes sum bit)
 * @param c        Qubit index for 'c'
 * @param ext_ctrl Qubit index for external control qubit
 */
static void emit_cUMA(sequence_t *seq, int *layer, int a, int b, int c, int ext_ctrl) {
    // Step 1: MCX(target=c, controls=[a, b, ext_ctrl]) -- 3 controls
    {
        qubit_t ctrls[3] = {(qubit_t)a, (qubit_t)b, (qubit_t)ext_ctrl};
        mcx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, ctrls, 3);
    }
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
 * @brief Emit cCQ-simplified controlled MAJ gate sequence.
 *
 * For cCQ, temp initialization uses CX(temp[i], ext_ctrl), which entangles
 * temp[i] with ext_ctrl for bit=1 positions. Therefore:
 * - bit=0 positions: temp[i]=|0> unconditionally -> can simplify
 * - bit=1 positions: temp[i] is entangled -> fold CX-init, emit standard cMAJ
 *
 * @param seq             Sequence to emit gates into
 * @param layer           Pointer to current layer index
 * @param a               Qubit index for 'a' (carry-in / previous carry)
 * @param b               Qubit index for 'b' (source bit)
 * @param c               Qubit index for 'c' (temp bit)
 * @param classical_bit_c Known classical value of qubit c (0 or 1)
 * @param a_known_zero    1 if qubit a is known to be |0> (first cMAJ only)
 * @param ext_ctrl        External control qubit index
 */
static void emit_cCQ_MAJ(sequence_t *seq, int *layer, int a, int b, int c, int classical_bit_c,
                         int a_known_zero, int ext_ctrl) {
    if (classical_bit_c == 0) {
        /* temp[i] unconditionally |0>: skip CCX steps (one control is |0>) */
        /* Step 1: CCX(b, c=|0>, ext_ctrl) -> NOP */
        /* Step 2: CCX(a, c=|0>, ext_ctrl) -> NOP */
        if (a_known_zero) {
            /* First cMAJ: carry=|0> AND temp[0]=|0> -> MCX has |0> control -> NOP */
            /* Entire cMAJ eliminated: 2 CCX + 1 MCX = 21T saved */
        } else {
            /* Step 3: MCX(c, [a, b, ext_ctrl]) -> emit as-is (c is target) */
            qubit_t ctrls[3] = {(qubit_t)a, (qubit_t)b, (qubit_t)ext_ctrl};
            mcx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, ctrls, 3);
            (*layer)++;
        }
    } else {
        /* temp[i] will be conditionally initialized: fold CX-init */
        /* CX(c, ext_ctrl) to conditionally initialize temp */
        cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, ext_ctrl);
        (*layer)++;
        /* Steps 1-3: emit standard cMAJ (temp is entangled, cannot simplify) */
        emit_cMAJ(seq, layer, a, b, c, ext_ctrl);
    }
}

/**
 * @brief Compute layer count for inline cCQ CDKM adder.
 *
 * - First cMAJ (i=0): if bit[0]==0, 0 layers; if bit[0]==1, 4 layers (CX-init + 3 cMAJ)
 * - Subsequent cMAJs (i>=1): if bit[i]==0, 1 layer (MCX only); if bit[i]==1, 4 layers
 * - cUMA chain: 3*bits layers (unchanged)
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
        /* First cMAJ: CX-init + 3 standard cMAJ gates = 4 layers */
        layers += 4;
    }
    for (int i = 1; i < bits; i++) {
        int bit_i = bin[bits - 1 - i];
        if (bit_i == 0) {
            /* Skip 2 CCX, emit 1 MCX */
            layers += 1;
        } else {
            /* CX-init + 3 standard cMAJ gates = 4 layers */
            layers += 4;
        }
    }

    /* Reverse cUMA sweep: unchanged, 3 gates per cUMA = 3*bits */
    layers += 3 * bits;

    /* Cleanup: 1 CX per bit=1 position */
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1)
            layers++;
    }

    return layers;
}

// ============================================================================
// Sequence allocation helper
// ============================================================================

/**
 * @brief Allocate a sequence with given number of layers, 1 gate per layer.
 */
static sequence_t *alloc_sequence(int num_layers) {
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL)
        return NULL;

    seq->num_layer = num_layers;
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
        seq->seq[i] = calloc(1, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; j++) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    return seq;
}

/**
 * @brief Deep-copy a const (hardcoded) sequence into a fresh malloc'd sequence.
 *
 * CQ/cCQ callers free the returned sequence, so hardcoded static sequences
 * must be copied before returning. This copies large_control arrays for MCX gates.
 *
 * @param src Source sequence (typically static const from hardcoded file)
 * @return Fresh sequence_t* owned by caller, or NULL on allocation failure
 */
static sequence_t *copy_hardcoded_sequence(const sequence_t *src) {
    if (src == NULL)
        return NULL;

    int n = (int)src->num_layer;
    sequence_t *dst = malloc(sizeof(sequence_t));
    if (dst == NULL)
        return NULL;

    dst->num_layer = src->num_layer;
    dst->used_layer = src->used_layer;
    dst->gates_per_layer = calloc(n, sizeof(num_t));
    dst->seq = calloc(n, sizeof(gate_t *));
    if (dst->gates_per_layer == NULL || dst->seq == NULL) {
        free(dst->gates_per_layer);
        free(dst->seq);
        free(dst);
        return NULL;
    }

    for (int i = 0; i < n; i++) {
        dst->gates_per_layer[i] = src->gates_per_layer[i];
        int gcount = (int)src->gates_per_layer[i];
        if (gcount <= 0)
            gcount = 1; /* allocate at least 1 slot */
        dst->seq[i] = calloc(gcount, sizeof(gate_t));
        if (dst->seq[i] == NULL) {
            for (int j = 0; j < i; j++) {
                if (dst->seq[j] != NULL) {
                    for (int g = 0; g < (int)dst->gates_per_layer[j]; g++) {
                        if (dst->seq[j][g].large_control != NULL)
                            free(dst->seq[j][g].large_control);
                    }
                    free(dst->seq[j]);
                }
            }
            free(dst->seq);
            free(dst->gates_per_layer);
            free(dst);
            return NULL;
        }
        for (int g = 0; g < (int)src->gates_per_layer[i]; g++) {
            dst->seq[i][g] = src->seq[i][g];
            dst->seq[i][g].large_control = NULL;
            if (src->seq[i][g].NumControls > 2 && src->seq[i][g].large_control != NULL) {
                dst->seq[i][g].large_control = malloc(src->seq[i][g].NumControls * sizeof(qubit_t));
                if (dst->seq[i][g].large_control != NULL) {
                    for (num_t c = 0; c < src->seq[i][g].NumControls; c++)
                        dst->seq[i][g].large_control[c] = src->seq[i][g].large_control[c];
                }
            }
        }
    }

    return dst;
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
            // SAFETY: Const cast is safe -- static sequences have program lifetime
            precompiled_toffoli_QQ_add[bits] = (sequence_t *)hardcoded;
            return (sequence_t *)hardcoded;
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
            return copy_hardcoded_sequence(hardcoded);
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
    //
    // For bits == 1: no ancilla. [0]=a, [1]=b, [2]=ext_control.
    //   Single CCX(target=0, ctrl1=1, ctrl2=2). Total qubits: 3.

    // Bounds check
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Check cache
    if (precompiled_toffoli_cQQ_add[bits] != NULL) {
        return precompiled_toffoli_cQQ_add[bits];
    }

    // Use hardcoded sequences for widths 1-8
    if (bits <= TOFFOLI_HARDCODED_MAX_WIDTH) {
        const sequence_t *hardcoded = get_hardcoded_toffoli_cQQ_add(bits);
        if (hardcoded != NULL) {
            precompiled_toffoli_cQQ_add[bits] = (sequence_t *)hardcoded;
            return (sequence_t *)hardcoded;
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

        precompiled_toffoli_cQQ_add[bits] = seq;
        return seq;
    }

    // General case (bits >= 2): controlled CDKM ripple-carry adder
    // Forward sweep: n cMAJ calls (3n layers)
    // Reverse sweep: n cUMA calls (3n layers)
    // Total: 6n layers
    int num_layers = 6 * bits;

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL)
        return NULL;

    int layer = 0;
    int ancilla = 2 * bits;      // ancilla carry qubit index
    int ext_ctrl = 2 * bits + 1; // external control qubit

    // Forward cMAJ sweep
    // First: cMAJ(ancilla, b[0], a[0], ext_ctrl)
    emit_cMAJ(seq, &layer, ancilla, bits + 0, 0, ext_ctrl);

    // Remaining: cMAJ(a[i-1], b[i], a[i], ext_ctrl) for i = 1..bits-1
    for (int i = 1; i < bits; i++) {
        emit_cMAJ(seq, &layer, i - 1, bits + i, i, ext_ctrl);
    }

    // Reverse cUMA sweep
    for (int i = bits - 1; i >= 1; i--) {
        emit_cUMA(seq, &layer, i - 1, bits + i, i, ext_ctrl);
    }

    // Last: cUMA(ancilla, b[0], a[0], ext_ctrl)
    emit_cUMA(seq, &layer, ancilla, bits + 0, 0, ext_ctrl);

    seq->used_layer = layer;

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
    //
    // Phase 73: Inline cCQ generator with classical-bit gate simplification.
    // For bit=0 positions, temp[i]=|0> unconditionally -> eliminate CCX gates.
    // For bit=1 positions, CX-init entangles temp[i] -> fold init, emit standard cMAJ.
    // NOT cached (value-dependent).

    // Bounds check
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Use hardcoded controlled increment sequence for value=1, widths 1-8
    if (value == 1 && bits <= TOFFOLI_HARDCODED_MAX_WIDTH) {
        const sequence_t *hardcoded = get_hardcoded_toffoli_cCQ_inc(bits);
        if (hardcoded != NULL) {
            return copy_hardcoded_sequence(hardcoded);
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
            // CX(target=0, control=1) where [0]=self, [1]=ext_control
            sequence_t *seq = alloc_sequence(1);
            if (seq == NULL) {
                free(bin);
                return NULL;
            }
            cx(&seq->seq[0][seq->gates_per_layer[0]++], 0, 1);
            seq->used_layer = 1;
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
            seq->gates_per_layer = NULL;
            seq->seq = NULL;
            free(bin);
            return seq;
        }
    }

    // General case (bits >= 2): Inline cCQ CDKM with classical-bit simplification
    //
    // Forward sweep: emit_cCQ_MAJ for each position (simplified based on classical bits)
    // Reverse sweep: emit_cUMA for each position (standard, no simplification)
    // Cleanup: CX(temp[i], ext_ctrl) for each bit=1 position

    int num_layers = compute_cCQ_layer_count(bits, bin);
    int ext_ctrl = 2 * bits + 1; // external control qubit

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
                 ext_ctrl);

    // Remaining cMAJs: a=temp[i-1] (quantum after cMAJ), b=self[i], c=temp[i]
    for (int i = 1; i < bits; i++) {
        emit_cCQ_MAJ(seq, &layer, i - 1, bits + i, i, bin[bits - 1 - i], /* classical bit[i] */
                     0,                                                  /* a_known_zero = 0 */
                     ext_ctrl);
    }

    // Reverse cUMA sweep (standard, no simplification)
    for (int i = bits - 1; i >= 1; i--) {
        emit_cUMA(seq, &layer, i - 1, bits + i, i, ext_ctrl);
    }
    emit_cUMA(seq, &layer, carry, bits + 0, 0, ext_ctrl);

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

// ============================================================================
// Brent-Kung Carry Look-Ahead Adder (Phase 71, Plan 05)
// ============================================================================

/**
 * @brief BK tree merge descriptor: one prefix-tree operation.
 */
typedef struct {
    int pos;     /* position being updated (target of group generate) */
    int partner; /* position being merged from (source) */
    int level;   /* tree level (0-based) */
    int is_down; /* 0 = up-sweep, 1 = down-sweep/tail */
} bk_merge_t;

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
static int bk_compute_merges(int n_carries, bk_merge_t *merges, int max_merges) {
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
                    leftmost[i] = 0;
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
 * After operation: a[] unchanged, b[] = a+b, g[] = |0>,
 * tree ancilla = |0>, c[] = carry values (NOT uncomputed).
 * Circuit is forward-only; subtraction uses RCA fallback at dispatch level.
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
     *
     * Order: A -> B -> C -> D -> E -> F
     * Note: carry-copy ancilla c[] are NOT uncomputed (remain dirty).
     * Subtraction handled at dispatch level by falling through to RCA.
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

    /* Cache and return */
    precompiled_toffoli_QQ_add_bk[bits] = seq;
    return seq;
}

// ============================================================================
// Kogge-Stone Carry Look-Ahead Adder (Phase 71, Plan 02)
// ============================================================================

/**
 * @brief Compute ancilla count for Kogge-Stone prefix tree.
 *
 * For n-bit addition, the KS tree needs:
 *   - (n-1) ancilla for initial generate values g[0..n-2]
 *   - Additional ancilla for propagate products at each tree level
 *
 * At each level k (0 to ceil(log2(n))-1), each merge position needs
 * a propagate product ancilla. The exact count depends on n.
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
     * Each merge needs 1 propagate product ancilla.
     * At level k: number of merges = n - 2^k (positions 2^k through n-1).
     * But we only count for positions with carry bits (0..n-2). */
    for (int k = 0; k < levels; k++) {
        int stride = 1 << k;
        for (int i = bits - 2; i >= stride; i--) {
            count++; /* one propagate product ancilla per merge */
        }
    }

    return count;
}

/**
 * @brief Kogge-Stone CLA QQ adder: b += a (in-place on b-register).
 *
 * STUB: Returns NULL to fall through to RCA (CDKM) adder.
 *
 * The Kogge-Stone parallel prefix CLA has the same fundamental ancilla
 * uncomputation challenge as Brent-Kung: after computing carries via the
 * prefix tree and extracting sums, the tree cannot be reversed because
 * the propagate controls (stored in b) have been modified by the sum
 * computation. The Kogge-Stone variant uses more ancilla (~n*log(n))
 * but fewer depth levels than Brent-Kung. However, the chicken-and-egg
 * uncomputation problem is identical.
 *
 * When this function returns NULL, the dispatch in hot_path_add.c
 * silently falls through to the proven CDKM RCA adder.
 *
 * Qubit layout (for future implementation):
 *   [0..bits-1]            = register a (source, preserved)
 *   [bits..2*bits-1]       = register b (target, gets a+b)
 *   [2*bits..]             = ks_ancilla_count(bits) ancilla qubits
 *   Total: 2*bits + ks_ancilla_count(bits)
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
// CQ CLA Adders (Phase 71, Plan 02)
// ============================================================================

/**
 * @brief Brent-Kung CLA CQ adder: self += classical_value.
 *
 * Phase 73: Inline BK CLA CQ generator with classical-bit gate simplification.
 * Applies simplification to Phase A and Phase E (generate/propagate init/uncompute):
 * - If temp[i]=0: CCX(g[i], temp[i], self[i]) -> NOP, CX(self[i], temp[i]) -> NOP
 * - If temp[i]=1: CCX -> CX(g[i], self[i]), CX -> X(self[i]); with X-init/cleanup
 * Phases B, C, D, F: copied from cached QQ BK sequence unchanged.
 *
 * Qubit layout:
 *   [0..bits-1]       = temp register (initialized to classical value, cleaned to |0>)
 *   [bits..2*bits-1]  = self register (target, gets self + value)
 *   [2*bits..end]     = CLA ancilla (bk_cla_ancilla_count(bits))
 *   Total: 2*bits + bk_cla_ancilla_count(bits)
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

    /* Compute layer count for CQ BK:
     * Phase A (simplified): for each of n-1 generate positions,
     *   bit=0: 0 CCX + 0 CX = 0 layers; bit=1: X-init + CX(g,self) + X(self) = 3 layers
     *   Plus for each of n propagate positions:
     *   bit=0: 0 CX = 0 layers; bit=1: already counted X(self) in generate block
     * Actually, simpler: Phase A has (n-1) CCX + n CX in the original.
     * Simplified Phase A:
     *   For generates (i=0..n-2):
     *     bit[i]=0: skip CCX (1 saved)
     *     bit[i]=1: X(temp[i]) + CX(g[i], self[i]) = 2 layers (instead of 1 CCX)
     *   For propagates (i=0..n-1):
     *     bit[i]=0: skip CX (1 saved)
     *     bit[i]=1: X(self[i]) = 1 layer (instead of 1 CX)
     *   Phase E (same as A reversed, same simplification)
     * Phases B, C, D, F: same as QQ BK
     * Cleanup: x_count X gates
     */
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
    /* Phase B starts at layer (n-1) + n = 2n-1 in the QQ BK sequence.
     * Phase B+C+D ends at the start of Phase E in QQ BK.
     * In QQ BK: Phase A = 2n-1 layers, Phase E starts at 2n-1 + 4*num_merges + (n-1) layers.
     *
     * We need to copy layers from QQ BK starting at Phase B through Phase D end.
     * Phase B: layers [2n-1 .. 2n-1+2*num_merges-1]
     * Phase C: layers [2n-1+2*num_merges .. 2n-1+2*num_merges+n-2]
     * Phase D: layers [2n-1+2*num_merges+n-1 .. 2n-1+4*num_merges+n-2]
     */
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
    /* Original Phase F: CX(self[i], temp[i]) for i=0..n-1, CX(self[i], c[i-1]) for i=1..n-1.
     * After Phase E, temp[i]=|0>, so CX(self[i], temp[i]=|0>) is NOP.
     * But we need self[i] ^= classical_bit[i] for the sum. So for bit=1: X(self[i]).
     * CX(self[i], c[i-1]) is unchanged (carry addition). */
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

#ifdef DEBUG
    if (layer != num_layers) {
        fprintf(stderr, "CQ_add_bk layer mismatch: expected %d, got %d (bits=%d)\n", num_layers,
                layer, bits);
    }
#endif

    free(bin);
    return seq;
}

/**
 * @brief Kogge-Stone CLA CQ adder: self += classical_value.
 *
 * STUB: Returns NULL to fall through to RCA (CDKM) CQ adder.
 *
 * Would use the temp-register approach (same as toffoli_CQ_add):
 * 1. X-init temp register with classical value bits
 * 2. Run toffoli_QQ_add_ks() on temp + self registers
 * 3. X-cleanup temp register
 *
 * Since toffoli_QQ_add_ks() returns NULL (ancilla uncomputation
 * impossibility), this function also returns NULL. The CQ dispatch
 * in hot_path_add.c silently falls through to the proven CDKM
 * RCA CQ adder (toffoli_CQ_add).
 *
 * Qubit layout (for future implementation):
 *   [0..bits-1]       = temp register (initialized to classical value, cleaned to |0>)
 *   [bits..2*bits-1]  = self register (target, gets self + value)
 *   [2*bits..]        = CLA ancilla (ks_ancilla_count(bits) for KS)
 *   Total: 2*bits + ks_ancilla_count(bits)
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 * NOT cached (value-dependent).
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
// Controlled CLA Adders (Phase 71, Plan 03)
// ============================================================================

/**
 * @brief Controlled Brent-Kung CLA QQ adder: b += a, controlled by ext_ctrl.
 *
 * Every gate in the uncontrolled QQ BK sequence gets an additional control
 * qubit (ext_ctrl):
 *   - X (0 controls) -> CX(target, ext_ctrl)
 *   - CX (1 control) -> CCX(target, control, ext_ctrl)
 *   - CCX (2 controls) -> MCX(target, [ctrl1, ctrl2, ext_ctrl])
 *
 * Qubit layout:
 *   [0..n-1]              = register a (source, preserved)
 *   [n..2n-1]             = register b (target, gets a+b)
 *   [2n..2n+anc-1]        = CLA ancilla (same count as uncontrolled BK)
 *   [2n+anc]              = ext_ctrl (external control qubit)
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

    /* Allocate new sequence with same layer count */
    sequence_t *seq = alloc_sequence((int)seq_qq->num_layer);
    if (seq == NULL)
        return NULL;

    int layer = 0;

    /* Copy each gate from QQ sequence, injecting ext_ctrl */
    for (num_t l = 0; l < seq_qq->num_layer; l++) {
        for (num_t g = 0; g < seq_qq->gates_per_layer[l]; g++) {
            gate_t *src = &seq_qq->seq[l][g];

            if (src->NumControls == 0) {
                /* X -> CX with ext_ctrl */
                cx(&seq->seq[layer][seq->gates_per_layer[layer]++], src->Target, (qubit_t)ext_ctrl);
            } else if (src->NumControls == 1) {
                /* CX -> CCX with [original_ctrl, ext_ctrl] */
                ccx(&seq->seq[layer][seq->gates_per_layer[layer]++], src->Target, src->Control[0],
                    (qubit_t)ext_ctrl);
            } else if (src->NumControls == 2) {
                /* CCX -> MCX with [ctrl1, ctrl2, ext_ctrl] */
                qubit_t ctrls[3] = {src->Control[0], src->Control[1], (qubit_t)ext_ctrl};
                mcx(&seq->seq[layer][seq->gates_per_layer[layer]++], src->Target, ctrls, 3);
            } else {
                /* MCX with n controls -> MCX with n+1 controls */
                num_t new_count = src->NumControls + 1;
                qubit_t *ctrls = malloc(new_count * sizeof(qubit_t));
                if (ctrls != NULL) {
                    if (src->large_control != NULL) {
                        for (num_t c = 0; c < src->NumControls; c++)
                            ctrls[c] = src->large_control[c];
                    } else {
                        for (num_t c = 0; c < src->NumControls && c < 2; c++)
                            ctrls[c] = src->Control[c];
                    }
                    ctrls[src->NumControls] = (qubit_t)ext_ctrl;
                    mcx(&seq->seq[layer][seq->gates_per_layer[layer]++], src->Target, ctrls,
                        new_count);
                    free(ctrls);
                }
            }
        }
        layer++;
    }

    seq->used_layer = layer;

    /* Cache and return */
    precompiled_toffoli_cQQ_add_bk[bits] = seq;
    return seq;
}

/**
 * @brief Controlled Kogge-Stone CLA QQ adder: b += a, controlled by ext_ctrl.
 *
 * STUB: Returns NULL to fall through to controlled RCA (CDKM) adder.
 *
 * The controlled variant inherits the same fundamental ancilla uncomputation
 * impossibility as the uncontrolled toffoli_QQ_add_ks(). The Kogge-Stone
 * tree uses more ancilla (~n*log(n)) but fewer depth levels than Brent-Kung.
 * However, the chicken-and-egg uncomputation problem is identical, and
 * adding a control qubit does not resolve it.
 *
 * When this function returns NULL, the dispatch in hot_path_add.c
 * silently falls through to the proven controlled CDKM RCA adder
 * (toffoli_cQQ_add).
 *
 * Qubit layout (for future implementation):
 *   [0..bits-1]            = register a (source, preserved)
 *   [bits..2*bits-1]       = register b (target, gets a+b)
 *   [2*bits..]             = ks_ancilla_count(bits) ancilla qubits
 *   [2*bits+ks_anc]        = external control qubit
 *   Total: 2*bits + ks_ancilla_count(bits) + 1 qubits
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 *
 * @param bits Width of operands (2-64; returns NULL for bits < 2)
 * @return NULL (controlled CLA not yet implemented; falls through to RCA)
 */
sequence_t *toffoli_cQQ_add_ks(int bits) {
    (void)bits; // suppress unused parameter warning
    // Controlled KS CLA not implemented -- fall through to controlled RCA
    return NULL;
}

/**
 * @brief Controlled Brent-Kung CLA CQ adder: self += classical_value, controlled.
 *
 * Phase 73: Inline BK CLA cCQ generator with classical-bit gate simplification.
 * Same approach as CQ BK but using controlled variant:
 * - Phase A: for bit=0, skip CCX+CX; for bit=1, fold CX-init + emit controlled gates
 * - Phases B-D: copy from cached cQQ BK sequence unchanged
 * - Phase E: same simplifications as Phase A
 * - Phase F: unchanged
 * - Cleanup: CX(temp[i], ext_ctrl) for each bit=1 position
 *
 * Qubit layout:
 *   [0..bits-1]           = temp register (controlled init to classical value)
 *   [bits..2*bits-1]      = self register (target, gets self + value)
 *   [2*bits..end-1]       = CLA ancilla (bk_cla_ancilla_count(bits))
 *   [end]                 = external control qubit
 *   Total: 2*bits + bk_cla_ancilla_count(bits) + 1
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 * NOT cached (value-dependent).
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return Fresh sequence, or NULL for bits < 2 or allocation failure
 */
sequence_t *toffoli_cCQ_add_bk(int bits, int64_t value) {
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

    /* Compute layer count for cCQ BK:
     * Phase A (simplified): same structure as CQ BK but controlled
     *   For generates (i=0..n-2):
     *     bit[i]=0: skip CCX (was MCX in controlled form) -> 0 layers
     *     bit[i]=1: CX-init(temp[i], ext_ctrl) + CCX(g[i], self[i], ext_ctrl) = 2 layers
     *   For propagates (i=0..n-1):
     *     bit[i]=0: skip CX (was CCX in controlled form) -> 0 layers
     *     bit[i]=1: CX(self[i], ext_ctrl) = 1 layer (controlled X)
     * Phase E: same as Phase A
     * Phases B, C, D, F: same as cQQ BK
     * Cleanup: x_count CX gates
     */
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

    /* Phase F (simplified): CX(self[i], ext_ctrl) for bit[i]=1 + CCX(self[i], c[i-1], ext_ctrl) for
     * i>=1 */
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
            /* temp[i]=|1> when ext_ctrl=|1>: CCX(self[i], temp[i]=|1>, ext_ctrl) -> CX(self[i],
             * ext_ctrl) */
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
    /* Original Phase F in cQQ: CCX(self[i], temp[i], ext_ctrl) for i=0..n-1,
     *                          CCX(self[i], c[i-1], ext_ctrl) for i=1..n-1.
     * After Phase E, temp[i]=|0>, so CCX(self[i], temp[i]=|0>, ext_ctrl) is NOP.
     * But we need controlled self[i] ^= classical_bit[i].
     * For bit=1: CX(self[i], ext_ctrl) (controlled X on self[i]).
     * CCX(self[i], c[i-1], ext_ctrl) is unchanged (carry addition). */
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

#ifdef DEBUG
    if (layer != num_layers) {
        fprintf(stderr, "cCQ_add_bk layer mismatch: expected %d, got %d (bits=%d)\n", num_layers,
                layer, bits);
    }
#endif

    free(bin);
    return seq;
}

/**
 * @brief Controlled Kogge-Stone CLA CQ adder: self += classical_value, controlled.
 *
 * STUB: Returns NULL to fall through to controlled RCA (CDKM) CQ adder.
 *
 * Would use the controlled temp-register approach (same as toffoli_cCQ_add):
 * 1. CX-init temp register with classical value bits (controlled by ext_ctrl)
 * 2. Run toffoli_cQQ_add_ks() on temp + self registers
 * 3. CX-cleanup temp register (controlled by ext_ctrl)
 *
 * Since toffoli_cQQ_add_ks() returns NULL (ancilla uncomputation
 * impossibility), this function also returns NULL. The CQ dispatch
 * in hot_path_add.c silently falls through to the proven controlled
 * CDKM RCA CQ adder (toffoli_cCQ_add).
 *
 * Qubit layout (for future implementation):
 *   [0..bits-1]       = temp register (controlled init to classical value)
 *   [bits..2*bits-1]  = self register (target, gets self + value)
 *   [2*bits..]        = CLA ancilla (ks_ancilla_count(bits) for KS)
 *   [2*bits+ks_anc]   = external control qubit
 *   Total: 2*bits + ks_ancilla_count(bits) + 1 qubits
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 * NOT cached (value-dependent).
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

void toffoli_sequence_free(sequence_t *seq) {
    if (seq == NULL)
        return;

    if (seq->seq != NULL) {
        for (num_t i = 0; i < seq->num_layer; i++) {
            // Free large_control arrays for MCX gates with 3+ controls
            if (seq->gates_per_layer != NULL) {
                for (num_t g = 0; g < seq->gates_per_layer[i]; g++) {
                    if (seq->seq[i][g].NumControls > 2 && seq->seq[i][g].large_control != NULL) {
                        free(seq->seq[i][g].large_control);
                    }
                }
            }
            free(seq->seq[i]);
        }
        free(seq->seq);
    }

    free(seq->gates_per_layer);
    free(seq);
}
