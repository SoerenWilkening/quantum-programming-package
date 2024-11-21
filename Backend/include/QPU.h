//
// Created by Sören Wilkening on 05.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_QPU_H
#define CQ_BACKEND_IMPROVED_QPU_H

#include "gate.h"

// functionality to store the circuit structure ========================================================================
#define QUBITBLOCK 100
#define LAYERBLOCK 5000
#define GATESPERLAYERBLOCK 30
#define LAYERQUBITBLOCK 5000
#define MAXQUBITS 10000

typedef struct {
    gate_t **sequence; // [layer][used_gates_per_layer]
    num_t used_layer;
    num_t allocated_layer;
    num_t *used_gates_per_layer; // [layer]
    num_t *allocated_gates_per_layer; // [layer]

    layer_t **layer_on_qubit; // [qubits][layer]
    num_t *allocated_layer_per_qubit; // [qubit]
    num_t *used_layer_per_qubit; // [qubits]

    num_t allocated_qubits;
    num_t used_qubits;
    size_t used;
    decompose_toffoli_t toff_decomp;

    qubit_t qubit_indices[MAXQUBITS]; // allow at most MAXQUBITS qubits
    qubit_t used_qubit_indices;
    qubit_t *ancilla;
} circuit_t;

typedef enum {
    BOOLEAN,
    SIGNED,
    UNSIGNED,
    UNINITIALIZED
} type_t;

typedef struct {
    bool_t qualifier;
    union {
        qubit_t q_address[INTEGERSIZE];
        int64_t *c_address;
    };
    type_t type;
} element_t;

typedef struct {
    element_t *el1;
    element_t *el2;
    element_t *el3;
    element_t *control;

    sequence_t *(*routine)();

    bool_t invert;
} instruction_t;

typedef struct {
    element_t GPR1[1];
    element_t GPR2[1];
    element_t GPR3[1];
    element_t GPC[1];

    instruction_t instruction_list[10000];
    int instruction_counter;

    circuit_t *circuit;
} hybrid_stack_t;

extern hybrid_stack_t stack;

circuit_t *init_circuit();

void print_circuit(circuit_t *circ);

void add_gate(circuit_t *circ, gate_t *g);

#endif //CQ_BACKEND_IMPROVED_QPU_H
