//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyOperations.h"

void branch(element_t *el1, int bit) {
	instruction_t *ins = init_instruction();
	ins->name = "branch_seq ";
	element_t *qbit = bit_of_int(el1, bit);

	ins->Q0 = qbit;

	ins->routine = branch_seq;
}

void not(element_t *el1) {
	instruction_t *ins = init_instruction();
	ins->name = "not ";
	ins->Q0 = el1;

	ins->routine = void_seq;
}

void qnot(element_t *el1) {
	instruction_t *ins = init_instruction();
	ins->name = "qnot ";
	ins->Q0 = el1;

	ins->routine = not_seq;
}

void cqnot(element_t *el1, element_t *ctrl) {
	instruction_t *ins = init_instruction();
	ins->name = "cqnot ";
	ins->Q0 = el1;
	ins->Q1 = ctrl;

	ins->routine = ctrl_not_seq;
}

void and(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	instruction_t *ins = init_instruction();
	ins->name = "and ";
	ins->Q0 = bool_res;
	ins->Q1 = bool_1;
	ins->Q2 = bool_2;

	ins->routine = and_seq;

	ins->invert = NOTINVERTED;
}

void qand(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	instruction_t *ins = init_instruction();
	ins->name = "qand ";
	ins->Q0 = bool_res;
	ins->Q1 = bool_1;
	ins->R0 = (int *) bool_2->c_address;

	ins->routine = q_and_seq;

	ins->invert = NOTINVERTED;
}

void qqand(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	instruction_t *ins = init_instruction();
	ins->name = "qqand ";
	ins->Q0 = bool_res;
	ins->Q1 = bool_1;
	ins->Q2 = bool_2;

	ins->routine = qq_and_seq;

	ins->invert = NOTINVERTED;
}