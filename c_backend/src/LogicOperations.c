//
// Created by Sören Wilkening on 05.11.24.
//

#include "LogicOperations.h"
#include "execution.h"

sequence_t *void_seq() {
    // OWNERSHIP: No sequence returned
    return NULL;
}

// jmp_seq removed (Phase 11) - manipulated global state for control flow that's no longer used

sequence_t *branch_seq() {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    seq->used_layer = 1;
    seq->num_layer = 1;
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
    seq->gates_per_layer[0] = 1;

    seq->seq[0][0].Gate = H;
    seq->seq[0][0].Target = INTEGERSIZE - 1;
    seq->seq[0][0].NumControls = 0;
    return seq;
}
sequence_t *ctrl_branch_seq() {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    seq->used_layer = 1;
    seq->num_layer = 1;
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
    seq->gates_per_layer[0] = 1;

    seq->seq[0][0].Gate = H;
    seq->seq[0][0].Target = INTEGERSIZE - 1;
    seq->seq[0][0].NumControls = 2 * INTEGERSIZE - 1;
    seq->seq[0][0].Control[0] = 1;
    return seq;
}

// not_seq removed (Phase 11) - purely classical, no quantum gate generation

sequence_t *q_not_seq() {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    //	int number = INTEGERSIZE;

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

    seq->gates_per_layer[0] = 1;
    seq->used_layer = 1;
    seq->num_layer = 1;
    int counter = 0;
    for (int i = INTEGERSIZE - 1; i < INTEGERSIZE; ++i) {
        x(&seq->seq[0][counter++], i);
    }
    return seq;
}
sequence_t *cq_not_seq() {
    //	int number = INTEGERSIZE;

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

    for (int i = 0; i < 1; ++i)
        seq->gates_per_layer[i] = 0;
    seq->used_layer = 0;
    seq->num_layer = 1;
    for (int i = INTEGERSIZE - 1; i < INTEGERSIZE; ++i) {
        cx(&seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++], i,
           2 * INTEGERSIZE - 1);
        seq->used_layer++;
    }
    return seq;
}

sequence_t *Q_not(int bits) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    // Width-parameterized NOT: applies X gate to each bit (all in parallel, O(1) depth)
    //
    // Qubit layout for Q_not(bits):
    // - Qubits [0, bits-1]: Target operand (inverted in place)

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    seq->num_layer = 1;
    seq->used_layer = 1;
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
    seq->seq[0] = calloc(bits, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }

    seq->gates_per_layer[0] = bits;
    for (int i = 0; i < bits; ++i) {
        x(&seq->seq[0][i], i);
    }

    return seq;
}

sequence_t *cQ_not(int bits) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    // Width-parameterized controlled NOT: applies CX gate to each bit (sequential, O(bits) depth)
    //
    // Qubit layout for cQ_not(bits):
    // - Qubits [0, bits-1]: Target operand (inverted in place when control is |1>)
    // - Qubit [bits]: Control qubit

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    seq->num_layer = bits;
    seq->used_layer = bits;
    seq->gates_per_layer = calloc(bits, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(bits, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < bits; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    for (int i = 0; i < bits; ++i) {
        seq->gates_per_layer[i] = 1;
        cx(&seq->seq[i][0], i, bits);
    }

    return seq;
}

sequence_t *Q_xor(int bits) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    // Width-parameterized XOR: applies CNOT gates (all in parallel, O(1) depth)
    // Computes target ^= source in-place
    //
    // Qubit layout for Q_xor(bits):
    // - Qubits [0, bits-1]: Target operand (modified in place: target ^= source)
    // - Qubits [bits, 2*bits-1]: Source operand (unchanged)

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    seq->num_layer = 1;
    seq->used_layer = 1;
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
    seq->seq[0] = calloc(bits, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }

    seq->gates_per_layer[0] = bits;
    for (int i = 0; i < bits; ++i) {
        // CNOT: target = i, control = bits + i
        // This performs target[i] ^= source[i]
        cx(&seq->seq[0][i], i, bits + i);
    }

    return seq;
}

