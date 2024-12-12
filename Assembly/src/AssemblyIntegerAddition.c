//
// Created by Sören Wilkening on 08.12.24.
//

#include "AssemblyOperations.h"

void add(int *R0, int *R1) {
	instruction_t *ins = init_instruction();
	ins->R0 = R0;
	ins->R1 = R1;
	ins->name = "CC_add ";
	ins->routine = CC_add;
}
void qadd(quantum_int_t *Q0, int *R0) {
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->R0 = R0;

	ins->name = "CQ_add ";
	ins->routine = CQ_add;
}
void cqadd(quantum_int_t *Q0, int *R0, quantum_int_t *ctrl) {
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->R0 = R0;
	ins->Q1 = ctrl;

	ins->name = "cCQ_add ";
	ins->routine = cCQ_add;
}
void qqadd(quantum_int_t *Q0, quantum_int_t *Q1) {
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;

	// routine assignments
	ins->name = "QQ_add ";
	ins->routine = QQ_add;
}
void cqqadd(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *ctrl) {
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;

	// routine assignments
	ins->name = "cQQ_add ";
	ins->routine = cQQ_add;
}

void sub(int *R0, int *R1) {
	add(R0, R1);
	instruction_list[instruction_counter - 1].invert = INVERTED;
}
void qsub(quantum_int_t *Q0, int *R0) {
	qadd(Q0, R0);
	instruction_list[instruction_counter - 1].invert = INVERTED;
}
void cqsub(quantum_int_t *Q0, int *R0, quantum_int_t *ctrl) {
	cqadd(Q0, R0, ctrl);
	instruction_list[instruction_counter - 1].invert = INVERTED;
}
void qqsub(quantum_int_t *Q0, quantum_int_t *Q1) {
	qqadd(Q0, Q1);
	instruction_list[instruction_counter - 1].invert = INVERTED;
}
void cqqsub(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *ctrl) {
	cqqadd(Q0, Q1, ctrl);
	instruction_list[instruction_counter - 1].invert = INVERTED;
}

void inc(int *R0) {
	int *cint = malloc(sizeof(int));
	cint[0] = 1;
	add(R0, cint);
}
void qinc(quantum_int_t *Q0) {
	int *cint = malloc(sizeof(int));
	cint[0] = 1;
	qadd(Q0, cint);
}
void cqinc(quantum_int_t *Q0, quantum_int_t *ctrl) {
	int *cint = malloc(sizeof(int));
	cint[0] = 1;
	cqadd(Q0, cint, ctrl);
}

void dcr(int *R0) {
	int *cint = malloc(sizeof(int));
	cint[0] = 1;
	sub(R0, cint);
}
void qdcr(quantum_int_t *Q0) {
	int *cint = malloc(sizeof(int));
	cint[0] = 1;
	qsub(Q0, cint);
}
void cqdcr(quantum_int_t *Q0, quantum_int_t *ctrl) {
	int *cint = malloc(sizeof(int));
	cint[0] = 1;
	cqsub(Q0, cint, ctrl);
}

void padd(quantum_int_t *el1, int *phase) {
	instruction_t *ins = init_instruction();
	ins->Q0 = el1;
	ins->R0 = phase;

	ins->routine = P_add;
}
void cpadd(quantum_int_t *Q0, int *phase, quantum_int_t *ctrl) {
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = ctrl;
	ins->R0 = phase;

	// TODO: controlled version
	ins->routine = P_add;
}