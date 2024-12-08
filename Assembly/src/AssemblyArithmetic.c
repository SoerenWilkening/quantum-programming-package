//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyOperations.h"

void inc(element_t *el1) {
	element_t *cint = INT(1);
	add(el1, cint);
}

void qinc(element_t *el1) {
	element_t *cint = INT(1);
	qadd(el1, cint);
}

void dcr(element_t *el1) {
	element_t *cint = INT(1);
	sub(el1, cint);
}

void qdcr(element_t *el1) {
	element_t *cint = INT(1);
	qsub(el1, cint);
}

void padd(element_t *el1, element_t *phase) {
	instruction_t *ins = init_instruction();
	MOV(ins->el1, el1, POINTER);
	MOV(ins->el2, phase, POINTER);

	ins->routine = P_add;
}

void neg(element_t *el1) {
	element_t *ctrl = stack.instruction_list[stack.instruction_counter].control;
	element_t *constant = INT(1);
	jez(ctrl);
	qnot(el1);
	qqsub(el1, constant);
	label("");
}

