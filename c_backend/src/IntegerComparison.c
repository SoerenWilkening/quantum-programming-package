//
// Created by Sören Wilkening on 09.11.24.
//
// Phase 74-03: MCX gates decomposed via AND-ancilla in equality comparisons.

#include "Integer.h"
#include "arithmetic_ops.h"
#include "circuit.h"
#include "comparison_ops.h"
#include "definition.h"
#include "execution.h"
#include "gate.h"
#include "toffoli_arithmetic_ops.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

// ======================================================
// AND-ancilla MCX decomposition helpers (Phase 74-03)
// ======================================================

/**
 * @brief Compute number of CCX layers for recursive MCX decomposition.
 *
 * @param num_controls Number of controls (>= 2)
 * @return Number of CCX layers needed
 */
static int mcx_decomp_layers(int num_controls) {
    if (num_controls <= 2)
        return 1;
    if (num_controls == 3)
        return 3;
    return 2 + mcx_decomp_layers(num_controls - 1);
}

/**
 * @brief Emit recursive AND-ancilla MCX decomposition into a comparison sequence.
 *
 * @param seq         Sequence to emit into
 * @param layer       Pointer to current layer index
 * @param target      Target qubit
 * @param controls    Array of control qubits
 * @param num_controls Number of controls (>= 2)
 * @param anc_start   First available AND-ancilla qubit index
 */
static void emit_mcx_decomp_seq(sequence_t *seq, int *layer, int target, const qubit_t *controls,
                                int num_controls, int anc_start) {
    if (num_controls == 2) {
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], target, controls[0], controls[1]);
        (*layer)++;
        seq->used_layer++;
    } else if (num_controls == 3) {
        int and_anc = anc_start;
        /* CCX(and_anc, c1, c2) -- compute AND */
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, controls[0], controls[1]);
        (*layer)++;
        seq->used_layer++;
        /* CCX(target, and_anc, c3) -- apply */
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], target, (qubit_t)and_anc,
            controls[2]);
        (*layer)++;
        seq->used_layer++;
        /* CCX(and_anc, c1, c2) -- uncompute AND */
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, controls[0], controls[1]);
        (*layer)++;
        seq->used_layer++;
    } else {
        int and_anc = anc_start;
        /* Compute AND of first 2 controls */
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, controls[0], controls[1]);
        (*layer)++;
        seq->used_layer++;

        /* Build reduced control list */
        qubit_t reduced[128];
        reduced[0] = (qubit_t)and_anc;
        for (int i = 2; i < num_controls; i++)
            reduced[i - 1] = controls[i];

        /* Recurse */
        emit_mcx_decomp_seq(seq, layer, target, reduced, num_controls - 1, anc_start + 1);

        /* Uncompute AND */
        ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], and_anc, controls[0], controls[1]);
        (*layer)++;
        seq->used_layer++;
    }
}

// ======================================================
// Sequence Copy Helpers (Phase 11.5)
// ======================================================

/**
 * @brief Copy layers from a source sequence into a destination sequence,
 *        remapping all qubit indices through a mapping table and optionally
 *        adding an extra control qubit to every gate.
 *
 * @param dst          Destination sequence (layers pre-allocated)
 * @param dst_layer    Pointer to current destination layer index (updated)
 * @param src          Source sequence to copy from
 * @param qubit_map    Mapping table: abstract index i -> qubit_map[i].
 *                     If NULL, indices are used as-is (identity mapping).
 * @param extra_ctrl   If >= 0, add this as an additional control to every gate.
 *                     Use -1 to skip.
 */