sequence_t *cQ_xor(int bits) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    // Width-parameterized controlled XOR: applies Toffoli gates (sequential, O(bits) depth)
    // Computes target ^= source only when control is |1>
    //
    // Qubit layout for cQ_xor(bits):
    // - Qubits [0, bits-1]: Target operand (modified in place when control is |1>)
    // - Qubits [bits, 2*bits-1]: Source operand (unchanged)
    // - Qubit [2*bits]: Control qubit

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    seq->num_layer = bits;
    seq->used_layer = bits;
    seq->gates_per_layer = calloc(bits, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(bits, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < bits; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    for (int i = 0; i < bits; ++i) {
        seq->gates_per_layer[i] = 1;
        // Toffoli: target = i, control1 = bits + i (source), control2 = 2*bits (control qubit)
        ccx(&seq->seq[i][0], i, bits + i, 2 * bits);
    }

    return seq;
}

// and_seq removed (Phase 11) - purely classical, no quantum gate generation

sequence_t *q_and_seq(int bits, int classical_value) {
    // semiclassical and
    // -> GRP2 always has to be the quantum element
    int number = bits;

    int *bin = two_complement(classical_value, INTEGERSIZE);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }
    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer = calloc(1, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq = calloc(1, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq[0] = calloc(INTEGERSIZE, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < INTEGERSIZE; ++i)
        seq->gates_per_layer[i] = 0;

    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        if (bin[i] == 1) {
            int control = INTEGERSIZE + i;
            int target = i;
            gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
            cx(g, target, control);
        }
    }
    free(bin);
    return seq;
}
sequence_t *qq_and_seq() {
    // pure quantum
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    //	int number = INTEGERSIZE;
    //	printf("%d\n", number);

    seq->used_layer = 1;
    seq->num_layer = 1;
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

    seq->gates_per_layer[0] = 1;
    int counter = 0;
    //	for (int i = number - 1; i < INTEGERSIZE; ++i) {
    ccx(&seq->seq[0][counter++], INTEGERSIZE - 1, 2 * INTEGERSIZE - 1, 3 * INTEGERSIZE - 1);
    //	}

    return seq;
}
sequence_t *cq_and_seq(int bits, int classical_value) {
    // semiclassical and
    // -> GRP2 always has to be the quantum element
    int number = bits;

    int *bin = two_complement(classical_value, INTEGERSIZE);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }
    seq->used_layer = 0;
    seq->num_layer = INTEGERSIZE;
    seq->gates_per_layer = calloc(INTEGERSIZE, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq = calloc(INTEGERSIZE, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < INTEGERSIZE; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
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

    for (int i = 0; i < INTEGERSIZE; ++i)
        seq->gates_per_layer[i] = 0;

    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        if (bin[i] == 1) {
            gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
            ccx(g, i, INTEGERSIZE + i, 4 * INTEGERSIZE - 1);
            seq->used_layer++;
        }
    }
    free(bin);
    return seq;
}
sequence_t *cqq_and_seq(int bits) {
    // pure quantum
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    int number = bits;

    seq->used_layer = 0;
    seq->num_layer = 3 * INTEGERSIZE;
    seq->gates_per_layer = calloc(3 * INTEGERSIZE, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(3 * INTEGERSIZE, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < 3 * INTEGERSIZE; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    for (int i = 0; i < 3 * INTEGERSIZE; ++i)
        seq->gates_per_layer[i] = 0;

    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
        seq->used_layer++;
        ccx(g, 4 * INTEGERSIZE, INTEGERSIZE + i, 2 * INTEGERSIZE);

        g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
        seq->used_layer++;
        ccx(g, i, 4 * INTEGERSIZE, 4 * INTEGERSIZE - 1);

        g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
        seq->used_layer++;
        ccx(g, 4 * INTEGERSIZE, INTEGERSIZE + i, 2 * INTEGERSIZE);
    }

    return seq;
}

// xor_seq removed (Phase 11) - purely classical, no quantum gate generation

sequence_t *q_xor_seq(int bits, int classical_value) {
    // pure quantum

    int number = bits;

    int *bin = two_complement(classical_value, INTEGERSIZE);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }
    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer = calloc(1, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq = calloc(1, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq[0] = calloc(INTEGERSIZE, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }

    seq->gates_per_layer[0] = 0;
    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        if (bin[i] == 1) {
            gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
            x(g, i);
        }
    }

    free(bin);
    return seq;
}
sequence_t *cq_xor_seq(int bits, int classical_value) {
    // pure quantum

    int number = bits;
    int *bin = two_complement(classical_value, INTEGERSIZE);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }
    seq->used_layer = 0;
    seq->num_layer = INTEGERSIZE;
    seq->gates_per_layer = calloc(INTEGERSIZE, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq = calloc(INTEGERSIZE, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < INTEGERSIZE; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
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

    for (int i = 0; i < INTEGERSIZE; ++i)
        seq->gates_per_layer[i] = 0;
    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        if (bin[i] == 1) {
            gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
            cx(g, i, 2 * INTEGERSIZE - 1);
            seq->used_layer++;
        }
    }

    free(bin);
    return seq;
}
sequence_t *qq_xor_seq(int bits) {
    // pure quantum
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    int number = bits;

    seq->used_layer = 1;
    seq->num_layer = 1;
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
    seq->seq[0] = calloc(INTEGERSIZE, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }

    seq->gates_per_layer[0] = INTEGERSIZE - number + 1;
    int counter = 0;
    for (int i = number - 1; i < INTEGERSIZE; ++i)
        cx(&seq->seq[0][counter++], i, INTEGERSIZE + i);

    return seq;
}
sequence_t *cqq_xor_seq(int bits) {
    // pure quantum
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    int number = bits;

    seq->used_layer = 0;
    seq->num_layer = INTEGERSIZE;
    seq->gates_per_layer = calloc(INTEGERSIZE, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(INTEGERSIZE, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < INTEGERSIZE; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    for (int i = 0; i < INTEGERSIZE; ++i) {
        seq->gates_per_layer[i] = 0;
    }
    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        ccx(&seq->seq[seq->used_layer][0], i, INTEGERSIZE + i, 3 * INTEGERSIZE - 1);
        seq->gates_per_layer[seq->used_layer]++;
        seq->used_layer++;
    }

    return seq;
}

// or_seq removed (Phase 11) - purely classical, no quantum gate generation

sequence_t *q_or_seq(int bits, int classical_value) {
    // pure quantum

    int number = bits;
    int *bin = two_complement(classical_value, INTEGERSIZE);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }
    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer = calloc(3, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq = calloc(1, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq[0] = calloc(2 * INTEGERSIZE, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }

    seq->gates_per_layer[0] = 0;
    seq->gates_per_layer[1] = 0;
    seq->gates_per_layer[2] = 0;

    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
            cx(g, i, INTEGERSIZE + i);
        }
    }

    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        if (bin[i] == 1) {
            gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
            x(g, i);
        }
    }
    free(bin);
    return seq;
}
sequence_t *qq_or_seq() {
    // pure quantum

    //	int number = INTEGERSIZE;

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }
    seq->used_layer = 3;
    seq->num_layer = 3;
    seq->gates_per_layer = calloc(3, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(3, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < 3; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    seq->gates_per_layer[0] = 0;
    seq->gates_per_layer[1] = 0;
    seq->gates_per_layer[2] = 0;

    for (int i = INTEGERSIZE - 1; i < INTEGERSIZE; ++i) {
        gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
        cx(g, i, INTEGERSIZE + i);
    }

    for (int i = INTEGERSIZE - 1; i < INTEGERSIZE; ++i) {
        gate_t *g = &seq->seq[1][seq->gates_per_layer[1]++];
        cx(g, i, 2 * INTEGERSIZE + i);
    }
    for (int i = INTEGERSIZE - 1; i < INTEGERSIZE; ++i) {
        gate_t *g = &seq->seq[2][seq->gates_per_layer[2]++];
        ccx(g, i, INTEGERSIZE + i, 2 * INTEGERSIZE + i);
    }

    return seq;
}

sequence_t *cq_or_seq(int bits, int classical_value) {
    // pure quantum

    int number = bits;

    int *bin = two_complement(classical_value, INTEGERSIZE);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }
    seq->num_layer = INTEGERSIZE;
    seq->used_layer = 0;
    seq->gates_per_layer = calloc(INTEGERSIZE, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq = calloc(INTEGERSIZE, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < INTEGERSIZE; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
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

    for (int i = 0; i < INTEGERSIZE; ++i)
        seq->gates_per_layer[i] = 0;

    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
            ccx(g, i, INTEGERSIZE + i, 2 * INTEGERSIZE - 1);
            seq->used_layer++;
        }
    }

    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        if (bin[i] == 1) {
            gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
            cx(g, i, 2 * INTEGERSIZE - 1);
            seq->used_layer++;
        }
    }
    free(bin);
    return seq;
}
sequence_t *cqq_or_seq(int bits) {
    // pure quantum

    int number = bits;

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }
    seq->used_layer = 0;
    seq->num_layer = 5 * INTEGERSIZE;
    seq->gates_per_layer = calloc(5 * INTEGERSIZE, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(5 * INTEGERSIZE, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < 5 * INTEGERSIZE; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    for (int i = 0; i < 5 * INTEGERSIZE; ++i) {
        seq->gates_per_layer[i] = 0;
    }
    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
        ccx(g, i, INTEGERSIZE + i, 4 * INTEGERSIZE - 1);
        seq->used_layer++;
    }
    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
        ccx(g, i, 2 * INTEGERSIZE + i, 4 * INTEGERSIZE - 1);
        seq->used_layer++;
    }
    for (int i = number - 1; i < INTEGERSIZE; ++i) {
        gate_t *g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
        ccx(g, 4 * INTEGERSIZE, 2 * INTEGERSIZE + i, 4 * INTEGERSIZE - 1);
        seq->used_layer++;

        g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
        ccx(g, i, 4 * INTEGERSIZE, INTEGERSIZE + i);
        seq->used_layer++;

        g = &seq->seq[seq->used_layer][seq->gates_per_layer[seq->used_layer]++];
        ccx(g, 4 * INTEGERSIZE, 2 * INTEGERSIZE + i, 4 * INTEGERSIZE - 1);
        seq->used_layer++;
    }

    return seq;
}

