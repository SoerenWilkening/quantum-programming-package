//
// Created by Sören Wilkening on 05.11.24.
//
#include "../include/Integer.h"


void CP_sequence(sequence_t *mul, num_t *layer, int rounds, num_t control, double multiplyer, int inverted) {
    int l1 = 0, l2 = INTEGERSIZE - rounds;
    int fac = 1;
    if (inverted) {
        l1 = INTEGERSIZE - 1;
        l2 = 0;
        fac = -1;
    }

    for (int i = l1; i < l2; i += fac) {
        num_t target = i + rounds;
        double value = M_PI / (pow(2, i + 1)) * multiplyer;
        gate_t *g = &mul->seq[*layer][mul->gates_per_layer[*layer]++];
        cp(g, target, control, value);
        (*layer)++;
    }
}

sequence_t *QQ_mul() {
    if (precompiled_QQ_mul != NULL) return precompiled_QQ_mul;

    sequence_t *mul = malloc(sizeof(sequence_t));

    mul->seq = malloc((INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1) * sizeof(gate_t));
    mul->used_layer = 0;
    mul->num_layer = INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1;
    mul->gates_per_layer = calloc(mul->num_layer, sizeof(num_t));

    for (int i = 0; i < mul->num_layer; ++i) mul->seq[i] = malloc(2 * INTEGERSIZE * sizeof(gate_t));

    QFT(mul);
    num_t layer = INTEGERSIZE;

    int rounds = 0;
    // First blocks of CCP decompositions
    // all the CP block of the first decomp step can be merged
    for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
        layer = INTEGERSIZE + 2 * rounds;
        CP_sequence(mul, &layer, rounds, INTEGERSIZE + bit, pow(2, INTEGERSIZE) - 1, false);
        rounds++;
    }
    layer -= INTEGERSIZE - 1;

    // intermediate step, C1X0 C0P_2(value/2)C1X0
    for (int bit_int2 = 0; bit_int2 < INTEGERSIZE; ++bit_int2) {
        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cx(g, control, 3 * INTEGERSIZE - bit_int2 - 1);
            layer++;
        }
        rounds = 0;
        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            CP_sequence(mul, &layer, rounds, INTEGERSIZE + bit, -pow(2, bit_int2), false);
            layer -= INTEGERSIZE - rounds;
            rounds++;
        }
        layer += INTEGERSIZE;

        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cx(g, control, 3 * INTEGERSIZE - bit_int2 - 1);
            layer++;
        }
        layer -= INTEGERSIZE - 1;
    }

    // the final step, C1P(value/2)
    rounds = INTEGERSIZE - 1;
    for (int bit = 0; bit < INTEGERSIZE; ++bit) {
        CP_sequence(mul, &layer, rounds, 3 * INTEGERSIZE - bit - 1, pow(2, INTEGERSIZE) - 1, true);
        rounds--;
    }

    mul->used_layer = layer - 1;
    QFT_inverse(mul);

    precompiled_QQ_mul = mul;
    return mul;
}


