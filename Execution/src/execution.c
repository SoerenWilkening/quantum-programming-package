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

            // Handle n-controlled gates (Phase 12): controls may be in large_control
            if (g->NumControls > 2 && res->seq[layer][gate].large_control != NULL) {
                // Allocate new large_control array for mapped qubits
                g->large_control = malloc(g->NumControls * sizeof(qubit_t));
                if (g->large_control != NULL) {
                    for (int i = 0; i < (int)g->NumControls; ++i) {
                        g->large_control[i] = qubit_array[res->seq[layer][gate].large_control[i]];
                    }
                    // Also update Control[0] and Control[1] for compatibility
                    g->Control[0] = g->large_control[0];
                    g->Control[1] = g->large_control[1];
                }
            } else {
                // Standard case: up to 2 controls in Control[] array
                for (int i = 0; i < (int)g->NumControls && i < MAXCONTROLS; ++i) {
                    g->Control[i] = qubit_array[g->Control[i]];
                }
            }
            g->GateValue *= pow(-1, invert);

            add_gate(circ, g);
        }
    }
}