// ======================================================
// Width-Parameterized AND Operations
// ======================================================

sequence_t *Q_and(int bits) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    //
    // Width-parameterized quantum-quantum AND operation.
    // Applies Toffoli gates to compute bitwise AND into output ancilla.
    //
    // Qubit layout:
    // - [0, bits-1]: Output ancilla (pre-initialized to |0>)
    // - [bits, 2*bits-1]: Operand A
    // - [2*bits, 3*bits-1]: Operand B
    //
    // Result: output[i] = A[i] AND B[i] for each bit i

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    // All Toffoli gates can be applied in parallel (single layer)
    seq->used_layer = 1;
    seq->num_layer = 1;
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
    seq->seq[0] = calloc(bits, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }

    seq->gates_per_layer[0] = bits;

    // Apply Toffoli gate for each bit position
    for (int i = 0; i < bits; i++) {
        // target = i (output bit)
        // control1 = bits + i (operand A bit)
        // control2 = 2*bits + i (operand B bit)
        ccx(&seq->seq[0][i], i, bits + i, 2 * bits + i);
    }

    sequence_compute_total_gate_count(seq);
    return seq;
}

sequence_t *CQ_and(int bits, int64_t value) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    //
    // Width-parameterized classical-quantum AND operation.
    // For each bit where classical value is 1, copy quantum bit to output via CNOT.
    // For bits where classical value is 0, output remains |0> (0 AND x = 0).
    //
    // Qubit layout:
    // - [0, bits-1]: Output ancilla (pre-initialized to |0>)
    // - [bits, 2*bits-1]: Quantum operand
    //
    // Result: output[i] = classical_bit[i] AND quantum_bit[i]

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Convert classical value to binary
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    // All CNOT gates can be applied in parallel (single layer)
    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer = calloc(1, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq = calloc(1, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    // Allocate enough gates for all bits (some may be unused if value has 0s)
    seq->seq[0] = calloc(bits, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }

    seq->gates_per_layer[0] = 0;

    // Apply CNOT only for bits where classical value is 1
    // For classical 1: output = quantum bit (CNOT copies)
    // For classical 0: output stays |0> (no gate needed)
    // Note: two_complement returns MSB-first (bin[0]=MSB, bin[bits-1]=LSB)
    // but qubit_array uses LSB-first (index 0=LSB), so we use bin[bits-1-i]
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) {
            // target = i (output bit)
            // control = bits + i (quantum operand bit)
            cx(&seq->seq[0][seq->gates_per_layer[0]++], i, bits + i);
        }
    }

    free(bin);
    sequence_compute_total_gate_count(seq);
    return seq;
}

