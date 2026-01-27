//
// Created by Sören Wilkening on 09.11.24.
//

#include "Integer.h"
#include "QPU.h"
#include "comparison_ops.h"
#include "definition.h"
#include "gate.h"
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
    // Stub: Returns NULL, Python converts value to qint and uses QQ pattern
    (void)bits;
    (void)value;
    return NULL;
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

sequence_t *CC_equal() {
    // OWNERSHIP: No sequence returned (performs classical computation only)
    *(QPU_state->R0) = *(QPU_state->R1) == *(QPU_state->R2);
    return NULL;
}
sequence_t *CQ_equal() {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    // READS: QPU_state->R0 for classical value
    // the ancilla count starts at 2 * INTEGERSIZE
    int ancilla = 2 * INTEGERSIZE; // reference

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    int factor = INTEGERSIZE;

    int *bin = two_complement(*(QPU_state->R0), INTEGERSIZE);
    if (bin == NULL) {
        free(seq);
        return NULL;
    }
    int Zeros = 0;
    for (int i = 0; i < INTEGERSIZE; ++i)
        Zeros += (1 - bin[i]);

    seq->used_layer = 0;
    int num_layers = (int)ceil(log2(Zeros + 1)) + 10;
    seq->num_layer = num_layers;
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
    for (int i = 0; i < num_layers; ++i) {
        seq->seq[i] = calloc(INTEGERSIZE, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(bin);
            free(seq);
            return NULL;
        }
    }
    memset(seq->gates_per_layer, 0, ceil(log2(Zeros + 1)) * sizeof(num_t));

    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
            x(g, factor + i);
        }
    }

    int ctrls[2 * Zeros];
    int index = 0;
    memset(ctrls, 0, 2 * Zeros * sizeof(int));
    seq->used_layer++;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[1][seq->gates_per_layer[1]++];
            cx(g, ancilla + index, factor + i);

            ctrls[index] = ancilla + index;
            ctrls[Zeros + index] = ancilla + Zeros + index;
            index++;
        }
    }
    seq->used_layer++;
    int Z = Zeros / 2;
    int Z1 = Zeros / 2;
    for (int i = 0; i < Zeros - 2; ++i) {
        layer_t layer = seq->used_layer;
        gate_t *g = &seq->seq[layer][seq->gates_per_layer[layer]++];
        ccx(g, ancilla + Zeros + i, ctrls[2 * i], ctrls[2 * i + 1]);
        if (i == Z - 1) {
            seq->used_layer++;
            Z1 /= 2;
            Z += Z1;
        }
    }

    ccx(&seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++], INTEGERSIZE - 1,
        ctrls[2 * Zeros - 4], ctrls[2 * Zeros - 3]);
    seq->used_layer++;

    for (int i = Zeros - 3; i >= 0; --i) {
        layer_t layer = seq->used_layer;
        gate_t *g = &seq->seq[layer][seq->gates_per_layer[layer]++];
        ccx(g, ancilla + Zeros + i, ctrls[2 * i], ctrls[2 * i + 1]);
        if (i == Z - 1) {
            seq->used_layer++;
            Z1 *= 2;
            Z -= Z1;
        }
    }
    seq->used_layer++;

    index = 0;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
            cx(g, ancilla + index, factor + i);

            ctrls[index] = ancilla + index;
            ctrls[Zeros + index] = ancilla + Zeros + index;
            index++;
        }
    }
    seq->used_layer++;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
            x(g, factor + i);
        }
    }
    seq->used_layer++;

    return seq;
}
sequence_t *cCQ_equal() {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    // READS: QPU_state->R0 for classical value
    // the ancilla count starts at 2 * INTEGERSIZE
    int ancilla = 3 * INTEGERSIZE; // reference

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    int factor = INTEGERSIZE;

    int *bin = two_complement(*(QPU_state->R0), INTEGERSIZE);
    if (bin == NULL) {
        free(seq);
        return NULL;
    }
    int Zeros = 0;
    for (int i = 0; i < INTEGERSIZE; ++i)
        Zeros += (1 - bin[i]);

    seq->used_layer = 0;
    int num_layers = (int)ceil(log2(Zeros + 1) + 2) + 10;
    seq->num_layer = num_layers;
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
    for (int i = 0; i < num_layers; ++i) {
        seq->seq[i] = calloc(INTEGERSIZE, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(bin);
            free(seq);
            return NULL;
        }
    }
    memset(seq->gates_per_layer, 0, ceil(log2(Zeros + 1) + 2) * sizeof(num_t));

    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
            x(g, factor + i);
        }
    }

    int ctrls[2 * Zeros + 2];
    int index = 0;
    memset(ctrls, 0, 2 * (Zeros + 1) * sizeof(int));
    seq->used_layer++;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[1][seq->gates_per_layer[1]++];
            cx(g, ancilla + index, factor + i);

            ctrls[index] = ancilla + index;
            ctrls[Zeros + index] = ancilla + Zeros + index;
            index++;
        }
    }
    seq->used_layer++;
    int Z = Zeros / 2;
    int Z1 = Zeros / 2;
    for (int i = 0; i < Zeros - 1; ++i) {
        layer_t layer = seq->used_layer;
        gate_t *g = &seq->seq[layer][seq->gates_per_layer[layer]++];
        ccx(g, ancilla + Zeros + i, ctrls[2 * i], ctrls[2 * i + 1]);
        if (i == Z - 1) {
            seq->used_layer++;
            Z1 /= 2;
            Z += Z1;
        }
    }

    ccx(&seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++], INTEGERSIZE - 1,
        3 * INTEGERSIZE - 1, ctrls[2 * Zeros - 2]);
    seq->used_layer++;

    for (int i = Zeros - 2; i >= 0; --i) {
        layer_t layer = seq->used_layer;
        gate_t *g = &seq->seq[layer][seq->gates_per_layer[layer]++];
        ccx(g, ancilla + Zeros + i, ctrls[2 * i], ctrls[2 * i + 1]);
        if (i == Z - 1) {
            seq->used_layer++;
            Z1 *= 2;
            Z -= Z1;
        }
    }
    seq->used_layer++;

    index = 0;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
            cx(g, ancilla + index, factor + i);

            ctrls[index] = ancilla + index;
            ctrls[Zeros + index] = ancilla + Zeros + index;
            index++;
        }
    }
    seq->used_layer++;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
            x(g, factor + i);
        }
    }
    seq->used_layer++;

    return seq;
}
