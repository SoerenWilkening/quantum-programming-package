//
// Created by Sören Wilkening on 26.10.24.
//

#ifndef CQ_BACKEND_IMPROVED_QPU_H
#define CQ_BACKEND_IMPROVED_QPU_H

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>


// desired functionality for storing all the gates and operations ======================================================
#define MAXCONTROLS 2
#define TRUE 1
#define FALSE 0

#define FREED 1
#define NOTFREED 0

#define INVERTED 1
#define NOTINVERTED 0

#define DECOMPOSETOFFOLI 1
#define DONTDECOMPOSETOFFOLI 0
typedef char decompose_toffoli_t;

typedef unsigned int qubit_t;
typedef size_t layer_t;
typedef unsigned int num_t;
typedef unsigned char bool_t;

typedef enum {
    X, R, H, Rx, Ry, Rz, P, Z, M
} Standardgate_t;

typedef struct {
    qubit_t Control[MAXCONTROLS];
    qubit_t *large_control;
    num_t NumControls;
    Standardgate_t Gate;
    double GateValue;
    qubit_t Target;
    num_t NumBasisGates;
    // store range of multiqubit gates
} gate_t;

typedef struct {
    gate_t **seq;
    num_t num_layer;
    num_t used_layer;
    num_t *gates_per_layer;
} sequence_t;


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

// funcitonality for stack operations and data =========================================================================
#define INTEGERSIZE 4

#define Qu 0
#define Cl 1

typedef enum {
    BOOL,
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

#define POINTER 1
#define VALUE 0

// circuit functions ===================================================================================================
circuit_t *init_circuit();

// integer generation and stack operation functions ====================================================================

int *two_complement(int64_t x, int n);

element_t *quantum_bool();

element_t *signed_quantum_integer();

element_t *unsigned_quantum_integer();

element_t *classical_integer(int64_t intg);

element_t *bit_of_int(element_t *el1, int bit);

//
//void push(element_t *element); // push qubit reference to stack
//
//void pop(element_t *element); // remove first entry from stack

void MOV(element_t *el1, element_t *el2, int pov);


// implementation of sequences, gates are already sorted by layer
// sequence is already supposed to use the stack
sequence_t *QFT(sequence_t *seq);

sequence_t *QFT_inverse(sequence_t *seq);

sequence_t *QQ_add();

sequence_t *cQQ_add();

void print_sequence(sequence_t *seq);

void ADD(element_t *el1, element_t *el2);

void SUB(element_t *el1, element_t *el2);

void IMUL(element_t *el1, element_t *el2, element_t *res);

void IDIV(element_t *el1, element_t *el2, element_t *remainder);

void NOT(element_t *el1);

void IF(element_t *el1);

void ELSE(element_t *el1);

void TSTBIT(element_t *el1, element_t *el2, int bit);

void init_instruction(instruction_t *instr);

void execute(instruction_t *instr);

extern sequence_t *precompiled_QQ_add;
extern sequence_t *precompiled_cQQ_add;
extern sequence_t *precompiled_CQ_add;
extern sequence_t *precompiled_cCQ_add;

#endif //CQ_BACKEND_IMPROVED_QPU_H