static void copy_remap_layers(sequence_t *dst, int *dst_layer, const sequence_t *src,
                              const int *qubit_map, int extra_ctrl) {
    for (int l = 0; l < (int)src->used_layer; l++) {
        int dl = *dst_layer;
        for (int g = 0; g < (int)src->gates_per_layer[l]; g++) {
            gate_t *dg = &dst->seq[dl][dst->gates_per_layer[dl]];
            memcpy(dg, &src->seq[l][g], sizeof(gate_t));
            if (qubit_map != NULL) {
                dg->Target = (qubit_t)qubit_map[dg->Target];
            }
            for (int c = 0; c < (int)dg->NumControls && c < MAXCONTROLS; c++) {
                if (qubit_map != NULL) {
                    dg->Control[c] = (qubit_t)qubit_map[dg->Control[c]];
                }
            }
            if (extra_ctrl >= 0) {
                if (dg->NumControls < MAXCONTROLS) {
                    dg->Control[dg->NumControls] = (qubit_t)extra_ctrl;
                    dg->NumControls++;
                } /* else: control overflow -- gate already at max controls */
            }
            dst->gates_per_layer[dl]++;
        }
        (*dst_layer)++;
        dst->used_layer++;
    }
}

/**
 * @brief Build a simple offset mapping table: map[i] = i + offset.
 */
static void build_offset_map(int *map, int count, int offset) {
    for (int i = 0; i < count; i++) {
        map[i] = i + offset;
    }
}

/**
 * @brief Copy layers from a source sequence in inverse order (adjoint),
 *        remapping qubit indices and optionally adding a control.
 *
 * Layers are iterated in reverse. Non-self-inverse gates (rotations)
 * have their GateValue negated.
 */
static void copy_remap_layers_inverse(sequence_t *dst, int *dst_layer, const sequence_t *src,
                                      const int *qubit_map, int extra_ctrl) {
    for (int l = (int)src->used_layer - 1; l >= 0; l--) {
        int dl = *dst_layer;
        for (int g = (int)src->gates_per_layer[l] - 1; g >= 0; g--) {
            gate_t *dg = &dst->seq[dl][dst->gates_per_layer[dl]];
            memcpy(dg, &src->seq[l][g], sizeof(gate_t));
            if (qubit_map != NULL) {
                dg->Target = (qubit_t)qubit_map[dg->Target];
            }
            for (int c = 0; c < (int)dg->NumControls && c < MAXCONTROLS; c++) {
                if (qubit_map != NULL) {
                    dg->Control[c] = (qubit_t)qubit_map[dg->Control[c]];
                }
            }
            switch (dg->Gate) {
            case X:
            case Y:
            case Z:
            case H:
            case M:
                break;
            default:
                dg->GateValue = -dg->GateValue;
                break;
            }
            if (extra_ctrl >= 0) {
                if (dg->NumControls < MAXCONTROLS) {
                    dg->Control[dg->NumControls] = (qubit_t)extra_ctrl;
                    dg->NumControls++;
                } /* else: control overflow -- gate already at max controls */
            }
            dst->gates_per_layer[dl]++;
        }
        (*dst_layer)++;
        dst->used_layer++;
    }
}

// ======================================================
// Width-Parameterized Comparison Operations (Phase 7)
// ======================================================

// Stub implementations for Phase 7
// Full C-level circuits will be implemented in Phase 8
// Phase 7 uses Python-level comparison via existing primitives

sequence_t *QQ_equal(int bits) {
    // Stub: Returns NULL, Python uses XOR pattern directly
    // Phase 8 will implement optimized C-level circuit
    (void)bits; // Suppress unused warning
    return NULL;
}

