//
// Created by Sören Wilkening on 05.11.24.
//
#include "AssemblyOperations.h"

void eq(int *bool_res, int *bool_1, int *bool_2) {
	instruction_t *ins = init_instruction();

	ins->R0 = bool_res;
	ins->R1 = bool_1;
	ins->R2 = bool_2;

    ins->routine = CC_equal;
}
void qeq(quantum_int_t *Q0, quantum_int_t *Q1, int *R0) {
	instruction_t *ins = init_instruction();

	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->R0 = R0;

    ins->routine = CQ_equal;
}
void qqeq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2) {
	qqsub(Q1, Q2);

	int *cint = malloc(sizeof(int));
	cint[0] = 1;

	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->R0 = cint;
	ins->routine = CQ_equal;

	qqadd(Q1, Q2);
}
void cqeq(quantum_int_t *Q0, quantum_int_t *Q1, int *R0, quantum_int_t *ctrl) {
	instruction_t *ins = init_instruction();

	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;
	ins->R0 = R0;

    ins->routine = cCQ_equal;
}
void cqqeq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl) {
    qqsub(Q1, Q2);

	instruction_t *ins = init_instruction();
	int *cint = malloc(sizeof(int));
	cint[0] = 1;

	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;
	ins->R0 = cint;

    ins->routine = cCQ_equal;

    qqadd(Q1, Q2);
}

void leq(int *R0, int *R1, int *R2) {
	// TODO: implement proper version
}
void qleq(quantum_int_t *Q0, quantum_int_t *Q1, int *R0) {
	qsub(Q1, R0);
	qtstbit(Q0, Q1, 0);
	qadd(Q1, R0);
}
void qqleq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2) {
	qqsub(Q1, Q2);
	qtstbit(Q0, Q1, 0);
	qqadd(Q1, Q2);
}
void cqleq(quantum_int_t *Q0, quantum_int_t *Q1, int *R0, quantum_int_t *ctrl) {
	qsub(Q1, R0);
	cqtstbit(Q0, Q1, ctrl, 0);
	qadd(Q1, R0);
}
void cqqleq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl) {
	qqsub(Q1, Q2);
	cqtstbit(Q0, Q1, ctrl, 0);
	qqadd(Q1, Q2);
}

void geq(int *bool_res, int *bool_1, int *bool_2) {
	// TODO: implement proper version
}
void qgeq(quantum_int_t *Q0, int *R0, quantum_int_t *Q1) {
	qsub(Q1, R0);
	qtstbit(Q0, Q1, 0);
	qadd(Q1, R0);
}
void qqgeq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2) {
	qqsub(Q2, Q1);
	qtstbit(Q0, Q2, 0);
	qqadd(Q2, Q1);
}
void cqgeq(quantum_int_t *Q0, int *R0, quantum_int_t *Q1, quantum_int_t *ctrl) {
	qsub(Q1, R0);
	cqtstbit(Q0, Q1, ctrl, 0);
	qadd(Q1, R0);
}
void cqqgeq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl) {
	qqsub(Q2, Q1);
	cqtstbit(Q0, Q2, ctrl, 0);
	qqadd(Q2, Q1);
}
