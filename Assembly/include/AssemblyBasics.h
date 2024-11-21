//
// Created by Sören Wilkening on 21.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_ASSEMBLYBASICS_H
#define CQ_BACKEND_IMPROVED_ASSEMBLYBASICS_H

#include "Integer.h"
#include "gate.h"
#include "QPU.h"
#include "LogicOperations.h"
#include "IntegerComparison.h"
#include "AssemblyBasics.h"

void MOV(element_t *el1, element_t *el2, int pov);

void NEG(element_t *el1);

void TSTBIT(element_t *el1, element_t *el2, int bit);

// program functionality
void IF(element_t *el1);
void ELSE(element_t *el1);
void INV();

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYBASICS_H
