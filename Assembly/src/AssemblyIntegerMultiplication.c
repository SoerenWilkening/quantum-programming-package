//
// Created by Sören Wilkening on 08.12.24.
//
#include "AssemblyOperations.h"


void mul(int *R0, int *R1, int *R2) {
	instruction_t *ins = &instruction_list[instruction_counter];
	init_instruction();

	// copy values instruction registers
	ins->R0 = R0;
	ins->R1 = R1;
	ins->R2 = R2;

	ins->routine = CC_mul; // replace with actual multiplication
}
void qmul(quantum_int_t *Q0, quantum_int_t *Q1, int *R0) {
	instruction_t *ins = &instruction_list[instruction_counter];
	init_instruction();

	// copy values instruction registers
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->R0 = R0;

	ins->routine = CQ_mul;
}
void cqmul(quantum_int_t *Q0, quantum_int_t *Q1, int *R0, quantum_int_t *ctrl) {
	instruction_t *ins = &instruction_list[instruction_counter];
	init_instruction();

	// copy values instruction registers
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;
	ins->R0 = R0;

	ins->routine = cCQ_mul;
}
void qqmul(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2) {
	instruction_t *ins = &instruction_list[instruction_counter];
	init_instruction();

	// copy values instruction registers
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = Q2;

	ins->routine = QQ_mul;
}
void cqqmul(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl) {
	instruction_t *ins = &instruction_list[instruction_counter];
	init_instruction();

	// copy values instruction registers
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = Q2;
	ins->Q3 = ctrl;

	ins->routine = cQQ_mul;
}

void qneg(quantum_int_t *Q0) {
	int *cint = malloc(sizeof(int));
	cint[0] = 1;
	qnot(Q0);
	qsub(Q0, cint);
}
void cqneg(quantum_int_t *Q0, quantum_int_t *ctrl) {
	int *cint = malloc(sizeof(int));
	cint[0] = 1;
	cqnot(Q0, ctrl);
	cqsub(Q0, cint, ctrl);
}