sequence_t *cQQ_mul() {
    // TODO:
    //  - control necessary rotation gates

    sequence_t *mul = malloc(sizeof(sequence_t));

    mul->seq = malloc(3 * (INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1) * sizeof(gate_t));
    mul->used_layer = 0;
    mul->num_layer = 3 * INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1;
    mul->gates_per_layer = calloc(mul->num_layer, sizeof(num_t));

    for (int i = 0; i < mul->num_layer; ++i) mul->seq[i] = malloc(2 * INTEGERSIZE * sizeof(gate_t));

    QFT(mul);
    num_t layer = INTEGERSIZE;
    int rounds = 0;

    double values[INTEGERSIZE];
    memset(values, 0, INTEGERSIZE * sizeof(double));

    // First blocks of CCP decompositions
    // all the CP block of the first decomp step can be merged
    for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
        num_t control = INTEGERSIZE + bit;
        CP_sequence(mul, &layer, rounds, control, (pow(2, INTEGERSIZE) - 1) / 2, false);
        rounds++;
    }
    layer -= INTEGERSIZE - 1;
    for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
        num_t control = INTEGERSIZE + bit;
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, control, 3 * INTEGERSIZE);
        layer++;
    }
    rounds = 0;
    for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
        num_t control = INTEGERSIZE + bit;
        CP_sequence(mul, &layer, rounds, control, -(pow(2, INTEGERSIZE) - 1) / 2, false);
        layer -= INTEGERSIZE - rounds;
        rounds++;
    }
    layer += INTEGERSIZE;
    for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
        num_t control = INTEGERSIZE + bit;
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, control, 3 * INTEGERSIZE);
        layer++;
    }
    rounds = 0;
    for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
        // rotation gates will be merged and applied at the end
        for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
            values[i + rounds] += M_PI / (pow(2, i + 1)) * (pow(2, INTEGERSIZE) - 1) / 2;
        }
        rounds++;
    }
    layer -= INTEGERSIZE - 1;

    // intermediate step, C1X0 C0P_2(value/2)C1X0
    for (int bit_int2 = 0; bit_int2 < INTEGERSIZE; ++bit_int2) {

        // sequence of cnots from non controlled multiplication
        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cx(g, control, 3 * INTEGERSIZE - bit_int2 - 1);
            layer++;
        }
        rounds = 0;
        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            CP_sequence(mul, &layer, rounds, control, -pow(2, bit_int2) / 2, false);
            layer -= INTEGERSIZE - rounds;
            rounds++;
        }
        layer += INTEGERSIZE;
        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cx(g, control, 3 * INTEGERSIZE);
            layer++;
        }

        rounds = 0;
        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            CP_sequence(mul, &layer, rounds, control, pow(2, bit_int2) / 2, false);
            layer -= INTEGERSIZE - rounds;
            rounds++;
        }
        layer += INTEGERSIZE;

        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cx(g, control, 3 * INTEGERSIZE);
            layer++;
        }
        rounds = 0;
        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            // rotation gates will be merged and applied at the end
            for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
                values[i + rounds] += -M_PI / (pow(2, i + 1)) * pow(2, bit_int2) / 2;
            }
            rounds++;
        }
        layer -= INTEGERSIZE - 1;
        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cx(g, control, 3 * INTEGERSIZE - bit_int2 - 1);
            layer++;
        }
        layer -= INTEGERSIZE - 1;
    }

    // the final step, C1P(value/2)
    rounds = INTEGERSIZE - 1;
    for (int bit = 0; bit < INTEGERSIZE; ++bit) {
        num_t control = 3 * INTEGERSIZE - bit - 1;
        CP_sequence(mul, &layer, rounds, control, (pow(2, INTEGERSIZE) - 1) / 2, false);
        layer -= INTEGERSIZE - rounds;
        rounds--;
    }
    layer += INTEGERSIZE;

    for (int bit = 0; bit < INTEGERSIZE; ++bit) {
        num_t control = 3 * INTEGERSIZE - bit - 1;
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, control, 3 * INTEGERSIZE);
        layer++;
    }

    rounds = INTEGERSIZE - 1;
    for (int bit = 0; bit < INTEGERSIZE; ++bit) {
        num_t control = 3 * INTEGERSIZE - bit - 1;
        CP_sequence(mul, &layer, rounds, control, -(pow(2, INTEGERSIZE) - 1) / 2, false);
        layer -= INTEGERSIZE - rounds;
        rounds--;
    }
    layer += 1;

    for (int bit = 0; bit < INTEGERSIZE; ++bit) {
        num_t control = 3 * INTEGERSIZE - bit - 1;
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, control, 3 * INTEGERSIZE);
        layer++;
    }

    rounds = INTEGERSIZE - 1;
    for (int bit = 0; bit < INTEGERSIZE; ++bit) {
        for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
            values[i + rounds] += M_PI / (pow(2, i + 1)) * (pow(2, INTEGERSIZE) - 1) / 2;
        }
        rounds--;
    }

    for (int i = INTEGERSIZE - 1; i >= 0; --i) {
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cp(g, i, 3 * INTEGERSIZE, values[i]);
        layer++;
    }

    mul->used_layer = layer - INTEGERSIZE + 1;
    QFT_inverse(mul);