sequence_t *QQ_less_than(int bits) {
    // QFT-mode QQ less-than: result = (A < B)
    // Borrow-ancilla pattern via (n+1)-bit addition:
    //   1. A -= B (mod 2^n)
    //   2. [A, borrow] += [B, zero_ext]  ((n+1)-bit add detects wrap)
    //   3. CX(borrow -> result)
    //   4. Undo step 2
    //   5. A += B (restore)
    //
    // Qubit layout:
    //   [0]            = result qbool
    //   [1..bits]      = A
    //   [bits+1..2*bits] = B
    //   [2*bits+1]     = borrow ancilla
    //   [2*bits+2]     = zero extension
    //
    // Total abstract qubits: 2*bits + 3

    if (bits < 1 || bits > 63) {
        return NULL;
    }

    int comp_width = bits + 1;

    /* Get cached QQ_add sequences (DO NOT FREE) */
    sequence_t *add_n = QQ_add(bits);
    sequence_t *add_ext = QQ_add(comp_width);
    if (add_n == NULL || add_ext == NULL) {
        return NULL;
    }

    /* Count total layers:
     * step1 (sub = inverse add_n): add_n->used_layer
     * step2 (extended add): add_ext->used_layer
     * step3 (CX): 1
     * step4 (inverse extended add): add_ext->used_layer
     * step5 (add = forward add_n): add_n->used_layer
     */
    int total_layers = 2 * (int)add_n->used_layer + 2 * (int)add_ext->used_layer + 1;
    int max_gpg = 2 * bits + 4; /* generous max gates per layer */

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL)
        return NULL;
    seq->num_layer = total_layers;
    seq->used_layer = 0;
    seq->total_gate_count = 0;
    seq->gates_per_layer = calloc(total_layers, sizeof(num_t));
    seq->seq = calloc(total_layers, sizeof(gate_t *));
    if (seq->gates_per_layer == NULL || seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq->seq);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < total_layers; i++) {
        seq->seq[i] = calloc(max_gpg, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; j++)
                free(seq->seq[j]);
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    /* Build mapping for QQ_add(bits): abstract [0..2*bits-1]
     *   target [0..bits-1] -> combined [1..bits] (A)
     *   other  [bits..2*bits-1] -> combined [bits+1..2*bits] (B)
     */
    int map_n[256];
    for (int i = 0; i < bits; i++)
        map_n[i] = i + 1; /* A */
    for (int i = 0; i < bits; i++)
        map_n[bits + i] = bits + 1 + i; /* B */

    /* Build mapping for QQ_add(comp_width): abstract [0..2*comp_width-1]
     *   target [0..bits-1] -> combined [1..bits] (A)
     *   target [bits]      -> combined [2*bits+1] (borrow)
     *   other  [comp_width..comp_width+bits-1] -> combined [bits+1..2*bits] (B)
     *   other  [comp_width+bits] (= 2*comp_width-1) -> combined [2*bits+2] (zero_ext)
     */
    int map_ext[256];
    for (int i = 0; i < bits; i++)
        map_ext[i] = i + 1;       /* A */
    map_ext[bits] = 2 * bits + 1; /* borrow */
    for (int i = 0; i < bits; i++)
        map_ext[comp_width + i] = bits + 1 + i; /* B */
    map_ext[comp_width + bits] = 2 * bits + 2;  /* zero_ext */

    int current_layer = 0;

    /* Step 1: A -= B (QQ_add inverse) */
    copy_remap_layers_inverse(seq, &current_layer, add_n, map_n, -1);

    /* Step 2: [A,borrow] += [B,zero_ext] (extended QQ_add forward) */
    copy_remap_layers(seq, &current_layer, add_ext, map_ext, -1);

    /* Step 3: CX(target=0, control=2*bits+1) */
    cx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]++], 0, (qubit_t)(2 * bits + 1));
    current_layer++;
    seq->used_layer++;

    /* Step 4: Undo extended add (QQ_add inverse) */
    copy_remap_layers_inverse(seq, &current_layer, add_ext, map_ext, -1);

    /* Step 5: A += B (QQ_add forward, restore) */
    copy_remap_layers(seq, &current_layer, add_n, map_n, -1);

    sequence_compute_total_gate_count(seq);
    return seq;
}

/**
 * @brief Controlled QQ less-than: result = (A < B), controlled.
 *
 * Same borrow-ancilla pattern as QQ_less_than but using controlled
 * QQ_add sequences (cQQ_add).
 *
 * Qubit layout:
 *   [0]               = result qbool
 *   [1..bits]         = A
 *   [bits+1..2*bits]  = B
 *   [2*bits+1]        = borrow ancilla
 *   [2*bits+2]        = zero extension
 *   [2*bits+3]        = control qubit
 *
 * @param bits Width of operands (1-63)
 * @return Sequence for controlled comparison, NULL on error. CALLER MUST FREE.
 */
