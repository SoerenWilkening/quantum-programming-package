//
// Created by Sören Wilkening on 21.11.24.
//
// qubit_mapping() and execute() removed (Phase 11)
// These functions depended on QPU_state global state.
// Python layer passes qubit arrays directly to run_instruction().
// Test code in main.c now uses explicit qubit array initialization.
//

#include "execution.h"

// apply the sequences to the desired qubits
void run_instruction(sequence_t *res, const qubit_t qubit_array[], int invert, circuit_t *circ) {

    if (res == NULL)
        return;
    int direction = (invert) ? -1 : 1;

    //    printf("%d %d\n", direction, invert);

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

            add_gate(circ, g);
        }
    }
}
