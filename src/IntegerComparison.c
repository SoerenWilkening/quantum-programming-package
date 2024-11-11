//
// Created by Sören Wilkening on 09.11.24.
//

#include "../include/IntegerComparison.h"


sequence_t *QQ_equal() {
    sequence_t *eq = malloc(sizeof(sequence_t));

    return eq;
}

sequence_t *CQ_equal() {
    sequence_t *seq = malloc(sizeof(sequence_t));

    element_t *classical_element;
    element_t *quantum_element;
    int factor = 1;

    if (stack.GPR2[0].qualifier == Qu) {
        quantum_element = stack.GPR2;
        classical_element = stack.GPR3;
    } else {
        quantum_element = stack.GPR3;
        classical_element = stack.GPR2;
        factor = 1 + INTEGERSIZE;
    }

    int *bin = two_complement(*classical_element->c_address, INTEGERSIZE);
    int Zeros = 0;
    for (int i = 0; i < INTEGERSIZE; ++i) Zeros += bin[i];

    seq->seq = malloc(sizeof(gate_t *));
    for (int i = 0; i < ceil(log2(Zeros + 1)); ++i) {
        seq->seq[i] = malloc(Zeros * sizeof(gate_t));
    }
    seq->gates_per_layer = malloc(ceil(log2(Zeros + 1)) * sizeof(num_t));
    seq->used_layer = 0;
    seq->num_layer = 1;
    for (int i = 0; i < ceil(log2(Zeros + 1)); ++i) {
        seq->gates_per_layer[i] = 0;
    }

    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
            x(g, factor + i);
        }
    }
    seq->used_layer++;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        if (bin[i] == 0) {
            gate_t *g = &seq->seq[1][seq->gates_per_layer[1]++];
            cx(g, 2 * INTEGERSIZE + 1 + i, factor + i);
        }
    }
    seq->used_layer++;

    return seq;
}

sequence_t *CC_equal() {
    *stack.GPR1[0].c_address = *stack.GPR2[0].c_address == *stack.GPR3[0].c_address;
    return NULL;
}