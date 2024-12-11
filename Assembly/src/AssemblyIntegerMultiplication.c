//
// Created by Sören Wilkening on 08.12.24.
//
#include "AssemblyOperations.h"


void mul(element_t *el1, element_t *el2, element_t *res) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	ins->R0 = (int *) res->c_address;
	ins->R1 = (int *) el1->c_address;
	ins->R2 = (int *) el2->c_address;

	ins->routine = CC_mul; // replace with actual multiplication
}
void qmul(element_t *el1, element_t *el2, element_t *res) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	ins->Q0 = res;
	ins->Q1 = el1;
	ins->R0 = (int *) el2->c_address;

	ins->routine = CQ_mul;
}
void cqmul(element_t *el1, element_t *el2, element_t *res, element_t *ctrl) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	ins->Q0 = res;
	ins->Q1 = el1;
	ins->R0 = (int *)el2->c_address;
	ins->Q2 = ctrl;

	ins->routine = cCQ_mul;
}
void qqmul(element_t *el1, element_t *el2, element_t *res) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	ins->Q0 = res;
	ins->Q1 = el1;
	ins->Q2 = el2;

	ins->routine = QQ_mul;
}
void cqqmul(element_t *el1, element_t *el2, element_t *res, element_t *ctrl) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	ins->Q0 = res;
	ins->Q1 = el1;
	ins->Q2 = el2;
	ins->Q3 = ctrl;

	ins->routine = cQQ_mul;
}

void qneg(element_t *el1) {
	element_t *constant = INT(1);
	qnot(el1);
	qsub(el1, constant);
}
void cqneg(element_t *el1, element_t *ctrl) {
	element_t *constant = INT(1);
	cqnot(el1, ctrl);
	cqsub(el1, constant, ctrl);
}