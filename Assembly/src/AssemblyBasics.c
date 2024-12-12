//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyOperations.h"

instruction_t *init_instruction() {
	instruction_t *instr = &instruction_list[instruction_counter];
	instr->Q0 = NULL;
	instr->Q1 = NULL;
	instr->Q2 = NULL;
	instr->Q3 = NULL;

	instr->R0 = NULL;
	instr->R1 = NULL;
	instr->R2 = NULL;
	instr->R3 = NULL;

	instr->routine = NULL;
	instr->invert = NOTINVERTED;
	instr->next_instruction = NULL;
	instruction_counter++;

	return instr;
}

void tstbit(element_t *el1, element_t *el2, int bit) {
	instruction_t *ins = init_instruction();
	ins->name = "testbit ";
	ins->Q0 = el1;

	element_t *qbit = bit_of_int(el2, bit);

	ins->Q1 = qbit;
	ins->routine = void_seq;
}

void qtstbit(element_t *el1, element_t *el2, int bit) {
	instruction_t *ins = init_instruction();
	ins->name = "testbit ";
	ins->Q0 = el1; // return value

	element_t *qbit = bit_of_int(el2, bit);

	ins->Q1 = qbit;
	ins->routine = cx_gate;
}

void cqtstbit(element_t *el1, element_t *el2, element_t *ctrl, int bit) {
	instruction_t *ins = init_instruction();
	ins->name = "testbit ";
	ins->Q0 = el1; // return value

	element_t *qbit = bit_of_int(el2, bit);

	ins->Q1 = qbit;
	ins->Q2 = ctrl;
	ins->routine = ccx_gate;
}

void inv() {
	instruction_list[instruction_counter].invert = INVERTED;
}

void jmp() {
	element_t *cb = BOOL(0);
	jez(cb);
}

void jez(element_t *bool1) {
	// jumps are purely classical

	instruction_t *ins = init_instruction();
	ins->R0 = (int *) bool1->c_address;
	ins->name = "jez ";

	ins->routine = jmp_seq;

}

void label(char label[]) {
	instruction_t *ins = init_instruction();
	ins->name = "label ";
	labels[label_counter].ins_ptr = ins;
	labels[label_counter].label = label;
	label_counter++;
	ins->routine = void_seq;
}
