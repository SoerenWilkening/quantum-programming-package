//
// Created by Sören Wilkening on 05.11.24.
//
#include "Integer.h"

// Legacy globals for backward compatibility (point to INTEGERSIZE versions)
sequence_t *precompiled_QQ_mul = NULL;
sequence_t *precompiled_cQQ_mul = NULL;

// Width-parameterized precompiled caches (index 0 unused, 1-64 valid)
sequence_t *precompiled_QQ_mul_width[65] = {NULL};
sequence_t *precompiled_cQQ_mul_width[65] = {NULL};

void CP_sequence(sequence_t *mul, num_t *layer, int rounds, num_t control, double multiplyer,
                 int inverted, int bits) {
    int l1 = 0, l2 = bits - rounds;
    int fac = 1;
    if (inverted) {
        l1 = bits - 1;
        l2 = 0;
        fac = -1;
    }
    for (int i = l1; (fac > 0 ? i < l2 : i > l2); i += fac) {
        num_t target = bits - i - 1 - rounds;
        double value = M_PI / (pow(2, i + 1)) * multiplyer;
        gate_t *g = &mul->seq[*layer][mul->gates_per_layer[*layer]++];
        cp(g, target, control, value);
        (*layer)++;
    }
}
void CX_sequence(sequence_t *mul, num_t *layer, int bit_int2, int bits) {
    for (int bit = bits - 1; bit >= 0; --bit) {
        // FIX BUG-03: Control qubit reversal (same as QQ_add fix in plan 29-06)
        num_t control = 2 * bits - 1 - bit;
        gate_t *g = &mul->seq[*layer][mul->gates_per_layer[*layer]++];
        cx(g, control, 3 * bits + bit_int2 - 1);
        (*layer)++;
    }
}
void CX2_sequence(sequence_t *mul, num_t *layer, int bit_int2, int bits) {
    for (int bit = bits - 1; bit >= 0; --bit) {
        num_t control = 2 * bits + bit;
        gate_t *g = &mul->seq[*layer][mul->gates_per_layer[*layer]++];
        cx(g, control, 3 * bits + bit_int2 - 1);
        (*layer)++;
    }
}
void CCX_sequence(sequence_t *mul, num_t *layer, int bit_int2, int bits) {
    for (int bit = bits - 1; bit >= 0; --bit) {
        // FIX BUG-03: Control qubit reversal (same as QQ_add fix in plan 29-06)
        num_t control = 2 * bits - 1 - bit;
        gate_t *g = &mul->seq[*layer][mul->gates_per_layer[*layer]++];
        ccx(g, control, 3 * bits + bit_int2 - 1, 4 * bits - 1);
        (*layer)++;
    }
}
void all_rot(sequence_t *mul, num_t *layer, int inverted, double multiplyer, int bits) {
    int rounds = 0;
    for (int bit = bits - 1; bit >= 0; --bit) {
        // FIX BUG-03: Control qubit reversal (same as QQ_add fix in plan 29-06)
        num_t control = 2 * bits - 1 - bit;
        //        CP_sequence(mul, layer, rounds, control, -(pow(2, bits) - 1) / 2 *
        //        multiplyer, inverted, bits);
        CP_sequence(mul, layer, rounds, control, -multiplyer / 2, inverted, bits);
        *layer -= bits - rounds;
        rounds++;
    }
    *layer += bits;
}
void all_rot_final_block(sequence_t *mul, num_t *layer, int rounds, num_t control,
                         double multiplyer, int inverted, int bits) {}

// CC_mul removed (Phase 11) - purely classical, no quantum gate generation

