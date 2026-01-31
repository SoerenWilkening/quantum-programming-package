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
    for (int i = l1; i < l2; i += fac) {
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
            num_t target = bits - i - 1 - rounds;

            double value = 0;
            for (int bit_int2 = 0; bit_int2 < bits; ++bit_int2) {
                // FIX BUG-03: two_complement returns MSB-first, reverse indexing for LSB-first
                // We need bin[bits-1-bit_int2] to get LSB-first access
                // Then bit_int2=0 accesses LSB, which should have weight pow(2,0)
                // CRITICAL: Also multiply by pow(2, bits-1-bit) for the control qubit's positional
                // weight With reversed control mapping: bit=bits-1 (LSB control) needs weight 2^0
                // bit=0 (MSB control) needs weight 2^(bits-1)
                value += bin[bits - 1 - bit_int2] * 2 * M_PI / (pow(2, i + 1)) * pow(2, bit_int2) *
                         pow(2, bits - 1 - bit);
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
    num_t layer = bits;

    // block 1
    int rounds = 0;
    // First blocks of CCP decompositions
    // all the CP block of the first decomp step can be merged
    for (int bit = bits - 1; bit >= 0; --bit) {
        layer = 2 * bits + 2 * rounds - 1;
        // FIX BUG-03: Same control reversal as in CQ_mul and QQ_add (plan 29-06)
        CP_sequence(mul, &layer, rounds, 2 * bits - 1 - bit, pow(2, bits) - 1, false, bits);
        rounds++;
    }
    layer++;

    // block 2
    // intermediate step, C1X0 C0P_2(value/2)C1X0
    for (int bit_int2 = 0; bit_int2 < bits; ++bit_int2) {
        layer -= bits;
        CX_sequence(mul, &layer, -bit_int2, bits);

        all_rot(mul, &layer, false, pow(2, 1 + bit_int2), bits);

        CX_sequence(mul, &layer, -bit_int2, bits);

        for (int i = 0; i < bits; ++i) {
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            //		    printf("%d %d %f %f\n", bit_int2, i, pow(2, i + 1) - 1, pow(2,
            // bit_int2));
            double value = pow(2, -i - 1) * M_PI * (pow(2, i + 1) - 1) * pow(2, bit_int2);
            cp(g, bits - i - 1, 3 * bits - bit_int2 - 1, value);
            layer++;
        }
    }
    layer++;
    //	layer -= bits - 1;
    mul->used_layer = layer - 1;
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
