//
// QPU.h - Circuit management
// Dependencies: types.h, gate.h, qubit_allocator.h, optimizer.h
//
// Note: Gate adding functionality moved to optimizer.h
//

#ifndef CQ_BACKEND_IMPROVED_QPU_H
#define CQ_BACKEND_IMPROVED_QPU_H

#include "gate.h"
#include "optimizer.h"
#include "qubit_allocator.h"
#include "types.h"

// functionality to store the circuit structure
// ========================================================================
#define QUBIT_BLOCK 128
#define LAYER_BLOCK 128
#define GATES_PER_LAYER_BLOCK 32
#define QUBIT_INDEX_BLOCK 128
#define MAXQUBITS 8000

#define MAXINSTRUCTIONS 7

#define NUM_GATE_LAYERS 100
#define NUM_GATE_LAYER_QUBITS 50

// Circuit structure definition (matches forward declaration in optimizer.h)
typedef struct circuit_s {
    gate_t **sequence; // [layer][used_gates_per_layer]
    num_t used_layer;
    num_t allocated_layer;
    num_t *allocated_gates_per_layer; // [layer]
    num_t *used_gates_per_layer;      // [layer]

    int **gate_index_of_layer_and_qubits; // [layer][qubit] stores for every layer the gate index
                                          // occupying the respective qubits
    // -1 refers to the qubit being not occupied

    layer_t **occupied_layers_of_qubit;            // [qubits][index]
    num_t *allocated_occupation_indices_per_qubit; // [qubit]
    num_t *used_occupation_indices_per_qubit;      // [qubits]

    num_t allocated_qubits;
    num_t used_qubits;
    size_t used;
    decompose_toffoli_t toff_decomp;

    qubit_allocator_t *allocator; // Centralized qubit allocation
    // TODO(Phase 3): Remove qubit_indices/ancilla after migration
    qubit_t qubit_indices[MAXQUBITS]; // allow at most MAXQUBITS qubits
    qubit_t used_qubit_indices;
    qubit_t *ancilla;
} circuit_t;

typedef struct {
    char MSB;
    qubit_t q_address[INTEGERSIZE];
    //    int64_t *c_address;
} quantum_int_t;

typedef struct instruction_t {
    char *name;

    // quantum storing registers
    quantum_int_t *Q0;
    quantum_int_t *Q1;
    quantum_int_t *Q2;
    quantum_int_t *Q3;

    // classical storing registers
    int *R0;
    int *R1;
    int *R2;
    int *R3;

    sequence_t *(*routine)();

    bool invert;
    struct instruction_t *next_instruction; // used for jumps
} instruction_t;

// Global instruction state (used by sequence generation functions in IntegerAddition, etc.)
// TODO(Phase 5+): These are needed for CQ_add/CC_mul style functions that generate sequences
// from classical inputs. Not related to circuit gate adding (which moved to optimizer.c)
extern instruction_t instruction_list[MAXINSTRUCTIONS];
extern int instruction_counter;
extern instruction_t *QPU_state;

// Circuit management functions
circuit_t *init_circuit();
void allocate_more_qubits(circuit_t *circ, gate_t *g);
void allocate_more_layer(circuit_t *circ, layer_t min_possible_layer);
void allocate_more_gates_per_layer(circuit_t *circ, layer_t layer, layer_t pos);
void allocate_more_indices_per_qubit(circuit_t *circ, int loc);

// Circuit output functions
void print_circuit(circuit_t *circ);
void free_circuit(circuit_t *circ);
void circuit_to_opanqasm(circuit_t *circ, char *path);

#endif // CQ_BACKEND_IMPROVED_QPU_H
