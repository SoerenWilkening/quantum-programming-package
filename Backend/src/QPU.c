//
// Created by Sören Wilkening on 27.10.24.
//
#include "QPU.h"


layer_t minimum_layer(circuit_t *circ, gate_t *g, int offset) {
    qubit_t *ctrl = g->Control;
    layer_t min_possible_layer = 0;
    // Determine the minimal possible layer where gate can be applied
    min_possible_layer = 0;
    for (int j = 0; j < g->NumControls; ++j) {
        layer_t qubit = ctrl[j];
        int last_layer = (int) circ->used_occupation_indices_per_qubit[qubit] - offset;
        
        if (last_layer >= 0) {
            if (last_layer > 0 && circ->occupied_layers_of_qubit[qubit][last_layer - 1] > min_possible_layer) {
                min_possible_layer = circ->occupied_layers_of_qubit[qubit][last_layer - 1];
            }
        }
    }
    layer_t qubit = g->Target;
    int last_layer = (int) circ->used_occupation_indices_per_qubit[qubit] - offset;
    if (last_layer >= 0) {
        if (last_layer > 0 && circ->occupied_layers_of_qubit[qubit][last_layer - 1] > min_possible_layer) {
            min_possible_layer = circ->occupied_layers_of_qubit[qubit][last_layer - 1];
        }
    }
    return min_possible_layer;
}

int merge_gates(circuit_t *circ, gate_t *g, layer_t min_possible_layer, int gate_index) {
    // get the index of the gate occupying the current gates qubits
    // requres only to check for the gates target qubit, because in "is_inverse", the rest will be evaluated
    // if index == -1: qubit not occupied -> cannot be inverse to other gates
    
    // if is inverse: remove gate
    circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][g->Target] = -1; // reset target index
    for (int k = 0; k < g->NumControls; ++k) {
        circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][g->Control[k]] = -1; // reset control indices
        circ->used_occupation_indices_per_qubit[g->Control[k]]--;
    }
    
    circ->occupied_layers_of_qubit[g->Target][circ->used_occupation_indices_per_qubit[g->Target] - 1] = 0;
    circ->used_occupation_indices_per_qubit[g->Target]--;
    
    // swap gate to the end of layer to be reused
    for (int k = gate_index; k < circ->used_gates_per_layer[min_possible_layer - 1]; ++k) {
        circ->sequence[min_possible_layer - 1][k] = circ->sequence[min_possible_layer - 1][k + 1];
        
        gate_t *helper = &circ->sequence[min_possible_layer - 1][k];
        // reduce the stored gate index of remaining gates
        circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][helper->Target]--;
        for (int l = 0; l < helper->NumControls; ++l)
            circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][helper->Control[l]]--;
    }
    // layer contains less gates
    circ->used_gates_per_layer[min_possible_layer - 1]--;
    circ->used--;
    
    // remove layer, if last gate was removed
    if (circ->used_gates_per_layer[min_possible_layer - 1] == 0) {
        for (int j = min_possible_layer - 1; j < circ->used_layer - 1; ++j) *circ->sequence[j] = *circ->sequence[j + 1];
        circ->used_layer--;
    }
    return false;
}

void apply_layer(circuit_t *circ, gate_t *g, layer_t min_possible_layer) {
    for (int j = 0; j < g->NumControls; ++j) {
        qubit_t loc = g->Control[j];
        allocate_more_indices_per_qubit(circ, loc);
        
        circ->occupied_layers_of_qubit[loc][circ->used_occupation_indices_per_qubit[loc]++] = min_possible_layer + 1;
    }
    qubit_t loc = g->Target;
    allocate_more_indices_per_qubit(circ, loc);
    
    circ->occupied_layers_of_qubit[loc][circ->used_occupation_indices_per_qubit[loc]++] = min_possible_layer + 1;
    circ->used_gates_per_layer[min_possible_layer]++; // layer contains more gates
    if (min_possible_layer + 1 > circ->used_layer) circ->used_layer = min_possible_layer + 1;
}

void append_gate(circuit_t *circ, gate_t *g, layer_t min_possible_layer) {
    // gate will be added to MinPossibleLayer
    // assign layer
    layer_t pos = circ->used_gates_per_layer[min_possible_layer];
    allocate_more_gates_per_layer(circ, min_possible_layer, pos);
    
    // increase the number of storable gates on MinPossibleLayer if needed
    memcpy(&circ->sequence[min_possible_layer][pos], g, sizeof(gate_t));
    
    circ->gate_index_of_layer_and_qubits[min_possible_layer][g->Target] = pos;
    for (int i = 0; i < g->NumControls; ++i) circ->gate_index_of_layer_and_qubits[min_possible_layer][g->Control[i]] = pos;
    
    circ->used++;
}


gate_t *colliding_gate(circuit_t *circ, gate_t *g, layer_t min_possible_layer, int *gate_index) {
    if (min_possible_layer == 0) return NULL;
    *gate_index = circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][g->Target]; // index of gate
    for (int i = 0; i < g->NumControls; ++i) {
        int step = circ->gate_index_of_layer_and_qubits[min_possible_layer - 1][g->Control[i]];
        *gate_index = (step >= 0) ? step : *gate_index;
    }
    return &circ->sequence[min_possible_layer - 1][*gate_index];
}

void add_gate(circuit_t *circ, gate_t *g) {
    // Before adding gate, check if multicontrolled gate needs to be decomposed
    // Currently: Toffoli (CCX) and every single control single qubit gate (CU) is allowed
    // Determine the minimal possible layer where gate can be applied
    allocate_more_qubits(circ, g);
    layer_t min_possible_layer = minimum_layer(circ, g, 0);
    allocate_more_layer(circ, min_possible_layer);
    
    // will be NULL, if min_possible_layer = 0
    int gate_index;
    gate_t *g2 = colliding_gate(circ, g, min_possible_layer, &gate_index);

//    int commute = gates_commute(g, g2);
    
    // if inverse, gate is removed
    if (gates_are_inverse(g, g2)) {
        merge_gates(circ, g, min_possible_layer, gate_index);
        return;
    }
    
    append_gate(circ, g, min_possible_layer);
    apply_layer(circ, g, min_possible_layer);
}