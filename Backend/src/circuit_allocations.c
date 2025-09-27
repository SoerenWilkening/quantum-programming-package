//
// Created by Sören Wilkening on 27.09.25.
//

#include "QPU.h"

circuit_t *init_circuit() {
    circuit_t *circ = malloc(sizeof(circuit_t));
    circ->used = 0;
    circ->used_layer = 0;
    circ->toff_decomp = DONTDECOMPOSETOFFOLI;
    
    // allocate sequence structures
    circ->allocated_layer = LAYER_BLOCK;
    circ->used_gates_per_layer = calloc(LAYER_BLOCK, sizeof(num_t));
    circ->allocated_gates_per_layer = malloc(LAYER_BLOCK * sizeof(num_t));
    for (int i = 0; i < LAYER_BLOCK; ++i) {
        circ->allocated_gates_per_layer[i] = GATES_PER_LAYER_BLOCK;
    }
    circ->sequence = malloc(LAYER_BLOCK * sizeof(gate_t *));
    for (int i = 0; i < LAYER_BLOCK; ++i) {
        circ->sequence[i] = malloc(GATES_PER_LAYER_BLOCK * sizeof(gate_t));
    }
    
    circ->gate_index_of_layer_and_qubits = malloc(LAYER_BLOCK * sizeof(int *));
    for (int i = 0; i < LAYER_BLOCK; ++i) {
        circ->gate_index_of_layer_and_qubits[i] = malloc(QUBIT_BLOCK * sizeof(int));
        memset(circ->gate_index_of_layer_and_qubits[i], 0xFF, QUBIT_BLOCK * sizeof(int));
    }
    
    // allocate layer informations
    circ->used_occupation_indices_per_qubit = calloc(QUBIT_BLOCK, sizeof(num_t));
    circ->allocated_occupation_indices_per_qubit = malloc(LAYER_BLOCK * sizeof(num_t));
    
    circ->occupied_layers_of_qubit = malloc(QUBIT_BLOCK * sizeof(layer_t *));
    for (int i = 0; i < QUBIT_BLOCK; ++i) {
        circ->occupied_layers_of_qubit[i] = malloc(QUBIT_INDEX_BLOCK * sizeof(layer_t));
        circ->allocated_occupation_indices_per_qubit[i] = QUBIT_INDEX_BLOCK;
    }
    memset(circ->used_gates_per_layer, 0, LAYER_BLOCK * sizeof(num_t));
    
    circ->allocated_qubits = QUBIT_BLOCK;
    circ->used_qubits = 0;
    
    // initialize all the qubit indices and the ancilla register
    for (int i = 0; i < MAXQUBITS; ++i) {
        circ->qubit_indices[i] = i;
    }
    circ->used_qubit_indices = 0;
    circ->ancilla = &circ->qubit_indices[0];
    
    return circ;
}

void free_circuit(circuit_t *circ) {
    for (int i = 0; i < circ->allocated_layer; ++i) {
        free(circ->sequence[i]);
        free(circ->gate_index_of_layer_and_qubits[i]);
    }
    free(circ->sequence);
    free(circ->gate_index_of_layer_and_qubits);
    
    for (int i = 0; i < circ->allocated_qubits; ++i) free(circ->occupied_layers_of_qubit[i]);
    free(circ->occupied_layers_of_qubit);
    
    free(circ->used_gates_per_layer);
    free(circ->allocated_gates_per_layer);
    
    free(circ->used_occupation_indices_per_qubit);
    free(circ->allocated_occupation_indices_per_qubit);
    
}