// ======================================================
// Width-Parameterized OR Operations
// ======================================================

sequence_t *Q_or(int bits) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    //
    // Width-parameterized quantum-quantum OR operation.
    // Uses the identity: A OR B = (A XOR B) XOR (A AND B)
    //                          = A XOR B XOR (A AND B)
    //
    // Circuit pattern (from existing qq_or_seq):
    // Layer 0: CNOT from A to output (copies A to output)
    // Layer 1: CNOT from B to output (XORs B into output, giving A XOR B)
    // Layer 2: Toffoli from A,B to output (adds A AND B)
    // Result: A XOR B XOR (A AND B) = A OR B
    //
    // Qubit layout:
    // - [0, bits-1]: Output ancilla (pre-initialized to |0>)
    // - [bits, 2*bits-1]: Operand A
    // - [2*bits, 3*bits-1]: Operand B
    //
    // Result: output[i] = A[i] OR B[i] for each bit i

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    // 3 layers: CNOT from A, CNOT from B, Toffoli from A and B
    seq->used_layer = 3;
    seq->num_layer = 3;
    seq->gates_per_layer = calloc(3, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(3, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < 3; ++i) {
        seq->seq[i] = calloc(bits, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    seq->gates_per_layer[0] = bits;
    seq->gates_per_layer[1] = bits;
    seq->gates_per_layer[2] = bits;

    // Layer 0: CNOT from A to output (output = A)
    for (int i = 0; i < bits; i++) {
        // target = i (output bit)
        // control = bits + i (operand A bit)
        cx(&seq->seq[0][i], i, bits + i);
    }

    // Layer 1: CNOT from B to output (output = A XOR B)
    for (int i = 0; i < bits; i++) {
        // target = i (output bit)
        // control = 2*bits + i (operand B bit)
        cx(&seq->seq[1][i], i, 2 * bits + i);
    }

    // Layer 2: Toffoli from A and B to output (output = A XOR B XOR (A AND B) = A OR B)
    for (int i = 0; i < bits; i++) {
        // target = i (output bit)
        // control1 = bits + i (operand A bit)
        // control2 = 2*bits + i (operand B bit)
        ccx(&seq->seq[2][i], i, bits + i, 2 * bits + i);
    }

    sequence_compute_total_gate_count(seq);
    return seq;
}

sequence_t *CQ_or(int bits, int64_t value) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    //
    // Width-parameterized classical-quantum OR operation.
    // For each bit:
    // - If classical bit is 1: output is always 1 (X gate sets to |1>)
    // - If classical bit is 0: output equals quantum bit (CNOT copies)
    //
    // Qubit layout:
    // - [0, bits-1]: Output ancilla (pre-initialized to |0>)
    // - [bits, 2*bits-1]: Quantum operand
    //
    // Result: output[i] = classical_bit[i] OR quantum_bit[i]

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Convert classical value to binary
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    // Single layer: X gates for classical 1s, CNOT for classical 0s
    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer = calloc(1, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq = calloc(1, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    // Allocate enough gates for all bits
    seq->seq[0] = calloc(bits, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }

    seq->gates_per_layer[0] = 0;

    // Apply gates based on classical bit values
    // Note: two_complement returns MSB-first (bin[0]=MSB, bin[bits-1]=LSB)
    // but qubit_array uses LSB-first (index 0=LSB), so we use bin[bits-1-i]
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) {
            // Classical 1: output is always 1 (1 OR x = 1)
            // Apply X gate to set output to |1>
            x(&seq->seq[0][seq->gates_per_layer[0]++], i);
        } else {
            // Classical 0: output equals quantum bit (0 OR x = x)
            // Apply CNOT to copy quantum bit to output
            // target = i (output bit)
            // control = bits + i (quantum operand bit)
            cx(&seq->seq[0][seq->gates_per_layer[0]++], i, bits + i);
        }
    }

    free(bin);
    sequence_compute_total_gate_count(seq);
    return seq;
}

// ======================================================
// Controlled Width-Parameterized AND Operations
// ======================================================

sequence_t *cQ_and(int bits) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    //
    // Controlled width-parameterized quantum-quantum AND operation.
    // Adds one external control qubit to every gate in Q_and.
    // Each Toffoli (2-controlled X) becomes a 3-controlled X (MCX).
    // Gates are sequential since they share the common control qubit.
    //
    // Qubit layout:
    // - [0, bits-1]: Output ancilla (pre-initialized to |0>)
    // - [bits, 2*bits-1]: Operand A
    // - [2*bits, 3*bits-1]: Operand B
    // - [3*bits]: External control qubit
    //
    // Result: output[i] = A[i] AND B[i] when control is |1>

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    // Each MCX gate gets its own layer (sequential due to shared control)
    seq->used_layer = bits;
    seq->num_layer = bits;
    seq->gates_per_layer = calloc(bits, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(bits, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < bits; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    qubit_t ext_ctrl = 3 * bits;
    for (int i = 0; i < bits; i++) {
        seq->gates_per_layer[i] = 1;
        // 3-controlled X: target = i, controls = {bits+i, 2*bits+i, ext_ctrl}
        qubit_t controls[3] = {bits + i, 2 * bits + i, ext_ctrl};
        mcx(&seq->seq[i][0], i, controls, 3);
    }

    sequence_compute_total_gate_count(seq);
    return seq;
}

sequence_t *cCQ_and(int bits, int64_t value) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    //
    // Controlled width-parameterized classical-quantum AND operation.
    // Adds one external control qubit to every gate in CQ_and.
    // Each CNOT becomes a Toffoli (CCX).
    // Gates are sequential since they share the common control qubit.
    //
    // Qubit layout:
    // - [0, bits-1]: Output ancilla (pre-initialized to |0>)
    // - [bits, 2*bits-1]: Quantum operand
    // - [2*bits]: External control qubit
    //
    // Result: output[i] = classical_bit[i] AND quantum_bit[i] when control is |1>

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Convert classical value to binary
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    // Count active bits (where classical value is 1)
    int active_bits = 0;
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) {
            active_bits++;
        }
    }

    // Handle edge case: no active bits
    if (active_bits == 0) {
        free(bin);
        sequence_t *seq = malloc(sizeof(sequence_t));
        if (seq == NULL) {
            return NULL;
        }
        seq->used_layer = 0;
        seq->num_layer = 1;
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
        seq->gates_per_layer[0] = 0;
        return seq;
    }

    int num_layers = active_bits;
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    seq->used_layer = num_layers;
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
        seq->seq[i] = calloc(1, sizeof(gate_t));
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

    qubit_t ext_ctrl = 2 * bits;
    int layer = 0;
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) {
            seq->gates_per_layer[layer] = 1;
            // Toffoli: target = i, control1 = bits+i, control2 = ext_ctrl
            ccx(&seq->seq[layer][0], i, bits + i, ext_ctrl);
            layer++;
        }
    }

    free(bin);
    sequence_compute_total_gate_count(seq);
    return seq;
}

