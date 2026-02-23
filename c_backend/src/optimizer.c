//
// optimizer.c - Gate optimization implementation
// Dependencies: optimizer.h, circuit.h (for circuit_t), gate.h
//
// Implements intelligent gate placement:
// - Layer assignment for minimal circuit depth
// - Gate merging (inverse gate cancellation)
// - Collision detection between gates
//

#include "optimizer.h"
#include "circuit.h"
#include "gate.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

// Helper: Get control qubit at index i, handling large_control for n-controlled gates (Phase 13)
static inline qubit_t get_control(gate_t *g, int i) {
    if (g->NumControls > MAXCONTROLS && g->large_control != NULL) {
        return g->large_control[i];
    }
    return g->Control[i];
}

layer_t smallest_layer_below_comp(circuit_t *circ, qubit_t qubit, layer_t compar) {
    // Scan backward through occupied layers to find the largest layer < compar
    int last_index = (int)circ->used_occupation_indices_per_qubit[qubit];
    if (last_index <= 0)
        return 0;
    for (int i = last_index; i > 0; --i) {
        if (circ->occupied_layers_of_qubit[qubit][i - 1] < compar) {
            return circ->occupied_layers_of_qubit[qubit][i - 1];
        }
    }
    return 0;
}

layer_t minimum_layer(circuit_t *circ, gate_t *g, layer_t compared_layer) {
    layer_t min_possible_layer = circ->layer_floor;
    // Determine the minimal possible layer where gate can be applied
    for (int j = 0; j < (int)g->NumControls; ++j) {
        layer_t qubit = get_control(g, j);
        layer_t min_layer = smallest_layer_below_comp(circ, qubit, compared_layer);
        if (min_layer > min_possible_layer)
            min_possible_layer = min_layer;
    }
    layer_t qubit = g->Target;
    layer_t min_layer = smallest_layer_below_comp(circ, qubit, compared_layer);
    if (min_layer > min_possible_layer)
        min_possible_layer = min_layer;

    return min_possible_layer;
}

int merge_gates(circuit_t *circ, gate_t *g, layer_t min_possible_layer, int gate_index) {
    // get the index of the gate occupying the current gates qubits
    // requres only to check for the gates target qubit, because in "is_inverse", the rest will be
    // evaluated if index == -1: qubit not occupied -> cannot be inverse to other gates

    // if is inverse: remove gate
    circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][g->Target] =
        -1; // reset target index
    for (int k = 0; k < (int)g->NumControls; ++k) {
        qubit_t ctrl = get_control(g, k);
        circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][ctrl] =
            -1; // reset control indices
        circ->used_occupation_indices_per_qubit[ctrl]--;
    }

    circ->occupied_layers_of_qubit[g->Target]
                                  [circ->used_occupation_indices_per_qubit[g->Target] - 1] = 0;
    circ->used_occupation_indices_per_qubit[g->Target]--;

    // swap gate to the end of layer to be reused
    for (int k = gate_index; k < (int)circ->used_gates_per_layer[min_possible_layer - 1] - 1; ++k) {
        circ->sequence[min_possible_layer - 1][k] = circ->sequence[min_possible_layer - 1][k + 1];

        gate_t *helper = &circ->sequence[min_possible_layer - 1][k];
        // reduce the stored gate index of remaining gates
        circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][helper->Target]--;
        for (int l = 0; l < (int)helper->NumControls; ++l) {
            qubit_t hctrl = get_control(helper, l);
            circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][hctrl]--;
        }
    }
    // layer contains less gates
    circ->used_gates_per_layer[min_possible_layer - 1]--;
    circ->used--;

    // remove layer, if last gate was removed
    if (circ->used_gates_per_layer[min_possible_layer - 1] == 0) {
        for (int j = min_possible_layer - 1; j < (int)circ->used_layer - 1; ++j)
            *circ->sequence[j] = *circ->sequence[j + 1];
        circ->used_layer--;
    }
    return false;
}

