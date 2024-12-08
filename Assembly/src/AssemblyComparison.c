//
// Created by Sören Wilkening on 05.11.24.
//
#include "AssemblyOperations.h"

void EQ(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
    if (bool_1->qualifier == Qu && bool_2->qualifier == Qu) {
	    qqsub(bool_1, bool_2);
    }
	instruction_t *ins = init_instruction();

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

    if (bool_1->qualifier == Qu && bool_2->qualifier == Qu) {
	    qqadd(bool_1, bool_2);
    }
}

void LEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	qqsub(bool_1, bool_2);
	tstbit(bool_res, bool_1, 0);
	qqadd(bool_1, bool_2);
}

void GEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	qqsub(bool_1, bool_2);
	tstbit(bool_res, bool_1, 0);
	qqadd(bool_1, bool_2);
}

