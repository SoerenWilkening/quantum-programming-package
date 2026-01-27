//
// Created by Sören Wilkening on 27.10.24.
//

#include "gate.h"

void print_dash(int k) {
    for (int i = 0; i < k; ++i) {
        printf("\u2500");
        //	    printf("-");
    }
}
void print_empty(int k) {
    for (int i = 0; i < k; ++i) {
        printf(" ");
    }
}
qubit_t min_qubit(gate_t *g) {
    qubit_t min = g->Target;
    for (int i = 0; i < g->NumControls; ++i) {
        if (g->Control[i] < min) {
            min = g->Control[i];
        }
    }
    return min;
}
qubit_t max_qubit(gate_t *g) {
    qubit_t max = g->Target;
    for (int i = 0; i < g->NumControls; ++i) {
        if (g->Control[i] > max) {
            max = g->Control[i];
        }
    }
    return max;
}
void print_sequence(sequence_t *seq) {
    if (seq == NULL)
        return;
    int count = 0;
    for (int layer = 0; layer < seq->used_layer; ++layer) {
        count += seq->gates_per_layer[layer];
    }
    printf("cycles = %d\n", seq->used_layer);
    printf("gates = %d\n", count);
    if (seq->used_layer > 300)
        return;

    int width[count];
    int counter = 0;
    for (int layer_index = 0; layer_index < seq->used_layer; ++layer_index) {
        for (int gate_index = 0; gate_index < seq->gates_per_layer[layer_index]; ++gate_index) {
            if (seq->seq[layer_index][gate_index].Gate == P) {
                width[counter++] = 8;
            } else {
                width[counter++] = 3;
            }
        }
    }

    for (int qubit = 0; qubit < 4 * INTEGERSIZE + 2; ++qubit) {
        printf("%3d ", qubit + 1);
        counter = 0;
        for (int layer = 0; layer < seq->used_layer; ++layer) {
            for (int gate = 0; gate < seq->gates_per_layer[layer]; ++gate) {
                int skip_dash = 0;
                gate_t *g = &seq->seq[layer][gate];
                if ((g->NumControls > 0) && g->Control[0] == qubit ||
                    (g->NumControls > 1) && g->Control[1] == qubit) {
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
                } else if (qubit > min_qubit(g) && qubit < max_qubit(g)) {
                    printf("\xE2\x94\x82");
                } else
                    print_dash(1);
                if (width[counter] == 3)
                    print_dash(1);
                else if (skip_dash == 0)
                    print_dash(6);
                counter++;
            }
            printf("\u250A");
        }
        printf("\n");
    }
}

void print_gate(gate_t *g) {
    if (g == NULL)
        return;
    switch (g->Gate) {
    case X:
        printf("X->");
        break;
    case Y:
        printf("Y->");
        break;
    case H:
        printf("H->");
        break;
    case P:
        printf("P(%.1f)->", g->GateValue);
        break;
    case Z:
        printf("Z->");
        break;
    case M:
        printf("M->");
        break;
    }
    printf("(%d,", g->Target);
    for (int i = 0; i < g->NumControls; ++i) {
        printf("%d,", g->Control[i]);
    }
    printf(")\n");
}

