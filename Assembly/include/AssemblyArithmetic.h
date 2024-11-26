//
// Created by Sören Wilkening on 21.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_ASSEMBLYARITHMETIC_H
#define CQ_BACKEND_IMPROVED_ASSEMBLYARITHMETIC_H

#include "Integer.h"
#include "gate.h"
#include "QPU.h"
#include "LogicOperations.h"
#include "IntegerComparison.h"
#include "AssemblyBasics.h"
#include "AssemblyLogic.h"

// integer arithmetic
void IADD(element_t *el1, element_t *el2);
void ISUB(element_t *el1, element_t *el2);
void INC(element_t *el1);
void DCR(element_t *el1);
void IMUL(element_t *el1, element_t *el2, element_t *res);
void IDIV(element_t *el1, element_t *el2, element_t *remainder);
void MOD(element_t *mod, element_t *el1, element_t *el2);
// phase operations
void PADD(element_t *el1, element_t *phase);

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYARITHMETIC_H