sequence_t *cQQ_less_than(int bits) {
    if (bits < 1 || bits > 63) {
        return NULL;
    }

    int comp_width = bits + 1;
    int ctrl_qubit = 2 * bits + 3;

    /* Get cached controlled QQ_add sequences (DO NOT FREE) */
    sequence_t *cadd_n = cQQ_add(bits);
    sequence_t *cadd_ext = cQQ_add(comp_width);
    if (cadd_n == NULL || cadd_ext == NULL) {
        return NULL;
    }

    int total_layers = 2 * (int)cadd_n->used_layer + 2 * (int)cadd_ext->used_layer + 1;
    int max_gpg = 2 * bits + 6;

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL)
        return NULL;
    seq->num_layer = total_layers;
    seq->used_layer = 0;
    seq->total_gate_count = 0;
    seq->gates_per_layer = calloc(total_layers, sizeof(num_t));
    seq->seq = calloc(total_layers, sizeof(gate_t *));
    if (seq->gates_per_layer == NULL || seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq->seq);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < total_layers; i++) {
        seq->seq[i] = calloc(max_gpg, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; j++)
                free(seq->seq[j]);
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    /* Mapping for cQQ_add(bits):
     *   abstract [0..bits-1] = target -> combined [1..bits] (A)
     *   abstract [bits..2*bits-1] = other -> combined [bits+1..2*bits] (B)
     *   abstract [2*bits] = control -> combined [2*bits+3] (ctrl)
     */
    int map_n[256];
    for (int i = 0; i < bits; i++)
        map_n[i] = i + 1;
    for (int i = 0; i < bits; i++)
        map_n[bits + i] = bits + 1 + i;
    map_n[2 * bits] = ctrl_qubit;

    /* Mapping for cQQ_add(comp_width):
     *   abstract [0..bits-1] = target -> combined [1..bits] (A)
     *   abstract [bits] = target MSB -> combined [2*bits+1] (borrow)
     *   abstract [comp_width..comp_width+bits-1] = other -> combined [bits+1..2*bits] (B)
     *   abstract [comp_width+bits] = other MSB -> combined [2*bits+2] (zero_ext)
     *   abstract [2*comp_width] = control -> combined [2*bits+3] (ctrl)
     */
    int map_ext[256];
    for (int i = 0; i < bits; i++)
        map_ext[i] = i + 1;
    map_ext[bits] = 2 * bits + 1;
    for (int i = 0; i < bits; i++)
        map_ext[comp_width + i] = bits + 1 + i;
    map_ext[comp_width + bits] = 2 * bits + 2;
    map_ext[2 * comp_width] = ctrl_qubit;

    int current_layer = 0;

    /* Step 1: Controlled A -= B (inverse cQQ_add) */
    copy_remap_layers_inverse(seq, &current_layer, cadd_n, map_n, -1);

    /* Step 2: Controlled extended add */
    copy_remap_layers(seq, &current_layer, cadd_ext, map_ext, -1);

    /* Step 3: CCX(target=0, ctrl1=2*bits+1, ctrl2=ctrl_qubit) */
    ccx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]++], 0, (qubit_t)(2 * bits + 1),
        (qubit_t)ctrl_qubit);
    current_layer++;
    seq->used_layer++;

    /* Step 4: Undo controlled extended add */
    copy_remap_layers_inverse(seq, &current_layer, cadd_ext, map_ext, -1);

    /* Step 5: Controlled A += B (forward cQQ_add, restore) */
    copy_remap_layers(seq, &current_layer, cadd_n, map_n, -1);

    sequence_compute_total_gate_count(seq);
    return seq;
}

