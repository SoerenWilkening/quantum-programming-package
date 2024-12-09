//
// Created by Sören Wilkening on 05.11.24.
//
#include "AssemblyOperations.h"

void eq(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	instruction_t *ins = init_instruction();

	mov(ins->el1, bool_res, POINTER);
	mov(ins->el2, bool_1, POINTER);
	mov(ins->el3, bool_2, POINTER);

    ins->routine = CC_equal;
}
void qeq(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	instruction_t *ins = init_instruction();

	mov(ins->el1, bool_res, POINTER);
	mov(ins->el2, bool_1, POINTER);
	mov(ins->el3, bool_2, POINTER);

    ins->routine = CQ_equal;
}
void qqeq(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	qqsub(bool_1, bool_2);
	instruction_t *ins = init_instruction();

	mov(ins->el1, bool_res, POINTER);
	mov(ins->el2, bool_1, POINTER);

	element_t *zero = INT(0);
	mov(ins->el3, zero, POINTER);

	ins->routine = CQ_equal;
	qqadd(bool_1, bool_2);
}
void cqeq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl) {
	instruction_t *ins = init_instruction();

	mov(ins->el1, bool_res, POINTER);
	mov(ins->el2, bool_1, POINTER);
	mov(ins->el3, bool_2, POINTER);
	mov(ins->control, ctrl, POINTER);

	// TODO: needs controlled version !!
    ins->routine = CQ_equal;
}
void cqqeq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl) {
    qqsub(bool_1, bool_2);

	instruction_t *ins = init_instruction();
	mov(ins->el1, bool_res, POINTER);
	mov(ins->el2, bool_1, POINTER);
    element_t *zero = INT(0);
	mov(ins->el3, zero, POINTER);
	mov(ins->control, ctrl, POINTER);

	// TODO: needs controlled sequence
    ins->routine = CQ_equal;

    qqadd(bool_1, bool_2);
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

