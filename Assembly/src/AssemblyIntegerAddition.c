//
// Created by Sören Wilkening on 08.12.24.
//

#include "AssemblyOperations.h"

void add(element_t *el1, element_t *el2) {
	instruction_t *ins = init_instruction();
	MOV(ins->el1, el1, POINTER);
	MOV(ins->el2, el2, POINTER);
	ins->name = "CC_add ";
	ins->routine = CC_add;
}

void qadd(element_t *el1, element_t *el2) {
	instruction_t *ins = init_instruction();
	MOV(ins->el1, el1, POINTER);
	MOV(ins->el2, el2, POINTER);

	ins->name = "CQ_add ";
	ins->routine = CQ_add;
}

void cqadd(element_t *el1, element_t *el2, element_t *ctrl) {
	instruction_t *ins = init_instruction();
	MOV(ins->el1, el1, POINTER);
	MOV(ins->el2, el2, POINTER);

	ins->name = "cCQ_add ";
	ins->routine = cCQ_add;
}

void qqadd(element_t *el1, element_t *el2) {
	instruction_t *ins = init_instruction();
	MOV(ins->el1, el1, POINTER);
	MOV(ins->el2, el2, POINTER);

	// routine assignments
	ins->name = "QQ_add ";
	ins->routine = QQ_add;
}

void cqqadd(element_t *el1, element_t *el2, element_t *ctrl) {
	instruction_t *ins = init_instruction();
	MOV(ins->el1, el1, POINTER);
	MOV(ins->el2, el2, POINTER);
	MOV(ins->control, ctrl, POINTER);

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