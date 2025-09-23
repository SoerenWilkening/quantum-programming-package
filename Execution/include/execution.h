//
// Created by Sören Wilkening on 21.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_EXECUTION_H
#define CQ_BACKEND_IMPROVED_EXECUTION_H


#include "AssemblyOperations.h"
#include "QPU.h"

// functionality for C
//void init_instruction(instruction_t *instr);
void qubit_mapping(qubit_t qubit_arrray[]);
void run_instruction(sequence_t *res, qubit_t qubit_array[], bool invert);
int execute();

#endif //CQ_BACKEND_IMPROVED_EXECUTION_H
