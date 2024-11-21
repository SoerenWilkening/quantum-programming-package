//
// Created by Sören Wilkening on 21.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_EXECUTION_H
#define CQ_BACKEND_IMPROVED_EXECUTION_H


#include "AssemblyArithmetic.h"
#include "AssemblyBasics.h"
#include "AssemblyLogic.h"
#include "QPU.h"

// functionality for C
void init_instruction(instruction_t *instr);
void execute(instruction_t *instr);

#endif //CQ_BACKEND_IMPROVED_EXECUTION_H
