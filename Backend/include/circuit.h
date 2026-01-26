//
// circuit.h - Main public API for Quantum Assembly circuits
// Dependencies: types.h, gate.h, optimizer.h, circuit_output.h, qubit_allocator.h
//
// This is the primary header for users of the library.
// Include this header to access all circuit functionality.
//
// Module organization:
//   types.h         - Core types (qubit_t, gate_t, circuit_t, etc.)
//   gate.h          - Gate creation functions (x, cx, h, p, etc.)
//   optimizer.h     - Gate placement and optimization (add_gate)
//   circuit_output.h - Visualization and export
//   qubit_allocator.h - Qubit lifecycle management
//

#ifndef QUANTUM_CIRCUIT_H
#define QUANTUM_CIRCUIT_H

// Core types
#include "types.h"

// Gate creation and manipulation
#include "gate.h"

// Qubit allocation
#include "qubit_allocator.h"

// Circuit structure constants
#define QUBIT_BLOCK 128
#define LAYER_BLOCK 128
#define GATES_PER_LAYER_BLOCK 32
#define QUBIT_INDEX_BLOCK 128
#define MAXQUBITS 8000

#define MAXINSTRUCTIONS 7

#define NUM_GATE_LAYERS 100
#define NUM_GATE_LAYER_QUBITS 50

// Circuit structure - holds the quantum circuit being built
typedef struct circuit_s {
    gate_t **sequence; // [layer][used_gates_per_layer]
    num_t used_layer;
    num_t allocated_layer;
    num_t *allocated_gates_per_layer; // [layer]
    num_t *used_gates_per_layer;      // [layer]

    int **gate_index_of_layer_and_qubits; // [layer][qubit]
    // -1 refers to the qubit being not occupied

    layer_t **occupied_layers_of_qubit;            // [qubits][index]
    num_t *allocated_occupation_indices_per_qubit; // [qubit]
    num_t *used_occupation_indices_per_qubit;      // [qubits]

    num_t allocated_qubits;
    num_t used_qubits;
    size_t used;
    decompose_toffoli_t toff_decomp;

    qubit_allocator_t *allocator; // Centralized qubit allocation

    // Legacy fields (deprecated, kept for backward compatibility)
    qubit_t qubit_indices[MAXQUBITS];
    qubit_t used_qubit_indices;
    qubit_t *ancilla;
} circuit_t;

// Quantum integer structure
typedef struct {
    char MSB;
    qubit_t q_address[INTEGERSIZE];
} quantum_int_t;

// Circuit lifecycle
circuit_t *init_circuit(void);
void free_circuit(circuit_t *circ);

// Memory allocation (internal use, but exposed for advanced usage)
void allocate_more_qubits(circuit_t *circ, gate_t *g);
void allocate_more_layer(circuit_t *circ, layer_t min_possible_layer);
void allocate_more_gates_per_layer(circuit_t *circ, layer_t layer, layer_t pos);
void allocate_more_indices_per_qubit(circuit_t *circ, int loc);

// Import optimizer functions (add_gate is the main entry point)
#include "optimizer.h"

// Import output functions
#include "circuit_output.h"

#endif // QUANTUM_CIRCUIT_H
