//
// Created by Sören Wilkening on 05.11.24.
//
#include "AssemblyOperations.h"

void eq(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	instruction_t *ins = init_instruction();

	ins->Q0 = bool_res;
	ins->Q1 = bool_1;
	ins->Q2 = bool_2;

    ins->routine = CC_equal;
}
void qeq(element_t *Q0, element_t *Q1, element_t *R0) {
	instruction_t *ins = init_instruction();

	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->R0 = (int *) R0->c_address;

    ins->routine = CQ_equal;
}
void qqeq(element_t *Q0, element_t *Q1, element_t *Q2) {
	qqsub(Q1, Q2);

	element_t *zero = INT(0);

	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->R0 = (int *) zero->c_address;
	ins->routine = CQ_equal;

	qqadd(Q1, Q2);
}
void cqeq(element_t *Q0, element_t *Q1, element_t *R0, element_t *ctrl) {
	instruction_t *ins = init_instruction();

	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;
	ins->R0 = (int *) R0->c_address;

    ins->routine = cCQ_equal;
}
void cqqeq(element_t *Q0, element_t *Q1, element_t *Q2, element_t *ctrl) {
    qqsub(Q1, Q2);

	instruction_t *ins = init_instruction();
	element_t *zero = INT(0);

	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;
	ins->R0 = (int *) zero->c_address;

    ins->routine = cCQ_equal;

    qqadd(Q1, Q2);
}

void leq(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	// TODO: implement proper version
}
void qleq(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	qsub(bool_1, bool_2);
	qtstbit(bool_res, bool_1, 0);
	qadd(bool_1, bool_2);
}
void qqleq(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	qqsub(bool_1, bool_2);
	qtstbit(bool_res, bool_1, 0);
	qqadd(bool_1, bool_2);
}
void cqleq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl) {
	qsub(bool_1, bool_2);
	cqtstbit(bool_res, bool_1, ctrl, 0);
	qqadd(bool_1, bool_2);
}
void cqqleq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl) {
	qqsub(bool_1, bool_2);
	cqtstbit(bool_res, bool_1, ctrl, 0);
	qqadd(bool_1, bool_2);
}

void geq(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	// TODO: implement proper version
}
void qgeq(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	qsub(bool_2, bool_1);
	qtstbit(bool_res, bool_2, 0);
	qadd(bool_2, bool_1);
}
void qqgeq(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	qqsub(bool_2, bool_1);
	qtstbit(bool_res, bool_2, 0);
	qqadd(bool_2, bool_1);
}
void cqgeq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl) {
	qsub(bool_2, bool_1);
	cqtstbit(bool_res, bool_2, ctrl, 0);
	qadd(bool_2, bool_1);
}
void cqqgeq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl) {
	qqsub(bool_2, bool_1);
	cqtstbit(bool_res, bool_2, ctrl, 0);
	qqadd(bool_2, bool_1);
}

