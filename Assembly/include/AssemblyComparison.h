//
// Created by Sören Wilkening on 05.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_ASSEMBLYCOMPARISON_H
#define CQ_BACKEND_IMPROVED_ASSEMBLYCOMPARISON_H

#include "Integer.h"
#include "gate.h"
#include "QPU.h"
#include "LogicOperations.h"
#include "IntegerComparison.h"
#include "AssemblyBasics.h"
#include "AssemblyArithmetic.h"

// integer comparisons
void EQ(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void GEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void LEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2);

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYCOMPARISON_H
