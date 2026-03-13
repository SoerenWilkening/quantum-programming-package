//
// Created by Sören Wilkening on 21.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_EXECUTION_H
#define CQ_BACKEND_IMPROVED_EXECUTION_H

// #include "AssemblyOperations.h"
#include "circuit.h"
#include "validation.h"

// functionality for C
// void init_instruction(instruction_t *instr);
void qubit_mapping(qubit_t qubit_arrray[], circuit_t *circ);
void run_instruction(sequence_t *res, const qubit_t qubit_array[], int invert, circuit_t *circ,
                     int tracking_only);
int execute(circuit_t *circ);
void reverse_circuit_range(circuit_t *circ, int start_layer, int end_layer);

// Validated entry points for Cython boundary (Phase 84)
// These wrap the originals with NULL checks and return error codes.
int validated_run_instruction(sequence_t *res, const qubit_t qubit_array[], int invert,
                              circuit_t *circ, int tracking_only);
int validated_reverse_circuit_range(circuit_t *circ, int start_layer, int end_layer);

#endif // CQ_BACKEND_IMPROVED_EXECUTION_H