sequence_t *CQ_equal_width(int bits, int64_t value) {
    // Classical-quantum equality comparison using XOR-based algorithm
    // Qubit layout: [0] = result qbool, [1:bits+1] = quantum operand
    // For bits >= 3: [bits+1 .. bits+bits-2] = AND-ancilla (Phase 74-03)
    // Algorithm:
    // 1. Flip qubits where classical bit is 0 (so equal qubits become |1>)
    // 2. Multi-controlled X to set result qubit (AND-ancilla decomposed for bits>=3)
    // 3. Uncompute: reverse the flips to restore original state

    // Validate input parameters
    if (bits <= 0 || bits > 64) {
        return NULL; // Invalid bit width
    }

    // Check for overflow: if value doesn't fit in bits
    uint64_t max_val = (bits == 64) ? UINT64_MAX : ((1ULL << bits) - 1);
    if (value < 0) {
        int64_t min_val = -(1LL << (bits - 1));
        if (value < min_val) {
            sequence_t *seq = malloc(sizeof(sequence_t));
            if (seq == NULL)
                return NULL;
            seq->num_layer = 0;
            seq->used_layer = 0;
            seq->gates_per_layer = NULL;
            seq->seq = NULL;
            return seq;
        }
    } else {
        if ((uint64_t)value > max_val) {
            sequence_t *seq = malloc(sizeof(sequence_t));
            if (seq == NULL)
                return NULL;
            seq->num_layer = 0;
            seq->used_layer = 0;
            seq->gates_per_layer = NULL;
            seq->seq = NULL;
            return seq;
        }
    }

    // Convert value to binary using two_complement
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    // Count how many bits are 0 in classical value (need X gates for those)
    int num_x_gates = 0;
    for (int i = 0; i < bits; i++) {
        if (bin[i] == 0) {
            num_x_gates++;
        }
    }

    // Calculate number of layers needed:
    // Phase 74-03: MCX(bits) for bits >= 3 uses recursive decomposition
    int mcx_layers;
    if (bits <= 2) {
        mcx_layers = 1; // CX or CCX
    } else {
        mcx_layers = mcx_decomp_layers(bits); // 2*bits - 3 CCX layers
    }
    int num_layers = num_x_gates + mcx_layers + num_x_gates;

    // Allocate sequence structure
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    seq->num_layer = num_layers;
    seq->used_layer = 0;
    seq->gates_per_layer = calloc(num_layers, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }

    seq->seq = calloc(num_layers, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }

    // Allocate gate arrays for each layer
    for (int i = 0; i < num_layers; i++) {
        seq->seq[i] = calloc(bits + 1, sizeof(gate_t)); // Max bits+1 gates per layer
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; j++) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(bin);
            free(seq);
            return NULL;
        }
    }

    int current_layer = 0;

    // Phase 1: Apply X gates to qubits where classical bit is 0
    for (int i = 0; i < bits; i++) {
        if (bin[i] == 0) {
            x(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], i + 1);
            seq->gates_per_layer[current_layer]++;
            current_layer++;
            seq->used_layer++;
        }
    }

    // Phase 2: Multi-controlled X to set result qubit
    if (bits == 1) {
        cx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], 0, 1);
        seq->gates_per_layer[current_layer]++;
        current_layer++;
        seq->used_layer++;
    } else if (bits == 2) {
        ccx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], 0, 1, 2);
        seq->gates_per_layer[current_layer]++;
        current_layer++;
        seq->used_layer++;
    } else {
        // Multi-bit (3+): AND-ancilla decomposition (Phase 74-03)
        // Controls: qubits [1..bits], target: qubit 0
        // AND-ancilla: qubits [bits+1 .. bits+bits-2]
        qubit_t controls[128];
        for (int i = 0; i < bits; i++) {
            controls[i] = i + 1;
        }
        int anc_start = bits + 1; // First AND-ancilla qubit
        emit_mcx_decomp_seq(seq, &current_layer, 0, controls, bits, anc_start);
    }

    // Phase 3: Uncompute - reverse the X gates to restore original state
    for (int i = 0; i < bits; i++) {
        if (bin[i] == 0) {
            x(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], i + 1);
            seq->gates_per_layer[current_layer]++;
            current_layer++;
            seq->used_layer++;
        }
    }

    free(bin);
    sequence_compute_total_gate_count(seq);
    return seq;
}

