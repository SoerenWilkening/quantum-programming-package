//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyOperations.h"

void branch(element_t *el1, int bit) {
	instruction_t *ins = init_instruction();
	ins->name = "branch_seq ";
    element_t *qbit = bit_of_int(el1, bit);

    MOV(ins->el1, qbit, POINTER);

    ins->routine = branch_seq;
}

void not(element_t *el1) {
	instruction_t *ins = init_instruction();
	ins->name = "not ";
	MOV(ins->el1, el1, POINTER);

	ins->routine = void_seq;
}

void qnot(element_t *el1) {
	instruction_t *ins = init_instruction();
	ins->name = "qnot ";
    MOV(ins->el1, el1, POINTER);

    ins->routine = not_seq;
}

void cqnot(element_t *el1, element_t *ctrl) {
	instruction_t *ins = init_instruction();
	ins->name = "qnot ";
	MOV(ins->el1, el1, POINTER);

	ins->routine = cx_gate;
}

void and(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	instruction_t *ins = init_instruction();
	ins->name = "and ";
	MOV(ins->el1, bool_res, POINTER);
	MOV(ins->el2, bool_1, POINTER);
	MOV(ins->el3, bool_2, POINTER);

	ins->routine = and_sequence;

	ins->invert = NOTINVERTED;
}

void qand(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	instruction_t *ins = init_instruction();
	ins->name = "qand ";
	MOV(ins->el1, bool_res, POINTER);
	MOV(ins->el2, bool_1, POINTER);
	MOV(ins->el3, bool_2, POINTER);

	ins->routine = and_sequence;

	ins->invert = NOTINVERTED;
}

void qqand(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	instruction_t *ins = init_instruction();
	ins->name = "qqand ";
    MOV(ins->el1, bool_res, POINTER);
    MOV(ins->el2, bool_1, POINTER);
    MOV(ins->el3, bool_2, POINTER);

    ins->routine = and_sequence;

    ins->invert = NOTINVERTED;
}