//    precompiled_QQ_mul = mul;
    return mul;
}


sequence_t *CQ_mul() {
    int *bin = two_complement(*stack.GPR3->c_address, INTEGERSIZE);

    sequence_t *mul = malloc(sizeof(sequence_t));

    mul->seq = malloc(
            (INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1) * sizeof(gate_t));
    mul->used_layer = 0;
    mul->num_layer = INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1;
    mul->gates_per_layer = calloc(mul->num_layer, sizeof(num_t));

    for (int i = 0; i < mul->num_layer; ++i) mul->seq[i] = malloc(2 * INTEGERSIZE * sizeof(gate_t));

    QFT(mul);
    num_t layer = INTEGERSIZE;
    int rounds = 0;

    // First blocks of CCP decompositions
    // all the CP block of the first decomp step can be merged
    for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
        layer = INTEGERSIZE + 2 * rounds;
        num_t control = INTEGERSIZE + bit;
        for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
            num_t target = i + rounds;
            double value = 0;
            for (int bit_int2 = 0; bit_int2 < INTEGERSIZE; ++bit_int2) {
                value += bin[bit_int2] * M_PI / (pow(2, i + 1)) * pow(2, INTEGERSIZE - bit_int2 - 1);
            }
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, target, control, value);
            layer++;
        }
        rounds++;
    }

    mul->used_layer = layer;
    QFT_inverse(mul);

    return mul;
}

sequence_t *cCQ_mul() {
    int *bin = two_complement(*stack.GPR3->c_address, INTEGERSIZE);

    sequence_t *mul = malloc(sizeof(sequence_t));

    mul->seq = malloc(
            (INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1) * sizeof(gate_t));
    mul->used_layer = 0;
    mul->num_layer = INTEGERSIZE * (2 * INTEGERSIZE + 6) - 1;
    mul->gates_per_layer = calloc(mul->num_layer, sizeof(num_t));

    for (int i = 0; i < mul->num_layer; ++i) mul->seq[i] = malloc(2 * INTEGERSIZE * sizeof(gate_t));

    QFT(mul);

    // precompute all the rotation angles
    double values[INTEGERSIZE];
    memset(values, 0, INTEGERSIZE * sizeof(double));
    for (int i = 0; i < INTEGERSIZE; ++i) {
        for (int bit_int2 = 0; bit_int2 < INTEGERSIZE; ++bit_int2) {
            values[i] += bin[bit_int2] * M_PI / (pow(2, i + 1)) * pow(2, INTEGERSIZE - bit_int2 - 1);
        }
    }

    int rounds;
    int layer = INTEGERSIZE;
    for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
        double value = 0;
        for (int i = 0; i < INTEGERSIZE - bit; ++i) {
            value += values[i] / 2;
        }
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cp(g, INTEGERSIZE - bit - 1, 2 * INTEGERSIZE, value);
        layer++;
    }


    rounds = 0;
    for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
        gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, 2 * INTEGERSIZE, INTEGERSIZE + bit);
        layer++;
        for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
            g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, i + rounds, 2 * INTEGERSIZE, -values[i] / 2);
            layer++;
        }
        g = &mul->seq[layer][mul->gates_per_layer[layer]++];
        cx(g, 2 * INTEGERSIZE, INTEGERSIZE + bit);
        layer++;
        rounds++;
    }

    rounds = 0;
    for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
        for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, i + rounds, INTEGERSIZE + bit, values[i] / 2);
            layer++;
        }
        layer -= INTEGERSIZE - rounds;
        rounds++;
    }
    mul->used_layer = layer + INTEGERSIZE;

    QFT_inverse(mul);

    return mul;
}