sequence_t *cCQ_equal_width(int bits, int64_t value) {
    // Controlled classical-quantum equality comparison
    // Qubit layout: [0] = result qbool, [1:bits+1] = quantum operand, [bits+1] = control
    // For bits >= 2: [bits+2 .. ] = AND-ancilla (Phase 74-03)
    // Same algorithm as CQ_equal_width but with controlled gates

    if (bits <= 0 || bits > 64) {
        return NULL;
    }

    uint64_t max_val = (bits == 64) ? UINT64_MAX : ((1ULL << bits) - 1);
    if (value < 0) {
        int64_t min_val = -(1LL << (bits - 1));
        if (value < min_val) {
            sequence_t *seq = malloc(sizeof(sequence_t));
            if (seq == NULL)
                return NULL;
            seq->num_layer = 0;
            seq->used_layer = 0;
            seq->gates_per_layer = NULL;
            seq->seq = NULL;
            return seq;
        }
    } else {
        if ((uint64_t)value > max_val) {
            sequence_t *seq = malloc(sizeof(sequence_t));
            if (seq == NULL)
                return NULL;
            seq->num_layer = 0;
            seq->used_layer = 0;
            seq->gates_per_layer = NULL;
            seq->seq = NULL;
            return seq;
        }
    }

    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    int num_cx_gates = 0;
    for (int i = 0; i < bits; i++) {
        if (bin[i] == 0) {
            num_cx_gates++;
        }
    }

    // Phase 74-03: MCX decomposition for controlled equality
    // For bits==1: CCX (1 layer)
    // For bits==2: MCX(3) -> 3 CCX layers
    // For bits>=3: MCX(bits+1) -> recursive decomposition layers
    int mcx_layers;
    if (bits == 1) {
        mcx_layers = 1;
    } else {
        mcx_layers = mcx_decomp_layers(bits + 1); // bits+1 controls (operand + ext_ctrl)
    }
    int num_layers = num_cx_gates + mcx_layers + num_cx_gates;

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    seq->num_layer = num_layers;
    seq->used_layer = 0;
    seq->gates_per_layer = calloc(num_layers, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }

    seq->seq = calloc(num_layers, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }

    for (int i = 0; i < num_layers; i++) {
        seq->seq[i] = calloc(bits + 2, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; j++) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(bin);
            free(seq);
            return NULL;
        }
    }

    int current_layer = 0;
    int control_qubit = bits + 1;

    // Phase 1: Apply controlled X (CX) gates to qubits where classical bit is 0
    for (int i = 0; i < bits; i++) {
        if (bin[i] == 0) {
            cx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], i + 1, control_qubit);
            seq->gates_per_layer[current_layer]++;
            current_layer++;
            seq->used_layer++;
        }
    }

    // Phase 2: Controlled multi-controlled X with AND-ancilla decomposition
    if (bits == 1) {
        // Single bit: CCX with control_qubit and qubit[1] controlling qubit[0]
        ccx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], 0, control_qubit, 1);
        seq->gates_per_layer[current_layer]++;
        current_layer++;
        seq->used_layer++;
    } else {
        // Phase 74-03: MCX(bits+1) decomposed via AND-ancilla
        // Controls: [control_qubit, 1, 2, ..., bits]
        // AND-ancilla starts at qubit bits+2
        qubit_t controls[128];
        controls[0] = control_qubit;
        for (int i = 0; i < bits; i++) {
            controls[i + 1] = i + 1;
        }
        int anc_start = bits + 2; // First AND-ancilla qubit
        emit_mcx_decomp_seq(seq, &current_layer, 0, controls, bits + 1, anc_start);
    }

    // Phase 3: Uncompute - reverse the controlled X gates
    for (int i = 0; i < bits; i++) {
        if (bin[i] == 0) {
            cx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], i + 1, control_qubit);
            seq->gates_per_layer[current_layer]++;
            current_layer++;
            seq->used_layer++;
        }
    }

    free(bin);
    sequence_compute_total_gate_count(seq);
    return seq;
}

/**
 * @brief Classical-quantum less-than: result = (A < value).
 *
 * Implements the borrow-ancilla pattern as a single sequence:
 *   1. Subtract classical value from [A, borrow] register
 *   2. CX from borrow to result (copy borrow bit)
 *   3. Add classical value back to restore [A, borrow]
 *
 * Qubit layout: [0]=result, [1..bits]=A, [bits+1]=borrow_ancilla
 *
 * @param bits  Width of quantum operand A (1-63)
 * @param value Classical value to compare against
 * @return Sequence for comparison, NULL on error. CALLER MUST FREE.
 */
