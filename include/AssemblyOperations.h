//
// Created by Sören Wilkening on 05.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_ASSEMBLYOPERATIONS_H
#define CQ_BACKEND_IMPROVED_ASSEMBLYOPERATIONS_H

#include "Integer.h"
#include "gate.h"
#include "QPU.h"
#include "LogicOperations.h"
#include "IntegerComparison.h"

void MOV(element_t *el1, element_t *el2, int pov);

void ADD(element_t *el1, element_t *el2);

void SUB(element_t *el1, element_t *el2);

void IMUL(element_t *el1, element_t *el2, element_t *res);

void IDIV(element_t *el1, element_t *el2, element_t *remainder);

void NOT(element_t *el1);

void IF(element_t *el1);

void ELSE(element_t *el1);

void TSTBIT(element_t *el1, element_t *el2, int bit);

void AND(element_t *bool_res, element_t *bool_1, element_t *bool_2);

void init_instruction(instruction_t *instr);

void execute(instruction_t *instr);

void GE(element_t *bool_res, element_t *bool_1, element_t *bool_2);

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYOPERATIONS_H
