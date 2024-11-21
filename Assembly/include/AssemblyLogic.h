//
// Created by Sören Wilkening on 21.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_ASSEMBLYLOGIC_H
#define CQ_BACKEND_IMPROVED_ASSEMBLYLOGIC_H

#include "Integer.h"
#include "gate.h"
#include "QPU.h"
#include "LogicOperations.h"
#include "IntegerComparison.h"
#include "AssemblyBasics.h"

// Logical operations
void BRANCH(element_t *el1, int bit);
void NOT(element_t *el1);
void AND(element_t *bool_res, element_t *bool_1, element_t *bool_2);

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYLOGIC_H
