//
// Created by Sören Wilkening on 09.11.24.
//

#include "Integer.h"
#include "QPU.h"
#include "comparison_ops.h"
#include "definition.h"
#include "gate.h"
#include <stdint.h>
#include <stdlib.h>

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
    // Algorithm:
    // 1. Flip qubits where classical bit is 0 (so equal qubits become |1>)
    // 2. Multi-controlled X to set result qubit (all must be |1> = equal)
    // 3. Uncompute: reverse the flips to restore original state

    // Validate input parameters
    if (bits <= 0 || bits > 64) {
        return NULL; // Invalid bit width
    }

    // Check for overflow: if value doesn't fit in bits
    // For unsigned interpretation: value must be in [0, 2^bits - 1]
    // Handle negative values via two's complement
    uint64_t max_val = (bits == 64) ? UINT64_MAX : ((1ULL << bits) - 1);
    if (value < 0) {
        // Negative values need two's complement conversion
        // If |value| > 2^bits, it overflows
        int64_t min_val = -(1LL << (bits - 1));
        if (value < min_val) {
            // Overflow: return empty sequence
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
        // Positive value overflow check
        if ((uint64_t)value > max_val) {
            // Overflow: return empty sequence
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
    // - num_x_gates layers for initial X gates (one per zero bit)
    // - bits-1 layers for cascaded Toffoli gates (multi-controlled X)
    // - num_x_gates layers for uncompute (reverse X gates)
    int num_layers = num_x_gates + (bits > 1 ? bits - 1 : 1) + num_x_gates;

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
            // Cleanup on failure
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
            // Qubit i+1 (offset by result qubit at index 0)
            x(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], i + 1);
            seq->gates_per_layer[current_layer]++;
            current_layer++;
            seq->used_layer++;
        }
    }

    // Phase 2: Multi-controlled X to set result qubit
    if (bits == 1) {
        // Single bit: just copy qubit[1] to qubit[0] (CX gate)
        cx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], 0, 1);
        seq->gates_per_layer[current_layer]++;
        current_layer++;
        seq->used_layer++;
    } else if (bits == 2) {
        // Two bits: single CCX with qubits[1] and qubits[2] controlling qubit[0]
        ccx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], 0, 1, 2);
        seq->gates_per_layer[current_layer]++;
        current_layer++;
        seq->used_layer++;
    } else {
        // Multi-bit (3+): Requires proper multi-controlled gates
        // Phase 12-01: Placeholder implementation - returns valid sequence structure
        // but gate logic needs ancilla qubits for correct multi-controlled X
        // Full implementation will use large_control array for >2 controls
        // For now: just apply CCX for first two bits (partial check)
        ccx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], 0, 1, 2);
        seq->gates_per_layer[current_layer]++;
        current_layer++;
        seq->used_layer++;
        // TODO(Phase 12-02): Implement proper n-bit AND with ancilla/large_control
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
    // Same algorithm as CQ_equal_width but with controlled gates (CX instead of X)
    // Control qubit at position bits+1 gates the entire operation

    // Validate input parameters
    if (bits <= 0 || bits > 64) {
        return NULL; // Invalid bit width
    }

    // Check for overflow (same as CQ_equal_width)
    uint64_t max_val = (bits == 64) ? UINT64_MAX : ((1ULL << bits) - 1);
    if (value < 0) {
        int64_t min_val = -(1LL << (bits - 1));
        if (value < min_val) {
            // Overflow: return empty sequence
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
            // Overflow: return empty sequence
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

    // Convert value to binary
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    // Count how many bits are 0 in classical value (need CX gates for those)
    int num_cx_gates = 0;
    for (int i = 0; i < bits; i++) {
        if (bin[i] == 0) {
            num_cx_gates++;
        }
    }

    // Calculate number of layers (same structure as uncontrolled version)
    int num_layers = num_cx_gates + (bits > 1 ? bits - 1 : 1) + num_cx_gates;

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
        seq->seq[i] = calloc(bits + 2, sizeof(gate_t)); // bits+2 for result, operand, control
        if (seq->seq[i] == NULL) {
            // Cleanup on failure
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
    int control_qubit = bits + 1; // Control qubit position

    // Phase 1: Apply controlled X (CX) gates to qubits where classical bit is 0
    for (int i = 0; i < bits; i++) {
        if (bin[i] == 0) {
            // Controlled X: target is qubit i+1, control is control_qubit
            cx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], i + 1, control_qubit);
            seq->gates_per_layer[current_layer]++;
            current_layer++;
            seq->used_layer++;
        }
    }

    // Phase 2: Controlled multi-controlled X to set result qubit
    if (bits == 1) {
        // Single bit: CCX with control_qubit and qubit[1] controlling qubit[0]
        ccx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], 0, control_qubit, 1);
        seq->gates_per_layer[current_layer]++;
        current_layer++;
        seq->used_layer++;
    } else if (bits == 2) {
        // Two bits: Needs 3-controlled gate (control_qubit, qubit[1], qubit[2] -> qubit[0])
        // With MAXCONTROLS=2, need to decompose:
        // - CCX(control_qubit, qubit[1], qubit[0])
        // - Then check qubit[2] with CX or another pattern
        // Phase 12-01: Simplified - only check first two operands with control
        ccx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], 0, control_qubit, 1);
        seq->gates_per_layer[current_layer]++;
        current_layer++;
        seq->used_layer++;
        // TODO(Phase 12-02): Add proper 3-controlled gate decomposition
    } else {
        // Multi-bit (3+): Placeholder implementation
        // Full controlled multi-bit comparison requires ancilla and decomposition
        // Phase 12-01: Basic structure only
        ccx(&seq->seq[current_layer][seq->gates_per_layer[current_layer]], 0, control_qubit, 1);
        seq->gates_per_layer[current_layer]++;
        current_layer++;
        seq->used_layer++;
        // TODO(Phase 12-02): Implement proper n-bit controlled AND
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