// ======================================================
// Controlled Width-Parameterized OR Operations
// ======================================================

sequence_t *cQ_or(int bits) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    //
    // Controlled width-parameterized quantum-quantum OR operation.
    // Adds one external control qubit to every gate in Q_or.
    // Q_or has 3 phases: CNOT from A, CNOT from B, Toffoli from A,B.
    // Controlled: CNOTs become Toffolis, Toffolis become MCX(3).
    // All gates sequential since they share the common control qubit.
    //
    // Qubit layout:
    // - [0, bits-1]: Output ancilla (pre-initialized to |0>)
    // - [bits, 2*bits-1]: Operand A
    // - [2*bits, 3*bits-1]: Operand B
    // - [3*bits]: External control qubit
    //
    // Result: output[i] = A[i] OR B[i] when control is |1>

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        return NULL;
    }

    // 3 * bits layers: bits Toffolis (phase 1) + bits Toffolis (phase 2) + bits MCX(3) (phase 3)
    int total_layers = 3 * bits;
    seq->used_layer = total_layers;
    seq->num_layer = total_layers;
    seq->gates_per_layer = calloc(total_layers, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }
    seq->seq = calloc(total_layers, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < total_layers; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    qubit_t ext_ctrl = 3 * bits;
    int layer = 0;

    // Phase 1: Controlled CNOT from A to output -> Toffoli(output[i], A[i], ext_ctrl)
    for (int i = 0; i < bits; i++) {
        seq->gates_per_layer[layer] = 1;
        ccx(&seq->seq[layer][0], i, bits + i, ext_ctrl);
        layer++;
    }

    // Phase 2: Controlled CNOT from B to output -> Toffoli(output[i], B[i], ext_ctrl)
    for (int i = 0; i < bits; i++) {
        seq->gates_per_layer[layer] = 1;
        ccx(&seq->seq[layer][0], i, 2 * bits + i, ext_ctrl);
        layer++;
    }

    // Phase 3: Controlled Toffoli from A,B to output -> MCX(output[i], {A[i], B[i], ext_ctrl})
    for (int i = 0; i < bits; i++) {
        seq->gates_per_layer[layer] = 1;
        qubit_t controls[3] = {bits + i, 2 * bits + i, ext_ctrl};
        mcx(&seq->seq[layer][0], i, controls, 3);
        layer++;
    }

    sequence_compute_total_gate_count(seq);
    return seq;
}

