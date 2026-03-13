//
// Created by Sören Wilkening on 27.09.25.
//

#include "circuit.h"

circuit_t *init_circuit() {
    // OWNERSHIP: Caller owns returned circuit_t*, must call free_circuit() when done.
    // Circuit owns its allocator.
    circuit_t *circ = malloc(sizeof(circuit_t));
    if (circ == NULL) {
        return NULL;
    }
    circ->used = 0;
    circ->used_layer = 0;
    circ->layer_floor = 0;
    circ->gate_count = 0;
    circ->toff_decomp = DONTDECOMPOSETOFFOLI;
    circ->arithmetic_mode = ARITH_TOFFOLI;
    circ->cla_override = 0;            // Auto: use CLA when width >= threshold
    circ->qubit_saving = 0;            // Off: use Kogge-Stone (depth-optimized)
    circ->toffoli_decompose = 0;       // Off: CCX gates in output (not decomposed to Clifford+T)
    circ->tradeoff_auto_threshold = 4; // Default: CLA for width >= 4 in auto mode
    circ->tradeoff_min_depth = 0;      // Default: auto mode (not min_depth)

    // Create allocator for qubit management
    circ->allocator = allocator_create(QUBIT_BLOCK);
    if (circ->allocator == NULL) {
        free(circ);
        return NULL;
    }

    // allocate sequence structures
    circ->allocated_layer = LAYER_BLOCK;
    circ->used_gates_per_layer = calloc(LAYER_BLOCK, sizeof(num_t));
    if (circ->used_gates_per_layer == NULL) {
        allocator_destroy(circ->allocator);
        free(circ);
        return NULL;
    }
    circ->allocated_gates_per_layer = malloc(LAYER_BLOCK * sizeof(num_t));
    if (circ->allocated_gates_per_layer == NULL) {
        free(circ->used_gates_per_layer);
        allocator_destroy(circ->allocator);
        free(circ);
        return NULL;
    }
    for (int i = 0; i < LAYER_BLOCK; ++i) {
        circ->allocated_gates_per_layer[i] = GATES_PER_LAYER_BLOCK;
    }
    circ->sequence = malloc(LAYER_BLOCK * sizeof(gate_t *));
    if (circ->sequence == NULL) {
        free(circ->allocated_gates_per_layer);
        free(circ->used_gates_per_layer);
        allocator_destroy(circ->allocator);
        free(circ);
        return NULL;
    }
    for (int i = 0; i < LAYER_BLOCK; ++i) {
        circ->sequence[i] = malloc(GATES_PER_LAYER_BLOCK * sizeof(gate_t));
        if (circ->sequence[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(circ->sequence[j]);
            }
            free(circ->sequence);
            free(circ->allocated_gates_per_layer);
            free(circ->used_gates_per_layer);
            allocator_destroy(circ->allocator);
            free(circ);
            return NULL;
        }
    }

    circ->gate_index_of_layer_and_qubits = malloc(LAYER_BLOCK * sizeof(int *));
    if (circ->gate_index_of_layer_and_qubits == NULL) {
        for (int i = 0; i < LAYER_BLOCK; ++i) {
            free(circ->sequence[i]);
        }
        free(circ->sequence);
        free(circ->allocated_gates_per_layer);
        free(circ->used_gates_per_layer);
        allocator_destroy(circ->allocator);
        free(circ);
        return NULL;
    }
    for (int i = 0; i < LAYER_BLOCK; ++i) {
        circ->gate_index_of_layer_and_qubits[i] = malloc(QUBIT_BLOCK * sizeof(int));
        if (circ->gate_index_of_layer_and_qubits[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(circ->gate_index_of_layer_and_qubits[j]);
            }
            free(circ->gate_index_of_layer_and_qubits);
            for (int j = 0; j < LAYER_BLOCK; ++j) {
                free(circ->sequence[j]);
            }
            free(circ->sequence);
            free(circ->allocated_gates_per_layer);
            free(circ->used_gates_per_layer);
            allocator_destroy(circ->allocator);
            free(circ);
            return NULL;
        }
        memset(circ->gate_index_of_layer_and_qubits[i], 0xFF, QUBIT_BLOCK * sizeof(int));
    }

    // allocate layer informations
    circ->used_occupation_indices_per_qubit = calloc(QUBIT_BLOCK, sizeof(num_t));
    if (circ->used_occupation_indices_per_qubit == NULL) {
        for (int i = 0; i < LAYER_BLOCK; ++i) {
            free(circ->gate_index_of_layer_and_qubits[i]);
        }
        free(circ->gate_index_of_layer_and_qubits);
        for (int i = 0; i < LAYER_BLOCK; ++i) {
            free(circ->sequence[i]);
        }
        free(circ->sequence);
        free(circ->allocated_gates_per_layer);
        free(circ->used_gates_per_layer);
        allocator_destroy(circ->allocator);
        free(circ);
        return NULL;
    }
    circ->allocated_occupation_indices_per_qubit = malloc(LAYER_BLOCK * sizeof(num_t));
    if (circ->allocated_occupation_indices_per_qubit == NULL) {
        free(circ->used_occupation_indices_per_qubit);
        for (int i = 0; i < LAYER_BLOCK; ++i) {
            free(circ->gate_index_of_layer_and_qubits[i]);
        }
        free(circ->gate_index_of_layer_and_qubits);
        for (int i = 0; i < LAYER_BLOCK; ++i) {
            free(circ->sequence[i]);
        }
        free(circ->sequence);
        free(circ->allocated_gates_per_layer);
        free(circ->used_gates_per_layer);
        allocator_destroy(circ->allocator);
        free(circ);
        return NULL;
    }

    circ->occupied_layers_of_qubit = malloc(QUBIT_BLOCK * sizeof(layer_t *));
    if (circ->occupied_layers_of_qubit == NULL) {
        free(circ->allocated_occupation_indices_per_qubit);
        free(circ->used_occupation_indices_per_qubit);
        for (int i = 0; i < LAYER_BLOCK; ++i) {
            free(circ->gate_index_of_layer_and_qubits[i]);
        }
        free(circ->gate_index_of_layer_and_qubits);
        for (int i = 0; i < LAYER_BLOCK; ++i) {
            free(circ->sequence[i]);
        }
        free(circ->sequence);
        free(circ->allocated_gates_per_layer);
        free(circ->used_gates_per_layer);
        allocator_destroy(circ->allocator);
        free(circ);
        return NULL;
    }
    for (int i = 0; i < QUBIT_BLOCK; ++i) {
        circ->occupied_layers_of_qubit[i] = malloc(QUBIT_INDEX_BLOCK * sizeof(layer_t));
        if (circ->occupied_layers_of_qubit[i] == NULL) {
            for (int j = 0; j < i; ++j) {
                free(circ->occupied_layers_of_qubit[j]);
            }
            free(circ->occupied_layers_of_qubit);
            free(circ->allocated_occupation_indices_per_qubit);
            free(circ->used_occupation_indices_per_qubit);
            for (int j = 0; j < LAYER_BLOCK; ++j) {
                free(circ->gate_index_of_layer_and_qubits[j]);
            }
            free(circ->gate_index_of_layer_and_qubits);
            for (int j = 0; j < LAYER_BLOCK; ++j) {
                free(circ->sequence[j]);
            }
            free(circ->sequence);
            free(circ->allocated_gates_per_layer);
            free(circ->used_gates_per_layer);
            allocator_destroy(circ->allocator);
            free(circ);
            return NULL;
        }
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
    // Destroy allocator first
    if (circ->allocator != NULL) {
        allocator_destroy(circ->allocator);
    }

    for (int i = 0; i < circ->allocated_layer; ++i) {
        // Free large_control arrays for MCX gates with >2 controls (Phase 67)
        if (i < (int)circ->used_layer) {
            for (int g = 0; g < (int)circ->used_gates_per_layer[i]; ++g) {
                if (circ->sequence[i][g].NumControls > 2 &&
                    circ->sequence[i][g].large_control != NULL) {
                    free(circ->sequence[i][g].large_control);
                }
            }
        }
        free(circ->sequence[i]);
        free(circ->gate_index_of_layer_and_qubits[i]);
    }
    free(circ->sequence);
    free(circ->gate_index_of_layer_and_qubits);

    for (int i = 0; i < circ->allocated_qubits; ++i)
        free(circ->occupied_layers_of_qubit[i]);
    free(circ->occupied_layers_of_qubit);

    free(circ->used_gates_per_layer);
    free(circ->allocated_gates_per_layer);

    free(circ->used_occupation_indices_per_qubit);
    free(circ->allocated_occupation_indices_per_qubit);
}

void allocate_more_qubits(circuit_t *circ, gate_t *g) {
    qubit_t max = max_qubit(g);
    if (max >= circ->used_qubits)
        circ->used_qubits = max;
    max++;
    if (max <= circ->allocated_qubits)
        return;

    max += QUBIT_BLOCK;

    // increase the register storing how many layers are assigned to qubit
    num_t *new_used_occupation =
        realloc(circ->used_occupation_indices_per_qubit, max * sizeof(num_t));
    if (new_used_occupation == NULL) {
        return;
    }
    circ->used_occupation_indices_per_qubit = new_used_occupation;
    memset(circ->used_occupation_indices_per_qubit + circ->allocated_qubits, 0,
           (max - circ->allocated_qubits) * sizeof(num_t));

    // increase register storing which layers occupy qubits
    layer_t **new_occupied_layers =
        realloc(circ->occupied_layers_of_qubit, max * sizeof(layer_t *));
    if (new_occupied_layers == NULL) {
        return;
    }
    circ->occupied_layers_of_qubit = new_occupied_layers;

    num_t *new_allocated_occupation =
        realloc(circ->allocated_occupation_indices_per_qubit, max * sizeof(layer_t *));
    if (new_allocated_occupation == NULL) {
        return;
    }
    circ->allocated_occupation_indices_per_qubit = new_allocated_occupation;

    for (int i = circ->allocated_qubits; i < max; ++i) {
        circ->occupied_layers_of_qubit[i] = malloc(QUBIT_INDEX_BLOCK * sizeof(layer_t));
        if (circ->occupied_layers_of_qubit[i] == NULL) {
            // Clean up partially allocated memory
            for (int j = circ->allocated_qubits; j < i; ++j) {
                free(circ->occupied_layers_of_qubit[j]);
            }
            return;
        }
        circ->allocated_occupation_indices_per_qubit[i] = QUBIT_INDEX_BLOCK;
    }

    for (int lay = 0; lay < circ->allocated_layer; ++lay) {
        int *new_gate_index = realloc(circ->gate_index_of_layer_and_qubits[lay], max * sizeof(int));
        if (new_gate_index == NULL) {
            return;
        }
        circ->gate_index_of_layer_and_qubits[lay] = new_gate_index;
        memset(&circ->gate_index_of_layer_and_qubits[lay][circ->allocated_qubits], 0xFF,
               (max - circ->allocated_qubits) * sizeof(int));
    }

    circ->allocated_qubits = max;
}

void allocate_more_layer(circuit_t *circ, layer_t min_possible_layer) {
    // include sequence increase
    if (min_possible_layer < circ->allocated_layer)
        return;

    num_t new = circ->allocated_layer + LAYER_BLOCK;
    num_t *new_used_gates = realloc(circ->used_gates_per_layer, new * sizeof(num_t));
    if (new_used_gates == NULL) {
        return;
    }
    circ->used_gates_per_layer = new_used_gates;
    memset(&circ->used_gates_per_layer[circ->allocated_layer], 0, LAYER_BLOCK * sizeof(num_t));

    num_t *new_allocated_gates = realloc(circ->allocated_gates_per_layer, new * sizeof(num_t));
    if (new_allocated_gates == NULL) {
        return;
    }
    circ->allocated_gates_per_layer = new_allocated_gates;
    for (int i = circ->allocated_layer; i < new; ++i) {
        circ->allocated_gates_per_layer[i] = GATES_PER_LAYER_BLOCK;
    }

    // increase sequence layers
    gate_t **new_sequence = realloc(circ->sequence, new * sizeof(gate_t *));
    if (new_sequence == NULL) {
        return;
    }
    circ->sequence = new_sequence;
    for (int i = circ->allocated_layer; i < new; ++i) {
        circ->sequence[i] = malloc(GATES_PER_LAYER_BLOCK * sizeof(gate_t));
        if (circ->sequence[i] == NULL) {
            // Clean up partially allocated memory
            for (int j = circ->allocated_layer; j < i; ++j) {
                free(circ->sequence[j]);
            }
            return;
        }
    }

    int **new_gate_index = realloc(circ->gate_index_of_layer_and_qubits, new * sizeof(int *));
    if (new_gate_index == NULL) {
        return;
    }
    circ->gate_index_of_layer_and_qubits = new_gate_index;
    for (int i = circ->allocated_layer; i < new; ++i) {
        circ->gate_index_of_layer_and_qubits[i] = malloc(circ->allocated_qubits * sizeof(int));
        if (circ->gate_index_of_layer_and_qubits[i] == NULL) {
            // Clean up partially allocated memory
            for (int j = circ->allocated_layer; j < i; ++j) {
                free(circ->gate_index_of_layer_and_qubits[j]);
            }
            return;
        }
        memset(circ->gate_index_of_layer_and_qubits[i], 0xFF, circ->allocated_qubits * sizeof(int));
    }

    circ->allocated_layer = new;
}

void allocate_more_gates_per_layer(circuit_t *circ, layer_t layer, layer_t pos) {
    if (pos < circ->allocated_gates_per_layer[layer])
        return;

    num_t new_size = circ->allocated_gates_per_layer[layer] + GATES_PER_LAYER_BLOCK;
    gate_t *new_sequence = realloc(circ->sequence[layer], new_size * sizeof(gate_t));
    if (new_sequence == NULL) {
        return;
    }
    circ->sequence[layer] = new_sequence;
    circ->allocated_gates_per_layer[layer] = new_size;
}

void allocate_more_indices_per_qubit(circuit_t *circ, int loc) {
    if (circ->used_occupation_indices_per_qubit[loc] ==
        circ->allocated_occupation_indices_per_qubit[loc]) {
        layer_t *new_occupied_layers =
            realloc(circ->occupied_layers_of_qubit[loc],
                    (circ->allocated_occupation_indices_per_qubit[loc] + QUBIT_INDEX_BLOCK) *
                        sizeof(layer_t));
        if (new_occupied_layers == NULL) {
            return;
        }
        circ->occupied_layers_of_qubit[loc] = new_occupied_layers;
        circ->allocated_occupation_indices_per_qubit[loc] += QUBIT_INDEX_BLOCK;
    }
}