void apply_layer(circuit_t *circ, gate_t *g, layer_t min_possible_layer) {
    for (int j = 0; j < (int)g->NumControls; ++j) {
        qubit_t loc = get_control(g, j);
        allocate_more_indices_per_qubit(circ, loc);

        circ->occupied_layers_of_qubit[loc][circ->used_occupation_indices_per_qubit[loc]++] =
            min_possible_layer + 1;
    }
    qubit_t loc = g->Target;
    allocate_more_indices_per_qubit(circ, loc);

    circ->occupied_layers_of_qubit[loc][circ->used_occupation_indices_per_qubit[loc]++] =
        min_possible_layer + 1;
    circ->used_gates_per_layer[min_possible_layer]++; // layer contains more gates
    if (min_possible_layer + 1 > circ->used_layer)
        circ->used_layer = min_possible_layer + 1;
}

void append_gate(circuit_t *circ, gate_t *g, layer_t min_possible_layer) {
    // gate will be added to MinPossibleLayer
    // assign layer
    layer_t pos = circ->used_gates_per_layer[min_possible_layer];
    allocate_more_gates_per_layer(circ, min_possible_layer, pos);

    // increase the number of storable gates on MinPossibleLayer if needed
    memcpy(&circ->sequence[min_possible_layer][pos], g, sizeof(gate_t));

    circ->gate_index_of_layer_and_qubits[min_possible_layer][g->Target] = pos;
    for (int i = 0; i < (int)g->NumControls; ++i) {
        qubit_t ctrl = get_control(g, i);
        circ->gate_index_of_layer_and_qubits[min_possible_layer][ctrl] = pos;
    }

    circ->used++;
}

void colliding_gates(circuit_t *circ, gate_t *g, layer_t min_possible_layer, int *gate_index,
                     gate_t **coll) {
    coll[0] = NULL;
    coll[1] = NULL;
    coll[2] = NULL;
    if (min_possible_layer == 0)
        return;
    gate_index[0] = circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][g->Target];
    //    printf("indices %d ", gate_index[0]);
    if (gate_index[0] >= 0) {
        coll[0] = &circ->sequence[min_possible_layer - 1][gate_index[0]];
        return;
    }
    // we have at most three colliding gates
    for (int i = 0; i < (int)g->NumControls; ++i) {
        qubit_t ctrl = get_control(g, i);
        int step = circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][ctrl];
        //        printf("%d ", step);
        if (step >= 0) {
            coll[0] = &circ->sequence[min_possible_layer - 1][step];
            gate_index[0] = step;
            return;
        }
    }
}

void add_gate(circuit_t *circ, gate_t *g) {
    // Before adding gate, check if multicontrolled gate needs to be decomposed
    // Currently: Toffoli (CCX) and every single control single qubit gate (CU) is allowed
    // Determine the minimal possible layer where gate can be applied
    allocate_more_qubits(circ, g);
    layer_t min_possible_layer;

    int prev = INT32_MAX;

    for (int i = 0; i < 1; ++i) {
        min_possible_layer = minimum_layer(circ, g, prev);
        //        printf("min_layer = %d\n", min_possible_layer);
        allocate_more_layer(circ, min_possible_layer);

        // will be NULL, if min_possible_layer = 0
        int gate_index[3];
        gate_t *coll[3]; // Stack allocated -- no malloc/free per gate (Phase 61)
        colliding_gates(circ, g, min_possible_layer, gate_index, coll);
        //        printf("\n");
        (void)(prev); // delta = prev - min_possible_layer was unused

        for (int j = 0; j < 1; ++j) {
            // compare with all the colliding gates
            gate_t *g2 = coll[j];

            if (g2 != NULL) {
                // if inverse, gate is removed
                if (gates_are_inverse(g, g2)) {
                    merge_gates(circ, g, min_possible_layer, gate_index[j]);
                    return;
                }
            }
        }
        // only previous layer and dont merge: undo swap
        //        if (delta == 1 && !total_inverse) {
        //            min_possible_layer =  prev;
        //            break;
        //        }
        //        if (!commute) break;
        //        prev = min_possible_layer;
    }
    append_gate(circ, g, min_possible_layer);
    apply_layer(circ, g, min_possible_layer);
}
