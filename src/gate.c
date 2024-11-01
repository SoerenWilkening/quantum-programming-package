//
// Created by Sören Wilkening on 27.10.24.
//

#include "../QPU.h"

qubit_t MinQubit(gate_t *g) {
    qubit_t min = g->Target;
    for (int i = 0; i < g->NumControls; ++i) {
        if (g->Control[i] < min) {
            min = g->Control[i];
        }
    }
    return min;
}

qubit_t MaxQubit(gate_t *g) {
    qubit_t max = g->Target;
    for (int i = 0; i < g->NumControls; ++i) {
        if (g->Control[i] > max) {
            max = g->Control[i];
        }
    }
    return max;
}

void print_sequence(sequence_t *seq) {
    if (seq == NULL || seq->seq == NULL) return;
    if (seq->used_layer > 100) return;
    for (int qubit = 0; qubit < 2 * INTEGERSIZE + 2; ++qubit) {
        for (int layer = 0; layer < seq->used_layer; ++layer) {
            for (int gate = 0; gate < seq->gates_per_layer[layer]; ++gate) {
                gate_t *g = &seq->seq[layer][gate];
                if ((g->NumControls > 0) && g->Control[0] == qubit || (g->NumControls > 1) && g->Control[1] == qubit) {
                    printf("*------");
                } else if (g->Target == qubit) {
                    switch (g->Gate) {
                        case X:
                            printf("X------");
                            break;
                        case H:
                            printf("H------");
                            break;
                        case R:
                            printf("R_%2.0f---", g->GateValue);
                            break;
                        case Rx:
                            printf("Rx_%.1f_", g->GateValue);
                            break;
                        case Ry:
                            printf("Ry_%.1f_", g->GateValue);
                            break;
                        case Rz:
                            printf("Rz_%.1f_", g->GateValue);
                            break;
                        case P:
                            printf("P%5.1f-", g->GateValue);
                            break;
                        case Z:
                            printf("Z------");
                            break;
                        case M:
                            printf("M------");
                            break;
                    }
                } else if (qubit > MinQubit(g) && qubit < MaxQubit(g)) printf("|------");
                else printf("-------");
            }
        }
        printf("\n");
    }
}

void x(gate_t *g, qubit_t target) {
    g->Gate = X;
    g->Target = target;
    g->NumControls = 0;
}

void h(gate_t *g, qubit_t target) {
    g->Gate = H;
    g->Target = target;
    g->NumControls = 0;
}

void cp(gate_t *g, qubit_t target, qubit_t control, double value) {
    g->Gate = P;
    g->GateValue = value;
    g->Target = target;
    g->NumControls = 1;
    g->Control[0] = control;

}

void cx(gate_t *g, qubit_t target, qubit_t control) {
    g->Gate = X;
    g->Target = target;
    g->NumControls = 1;
    g->Control[0] = control;
}

sequence_t *cx_gate() {
//    printf("cx\n");
    sequence_t *seq = malloc(sizeof(sequence_t *));

    seq->seq = malloc(sizeof(gate_t *));
    seq->seq[0] = malloc(sizeof(gate_t));
    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer = malloc(sizeof(num_t));
    seq->gates_per_layer[0] = 1;
    seq->seq[0][0].Control[0] = 1;
    seq->seq[0][0].NumControls = 1;
    seq->seq[0][0].Target = 0;
    seq->seq[0][0].Gate = X;

    return seq;
}

sequence_t *not_seq() {
    int number = INTEGERSIZE;
    if (stack.GPR1[0].type == BOOL) number = 1;

    sequence_t *seq = malloc(sizeof(sequence_t));
    seq->gates_per_layer = malloc(sizeof(num_t));
    seq->gates_per_layer[0] = number;
    seq->seq = malloc(sizeof(gate_t *));
    seq->seq[0] = malloc(number * sizeof(gate_t));
    seq->used_layer = 1;
    seq->num_layer = 1;
    for (int i = 0; i < number; ++i) {
        x(&seq->seq[0][i], i);
    }
    return seq;
}