void y(gate_t *g, qubit_t target) {
    g->Gate = Y;
    g->Target = target;
    g->NumControls = 0;
}
void cy(gate_t *g, qubit_t target, qubit_t control) {
    g->Gate = Y;
    g->Target = target;
    g->NumControls = 1;
    g->Control[0] = control;
}
void z(gate_t *g, qubit_t target) {
    g->Gate = Z;
    g->Target = target;
    g->NumControls = 0;
}
void cz(gate_t *g, qubit_t target, qubit_t control) {
    g->Gate = Z;
    g->Target = target;
    g->NumControls = 1;
    g->Control[0] = control;
}
void h(gate_t *g, qubit_t target) {
    g->Gate = H;
    g->Target = target;
    g->NumControls = 0;
    g->GateValue = 0;
}
void p(gate_t *g, qubit_t target, double value) {
    g->Gate = P;
    g->GateValue = value;
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
void x(gate_t *g, qubit_t target) {
    g->Gate = X;
    g->Target = target;
    g->GateValue = 1;
    g->NumControls = 0;
}
void cx(gate_t *g, qubit_t target, qubit_t control) {
    g->Gate = X;
    g->Target = target;
    g->NumControls = 1;
    g->GateValue = 1;
    g->Control[0] = control;
}
void ccx(gate_t *g, qubit_t target, qubit_t control1, qubit_t control2) {
    g->Gate = X;
    g->Target = target;
    g->NumControls = 2;
    g->Control[0] = control1;
    g->Control[1] = control2;
    g->GateValue = 1;
}
void mcx(gate_t *g, qubit_t target, qubit_t *controls, num_t num_controls) {
    // Multi-controlled X gate (n-controlled X)
    // For num_controls <= 2: uses Control[0], Control[1] static array
    // For num_controls > 2: allocates and populates large_control array
    g->Gate = X;
    g->Target = target;
    g->NumControls = num_controls;
    g->GateValue = 1;
    g->large_control = NULL;

    if (num_controls <= 2) {
        // Use static array for 0-2 controls
        if (num_controls >= 1) {
            g->Control[0] = controls[0];
        }
        if (num_controls >= 2) {
            g->Control[1] = controls[1];
        }
    } else {
        // Use dynamic array for >2 controls
        g->large_control = malloc(num_controls * sizeof(qubit_t));
        if (g->large_control != NULL) {
            // Copy all controls to large_control
            for (num_t i = 0; i < num_controls; i++) {
                g->large_control[i] = controls[i];
            }
            // Also copy first 2 to Control[] for backward compatibility
            g->Control[0] = controls[0];
            g->Control[1] = controls[1];
        }
    }
}

sequence_t *cx_gate() {
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
    cx(&seq->seq[0][0], INTEGERSIZE - 1, 2 * INTEGERSIZE - 1);

    return seq;
}
sequence_t *ccx_gate() {
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
    ccx(&seq->seq[0][0], INTEGERSIZE - 1, 2 * INTEGERSIZE - 1, 3 * INTEGERSIZE - 1);

    return seq;
}

sequence_t *QFT(sequence_t *qft, int num_qubits) {
    // OWNERSHIP: Modifies and returns the passed sequence_t* (does not allocate new sequence)
    // Caller retains ownership of the sequence
    //
    // Qubit layout for QFT(num_qubits):
    // - Qubits [0, num_qubits-1]: Target operands for QFT transform
    int offset = 0; // Variable-width support: qubits start at index 0

    num_t sum[2 * num_qubits - 1];
    memset(sum, 0, (2 * num_qubits - 1) * sizeof(num_t));
    // determine the number of gates per layer for the qft
    for (int j = 0; j < num_qubits; ++j) {
        sum[2 * j]++; // for the hadamards
        for (int i = 0; i < num_qubits - 1 - j; ++i)
            sum[2 * j + i + 1]++;
    }
    if (qft == NULL) {
        qft = malloc(sizeof(sequence_t));
        if (qft == NULL) {
            return NULL;
        }
        qft->gates_per_layer = calloc(2 * num_qubits - 1, sizeof(num_t));
        if (qft->gates_per_layer == NULL) {
            free(qft);
            return NULL;
        }
        qft->seq = calloc(2 * num_qubits - 1, sizeof(gate_t *));
        if (qft->seq == NULL) {
            free(qft->gates_per_layer);
            free(qft);
            return NULL;
        }
        for (int i = 0; i < 2 * num_qubits - 1; ++i) {
            if (i < num_qubits)
                qft->seq[i] = calloc(i + 1, sizeof(gate_t));
            else
                qft->seq[i] = calloc(2 * num_qubits - i, sizeof(gate_t));
            if (qft->seq[i] == NULL) {
                for (int j = 0; j < i; ++j) {
                    free(qft->seq[j]);
                }
                free(qft->seq);
                free(qft->gates_per_layer);
                free(qft);
                return NULL;
            }
        }
        qft->used_layer = 0;
        qft->num_layer = 2 * num_qubits - 1;
        memset(qft->gates_per_layer, 0, qft->num_layer * sizeof(num_t));
    }
    memcpy(&qft->gates_per_layer[qft->used_layer], sum, (2 * num_qubits - 1) * sizeof(num_t));

    memset(sum, 0, (2 * num_qubits - 1) * sizeof(num_t));
    for (int j = 0; j < num_qubits; ++j) {
        h(&qft->seq[qft->used_layer + 2 * j][sum[2 * j]], offset + j);
        sum[2 * j]++;
        for (int i = 0; i < num_qubits - 1 - j; ++i) {
            cp(&qft->seq[qft->used_layer + 2 * j + i + 1][sum[2 * j + i + 1]], offset + j,
               offset + j + i + 1, M_PI / pow(2, i + 1));
            sum[2 * j + i + 1]++;
        }
    }
    qft->used_layer += 2 * num_qubits - 1;

    return qft;
}

sequence_t *QFT_inverse(sequence_t *qft, int num_qubits) {
    // OWNERSHIP: Modifies and returns the passed sequence_t* (does not allocate new sequence)
    // Caller retains ownership of the sequence
    //
    // Qubit layout for QFT_inverse(num_qubits):
    // - Qubits [0, num_qubits-1]: Target operands for inverse QFT transform
    int offset = 0; // Variable-width support: qubits start at index 0

    // determine the number of gates per layer for the qft
    num_t sum[2 * num_qubits - 1];
    memset(sum, 0, (2 * num_qubits - 1) * sizeof(num_t));
    for (int j = 0; j < num_qubits; ++j) {
        sum[2 * j]++; // for the hadamards
        for (int i = 0; i < num_qubits - 1 - j; ++i)
            sum[2 * j + i + 1]++;
    }
    if (qft == NULL) {
        qft = malloc(sizeof(sequence_t));
        if (qft == NULL) {
            return NULL;
        }
        qft->gates_per_layer = calloc(2 * num_qubits - 1, sizeof(num_t));
        if (qft->gates_per_layer == NULL) {
            free(qft);
            return NULL;
        }
        qft->seq = calloc(2 * num_qubits - 1, sizeof(gate_t *));
        if (qft->seq == NULL) {
            free(qft->gates_per_layer);
            free(qft);
            return NULL;
        }
        for (int i = 0; i < 2 * num_qubits - 1; ++i) {
            if (i < num_qubits)
                qft->seq[i] = calloc(i + 1, sizeof(gate_t));
            else
                qft->seq[i] = calloc(2 * num_qubits - i, sizeof(gate_t));
            if (qft->seq[i] == NULL) {
                for (int j = 0; j < i; ++j) {
                    free(qft->seq[j]);
                }
                free(qft->seq);
                free(qft->gates_per_layer);
                free(qft);
                return NULL;
            }
        }
        qft->used_layer = 0;
        qft->num_layer = 2 * num_qubits - 1;
        memset(qft->gates_per_layer, 0, qft->num_layer * sizeof(num_t));
    }

    for (int j = 0; j < num_qubits; ++j) {
        for (int i = 0; i < num_qubits - 1 - j; ++i) {
            num_t layer = qft->used_layer + 2 * num_qubits - 1 - (2 * j + i + 1) - 1;
            cp(&qft->seq[layer][qft->gates_per_layer[layer]++], offset + j, offset + (j + i + 1),
               -M_PI / pow(2, i + 1));
        }
        num_t layer = qft->used_layer + 2 * num_qubits - 1 - 2 * j - 1;
        h(&qft->seq[layer][qft->gates_per_layer[layer]++], offset + j);
    }
    qft->used_layer += 2 * num_qubits - 1;

    return qft;
}

bool gates_are_inverse(gate_t *G1, gate_t *G2) {
    if (G2 == NULL)
        return false;
    if (G1->Target != G2->Target)
        return false;
    if (G1->NumControls != G2->NumControls)
        return false;
    if (G1->Gate != G2->Gate)
        return false;
    if (G1->Gate == P) {
        if (G1->GateValue != -G2->GateValue)
            return false;
    } else if (G1->GateValue != G2->GateValue)
        return false;
    for (int i = 0; i < G1->NumControls; ++i)
        if (G1->Control[i] != G2->Control[i])
            return false;

    return true;
}

bool gates_commute(gate_t *g1, gate_t *g2) {
    if (g2 == NULL)
        return true;
    if (g1->NumControls > 0 && g2->NumControls > 0 && g1->Target != g2->Target)
        return true;
    switch (g1->Gate) {
    case P:
        if (g2->Gate == P)
            return true;
        if (g2->Gate == Z)
            return true;
        if (g2->Gate == X && g1->Target != g2->Target)
            return true; // does only apply, when targets dont overlap
        break;
    case X:
        if (g2->Gate == X && g1->Target == g2->Target)
            return true; // does not apply, when target and control overlap
        break;
    case H:
        if (g2->Gate == H && g1->Target == g2->Target)
            return true; // does not apply, when target and control overlap
        break;
    case Z:
        if (g2->Gate == P)
            return true;
        if (g2->Gate == Z)
            return true;
        if (g2->Gate == X && g1->Target != g2->Target)
            return true; // it connect to one of the controls
        break;
    }
    return false;
}