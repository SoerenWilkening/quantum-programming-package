//
// Created by Sören Wilkening on 08.12.24.
//

#include "AssemblyOperations.h"

void add(element_t *el1, element_t *el2) {
	instruction_t *ins = init_instruction();
	mov(ins->el1, el1, POINTER);
	mov(ins->el2, el2, POINTER);
	ins->name = "CC_add ";
	ins->routine = CC_add;
}

void qadd(element_t *el1, element_t *el2) {
	instruction_t *ins = init_instruction();
	mov(ins->el1, el1, POINTER);
	mov(ins->el2, el2, POINTER);

	ins->name = "CQ_add ";
	ins->routine = CQ_add;
}

void cqadd(element_t *el1, element_t *el2, element_t *ctrl) {
	instruction_t *ins = init_instruction();
	mov(ins->el1, el1, POINTER);
	mov(ins->el2, el2, POINTER);

	ins->name = "cCQ_add ";
	ins->routine = cCQ_add;
}

void qqadd(element_t *el1, element_t *el2) {
	instruction_t *ins = init_instruction();
	mov(ins->el1, el1, POINTER);
	mov(ins->el2, el2, POINTER);

	// routine assignments
	ins->name = "QQ_add ";
	ins->routine = QQ_add;
}

void cqqadd(element_t *el1, element_t *el2, element_t *ctrl) {
	instruction_t *ins = init_instruction();
	mov(ins->el1, el1, POINTER);
	mov(ins->el2, el2, POINTER);
	mov(ins->control, ctrl, POINTER);

	// routine assignments
	ins->name = "cQQ_add ";
	ins->routine = cQQ_add;
}

void sub(element_t *el1, element_t *el2) {
	add(el1, el2);
	stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void qsub(element_t *el1, element_t *el2) {
	qadd(el1, el2);
	stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void cqsub(element_t *el1, element_t *el2, element_t *ctrl) {
	cqadd(el1, el2, ctrl);
	stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void qqsub(element_t *el1, element_t *el2) {
	qqadd(el1, el2);
	stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void cqqsub(element_t *el1, element_t *el2, element_t *ctrl) {
	cqqadd(el1, el2, ctrl);
	stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void inc(element_t *el1) {
	element_t *cint = INT(1);
	add(el1, cint);
}

void qinc(element_t *el1) {
	element_t *cint = INT(1);
	qadd(el1, cint);
}

void cqinc(element_t *el1, element_t *ctrl) {
	element_t *cint = INT(1);
	cqadd(el1, cint, ctrl);
}

void dcr(element_t *el1) {
	element_t *cint = INT(1);
	sub(el1, cint);
}

void qdcr(element_t *el1) {
	element_t *cint = INT(1);
	qsub(el1, cint);
}

void cqdcr(element_t *el1, element_t *ctrl) {
	element_t *cint = INT(1);
	cqsub(el1, cint, ctrl);
}

void padd(element_t *el1, element_t *phase) {
	instruction_t *ins = init_instruction();
	mov(ins->el1, el1, POINTER);
	mov(ins->el2, phase, POINTER);

	ins->routine = P_add;
}

void cpadd(element_t *el1, element_t *phase, element_t *ctrl) {
	instruction_t *ins = init_instruction();
	mov(ins->el1, el1, POINTER);
	mov(ins->el2, phase, POINTER);
	mov(ins->control, ctrl, POINTER);

	ins->routine = P_add;
}