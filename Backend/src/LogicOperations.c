//
// Created by Sören Wilkening on 05.11.24.
//

#include "LogicOperations.h"

sequence_t *void_seq(){
	return NULL;
}


sequence_t *not_seq() {
    int number = INTEGERSIZE;
    if (stack.GPR1[0].type == BOOLEAN) number = 1;

    sequence_t *seq = malloc(sizeof(sequence_t));

    seq->gates_per_layer[0] = number;
    seq->used_layer = 1;
    seq->num_layer = 1;
    for (int i = 0; i < number; ++i) {
        x(&seq->seq[0][i], i);
    }
    return seq;
}


sequence_t *and_sequence() {
    if (stack.GPR2[0].qualifier == Cl && stack.GPR3[0].qualifier == Cl) {
        // classical and
        *stack.GPR1[0].c_address = (*stack.GPR2[0].c_address) & (*stack.GPR3[0].c_address);
        return NULL;
    } else if (stack.GPR2[0].qualifier == Cl || stack.GPR3[0].qualifier == Cl) {
        // semiclassical and
        element_t *classical_element;
        element_t *quantum_element;
        int factor = 1;

        if (stack.GPR2[0].qualifier == Qu) {
            quantum_element = stack.GPR2;
            classical_element = stack.GPR3;
        } else {
            quantum_element = stack.GPR3;
            classical_element = stack.GPR2;
            factor = 2;
        }

        if (quantum_element->type == BOOLEAN) {
            if (*classical_element->c_address == 0) return NULL;
            return cx_gate();
        }

        int *bin = two_complement(*classical_element->c_address, INTEGERSIZE);
        int Non_zero = 0;
        for (int i = 0; i < INTEGERSIZE; ++i) Non_zero += bin[i];

        sequence_t *seq = malloc(sizeof(sequence_t *));
        seq->used_layer = 1;
        seq->num_layer = 1;
        seq->gates_per_layer[0] = 0;

        for (int i = 0; i < INTEGERSIZE; ++i) {
            int control = factor * INTEGERSIZE + i;
            int target = i;
            if (bin[i] == 1) {
                gate_t *g = &seq->seq[0][seq->gates_per_layer[0]++];
                cx(g, target, control);
            }
        }
        free(bin);

        return seq;
    }
    // pure quantum
    sequence_t *seq = malloc(sizeof(sequence_t *));

    seq->used_layer = 1;
    seq->num_layer = 1;
    int number = INTEGERSIZE;
    if (stack.GPR1[0].type == BOOLEAN) number = 1;
    seq->gates_per_layer[0] = number;
    for (int i = 0; i < number; ++i) {
        ccx(&seq->seq[0][i], i, number + i, 2 * number + i);
    }

    return seq;
}

sequence_t *branch(){
    sequence_t *seq = malloc(sizeof(sequence_t *));

    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer[0] = 1;

    seq->seq[0][0].Gate = H;
    seq->seq[0][0].Target = 0;
    seq->seq[0][0].NumControls = 0;
    if (stack.GPC[0].type != UNINITIALIZED){
        seq->seq[0][0].NumControls = 1;
        seq->seq[0][0].Control[0] = 1;
    }
    return seq;
}