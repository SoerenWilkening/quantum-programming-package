//
// Created by Sören Wilkening on 21.11.24.
//

#include "execution.h"

void qubit_mapping(qubit_t qubit_arrray[]) {
    int start = 0;
    if (stack.GPR1[0].type != UNINITIALIZED && stack.GPR1[0].qualifier == Qu) {
        int value = (stack.GPR1[0].type == BOOLEAN) ? 1 : INTEGERSIZE;
        memcpy(qubit_arrray, stack.GPR1[0].q_address, value * sizeof(qubit_t));
        start += value;
    }
    if (stack.GPR2[0].type != UNINITIALIZED && stack.GPR2[0].qualifier == Qu) {
        int value = (stack.GPR2[0].type == BOOLEAN) ? 1 : INTEGERSIZE;
        memcpy(&qubit_arrray[start], stack.GPR2[0].q_address, value * sizeof(qubit_t));
        start += value;
    }
    if (stack.GPR3[0].type != UNINITIALIZED && stack.GPR3[0].qualifier == Qu) {
        int value = (stack.GPR3[0].type == BOOLEAN) ? 1 : INTEGERSIZE;
        memcpy(&qubit_arrray[start], stack.GPR3[0].q_address, value * sizeof(qubit_t));
        start += value;
    }
    if (stack.GPC[0].type != UNINITIALIZED && stack.GPC[0].qualifier == Qu){
        int value = 1;
        memcpy(&qubit_arrray[start], stack.GPC[0].q_address, value * sizeof(qubit_t));
        start += value;
    }
    for (int i = 0; i < 10 * INTEGERSIZE - start; ++i) {
        qubit_arrray[start + i] = stack.circuit->ancilla[i];
    }
}

void init_instruction(instruction_t *instr) {
    instr->el1 = malloc(sizeof(element_t));
    instr->el1->c_address = malloc(sizeof(int64_t));
    instr->el1->type = UNINITIALIZED;

    instr->el2 = malloc(sizeof(element_t));
    instr->el2->c_address = malloc(sizeof(int64_t));
    instr->el2->type = UNINITIALIZED;

    instr->el3 = malloc(sizeof(element_t));
    instr->el3->c_address = malloc(sizeof(int64_t));
    instr->el3->type = UNINITIALIZED;

    instr->control = malloc(sizeof(element_t));
    instr->control->c_address = malloc(sizeof(int64_t));
    instr->control->type = UNINITIALIZED;

	instr->next_instruction = NULL;
	instr->routine = NULL;
	instr->invert = NOTINVERTED;
}

// apply the sequences to the desired qubits
void run_instruction(sequence_t *res, qubit_t qubit_array[], bool_t invert){
    if (res == NULL) return;
    int direction = (invert) ? -1 : 1;

    for (int layer_index = 0; layer_index < res->used_layer; ++layer_index) {
        layer_t layer = invert * res->used_layer + direction * layer_index - invert;
        for (int gate_index = 0; gate_index < res->gates_per_layer[layer]; ++gate_index) {
            layer_t gate = invert * res->gates_per_layer[layer] + direction * gate_index - invert;
            gate_t *g = malloc(sizeof(gate_t));
            memcpy(g, &res->seq[layer][gate], sizeof(gate_t));
            g->Target = qubit_array[g->Target];
            for (int i = 0; i < g->NumControls; ++i) {
//                printf("%d %d\n", g->Control[i], qubit_array[g->Control[i]]);
                g->Control[i] = qubit_array[g->Control[i]];
            }
            g->GateValue *= pow(-1, invert);

            add_gate(stack.circuit, g);
        }
    }
}

void execute(instruction_t *instr) {
    if (instr->el1->type != UNINITIALIZED) MOV(stack.GPR1, instr->el1, POINTER);
    if (instr->el2->type != UNINITIALIZED) MOV(stack.GPR2, instr->el2, POINTER);
    if (instr->el3->type != UNINITIALIZED) MOV(stack.GPR3, instr->el3, POINTER);

    if (instr->control->type != UNINITIALIZED) MOV(stack.GPC, instr->control, POINTER);

	if (instr->routine == NULL) return;

    qubit_t qubit_array[10 * INTEGERSIZE];
    qubit_mapping(qubit_array);
    sequence_t *res = instr->routine();

    run_instruction(res, qubit_array, instr->invert);

    stack.GPR1[0].type = UNINITIALIZED;
    stack.GPR2[0].type = UNINITIALIZED;
    stack.GPR3[0].type = UNINITIALIZED;
    stack.GPC[0].type = UNINITIALIZED;

	instruction_t *pointer = instr + 1;
    if (instr->next_instruction != NULL) pointer = (instruction_t *) instr->next_instruction;
	execute(pointer);
}