sequence_t *QFT(sequence_t *qft) {
    num_t sum[2 * INTEGERSIZE - 1];
    memset(sum, 0, (2 * INTEGERSIZE - 1) * sizeof(num_t));
    // determine the number of gates per layer for the qft
    for (int j = 0; j < INTEGERSIZE; ++j) {
        sum[2 * j]++; // for the hadamards
        for (int i = 0; i < INTEGERSIZE - 1 - j; ++i) sum[2 * j + i + 1]++;
    }
    if (qft == NULL) {
        qft = malloc(sizeof(sequence_t));
        qft->used_layer = 0;
        qft->num_layer = 2 * INTEGERSIZE - 1;
        qft->gates_per_layer = calloc(2 * INTEGERSIZE - 1, sizeof(num_t));

        // allocate space for every gate
        qft->seq = malloc((2 * INTEGERSIZE - 1) * sizeof(gate_t *));
        for (int i = 0; i < (2 * INTEGERSIZE - 1); ++i) qft->seq[i] = malloc(sum[i] * sizeof(gate_t));
    }
    memcpy(&qft->gates_per_layer[qft->used_layer], sum, (2 * INTEGERSIZE - 1) * sizeof(num_t));

    memset(sum, 0, (2 * INTEGERSIZE - 1) * sizeof(num_t));
    for (int j = 0; j < INTEGERSIZE; ++j) {
        h(&qft->seq[qft->used_layer + 2 * j][sum[2 * j]], j);
        sum[2 * j]++;
        for (int i = 0; i < INTEGERSIZE - 1 - j; ++i) {
            cp(&qft->seq[qft->used_layer + 2 * j + i + 1][sum[2 * j + i + 1]], j, j + i + 1, 2 * M_PI / pow(2, i + 1));
            sum[2 * j + i + 1]++;
        }
    }
    qft->used_layer += 2 * INTEGERSIZE - 1;

    return qft;
}

sequence_t *QFT_inverse(sequence_t *qft) {
    // determine the number of gates per layer for the qft
    num_t sum[2 * INTEGERSIZE - 1];
    memset(sum, 0, (2 * INTEGERSIZE - 1) * sizeof(num_t));
    for (int j = 0; j < INTEGERSIZE; ++j) {
        sum[2 * j]++; // for the hadamards
        for (int i = 0; i < INTEGERSIZE - 1 - j; ++i) sum[2 * j + i + 1]++;
    }
    if (qft == NULL) {
        qft = malloc(sizeof(sequence_t));
        qft->used_layer = 0;
        qft->num_layer = 2 * INTEGERSIZE - 1;
        qft->gates_per_layer = calloc(2 * INTEGERSIZE - 1, sizeof(num_t));

        // allocate space for every gate
        qft->seq = malloc((2 * INTEGERSIZE - 1) * sizeof(gate_t *));
        for (int i = 0; i < (2 * INTEGERSIZE - 1); ++i) qft->seq[i] = malloc(sum[i] * sizeof(gate_t));
    }
    memcpy(&qft->gates_per_layer[qft->used_layer], sum, (2 * INTEGERSIZE - 1) * sizeof(num_t));

    memset(sum, 0, (2 * INTEGERSIZE - 1) * sizeof(num_t));
    for (int j = 0; j < INTEGERSIZE; ++j) {
        for (int i = 0; i < INTEGERSIZE - 1 - j; ++i) {
            num_t layer = qft->used_layer + 2 * INTEGERSIZE - 1 - (2 * j + i + 1) - 1;
            num_t index = 2 * INTEGERSIZE - 1 - (2 * j + i + 1) - 1;
            cp(&qft->seq[layer][sum[index]], j, j + i + 1, -2 * M_PI / pow(2, i + 1));
            sum[index]++;
        }
        num_t layer = qft->used_layer + 2 * INTEGERSIZE - 1 - 2 * j - 1;
        num_t index = 2 * INTEGERSIZE - 1 - 2 * j - 1;
        h(&qft->seq[layer][sum[index]], j);
        sum[index]++;
    }
    qft->used_layer += 2 * INTEGERSIZE - 1;

    return qft;
}

sequence_t *QQ_add() {
//    printf("QQ_add\n");
    if (precompiled_QQ_add != NULL) return precompiled_QQ_add;

    sequence_t *add = malloc(sizeof(sequence_t));

    // allocate exact number of layer and enough gates per layer
    add->used_layer = 0;
    add->num_layer = 4 * INTEGERSIZE - 2 + INTEGERSIZE;
    add->gates_per_layer = calloc(add->num_layer, sizeof(num_t));
    add->seq = malloc(add->num_layer * sizeof(gate_t *));
    for (int i = 0; i < add->num_layer; ++i) {
        add->seq[i] = malloc(INTEGERSIZE * sizeof(gate_t));
    }
    QFT(add);
    num_t starting_layer = INTEGERSIZE;

    int rounds = 0;
    for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
        for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
            num_t layer = INTEGERSIZE + i + 2 * rounds;
            num_t target = i + rounds;
            num_t control = INTEGERSIZE + bit;
            double value = 2 * M_PI / (pow(2, i + 1));
            gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
            cp(g, target, control, value);
        }
        rounds++;
    }
    add->used_layer += INTEGERSIZE;
    QFT_inverse(add);
    precompiled_QQ_add = add;

    return add;
}

