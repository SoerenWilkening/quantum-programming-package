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
    if (seq->used_layer > 600) return;
//    for (int layer = 0; layer < seq->used_layer; ++layer) {
    for (int qubit = 0; qubit < 3 * INTEGERSIZE + 2; ++qubit) {
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
//            printf("\n");
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

    for (int j = 0; j < INTEGERSIZE; ++j) {
        for (int i = 0; i < INTEGERSIZE - 1 - j; ++i) {
            num_t layer = qft->used_layer + 2 * INTEGERSIZE - 1 - (2 * j + i + 1) - 1;
            num_t index = 2 * INTEGERSIZE - 1 - (2 * j + i + 1) - 1;
            cp(&qft->seq[layer][qft->gates_per_layer[layer]++], j, j + i + 1, -2 * M_PI / pow(2, i + 1));
        }
        num_t layer = qft->used_layer + 2 * INTEGERSIZE - 1 - 2 * j - 1;
        h(&qft->seq[layer][qft->gates_per_layer[layer]++], j);
    }
    qft->used_layer += 2 * INTEGERSIZE - 1;

    return qft;
}

sequence_t *QQ_add() {
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
    // Compute rotation angles
    int NonZeroCount = 0;
    int *bin = two_complement(*stack.GPR2[0].c_address, INTEGERSIZE);

    // Compute rotations for addition
    double *rotations = calloc(INTEGERSIZE, sizeof(double));
    for (int i = 0; i < INTEGERSIZE; ++i) {
        for (int j = 0; j < INTEGERSIZE - i; ++j) {
            rotations[j + i] += bin[INTEGERSIZE - i - 1] * 2 * M_PI / (Z * pow(2, j + 1));
        }
        if (rotations[i] != 0) NonZeroCount++;
    }
    free(bin);
    int start_layer = INTEGERSIZE;

    if (precompiled_cCQ_add) {
        sequence_t *add = precompiled_cCQ_add;

        for (int i = 0; i < INTEGERSIZE; ++i) {
            add->seq[start_layer + i][add->gates_per_layer[start_layer + i] - 1].GateValue = rotations[i];
        }
        free(rotations);
        return add;
    }

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

    for (int i = 0; i < INTEGERSIZE; ++i) {
        p(&add->seq[start_layer + i][add->gates_per_layer[start_layer + i]++], i, rotations[i]);
    }
    free(rotations);
    add->used_layer++;

    QFT_inverse(add);

    precompiled_CQ_add = add;
    return add;
}

sequence_t *cCQ_add() {
    // Compute rotation angles
    int NonZeroCount = 0;
    int *bin = two_complement(*stack.GPR2[0].c_address, INTEGERSIZE);

    // Compute rotations for addition
    double *rotations = calloc(INTEGERSIZE, sizeof(double));
    for (int i = 0; i < INTEGERSIZE; ++i) {
        for (int j = 0; j < INTEGERSIZE - i; ++j) {
            rotations[j + i] += bin[INTEGERSIZE - i - 1] * 2 * M_PI / (Z * pow(2, j + 1));
        }
        if (rotations[i] != 0) NonZeroCount++;
    }
    free(bin);
    int start_layer = INTEGERSIZE;

    if (precompiled_cCQ_add) {
        sequence_t *add = precompiled_cCQ_add;

        for (int i = 0; i < INTEGERSIZE; ++i) {
            add->seq[start_layer + i][add->gates_per_layer[start_layer + i] - 1].GateValue = rotations[i];
        }
        free(rotations);
        return add;
    }

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

    for (int i = 0; i < INTEGERSIZE; ++i) {
        cp(&add->seq[start_layer + i][add->gates_per_layer[start_layer + i]++], i, INTEGERSIZE + 1, rotations[i]);
    }
    free(rotations);
    add->used_layer++;

    QFT_inverse(add);

    precompiled_cCQ_add = add;
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
    } else if (el1->qualifier == Qu && el2->qualifier == Cl) {
        if (ins->control->type != UNINITIALIZED) ins->routine = cCQ_add;
        else ins->routine = CQ_add;
    } else if (el1->qualifier == Cl && el2->qualifier == Cl) ins->routine = CC_add;
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

sequence_t *QQ_mul() {
    sequence_t *mul = malloc(sizeof(sequence_t));

    mul->seq = malloc(
            3 * INTEGERSIZE * (INTEGERSIZE * (INTEGERSIZE + 1) / 2 + 1) * sizeof(gate_t));
    mul->used_layer = 0;
    mul->num_layer = 3 * INTEGERSIZE * (INTEGERSIZE * (INTEGERSIZE + 1) / 2 + 1);
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
            double value = M_PI / (pow(2, i + 1)) * (pow(2, INTEGERSIZE) - 1);
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, target, control, value);
            layer++;
        }
        rounds++;
    }
