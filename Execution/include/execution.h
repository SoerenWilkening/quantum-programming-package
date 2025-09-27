//
// Created by Sören Wilkening on 21.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_EXECUTION_H
#define CQ_BACKEND_IMPROVED_EXECUTION_H


#include "AssemblyOperations.h"
#include "QPU.h"

// functionality for C
//void init_instruction(instruction_t *instr);
void qubit_mapping(qubit_t qubit_arrray[], circuit_t *circ);
void run_instruction(sequence_t *res, const qubit_t qubit_array[], bool invert, circuit_t *circ);
int execute(circuit_t *circ);

#endif //CQ_BACKEND_IMPROVED_EXECUTION_H
