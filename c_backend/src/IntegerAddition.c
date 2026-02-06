//
// Created by Sören Wilkening on 05.11.24.
//

#include "Integer.h"
#include "sequences.h"

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
    for (int bit_idx = 0; bit_idx < bits; ++bit_idx) {
        for (int qubit = bit_idx; qubit < bits; ++qubit) {
            // two_complement() returns MSB-first: bin[0]=MSB, bin[bits-1]=LSB
            // bit_idx: 0=LSB position, bits-1=MSB position
            // qubit: 0=LSB qubit, bits-1=MSB qubit
            // Higher bits don't affect lower qubits, so only iterate qubit >= bit_idx
            // Phase for qubit from bit: 2*PI / 2^(qubit-bit+1)
            rotations[qubit] += bin[bits - 1 - bit_idx] * 2 * M_PI / pow(2, qubit - bit_idx + 1);
        }
        if (rotations[bit_idx] != 0)
            NonZeroCount++;
    }
    free(bin);
    // Phase rotations start after QFT (which uses 2*bits-1 layers)
    int start_layer = 2 * bits - 1;

    // Check cache for this width (use width-parameterized cache)
    if (precompiled_CQ_add_width[bits] != NULL) {
        sequence_t *add = precompiled_CQ_add_width[bits];

        // Direct rotation mapping: with textbook QFT (no swaps, MSB-first processing),
        // the Fourier-domain qubit ordering matches the computational-basis qubit ordering.
        // rotations[i] applies to physical qubit i.
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
    // Total: QFT(2*bits-1) + rotations(bits) + IQFT(2*bits-1) = 5*bits-2
    add->used_layer = 0;
    add->num_layer = 5 * bits - 2;
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

    // Phase rotation gates: direct mapping. With textbook QFT (no swaps),
    // rotations[i] applies to physical qubit i.
    for (int i = 0; i < bits; ++i) {
        p(&add->seq[start_layer + i][add->gates_per_layer[start_layer + i]++], i, rotations[i]);
    }
    free(rotations);
    add->used_layer += bits;

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

    // Use hardcoded sequences for widths 1-16
    if (bits <= HARDCODED_MAX_WIDTH) {
        const sequence_t *hardcoded = get_hardcoded_QQ_add(bits);
        if (hardcoded != NULL) {
            // SAFETY: Const cast is safe here because:
            // 1. Static sequences have program lifetime (never freed)
            // 2. Caller should never free returned sequences anyway
            // 3. Cast needed only because existing API returns non-const
            return (sequence_t *)hardcoded;
        }
    }

    // Check cache for dynamically generated (widths > HARDCODED_MAX_WIDTH)
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
    // Draper QFT addition: apply controlled phase gates from second operand (control)
    // to first operand (target) in Fourier domain.
    // After textbook QFT (no swaps, MSB-first processing), physical qubit j corresponds
    // to Fourier mode j. Control bit k applies phase 2*pi/2^(j+1-k) to Fourier qubit j
    // for j >= k.
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        for (int i = 0; i < bits - rounds; ++i) {
            num_t layer = 2 * bits + i + 2 * rounds - 1;
            num_t target = rounds + i;
            // Control mapping: bit iterates MSB-first, maps to control qubits LSB-first
            num_t control = bits + (bits - 1 - bit); // Equivalent to: 2*bits - 1 - bit
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
    for (int bit_idx = 0; bit_idx < bits; ++bit_idx) {
        for (int qubit = bit_idx; qubit < bits; ++qubit) {
            // two_complement() returns MSB-first: bin[0]=MSB, bin[bits-1]=LSB
            // bit_idx: 0=LSB position, bits-1=MSB position
            // qubit: 0=LSB qubit, bits-1=MSB qubit
            // Higher bits don't affect lower qubits, so only iterate qubit >= bit_idx
            // Phase for qubit from bit: 2*PI / 2^(qubit-bit+1)
            rotations[qubit] += bin[bits - 1 - bit_idx] * 2 * M_PI / pow(2, qubit - bit_idx + 1);
        }
        if (rotations[bit_idx] != 0)
            NonZeroCount++;
    }
    free(bin);
    // Phase rotations start after QFT (which uses 2*bits-1 layers)
    int start_layer = 2 * bits - 1;

    // Check cache for this width (use width-parameterized cache)
    if (precompiled_cCQ_add_width[bits] != NULL) {
        sequence_t *add = precompiled_cCQ_add_width[bits];

        // Direct rotation mapping (same as CQ_add: textbook QFT convention)
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
    // Total: QFT(2*bits-1) + rotations(bits) + IQFT(2*bits-1) = 5*bits-2
    add->used_layer = 0;
    add->num_layer = 5 * bits - 2;
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
    // Direct rotation mapping (same as CQ_add: textbook QFT convention)
    for (int i = 0; i < bits; ++i) {
        cp(&add->seq[start_layer + i][add->gates_per_layer[start_layer + i]++], i, bits,
           rotations[i]);
    }
    free(rotations);
    add->used_layer += bits;

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
    // - Qubits [bits, 2*bits-1]: Second operand (other)
    // - Qubit [2*bits]: Conditional control qubit

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Use hardcoded sequences for widths 1-16
    if (bits <= HARDCODED_MAX_WIDTH) {
        const sequence_t *hardcoded = get_hardcoded_cQQ_add(bits);
        if (hardcoded != NULL) {
            // SAFETY: Const cast is safe here because:
            // 1. Static sequences have program lifetime (never freed)
            // 2. Caller should never free returned sequences anyway
            // 3. Cast needed only because existing API returns non-const
            return (sequence_t *)hardcoded;
        }
    }

    // Check cache for dynamically generated (widths > HARDCODED_MAX_WIDTH)
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

    int control = 2 * bits;
    int rounds;
    int layer = 2 * bits - 1;

    // block 1: unconditional half-rotations on Fourier qubits
    // With textbook QFT convention, reverse target qubit ordering
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        int target_q = bits - 1 - bit; // reversed for textbook QFT
        double value = 0;
        for (int i = 0; i < bits - bit; ++i) {
            value += 2 * M_PI / (pow(2, i + 1)) / 2;
        }
        gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
        cp(g, target_q, control, value);
        layer++;
    }

    // block 2: CNOT + negative half-rotations + CNOT
    rounds = 0;
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
        cx(g, control, bits + bit);
        layer++;
        for (int i = 0; i < bits - rounds; ++i) {
            double value = 2 * M_PI / (pow(2, i + 1)) / 2;
            int target_q = rounds + i; // reversed for textbook QFT
            g = &add->seq[layer][add->gates_per_layer[layer]++];
            cp(g, target_q, bits + bit, -value);
            layer++;
        }
        g = &add->seq[layer][add->gates_per_layer[layer]++];
        cx(g, control, bits + bit);
        layer++;
        rounds++;
    }

    // block 3: controlled rotations from b register
    rounds = 0;
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        for (int i = 0; i < bits - rounds; ++i) {
            double value = 2 * M_PI / (pow(2, i + 1)) / 2;
            int target_q = rounds + i; // reversed for textbook QFT
            gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
            cp(g, target_q, bits + bit, value);
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

// P_add() removed (Phase 11-04) - deprecated wrapper that used QPU_state->R0
// Use P_add_param(phase_value) instead

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

// cP_add() removed (Phase 11-04) - deprecated wrapper that used QPU_state->R0
// Use cP_add_param(phase_value) instead