//    // intermediate step, C1X0 C0P_2(value/2)C1X0
//    for (int bit_int2 = 0; bit_int2 < INTEGERSIZE; ++bit_int2) {
//        double value_list[INTEGERSIZE];
//        int rounds = 0;
//        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
//
//            num_t control = INTEGERSIZE + bit;
//            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
//            cx(g, control, 2 * INTEGERSIZE + bit_int2);
//            layer++;
//            for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
//                num_t target = i + rounds;
//                double value = -M_PI / (pow(2, i + 1)) * pow(2, bit_int2);
//                gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
//                cp(g, target, control, value);
//                layer++;
//            }
//            g = &mul->seq[layer][mul->gates_per_layer[layer]++];
//            cx(g, control, 2 * INTEGERSIZE + bit_int2);
//            layer++;
//            rounds++;
//        }
//    }
    // intermediate step, C1X0 C0P_2(value/2)C1X0
    for (int bit_int2 = 0; bit_int2 < INTEGERSIZE; ++bit_int2) {
        double value_list[INTEGERSIZE];
        int rounds = 0;
        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cx(g, control, 2 * INTEGERSIZE + bit_int2);
            layer++;
        }
        rounds = 0;
        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            for (int i = 0; i < INTEGERSIZE - rounds; ++i) {
                num_t target = i + rounds;
                double value = -M_PI / (pow(2, i + 1)) * pow(2, bit_int2);
                gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
                cp(g, target, control, value);
                layer++;
            }
            layer -= INTEGERSIZE - rounds;
            rounds++;
        }
        layer += INTEGERSIZE;


        for (int bit = INTEGERSIZE - 1; bit >= 0; --bit) {
            num_t control = INTEGERSIZE + bit;
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cx(g, control, 2 * INTEGERSIZE + bit_int2);
            layer++;
        }
    }

    // the final step, C1P(value/2)
    rounds = INTEGERSIZE - 1;
    for (int bit = 0; bit < INTEGERSIZE; ++bit) {
        num_t control = INTEGERSIZE + bit;
        for (int i = INTEGERSIZE - rounds - 1; i >= 0; --i) {
            num_t target = i + rounds;
            double value = M_PI / (pow(2, i + 1)) * (pow(2, INTEGERSIZE) - 1);
            gate_t *g = &mul->seq[layer][mul->gates_per_layer[layer]++];
            cp(g, target, control, value);
            layer++;
        }
        rounds--;
        layer -= bit;
    }

    mul->used_layer = layer;
    QFT_inverse(mul);
    printf("%d\n", mul->used_layer);

    return mul;
}

