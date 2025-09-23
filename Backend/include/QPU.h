//
// Created by Sören Wilkening on 05.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_QPU_H
#define CQ_BACKEND_IMPROVED_QPU_H

#include "gate.h"

// functionality to store the circuit structure ========================================================================
#define QUBITBLOCK 100
#define LAYERBLOCK 10000
#define GATESPERLAYERBLOCK 50
#define LAYERQUBITBLOCK 10000
#define MAXQUBITS 10000

#define MAXINSTRUCTIONS 7000

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

extern instruction_t instruction_list[MAXINSTRUCTIONS];
extern int instruction_counter;
extern instruction_t *QPU_state;
extern circuit_t *circuit;

circuit_t *init_circuit();

void print_circuit(circuit_t *circ);

void add_gate(circuit_t *circ, gate_t *g);

void CircuitToOPANQASM(circuit_t *circuit, char *path);

#endif //CQ_BACKEND_IMPROVED_QPU_H
