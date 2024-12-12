//
// Created by Sören Wilkening on 21.11.24.
//

#include "execution.h"

void qubit_mapping(qubit_t qubit_arrray[]) {
	int start = 0;
	if (stack.Q0 != NULL){
		start += INTEGERSIZE;
		memcpy(qubit_arrray, stack.Q0->q_address, INTEGERSIZE * sizeof(int));
	}
	if (stack.Q1 != NULL){
		start += INTEGERSIZE;
		memcpy(&qubit_arrray[INTEGERSIZE], stack.Q1->q_address, INTEGERSIZE * sizeof(int));
	}
	if (stack.Q2 != NULL){
		start += INTEGERSIZE;
		memcpy(&qubit_arrray[2 * INTEGERSIZE], stack.Q2->q_address, INTEGERSIZE * sizeof(int));
	}
	if (stack.Q3 != NULL){
		start += INTEGERSIZE;
		memcpy(&qubit_arrray[3 * INTEGERSIZE], stack.Q3->q_address, INTEGERSIZE * sizeof(int));
	}
	memcpy(&qubit_arrray[start], stack.circuit->ancilla, 2 * INTEGERSIZE * sizeof(int));
}

// apply the sequences to the desired qubits
void run_instruction(sequence_t *res, qubit_t qubit_array[], bool invert){
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
                g->Control[i] = qubit_array[g->Control[i]];
            }
            g->GateValue *= pow(-1, invert);

            add_gate(stack.circuit, g);
        }
    }
}

void execute(instruction_t *instr) {

	stack.Q0 = instr->Q0;
	stack.Q1 = instr->Q1;
	stack.Q2 = instr->Q2;
	stack.Q3 = instr->Q3;

	stack.R0 = instr->R0;
	stack.R1 = instr->R1;
	stack.R2 = instr->R2;
	stack.R3 = instr->R3;

	if (instr->routine == NULL) return;
	qubit_t qubit_array[6 * INTEGERSIZE];
	qubit_mapping(qubit_array);
	sequence_t *res = instr->routine();

	print_sequence(res);
    run_instruction(res, qubit_array, instr->invert);

    stack.Q0 = NULL;
    stack.Q1 = NULL;
    stack.Q2 = NULL;
    stack.Q3 = NULL;

	stack.R0 = NULL;
	stack.R1 = NULL;
	stack.R2 = NULL;
	stack.R3 = NULL;

	instruction_t *pointer = instr + 1;
    if (instr->next_instruction != NULL) {
		pointer = (instruction_t *) instr->next_instruction;
	    printf("jump \n");
	}

	execute(pointer);
}