sequence_t *CQ_less_than(int bits, int64_t value) {
    if (bits <= 0 || bits > 63) {
        return NULL;
    }

    /* Get sub and add sequences (freshly allocated, caller must free) */
    sequence_t *sub_seq = split_CQ_sub(bits, value);
    sequence_t *add_seq = split_CQ_add(bits, value);
    if (sub_seq == NULL || add_seq == NULL) {
        if (sub_seq)
            toffoli_sequence_free(sub_seq);
        if (add_seq)
            toffoli_sequence_free(add_seq);
        return NULL;
    }

    /* Total layers: sub layers + 1 (CX) + add layers */
    int total_layers = (int)sub_seq->used_layer + 1 + (int)add_seq->used_layer;
    int max_gates_per_layer = bits + 2; /* generous upper bound */

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        toffoli_sequence_free(sub_seq);
        toffoli_sequence_free(add_seq);
        return NULL;
    }
    seq->num_layer = total_layers;
    seq->used_layer = 0;
    seq->total_gate_count = 0;
    seq->gates_per_layer = calloc(total_layers, sizeof(num_t));
    seq->seq = calloc(total_layers, sizeof(gate_t *));
    if (seq->gates_per_layer == NULL || seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq->seq);
        free(seq);
        toffoli_sequence_free(sub_seq);
        toffoli_sequence_free(add_seq);
        return NULL;
    }
    for (int i = 0; i < total_layers; i++) {
        seq->seq[i] = calloc(max_gates_per_layer, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; j++)
                free(seq->seq[j]);
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            toffoli_sequence_free(sub_seq);
            toffoli_sequence_free(add_seq);
            return NULL;
        }
    }

    /* Build offset map: sub/add abstract index i -> combined index i + 1 */
    int offset_map[128];
    build_offset_map(offset_map, bits + 2, 1);

    int current_layer = 0;

    /* Step 1: Subtract -- copy sub_seq with qubit offset +1 */
    copy_remap_layers(seq, &current_layer, sub_seq, offset_map, -1);

    /* Step 2: CX(target=0, control=bits+1) -- copy borrow to result */
    cx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]++], 0, (qubit_t)(bits + 1));
    current_layer++;
    seq->used_layer++;

    /* Step 3: Add back -- copy add_seq with qubit offset +1 */
    copy_remap_layers(seq, &current_layer, add_seq, offset_map, -1);

    toffoli_sequence_free(sub_seq);
    toffoli_sequence_free(add_seq);
    sequence_compute_total_gate_count(seq);
    return seq;
}

/**
 * @brief Controlled classical-quantum less-than: result = (A < value), controlled.
 *
 * Same borrow-ancilla pattern as CQ_less_than, but every gate is controlled
 * by an external control qubit.
 *
 * Qubit layout: [0]=result, [1..bits]=A, [bits+1]=borrow, [bits+2]=control
 *
 * @param bits  Width of quantum operand A (1-63)
 * @param value Classical value to compare against
 * @return Sequence for controlled comparison, NULL on error. CALLER MUST FREE.
 */
