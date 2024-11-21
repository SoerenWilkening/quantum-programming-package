//
// Created by Sören Wilkening on 27.10.24.
//

#include "gate.h"

void print_dash(int k){
    for (int i = 0; i < k; ++i) {
        printf("\u2500");
    }
}

void print_empty(int k){
    for (int i = 0; i < k; ++i) {
        printf(" ");
    }
}


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
    if (seq == NULL) return;
    int count = 0;
    for (int layer = 0; layer < seq->used_layer; ++layer) {
        count += seq->gates_per_layer[layer];
    }
    printf("cycles = %d\n", seq->used_layer);
    printf("gates = %d\n", count);
    if (seq->used_layer > 300) return;


    int width[count];
    int counter = 0;
    for (int layer_index = 0; layer_index < seq->used_layer; ++layer_index) {
        for (int gate_index = 0; gate_index < seq->gates_per_layer[layer_index]; ++gate_index) {
            if (seq->seq[layer_index][gate_index].Gate == P){
                width[counter++] = 8;
            }else{
                width[counter++] = 3;
            }
        }
    }


    for (int qubit = 0; qubit < 4 * INTEGERSIZE + 2; ++qubit) {
        counter = 0;
        for (int layer = 0; layer < seq->used_layer; ++layer) {
            for (int gate = 0; gate < seq->gates_per_layer[layer]; ++gate) {
                int skip_dash = 0;
                gate_t *g = &seq->seq[layer][gate];
                if ((g->NumControls > 0) && g->Control[0] == qubit || (g->NumControls > 1) && g->Control[1] == qubit) {
                    printf("@");
                } else if (g->Target == qubit) {
                    switch (g->Gate) {
                        case X:
                            printf("X");
                            break;
                        case H:
                            printf("H");
                            break;
                        case P:
                            printf("P%5.1f", g->GateValue);
                            print_dash(1);
                            skip_dash = 1;
                            break;
                        case Z:
                            printf("Z");
                            break;
                        case M:
                            printf("M");
                            break;
                    }
                } else if (qubit > MinQubit(g) && qubit < MaxQubit(g)) {
                    printf("\xE2\x94\x82");
                }
                else print_dash(1);
                if (width[counter] == 3) print_dash(1);
                else if(skip_dash == 0) print_dash(6);
                counter++;
            }
            printf("\u250A");
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

void p(gate_t *g, qubit_t target, double value) {
    g->Gate = P;
    g->GateValue = value;
    g->Target = target;
    g->NumControls = 0;
}

void cx(gate_t *g, qubit_t target, qubit_t control) {
    g->Gate = X;
    g->Target = target;
    g->NumControls = 1;
    g->Control[0] = control;
}

void ccx(gate_t *g, qubit_t target, qubit_t control1, qubit_t control2) {
    g->Gate = X;
    g->Target = target;
    g->NumControls = 2;
    g->Control[0] = control1;
    g->Control[1] = control2;
}

sequence_t *cx_gate() {
    sequence_t *seq = malloc(sizeof(sequence_t *));

    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer[0] = 1;
    cx(&seq->seq[0][0], 0, 1);

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
        memset(qft->gates_per_layer, 0, qft->num_layer * sizeof(num_t));
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
        memset(qft->gates_per_layer, 0, qft->num_layer * sizeof(num_t));
    }

    for (int j = 0; j < INTEGERSIZE; ++j) {
        for (int i = 0; i < INTEGERSIZE - 1 - j; ++i) {
            num_t layer = qft->used_layer + 2 * INTEGERSIZE - 1 - (2 * j + i + 1) - 1;
            cp(&qft->seq[layer][qft->gates_per_layer[layer]++], j, j + i + 1, -2 * M_PI / pow(2, i + 1));
        }
        num_t layer = qft->used_layer + 2 * INTEGERSIZE - 1 - 2 * j - 1;
        h(&qft->seq[layer][qft->gates_per_layer[layer]++], j);
    }
    qft->used_layer += 2 * INTEGERSIZE - 1;

    return qft;
}

bool_t is_inverse(gate_t *G1, gate_t *G2) {
    if (G1->Target != G2->Target) return false;
    if (G1->NumControls != G2->NumControls) return false;
    for (int i = 0; i < G1->NumControls; ++i) if (G1->Control[i] != G2->Control[i]) return false;
    if (G1->Gate != G2->Gate) return false;
    if (G1->Gate == P) { if (G1->GateValue != -G2->GateValue) return false; }
    else if (G1->GateValue != G2->GateValue) return false;

    return true;
}