void allocate_more_qubits(circuit_t *circ, gate_t *g) {
    qubit_t max = max_qubit(g);
    if (max >= circ->used_qubits) circ->used_qubits = max;
    max++;
    if (max <= circ->allocated_qubits) return;
    
    max += QUBIT_BLOCK;
    
    // increase the register storing how many layers are assigned to qubit
    circ->used_occupation_indices_per_qubit = realloc(circ->used_occupation_indices_per_qubit, max * sizeof(num_t));
    memset(circ->used_occupation_indices_per_qubit + circ->allocated_qubits,
           0,
           (max - circ->allocated_qubits) * sizeof(num_t));
    
    // increase register storing which layers occupy qubits
    circ->occupied_layers_of_qubit = realloc(circ->occupied_layers_of_qubit, max * sizeof(layer_t *));
    circ->allocated_occupation_indices_per_qubit =
        realloc(circ->allocated_occupation_indices_per_qubit, max * sizeof(layer_t *));
    for (int i = circ->allocated_qubits; i < max; ++i) {
        circ->occupied_layers_of_qubit[i] = malloc(QUBIT_INDEX_BLOCK * sizeof(layer_t));
        circ->allocated_occupation_indices_per_qubit[i] = QUBIT_INDEX_BLOCK;
    }
    
    for (int lay = 0; lay < circ->allocated_layer; ++lay) {
        circ->gate_index_of_layer_and_qubits[lay] =
            realloc(circ->gate_index_of_layer_and_qubits[lay], max * sizeof(int));
        memset(&circ->gate_index_of_layer_and_qubits[lay][circ->allocated_qubits],
               0xFF,
               (max - circ->allocated_qubits) * sizeof(int));
    }
    
    circ->allocated_qubits = max;
}

void allocate_more_layer(circuit_t *circ, layer_t min_possible_layer) {
    // include sequence increase
    if (min_possible_layer < circ->allocated_layer) return;
    
    num_t new = circ->allocated_layer + LAYER_BLOCK;
    circ->used_gates_per_layer = realloc(circ->used_gates_per_layer, new * sizeof(num_t));
    memset(&circ->used_gates_per_layer[circ->allocated_layer], 0, LAYER_BLOCK * sizeof(num_t));
    circ->allocated_gates_per_layer = realloc(circ->allocated_gates_per_layer, new * sizeof(num_t));
    for (int i = circ->allocated_layer; i < new; ++i) {
        circ->allocated_gates_per_layer[i] = GATES_PER_LAYER_BLOCK;
    }
    // increase sequence layers
    circ->sequence = realloc(circ->sequence, new * sizeof(gate_t *));
    for (int i = circ->allocated_layer; i < new; ++i)
        circ->sequence[i] = malloc(GATES_PER_LAYER_BLOCK * sizeof(gate_t));
    
    
    circ->gate_index_of_layer_and_qubits = realloc(circ->gate_index_of_layer_and_qubits, new * sizeof(int *));
    for (int i = circ->allocated_layer; i < new; ++i) {
        circ->gate_index_of_layer_and_qubits[i] = malloc(circ->allocated_qubits * sizeof(int));
        memset(circ->gate_index_of_layer_and_qubits[i], 0xFF, circ->allocated_qubits * sizeof(int));
    }
    
    circ->allocated_layer = new;
}

void allocate_more_gates_per_layer(circuit_t *circ, layer_t layer, layer_t pos) {
    if (pos < circ->allocated_gates_per_layer[layer]) return;
    
    num_t new_size = circ->allocated_gates_per_layer[layer] + GATES_PER_LAYER_BLOCK;
    circ->sequence[layer] = realloc(circ->sequence[layer], new_size * sizeof(gate_t));
    circ->allocated_gates_per_layer[layer] = new_size;
}

void allocate_more_indices_per_qubit(circuit_t *circ, int loc) {
    if (circ->used_occupation_indices_per_qubit[loc] == circ->allocated_occupation_indices_per_qubit[loc]) {
        circ->occupied_layers_of_qubit[loc] = realloc(
            circ->occupied_layers_of_qubit[loc],
            (circ->allocated_occupation_indices_per_qubit[loc] + QUBIT_INDEX_BLOCK) * sizeof(layer_t)
        );
        circ->allocated_occupation_indices_per_qubit[loc] += QUBIT_INDEX_BLOCK;
    }
}
