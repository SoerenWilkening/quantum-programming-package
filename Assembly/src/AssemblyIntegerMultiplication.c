//
// Created by Sören Wilkening on 08.12.24.
//
#include "AssemblyOperations.h"


void mul(element_t *el1, element_t *el2, element_t *res) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	MOV(ins->el1, res, POINTER);
	MOV(ins->el2, el1, POINTER);
	MOV(ins->el3, el2, POINTER);

	ins->routine = void_seq; // replace with actual multiplication
}

void qmul(element_t *el1, element_t *el2, element_t *res) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	MOV(ins->el1, res, POINTER);
	MOV(ins->el2, el1, POINTER);
	MOV(ins->el3, el2, POINTER);

	ins->routine = CQ_mul;
}

void cqmul(element_t *el1, element_t *el2, element_t *res, element_t *ctrl) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	MOV(ins->el1, res, POINTER);
	MOV(ins->el2, el1, POINTER);
	MOV(ins->el3, el2, POINTER);
	MOV(ins->control, ctrl, POINTER);

	ins->routine = cCQ_mul;
}

void qqmul(element_t *el1, element_t *el2, element_t *res) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	MOV(ins->el1, res, POINTER);
	MOV(ins->el2, el1, POINTER);
	MOV(ins->el3, el2, POINTER);

	ins->routine = QQ_mul;
}

void cqqmul(element_t *el1, element_t *el2, element_t *res, element_t *ctrl) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	MOV(ins->el1, res, POINTER);
	MOV(ins->el2, el1, POINTER);
	MOV(ins->el3, el2, POINTER);
	MOV(ins->control, ctrl, POINTER);

	ins->routine = cQQ_mul;
}