sequence_t *cCQ_less_than(int bits, int64_t value) {
    if (bits <= 0 || bits > 63) {
        return NULL;
    }

    sequence_t *sub_seq = split_CQ_sub(bits, value);
    sequence_t *add_seq = split_CQ_add(bits, value);
    if (sub_seq == NULL || add_seq == NULL) {
        if (sub_seq)
            toffoli_sequence_free(sub_seq);
        if (add_seq)
            toffoli_sequence_free(add_seq);
        return NULL;
    }

    int ctrl_qubit = bits + 2;
    int total_layers = (int)sub_seq->used_layer + 1 + (int)add_seq->used_layer;
    int max_gates_per_layer = bits + 3;

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        toffoli_sequence_free(sub_seq);
        toffoli_sequence_free(add_seq);
        return NULL;
    }
    seq->num_layer = total_layers;
    seq->used_layer = 0;
    seq->total_gate_count = 0;
    seq->gates_per_layer = calloc(total_layers, sizeof(num_t));
    seq->seq = calloc(total_layers, sizeof(gate_t *));
    if (seq->gates_per_layer == NULL || seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq->seq);
        free(seq);
        toffoli_sequence_free(sub_seq);
        toffoli_sequence_free(add_seq);
        return NULL;
    }
    for (int i = 0; i < total_layers; i++) {
        seq->seq[i] = calloc(max_gates_per_layer, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; j++)
                free(seq->seq[j]);
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            toffoli_sequence_free(sub_seq);
            toffoli_sequence_free(add_seq);
            return NULL;
        }
    }

    int offset_map[128];
    build_offset_map(offset_map, bits + 2, 1);

    int current_layer = 0;

    /* Step 1: Controlled subtract */
    copy_remap_layers(seq, &current_layer, sub_seq, offset_map, ctrl_qubit);

    /* Step 2: CCX(target=0, control1=bits+1, control2=ctrl_qubit) */
    ccx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]++], 0, (qubit_t)(bits + 1),
        (qubit_t)ctrl_qubit);
    current_layer++;
    seq->used_layer++;

    /* Step 3: Controlled add back */
    copy_remap_layers(seq, &current_layer, add_seq, offset_map, ctrl_qubit);

    toffoli_sequence_free(sub_seq);
    toffoli_sequence_free(add_seq);
    sequence_compute_total_gate_count(seq);
    return seq;
}

/**
 * @brief Classical-quantum greater-than: result = (A > value).
 *
 * A > value is equivalent to NOT(A < value + 1).
 * For the sequence, we implement this directly as (A < value + 1)
 * and let the Python side handle the inversion via __invert__.
 *
 * However, to provide a gt-specific sequence for the IR, we just
 * delegate to CQ_less_than with value + 1.
 *
 * @param bits  Width of quantum operand A (1-63)
 * @param value Classical value to compare against
 * @return Sequence for comparison, NULL on error. CALLER MUST FREE.
 */
sequence_t *CQ_greater_than(int bits, int64_t value) {
    /* a > value iff a >= value+1 iff a < value+1 is false.
     * The Python side does ~(a < value+1), recording an lt IR entry
     * for (value+1) and a separate not IR entry for ~.
     * This function exists for DAG gate-count resolution: gt's
     * uncontrolled cost equals the lt cost for (value+1). */
    int64_t max_val = (bits == 64) ? (int64_t)UINT64_MAX : (int64_t)((1ULL << bits) - 1);
    if (value >= max_val) {
        /* a > max_val is always false -- no gates needed.
         * Return a minimal empty sequence. */
        sequence_t *seq = malloc(sizeof(sequence_t));
        if (seq == NULL)
            return NULL;
        seq->num_layer = 0;
        seq->used_layer = 0;
        seq->gates_per_layer = NULL;
        seq->seq = NULL;
        seq->total_gate_count = 0;
        return seq;
    }
    return CQ_less_than(bits, value + 1);
}

/**
 * @brief Controlled classical-quantum greater-than: result = (A > value), controlled.
 *
 * @param bits  Width of quantum operand A (1-63)
 * @param value Classical value to compare against
 * @return Sequence for controlled comparison, NULL on error. CALLER MUST FREE.
 */
sequence_t *cCQ_greater_than(int bits, int64_t value) {
    int64_t max_val = (bits == 64) ? (int64_t)UINT64_MAX : (int64_t)((1ULL << bits) - 1);
    if (value >= max_val) {
        sequence_t *seq = malloc(sizeof(sequence_t));
        if (seq == NULL)
            return NULL;
        seq->num_layer = 0;
        seq->used_layer = 0;
        seq->gates_per_layer = NULL;
        seq->seq = NULL;
        seq->total_gate_count = 0;
        return seq;
    }
    return cCQ_less_than(bits, value + 1);
}

// ======================================================
// Legacy Comparison Operations (INTEGERSIZE-based)
// ======================================================

// CC_equal removed (Phase 11) - purely classical, no quantum gate generation

// CQ_equal() removed (Phase 11-04) - used global state for classical value
// Use CQ_equal_width(bits, value) instead with explicit parameters

// cCQ_equal() removed (Phase 11-04) - used global state for classical value
// Use controlled version of CQ_equal_width() when available
