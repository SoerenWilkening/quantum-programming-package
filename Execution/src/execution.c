//
// Created by Sören Wilkening on 21.11.24.
//

#include "execution.h"

void qubit_mapping(qubit_t qubit_arrray[]) {
	int start = 0;
	if (QPU_state->Q0 != NULL){
		start += INTEGERSIZE;
		memcpy(qubit_arrray, QPU_state->Q0->q_address, INTEGERSIZE * sizeof(int));
	}
	if (QPU_state->Q1 != NULL){
		start += INTEGERSIZE;
		memcpy(&qubit_arrray[INTEGERSIZE], QPU_state->Q1->q_address, INTEGERSIZE * sizeof(int));
	}
	if (QPU_state->Q2 != NULL){
		start += INTEGERSIZE;
		memcpy(&qubit_arrray[2 * INTEGERSIZE], QPU_state->Q2->q_address, INTEGERSIZE * sizeof(int));
	}
	if (QPU_state->Q3 != NULL){
		start += INTEGERSIZE;
		memcpy(&qubit_arrray[3 * INTEGERSIZE], QPU_state->Q3->q_address, INTEGERSIZE * sizeof(int));
	}
	memcpy(&qubit_arrray[start], circuit->ancilla, 2 * INTEGERSIZE * sizeof(int));
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

            add_gate(circuit, g);
        }
    }
}

void execute() {

	instruction_t *instr = QPU_state;

	if (instr->routine == NULL) return;

	qubit_t qubit_array[6 * INTEGERSIZE];
	qubit_mapping(qubit_array);
	sequence_t *res = instr->routine();

    run_instruction(res, qubit_array, instr->invert);

	if (instr == QPU_state) QPU_state++;

	execute();
}