//--------P -1.6------------------------------------------------------------------------------------------------------------------------P -3.1------------------------------------------------------------------------------------------------------------------------P -6.3------------------------------------------------------------------------------------------------------------------------P-12.6----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------P 23.6---------------P -0.8--------P -1.6--------P -3.1-H------
//--------|------P -0.8-----------------------------P -1.6------------------------------------------------------------------------------|------P -1.6-----------------------------P -3.1------------------------------------------------------------------------------|------P -3.1-----------------------------P -6.3------------------------------------------------------------------------------|------P -6.3-----------------------------P-12.6-----------------------------------------------------------------------------------------------------------------P 23.6---------------P 11.8--------|------P -1.6--------|------P -3.1-|------H------*-------------
//--------|------|------P -0.4----------------------|------P -0.8----------------------P -1.6-------------------------------------------|------|------P -0.8----------------------|------P -1.6----------------------P -3.1-------------------------------------------|------|------P -1.6----------------------|------P -3.1----------------------P -6.3-------------------------------------------|------|------P -3.1----------------------|------P -6.3----------------------P-12.6--------------------------------------------------P 23.6--------P 11.8--------|------P  5.9--------|------P -3.1-|------|------H------|------*------*---------------------------
//--------|------|------|------P -0.2---------------|------|------P -0.4---------------|------P -0.8---------------P -1.6---------------|------|------|------P -0.4---------------|------|------P -0.8---------------|------P -1.6---------------P -3.1---------------|------|------|------P -0.8---------------|------|------P -1.6---------------|------P -3.1---------------P -6.3---------------|------|------|------P -1.6---------------|------|------P -3.1---------------|------P -6.3---------------P-12.6--------P 23.6-P 11.8-|------P  5.9-|------P  2.9-|------|------H------|------*------|------*-------------*-----------------------------------------
//--------|------|------|------|--------------------|------|------|--------------------|------|-------------X------*------X-------------|------|------|------|--------------------|------|------|--------------------|------|-------------X------*------X-------------|------|------|------|--------------------|------|------|--------------------|------|-------------X------*------X-------------|------|------|------|--------------------|------|------|--------------------|------|-------------X------*------X------*------|------|------|------|------|------|------|-------------|-------------|--------------------------------------------------------------
//--------|------|------|------|--------------------|------|------|-------------X------*------*------X------|-------------|-------------|------|------|------|--------------------|------|------|-------------X------*------*------X------|-------------|-------------|------|------|------|--------------------|------|------|-------------X------*------*------X------|-------------|-------------|------|------|------|--------------------|------|------|-------------X------*------*------X------|-------------|-------------*------*------|------|------|------|------|-------------|-------------|--------------------------------------------------------------
//--------|------|------|------|-------------X------*------*------*------X------|--------------------|------|-------------|-------------|------|------|------|-------------X------*------*------*------X------|--------------------|------|-------------|-------------|------|------|------|-------------X------*------*------*------X------|--------------------|------|-------------|-------------|------|------|------|-------------X------*------*------*------X------|--------------------|------|-------------|---------------------------*------*------|------*------|-------------|-------------|--------------------------------------------------------------
//-X------*------*------*------*------X------|---------------------------|------|--------------------|------|-------------|------X------*------*------*------*------X------|---------------------------|------|--------------------|------|-------------|------X------*------*------*------*------X------|---------------------------|------|--------------------|------|-------------|------X------*------*------*------*------X------|---------------------------|------|--------------------|------|-------------|-----------------------------------------*-------------*-------------*-------------*--------------------------------------------------------------
//-*----------------------------------*------*---------------------------*------*--------------------*------*-------------*------|----------------------------------|------|---------------------------|------|--------------------|------|-------------|------|----------------------------------|------|---------------------------|------|--------------------|------|-------------|------|----------------------------------|------|---------------------------|------|--------------------|------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------
//-------------------------------------------------------------------------------------------------------------------------------*----------------------------------*------*---------------------------*------*--------------------*------*-------------*------|----------------------------------|------|---------------------------|------|--------------------|------|-------------|------|----------------------------------|------|---------------------------|------|--------------------|------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------
//-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------*----------------------------------*------*---------------------------*------*--------------------*------*-------------*------|----------------------------------|------|---------------------------|------|--------------------|------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------
//-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------*----------------------------------*------*---------------------------*------*--------------------*------*-------------*--------------------------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


void IMUL(element_t *el1, element_t *el2, element_t *res) {
    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];

    // copy values instruction registers
    MOV(ins->el1, res, POINTER);
    MOV(ins->el2, el1, POINTER);
    MOV(ins->el3, el2, POINTER);

    ins->routine = QQ_mul;

    ins->invert = NOTINVERTED;
    stack.instruction_counter++;
}


void IDIV(element_t *el1, element_t *el2, element_t *remainder) {
    // create IDIV sequence to Divide Aq / Bq
    element_t *Y = malloc(sizeof(element_t));
    memcpy(Y, el1, sizeof(element_t));
    for (int i = 1; i < INTEGERSIZE; ++i) {
        memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
        memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));

        SUB(Y, el2); // subtract Bq from Aq
        element_t *bit = bit_of_int(remainder, i - 1);
        TSTBIT(bit, Y, 0); // check if Aq is negative, stored in Cq
        IF(bit); // create control for the next instruction
        ADD(Y, el2); // Add bq back to Aq (controlled by Cq)
        NOT(bit); // Invert Cq
    }
    SUB(el1, el2); // subtract Bq from Aq
    element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);
    TSTBIT(bit, el1, 0); // check if Aq is negative, stored in Cq
    IF(bit); // create control for the next instruction
    ADD(el1, el2); // Add bq back to Aq (controlled by Cq)
    ELSE(bit);
    SUB(el1, el2);
    NOT(bit); // Invert Cq

}

void TSTBIT(element_t *el1, element_t *el2, int bit) {
    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
    MOV(ins->el1, el1, POINTER); // return value

    element_t *qbit = malloc(sizeof(element_t));
    qbit->qualifier = Qu;
    qbit->type = BOOL;
    qbit->q_address[0] = el2->q_address[bit];

    MOV(ins->el2, qbit, POINTER);
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