sequence_t *CQ_mul(int bits, int64_t value) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *mul = malloc(sizeof(sequence_t));
    if (mul == NULL) {
        free(bin);
        return NULL;
    }
    mul->used_layer = 0;
    mul->num_layer = MAXLAYERINSEQUENCE;
    mul->gates_per_layer = calloc(mul->num_layer, sizeof(num_t));
    if (mul->gates_per_layer == NULL) {
        free(bin);
        free(mul);
        return NULL;
    }
    memset(mul->gates_per_layer, 0, mul->num_layer * sizeof(num_t));
    mul->seq = calloc(mul->num_layer, sizeof(gate_t *));
    if (mul->seq == NULL) {
        free(mul->gates_per_layer);
        free(bin);
        free(mul);
        return NULL;
    }
    for (int i = 0; i < mul->num_layer; ++i) {
        mul->seq[i] = calloc(10 * bits, sizeof(gate_t));
        if (mul->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(mul->seq[j]);
            }
            free(mul->seq);
            free(mul->gates_per_layer);
            free(bin);
            free(mul);
            return NULL;
        }
    }

    QFT(mul, bits);
    num_t layer = 2 * bits - 1;
    int rounds = 0;

    // all the CP block of the first decomp step can be merged
    for (int bit = bits - 1; bit >= 0; --bit) {
        layer = 2 * bits + 2 * rounds - 1;
        // FIX BUG-03: Control qubit mapping was reversed (same issue as QQ_add in plan 29-06)
        // bit=bits-1 should map to LSB control, bit=0 should map to MSB control
        num_t control = 2 * bits - 1 - bit;
        for (int i = 0; i < bits - rounds; ++i) {
            num_t target = rounds + i;

            double value = 0;
            for (int bit_int2 = 0; bit_int2 < bits; ++bit_int2) {
                // Phase for Draper QFT multiplication: encode v * 2^(bit_weight) in Fourier domain
                // With target = rounds + i and rounds tracking the control bit's position,
                // the positional weight is already accounted for by the target offset.
                // No additional pow(2, bits-1-bit) factor needed.
                value += bin[bits - 1 - bit_int2] * 2 * M_PI / (pow(2, i + 1)) * pow(2, bit_int2);
            }
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, target, control, value);
            layer++;
        }
        rounds++;
    }

    mul->used_layer = layer;
    QFT_inverse(mul, bits);

    free(bin);
    return mul;
}
sequence_t *QQ_mul(int bits) {
    // OWNERSHIP: Returns cached sequence (precompiled_QQ_mul_width[bits]) - DO NOT FREE
    // The precompiled sequence is reused across calls for performance

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Check cache for this width
    if (precompiled_QQ_mul_width[bits] != NULL)
        return precompiled_QQ_mul_width[bits];

    sequence_t *mul = malloc(sizeof(sequence_t));
    if (mul == NULL) {
        return NULL;
    }

    mul->used_layer = 0;
    mul->num_layer = MAXLAYERINSEQUENCE;
    mul->gates_per_layer = calloc(mul->num_layer, sizeof(num_t));
    if (mul->gates_per_layer == NULL) {
        free(mul);
        return NULL;
    }
    memset(mul->gates_per_layer, 0, mul->num_layer * sizeof(num_t));
    mul->seq = calloc(mul->num_layer, sizeof(gate_t *));
    if (mul->seq == NULL) {
        free(mul->gates_per_layer);
        free(mul);
        return NULL;
    }
    for (int i = 0; i < mul->num_layer; ++i) {
        mul->seq[i] = calloc(10 * bits, sizeof(gate_t));
        if (mul->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(mul->seq[j]);
            }
            free(mul->seq);
            free(mul->gates_per_layer);
            free(mul);
            return NULL;
        }
    }

    QFT(mul, bits);
    num_t layer = 2 * bits - 1; // layer after QFT

    // QQ_mul implements Draper QFT multiplication using CCP decomposition.
    //
    // Qubit layout (right-aligned storage: index 0 = LSB, index bits-1 = MSB):
    //   0..bits-1       : result register (QFT domain), 0=LSB, bits-1=MSB
    //   bits..2*bits-1   : operand a (self), bits=a_LSB, 2*bits-1=a_MSB
    //   2*bits..3*bits-1 : operand b (other), 2*bits=b_LSB, 3*bits-1=b_MSB
    //
    // Bit weight mapping: qubit at index (bits+k) has weight 2^k for operand a,
    //                     qubit at index (2*bits+j) has weight 2^j for operand b.
    //
    // For each bit of a (control) and each bit of b, we need CCP(theta) where
    // theta encodes the product weight in the Fourier domain.
    //
    // CCP(theta, a_ctrl, b_ctrl, target) decomposes into:
    //   CP(theta/2, target, a_ctrl)
    //   CX(a_ctrl, b_ctrl)
    //   CP(-theta/2, target, a_ctrl)
    //   CX(a_ctrl, b_ctrl)
    //   CP(theta/2, target, b_ctrl)
    //
    // For efficiency, we merge all b bits for fixed (a_ctrl, target):
    //   Step 1: CP(sum_theta/2, target, a_ctrl)
    //   Step 2: for each b bit j: CX, CP(-theta_j/2), CX
    //   Step 3: for each b bit j: CP(theta_j/2, target, b_ctrl_j)

    int rounds = 0;
    for (int bit = bits - 1; bit >= 0; --bit) {
        num_t a_ctrl = 2 * bits - 1 - bit;

        // Step 1: CP(sum_theta/2, target, a_ctrl) for each Fourier target
        // sum_theta for target at index i = M_PI * (2^bits - 1) / 2^i
        // so sum_theta/2 = M_PI * (2^bits - 1) / 2^(i+1)
        for (int i = 0; i < bits - rounds; ++i) {
            num_t target = rounds + i;
            double sum_phase = M_PI * (pow(2, bits) - 1) / pow(2, i + 1);
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, target, a_ctrl, sum_phase);
            layer++;
        }

        // Step 2: For each b bit j: CX(a_ctrl, b_ctrl) + negative CPs + CX
        for (int j = 0; j < bits; ++j) {
            num_t b_ctrl = 2 * bits + j; // b bit at weight 2^j

            // CX: b_ctrl controls, a_ctrl is target
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cx(g, a_ctrl, b_ctrl);
            layer++;

            // CP(-theta_j/2, target, a_ctrl) for each Fourier target
            // theta_j for target index i = 2*pi * 2^j / 2^(i+1) = M_PI * 2^(j-i)
            // -theta_j/2 = -M_PI * 2^(j-i) / 2 = -M_PI * 2^(j-i-1)
            for (int i = 0; i < bits - rounds; ++i) {
                num_t target = rounds + i;
                double neg_phase = -M_PI * pow(2, j) / pow(2, i + 1);
                g = &mul->seq[layer][mul->gates_per_layer[layer]++];
                cp(g, target, a_ctrl, neg_phase);
                layer++;
            }

            // CX: restore a_ctrl
            g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cx(g, a_ctrl, b_ctrl);
            layer++;
        }

        // Step 3: CP(theta_j/2, target, b_ctrl_j) for each b bit and target
        for (int j = 0; j < bits; ++j) {
            num_t b_ctrl = 2 * bits + j;

            for (int i = 0; i < bits - rounds; ++i) {
                num_t target = rounds + i;
                double phase = M_PI * pow(2, j) / pow(2, i + 1);
                gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
                cp(g, target, b_ctrl, phase);
                layer++;
            }
        }

        rounds++;
    }

    mul->used_layer = layer;
    QFT_inverse(mul, bits);

    // Cache the sequence
    precompiled_QQ_mul_width[bits] = mul;

    // Backward compatibility: set legacy global for INTEGERSIZE
    if (bits == INTEGERSIZE) {
        precompiled_QQ_mul = mul;
    }

    return mul;
}
sequence_t *cCQ_mul(int bits, int64_t value) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *mul = malloc(sizeof(sequence_t));
    if (mul == NULL) {
        free(bin);
        return NULL;
    }
    mul->used_layer = 0;
    mul->num_layer = MAXLAYERINSEQUENCE;
    mul->gates_per_layer = calloc(mul->num_layer, sizeof(num_t));
    if (mul->gates_per_layer == NULL) {
        free(bin);
        free(mul);
        return NULL;
    }
    memset(mul->gates_per_layer, 0, mul->num_layer * sizeof(num_t));
    mul->seq = calloc(mul->num_layer, sizeof(gate_t *));
    if (mul->seq == NULL) {
        free(mul->gates_per_layer);
        free(bin);
        free(mul);
        return NULL;
    }
    for (int i = 0; i < mul->num_layer; ++i) {
        mul->seq[i] = calloc(10 * bits, sizeof(gate_t));
        if (mul->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(mul->seq[j]);
            }
            free(mul->seq);
            free(mul->gates_per_layer);
            free(bin);
            free(mul);
            return NULL;
        }
    }

    QFT(mul, bits);

    int control = 3 * bits - 1;
    // precompute all the rotation angles
    double values[64]; // Max width is 64
    memset(values, 0, 64 * sizeof(double));
    for (int i = 0; i < bits; ++i) {
        for (int bit_int2 = 0; bit_int2 < bits; ++bit_int2) {
            // FIX BUG-03: same as CQ_mul - reverse bin indexing for LSB-first access
            values[i] += bin[bits - 1 - bit_int2] * 2 * M_PI / (pow(2, i + 1)) * pow(2, bit_int2);
        }
    }

    // block 1
    int rounds;
    int layer = 2 * bits - 1;
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        double value = 0;
        for (int i = 0; i < bits - bit; ++i) {
            value += values[i] / 2;
        }
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cp(g, bit, control, value);
        layer++;
    }

    // block 2
    rounds = 0;
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, control, bits + bit);
        layer++;
        for (int i = 0; i < bits - rounds; ++i) {
            g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, bit - i, control, -values[i] / 2);
            layer++;
        }
        g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, control, bits + bit);
        layer++;
        rounds++;
    }

    // block 3
    rounds = 0;
    for (int bit = (int)bits - 1; bit >= 0; --bit) {
        for (int i = 0; i < bits - rounds; ++i) {
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, bit - i, bits + bit, values[i] / 2);
            layer++;
        }
        layer -= bits - rounds;
        rounds++;
    }
    mul->used_layer = layer + 1;

    QFT_inverse(mul, bits);

    free(bin);
    return mul;
}
sequence_t *cQQ_mul(int bits) {
    // OWNERSHIP: Returns cached sequence (precompiled_cQQ_mul_width[bits]) - DO NOT FREE
    // The precompiled sequence is reused across calls for performance

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Check cache for this width
    if (precompiled_cQQ_mul_width[bits] != NULL)
        return precompiled_cQQ_mul_width[bits];

    sequence_t *mul = malloc(sizeof(sequence_t));
    if (mul == NULL) {
        return NULL;
    }

    mul->used_layer = 0;
    //	mul->num_layer = 20 * bits * (2 * bits + 6) - 1;
    mul->num_layer = MAXLAYERINSEQUENCE;
    mul->gates_per_layer = calloc(mul->num_layer, sizeof(num_t));
    if (mul->gates_per_layer == NULL) {
        free(mul);
        return NULL;
    }
    memset(mul->gates_per_layer, 0, mul->num_layer * sizeof(num_t));
    mul->seq = calloc(mul->num_layer, sizeof(gate_t *));
    if (mul->seq == NULL) {
        free(mul->gates_per_layer);
        free(mul);
        return NULL;
    }
    for (int i = 0; i < mul->num_layer; ++i) {
        mul->seq[i] = calloc(10 * bits, sizeof(gate_t));
        if (mul->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(mul->seq[j]);
            }
            free(mul->seq);
            free(mul->gates_per_layer);
            free(mul);
            return NULL;
        }
    }

    QFT(mul, bits);
    // start after qft
    num_t layer = 2 * bits - 1;

    double values[64]; // Max width is 64
    memset(values, 0, 64 * sizeof(double));

    // First blocks : decompose the controlled QQmul block from the first block in qq_mul
    int rounds = 0;
    for (int bit = bits - 1; bit >= 0; --bit) {
        num_t control = bits + bit;
        CP_sequence(mul, &layer, rounds, control, (pow(2, bits) - 1) / 2, false, bits);
        rounds++;
    }
    layer -= bits - 1;
    CX_sequence(mul, &layer, bits, bits);
    all_rot(mul, &layer, false, (pow(2, bits) - 1), bits);
    CX_sequence(mul, &layer, bits, bits);

    for (int bit = 0; bit < bits; ++bit) {
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        double value = M_PI / 2 * (pow(2, bits) - 1) * pow(2, -bit - 1) * (pow(2, bit + 1) - 1);
        cp(g, bits - bit - 1, 4 * bits - 1, value);
        layer++;
    }

    // block 2 and 3
    for (int bit_int2 = 0; bit_int2 < bits; ++bit_int2) {
        CCX_sequence(mul, &layer, -bit_int2, bits);
        all_rot(mul, &layer, false, pow(2, bit_int2), bits);
        CX_sequence(mul, &layer, bits, bits);
        all_rot(mul, &layer, false, -pow(2, bit_int2), bits);
        CX_sequence(mul, &layer, bits, bits);

        // culmination of controlled rotation gates
        for (int bit = 0; bit < bits; ++bit) {
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            double value = -M_PI * pow(2, bit_int2) * (pow(2, bit + 1) - 1) * pow(2, -bit - 1) / 2;
            cp(g, bits - bit - 1, 4 * bits - 1, value);
            layer++;
        }
        CCX_sequence(mul, &layer, -bit_int2, bits);

        // decomposition of the culminations from the QQ_mul
        for (int i = 0; i < bits; ++i) {
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            double value = pow(2, -i - 1) * M_PI * (pow(2, i + 1) - 1) * pow(2, bit_int2) / 2;
            cp(g, bits - i - 1, 3 * bits - bit_int2 - 1, value);
            layer++;
        }

        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, 3 * bits - bit_int2 - 1, 4 * bits - 1);
        layer++;

        for (int i = 0; i < bits; ++i) {
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            double value = -pow(2, -i - 1) * M_PI * (pow(2, i + 1) - 1) * pow(2, bit_int2) / 2;
            cp(g, bits - i - 1, 3 * bits - bit_int2 - 1, value);
            layer++;
        }
        g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, 3 * bits - bit_int2 - 1, 4 * bits - 1);
        layer++;

        for (int i = 0; i < bits; ++i) {
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            double value = pow(2, -i - 1) * M_PI * (pow(2, i + 1) - 1) * pow(2, bit_int2) / 2;
            cp(g, bits - i - 1, 4 * bits - 1, value);
            layer++;
        }
    }

    mul->used_layer = layer;
    QFT_inverse(mul, bits);

    // Cache the sequence
    precompiled_cQQ_mul_width[bits] = mul;

    // Backward compatibility: set legacy global for INTEGERSIZE
    if (bits == INTEGERSIZE) {
        precompiled_cQQ_mul = mul;
    }

    return mul;
}
