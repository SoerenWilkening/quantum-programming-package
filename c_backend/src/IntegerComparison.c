//
// Created by Sören Wilkening on 09.11.24.
//
// Phase 74-03: MCX gates decomposed via AND-ancilla in equality comparisons.

#include "Integer.h"
#include "QPU.h"
#include "comparison_ops.h"
#include "definition.h"
#include "gate.h"
#include <stdint.h>
#include <stdlib.h>

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
    // Stub: Returns NULL, Python uses subtraction + MSB check
    // Phase 8 will implement optimized C-level circuit
    (void)bits;
    return NULL;
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
    return seq;
}

sequence_t *CQ_less_than(int bits, int64_t value) {
    // Stub: Returns NULL, Python converts value to qint and uses QQ pattern
    (void)bits;
    (void)value;
    return NULL;
}

// ======================================================
// Legacy Comparison Operations (INTEGERSIZE-based)
// ======================================================

// CC_equal removed (Phase 11) - purely classical, no quantum gate generation

// CQ_equal() removed (Phase 11-04) - used QPU_state->R0 for classical value
// Use CQ_equal_width(bits, value) instead with explicit parameters

// cCQ_equal() removed (Phase 11-04) - used QPU_state->R0 for classical value
// Use controlled version of CQ_equal_width() when available
