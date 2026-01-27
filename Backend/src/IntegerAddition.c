//
// Created by Sören Wilkening on 05.11.24.
//

#include "Integer.h"

// Legacy globals for backward compatibility (point to INTEGERSIZE versions)
sequence_t *precompiled_QQ_add = NULL;
sequence_t *precompiled_cQQ_add = NULL;
sequence_t *precompiled_CQ_add[64] = {NULL};
sequence_t *precompiled_cCQ_add[64] = {NULL};

// Width-parameterized precompiled caches (index 0 unused, 1-64 valid)
sequence_t *precompiled_QQ_add_width[65] = {NULL};
sequence_t *precompiled_cQQ_add_width[65] = {NULL};

// CC_add removed (Phase 11) - purely classical, no quantum gate generation

// Width-parameterized precompiled caches for CQ_add (index 0 unused, 1-64 valid)
sequence_t *precompiled_CQ_add_width[65] = {NULL};
sequence_t *precompiled_cCQ_add_width[65] = {NULL};

sequence_t *CQ_add(int bits, int64_t value) {
    // OWNERSHIP: Returns cached sequence (precompiled_CQ_add_width[bits]) - DO NOT FREE
    // The precompiled sequence is reused across calls for performance
    //
    // Qubit layout for CQ_add(bits):
    // - Qubits [0, bits-1]: Target operand (modified in place)
    // Classical value comes from value parameter

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Compute rotation angles
    int NonZeroCount = 0;
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    // Compute rotations for addition
    double *rotations = calloc(bits, sizeof(double));
    if (rotations == NULL) {
        free(bin);
        return NULL;
    }
    for (int i = 0; i < bits; ++i) {
        for (int j = 0; j < bits - i; ++j) {
            rotations[j + i] += bin[bits - i - 1] * 2 * M_PI / (pow(2, j + 1));
        }
        if (rotations[i] != 0)
            NonZeroCount++;
    }
    free(bin);
    int start_layer = bits;

    // Check cache for this width (use width-parameterized cache)
    if (precompiled_CQ_add_width[bits] != NULL) {
        sequence_t *add = precompiled_CQ_add_width[bits];

        for (int i = 0; i < bits; ++i) {
            add->seq[start_layer + i][add->gates_per_layer[start_layer + i] - 1].GateValue =
                rotations[bits - i - 1];
        }
        free(rotations);
        return add;
    }

    sequence_t *add = malloc(sizeof(sequence_t));
    if (add == NULL) {
        free(rotations);
        return NULL;
    }
    // allocate exact number of layer and enough gates per layer
    add->used_layer = 0;
    add->num_layer = 4 * bits - 1;
    add->gates_per_layer = calloc(add->num_layer, sizeof(num_t));
    if (add->gates_per_layer == NULL) {
        free(rotations);
        free(add);
        return NULL;
    }
    memset(add->gates_per_layer, 0, add->num_layer * sizeof(num_t));
    add->seq = calloc(add->num_layer, sizeof(gate_t *));
    if (add->seq == NULL) {
        free(add->gates_per_layer);
        free(rotations);
        free(add);
        return NULL;
    }
    for (int i = 0; i < add->num_layer; ++i) {
        add->seq[i] = calloc(2 * bits, sizeof(gate_t));
        if (add->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(add->seq[j]);
            }
            free(add->seq);
            free(add->gates_per_layer);
            free(rotations);
            free(add);
            return NULL;
        }
    }
    QFT(add, bits);

    // Phase rotation gates: target qubits are at indices [0, bits-1]
    for (int i = 0; i < bits; ++i) {
        p(&add->seq[start_layer + i][add->gates_per_layer[start_layer + i]++], i,
          rotations[bits - i - 1]);
    }
    free(rotations);
    add->used_layer++;

    QFT_inverse(add, bits);

    // Cache the sequence
    precompiled_CQ_add_width[bits] = add;

    // Backward compatibility: set legacy global for INTEGERSIZE
    if (bits == INTEGERSIZE) {
        precompiled_CQ_add[bits] = add;
    }

    return add;
}
sequence_t *QQ_add(int bits) {
    // OWNERSHIP: Returns cached sequence (precompiled_QQ_add_width[bits]) - DO NOT FREE
    // The precompiled sequence is reused across calls for performance
    //
    // Qubit layout for QQ_add(bits):
    // - Qubits [0, bits-1]: First operand (target, modified in place)
    // - Qubits [bits, 2*bits-1]: Second operand (control)

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Check cache for this width
    if (precompiled_QQ_add_width[bits] != NULL)
        return precompiled_QQ_add_width[bits];

    sequence_t *add = malloc(sizeof(sequence_t));
    if (add == NULL) {
        return NULL;
    }

    // allocate exact number of layer and enough gates per layer
    add->used_layer = 0;
    add->num_layer = 5 * bits - 2;
    add->gates_per_layer = calloc(add->num_layer, sizeof(num_t));
    if (add->gates_per_layer == NULL) {
        free(add);
        return NULL;
    }
    memset(add->gates_per_layer, 0, add->num_layer * sizeof(num_t));
    add->seq = calloc(add->num_layer, sizeof(gate_t *));
    if (add->seq == NULL) {
        free(add->gates_per_layer);
        free(add);
        return NULL;
    }
    for (int i = 0; i < add->num_layer; ++i) {
        add->seq[i] = calloc(2 * bits, sizeof(gate_t));
        if (add->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(add->seq[j]);
            }
            free(add->seq);
            free(add->gates_per_layer);
            free(add);
            return NULL;
        }
    }
    QFT(add, bits);
    int rounds = 0;
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        for (int i = 0; i < bits - rounds; ++i) {
            num_t layer = 2 * bits + i + 2 * rounds - 1;
            num_t target = bits - i - 1 - rounds;
            num_t control = bits + bit;
            double value = 2 * M_PI / (pow(2, i + 1));
            gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
            cp(g, target, control, value);
        }
        rounds++;
    }
    add->used_layer += bits;
    QFT_inverse(add, bits);

    // Cache the sequence
    precompiled_QQ_add_width[bits] = add;

    // Backward compatibility: set legacy global for INTEGERSIZE
    if (bits == INTEGERSIZE) {
        precompiled_QQ_add = add;
    }

    return add;
}
sequence_t *cCQ_add(int bits, int64_t value) {
    // OWNERSHIP: Returns cached sequence (precompiled_cCQ_add_width[bits]) - DO NOT FREE
    // The precompiled sequence is reused across calls for performance
    //
    // Qubit layout for cCQ_add(bits):
    // - Qubits [0, bits-1]: Target operand (modified in place)
    // - Qubit [bits]: Conditional control qubit
    // Classical value comes from value parameter

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Compute rotation angles
    int NonZeroCount = 0;
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    // Compute rotations for addition
    double *rotations = calloc(bits, sizeof(double));
    if (rotations == NULL) {
        free(bin);
        return NULL;
    }
    for (int i = 0; i < bits; ++i) {
        for (int j = 0; j < bits - i; ++j) {
            rotations[j + i] += bin[bits - i - 1] * 2 * M_PI / (pow(2, j + 1));
        }
        if (rotations[i] != 0)
            NonZeroCount++;
    }
    free(bin);
    int start_layer = bits;

    // Check cache for this width (use width-parameterized cache)
    if (precompiled_cCQ_add_width[bits] != NULL) {
        sequence_t *add = precompiled_cCQ_add_width[bits];

        for (int i = 0; i < bits; ++i) {
            add->seq[start_layer + i][add->gates_per_layer[start_layer + i] - 1].GateValue =
                rotations[i];
        }
        free(rotations);
        return add;
    }

    sequence_t *add = malloc(sizeof(sequence_t));
    if (add == NULL) {
        free(rotations);
        return NULL;
    }
    // allocate exact number of layer and enough gates per layer
    add->used_layer = 0;
    add->num_layer = 4 * bits - 1;
    add->gates_per_layer = calloc(add->num_layer, sizeof(num_t));
    if (add->gates_per_layer == NULL) {
        free(rotations);
        free(add);
        return NULL;
    }
    memset(add->gates_per_layer, 0, add->num_layer * sizeof(num_t));
    add->seq = calloc(add->num_layer, sizeof(gate_t *));
    if (add->seq == NULL) {
        free(add->gates_per_layer);
        free(rotations);
        free(add);
        return NULL;
    }
    for (int i = 0; i < add->num_layer; ++i) {
        add->seq[i] = calloc(2 * bits, sizeof(gate_t));
        if (add->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(add->seq[j]);
            }
            free(add->seq);
            free(add->gates_per_layer);
            free(rotations);
            free(add);
            return NULL;
        }
    }
    QFT(add, bits);

    // Controlled phase rotation gates: target at [0, bits-1], control at [bits]
    for (int i = 0; i < bits; ++i) {
        cp(&add->seq[start_layer + i][add->gates_per_layer[start_layer + i]++], i, bits,
           rotations[bits - i - 1]);
    }
    free(rotations);
    add->used_layer++;

    QFT_inverse(add, bits);

    // Cache the sequence
    precompiled_cCQ_add_width[bits] = add;

    // Backward compatibility: set legacy global for INTEGERSIZE
    if (bits == INTEGERSIZE) {
        precompiled_cCQ_add[bits] = add;
    }

    return add;
}
sequence_t *cQQ_add(int bits) {
    // OWNERSHIP: Returns cached sequence (precompiled_cQQ_add_width[bits]) - DO NOT FREE
    // The precompiled sequence is reused across calls for performance
    //
    // Qubit layout for cQQ_add(bits):
    // - Qubits [0, bits-1]: First operand (target, modified in place)
    // - Qubits [bits, 2*bits-1]: Second operand (control)
    // - Qubit [3*bits-1]: Conditional control qubit

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Check cache for this width
    if (precompiled_cQQ_add_width[bits] != NULL)
        return precompiled_cQQ_add_width[bits];

    sequence_t *add = malloc(sizeof(sequence_t));
    if (add == NULL) {
        return NULL;
    }

    // allocate exact number of layer and enough gates per layer
    add->used_layer = 0;
    add->num_layer = bits * (bits + 1) / 2 * 4 + 4 * bits - 2 - bits / 4 * 4 + 3;
    add->gates_per_layer = calloc(add->num_layer, sizeof(num_t));
    if (add->gates_per_layer == NULL) {
        free(add);
        return NULL;
    }
    memset(add->gates_per_layer, 0, add->num_layer * sizeof(num_t));
    add->seq = calloc(add->num_layer, sizeof(gate_t *));
    if (add->seq == NULL) {
        free(add->gates_per_layer);
        free(add);
        return NULL;
    }
    for (int i = 0; i < add->num_layer; ++i) {
        add->seq[i] = calloc(2 * bits, sizeof(gate_t));
        if (add->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(add->seq[j]);
            }
            free(add->seq);
            free(add->gates_per_layer);
            free(add);
            return NULL;
        }
    }

    QFT(add, bits);

    int control = 3 * bits - 1;
    int rounds;
    int layer = 2 * bits - 1;

    // block 1
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        double value = 0;
        for (int i = 0; i < bits - bit; ++i) {
            value += 2 * M_PI / (pow(2, i + 1)) / 2;
        }
        gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
        cp(g, bit, control, value);
        layer++;
    }

    // block 2
    rounds = 0;
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
        cx(g, control, bits + bit);
        layer++;
        for (int i = 0; i < bits - rounds; ++i) {
            double value = 2 * M_PI / (pow(2, i + 1)) / 2;
            g = &add->seq[layer][add->gates_per_layer[layer]++];
            cp(g, bit - i, control, -value);
            layer++;
        }
        g = &add->seq[layer][add->gates_per_layer[layer]++];
        cx(g, control, bits + bit);
        layer++;
        rounds++;
    }

    // block 3
    rounds = 0;
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        for (int i = 0; i < bits - rounds; ++i) {
            double value = 2 * M_PI / (pow(2, i + 1)) / 2;
            gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
            cp(g, bit - i, bits + bit, value);
            layer++;
        }
        layer -= bits - rounds;
        rounds++;
    }
    add->used_layer = layer + 1;
    QFT_inverse(add, bits);

    // Cache the sequence
    precompiled_cQQ_add_width[bits] = add;

    // Backward compatibility: set legacy global for INTEGERSIZE
    if (bits == INTEGERSIZE) {
        precompiled_cQQ_add = add;
    }

    return add;
}

sequence_t *P_add_param(double phase_value) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    // Width-parameterized single-qubit phase gate
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    seq->gates_per_layer = calloc(1, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(1, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    seq->seq[0] = calloc(1, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer[0] = 1;

    // Apply phase gate with explicit parameter value
    p(&seq->seq[0][0], 0, phase_value);

    return seq;
}

// DEPRECATED: Use P_add_param(phase_value) instead
// This function will be removed when all callers are migrated
sequence_t *P_add() {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    // READS: QPU_state->R0 for phase value
    return P_add_param(*(QPU_state->R0));
}
sequence_t *cP_add_param(double phase_value) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    // Width-parameterized controlled phase gate
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    seq->gates_per_layer = calloc(1, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(1, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    seq->seq[0] = calloc(1, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer[0] = 1;

    // Apply controlled phase gate with explicit parameter value
    cp(&seq->seq[0][0], 0, 1, phase_value);

    return seq;
}

// DEPRECATED: Use cP_add_param(phase_value) instead
// This function will be removed when all callers are migrated
sequence_t *cP_add() {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    // READS: QPU_state->R0 for phase value
    return cP_add_param(*(QPU_state->R0));
}