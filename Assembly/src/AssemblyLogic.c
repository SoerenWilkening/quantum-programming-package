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
void cbranch(element_t *el1, element_t *ctrl, int bit) {
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
void cqand(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl) {
	instruction_t *ins = init_instruction();
	ins->name = "qand ";
	ins->Q0 = bool_res;
	ins->Q1 = bool_1;
	ins->Q2 = ctrl;
	ins->R0 = (int *) bool_2->c_address;

	ins->routine = cq_and_seq;

	ins->invert = NOTINVERTED;
}
void cqqand(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl) {
	instruction_t *ins = init_instruction();
	ins->name = "qqand ";
	ins->Q0 = bool_res;
	ins->Q1 = bool_1;
	ins->Q2 = bool_2;
	ins->Q3 = ctrl;

	ins->routine = cqq_and_seq;

	ins->invert = NOTINVERTED;
}

void xor(element_t *R0, element_t *R1){}
void qxor(element_t *Q0, element_t *R0){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->R0 = (int *) R0->c_address;
	ins->routine = q_xor_seq;
}
void qqxor(element_t *Q0, element_t *Q1){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->routine = qq_xor_seq;
}
void cqxor(element_t *Q0, element_t *R0, element_t *ctrl){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = ctrl;
	ins->R0 = (int *) R0->c_address;
	ins->routine = cq_xor_seq;
}
void cqqxor(element_t *Q0, element_t *Q1, element_t *ctrl){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;
	ins->routine = cqq_xor_seq;
}


void or(element_t *R0, element_t *R1){}
void qor(element_t *Q0, element_t *Q1, element_t *R0){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->R0 = (int *) R0->c_address;
	ins->routine = q_or_seq;
}
void qqor(element_t *Q0, element_t *Q1, element_t *Q2){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = Q2;
	ins->routine = qq_or_seq;
}
void cqor(element_t *Q0, element_t *Q1, element_t *R0, element_t *ctrl){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;
	ins->R0 = (int *) R0->c_address;
	ins->routine = cq_or_seq;
}
void cqqor(element_t *Q0, element_t *Q1, element_t *Q2, element_t *ctrl){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = Q2;
	ins->Q3 = ctrl;
	ins->routine = cqq_or_seq;
}