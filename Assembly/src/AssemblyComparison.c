//
// Created by Sören Wilkening on 05.11.24.
//
#include "AssemblyOperations.h"

void EQ(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
    if (bool_1->qualifier == Qu && bool_2->qualifier == Qu) {
        ISUB(bool_1, bool_2);
    }

    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);

    MOV(ins->el1, bool_res, POINTER);
    MOV(ins->el2, bool_1, POINTER);

    if (bool_1->qualifier == Qu && bool_2->qualifier == Qu) {
        element_t *zero = INT(0);
        MOV(ins->el3, zero, POINTER);
    } else {
        MOV(ins->el3, bool_2, POINTER);
    }

    if (bool_1->qualifier == Cl && bool_2->qualifier == Cl) ins->routine = CC_equal;
    else ins->routine = CQ_equal;

    ins->invert = NOTINVERTED;
    stack.instruction_counter++;

    if (bool_1->qualifier == Qu && bool_2->qualifier == Qu) {
        IADD(bool_1, bool_2);
    }
}

void LEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2) {

    ISUB(bool_1, bool_2);

    TSTBIT(bool_res, bool_1, 0);

    IADD(bool_1, bool_2);
}

void GEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2) {

    ISUB(bool_1, bool_2);

    TSTBIT(bool_res, bool_1, 0);

    IADD(bool_1, bool_2);
}