sequence_t *cCQ_or(int bits, int64_t value) {
    // OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
    //
    // Controlled width-parameterized classical-quantum OR operation.
    // Adds one external control qubit to every gate in CQ_or.
    // X gates (for classical 1) become CX, CNOT gates (for classical 0) become Toffoli.
    // All gates sequential since they share the common control qubit.
    //
    // Qubit layout:
    // - [0, bits-1]: Output ancilla (pre-initialized to |0>)
    // - [bits, 2*bits-1]: Quantum operand
    // - [2*bits]: External control qubit
    //
    // Result: output[i] = classical_bit[i] OR quantum_bit[i] when control is |1>

    // Bounds check: valid widths are 1-64
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Convert classical value to binary
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    // Each bit produces one gate in its own layer (sequential due to shared control)
    seq->used_layer = bits;
    seq->num_layer = bits;
    seq->gates_per_layer = calloc(bits, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq = calloc(bits, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < bits; ++i) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
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

    qubit_t ext_ctrl = 2 * bits;
    for (int i = 0; i < bits; i++) {
        seq->gates_per_layer[i] = 1;
        if (bin[bits - 1 - i] == 1) {
            // Classical 1: X becomes CX(output[i], ext_ctrl)
            cx(&seq->seq[i][0], i, ext_ctrl);
        } else {
            // Classical 0: CNOT becomes Toffoli(output[i], quantum[i], ext_ctrl)
            ccx(&seq->seq[i][0], i, bits + i, ext_ctrl);
        }
    }

    free(bin);
    sequence_compute_total_gate_count(seq);
    return seq;
}