sequence_t *cQQ_add() {
//    printf("cQQ_add\n");
    if (precompiled_cQQ_add != NULL) return precompiled_cQQ_add;

    sequence_t *add = malloc(sizeof(sequence_t));

    // allocate exact number of layer and enough gates per layer
    add->used_layer = 0;
    add->num_layer = INTEGERSIZE * (INTEGERSIZE + 1) / 2 * 4 + 4 * INTEGERSIZE - 2 - INTEGERSIZE / 4 * 4 + 3;

    add->gates_per_layer = calloc(add->num_layer, sizeof(num_t));
    add->seq = malloc(add->num_layer * sizeof(gate_t *));
    for (int i = 0; i < add->num_layer; ++i) {
        add->seq[i] = malloc(INTEGERSIZE * sizeof(gate_t));
    }
    QFT(add);
    num_t starting_layer = INTEGERSIZE;

    int rounds = 0;
    int layer = starting_layer;
    for (int bit = (int) INTEGERSIZE - 1; bit >= 0; --bit) {
        for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
            double value = 2 * M_PI / (pow(2, i + 1)) / 2;
            gate_t *g = &add->seq[layer][add->gates_per_layer[layer]++];
            cp(g, i + rounds, 2 * INTEGERSIZE, value);
            layer++;

            g = &add->seq[layer][add->gates_per_layer[layer]++];
            cx(g, 2 * INTEGERSIZE, INTEGERSIZE + bit);
            layer++;

            g = &add->seq[layer][add->gates_per_layer[layer]++];
            cp(g, i + rounds, 2 * INTEGERSIZE, -value);
            layer++;

            g = &add->seq[layer][add->gates_per_layer[layer]++];
            cx(g, 2 * INTEGERSIZE, INTEGERSIZE + bit);
            layer++;

            g = &add->seq[layer][add->gates_per_layer[layer]++];
            cp(g, i + rounds, INTEGERSIZE + bit, value);
            if (bit == 1) layer++;
        }
        rounds++;
    }
    add->used_layer = add->num_layer - 2 * INTEGERSIZE + 1;
    QFT_inverse(add);
    precompiled_cQQ_add = add;

    return add;
}

sequence_t *CQ_add() {
    printf("CQ_add\n");
    sequence_t *add = malloc(sizeof(sequence_t));
    // allocate exact number of layer and enough gates per layer
    add->used_layer = 0;
    add->num_layer = 4 * INTEGERSIZE - 1;
    add->seq = malloc(add->num_layer * sizeof(gate_t *));
    add->gates_per_layer = calloc(add->num_layer, sizeof(num_t));
    for (int i = 0; i < add->num_layer; ++i) {
        add->seq[i] = malloc(INTEGERSIZE * sizeof(gate_t));
    }
    QFT(add);

    return add;
}

sequence_t *CC_add() {
    sequence_t *seq = malloc(sizeof(sequence_t));
    seq->seq = NULL;
    seq->used_layer = 0;
    seq->gates_per_layer = NULL;

    *stack.GPR1->c_address += *stack.GPR2->c_address;
    return seq;
}

void ADD(element_t *el1, element_t *el2) {
    if (el1->qualifier == Cl && el2->qualifier == Qu) exit(5);

    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];

    // copy values instruction registers
    MOV(ins->el1, el1, POINTER);
    MOV(ins->el2, el2, POINTER);

    // routine assignments
    ins->routine = NULL;
    if (el1->qualifier == Qu && el2->qualifier == Qu) {
        if (ins->control->type != UNINITIALIZED) ins->routine = cQQ_add;
        else ins->routine = QQ_add;
    } else if (el1->qualifier == Qu && el2->qualifier == Cl) ins->routine = CQ_add;
    else if (el1->qualifier == Cl && el2->qualifier == Cl) ins->routine = CC_add;
    else {
        printf("Cannot add quantum integer to classical integer!\n");
        exit(6);
    }
    ins->invert = NOTINVERTED;
    stack.instruction_counter++;
}

void SUB(element_t *el1, element_t *el2) {
    ADD(el1, el2);
    stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void IDIV(element_t *el1, element_t *el2){

}

void TSTBIT(element_t *el1, element_t *el2, int bit) {
    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
    MOV(ins->el1, el1, POINTER); // return value

    element_t *qbit = malloc(sizeof(element_t));
    qbit->qualifier = Qu;
    qbit->type = BOOL;
    qbit->q_address = el2->q_address + bit;

    MOV(ins->el1, qbit, POINTER);
    ins->routine = cx_gate;
    ins->invert = NOTINVERTED;
    stack.instruction_counter++;
}

void NOT(element_t *el1) {
    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
    MOV(ins->el1, el1, POINTER);

    ins->routine = not_seq;
    ins->invert = NOTINVERTED;
    stack.instruction_counter++;
}

void IF(element_t *el1) {
    MOV(stack.instruction_list[stack.instruction_counter].control, el1, POINTER);
}

void ELSE(element_t *el1) {
    NOT(el1);
    MOV(stack.instruction_list[stack.instruction_counter].control, el1, POINTER);
    NOT(el1);
}

void SHR(element_t *el1){
    el1->q_address++;
}

void SHL(element_t *el1){
    el1->q_address--;
}