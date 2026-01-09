//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyOperations.h"

int label_counter = 0;
label_t labels[3];

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

void qset(quantum_int_t *Q0, int *R0){
	instruction_t *ins = init_instruction();
	ins->name = "qset ";
	ins->Q0 = Q0;
	ins->R0 = R0;

	ins->routine = setting_seq;
}

void tstbit(quantum_int_t *el1, quantum_int_t *el2, int bit) {
	instruction_t *ins = init_instruction();
	ins->name = "testbit ";
	ins->Q0 = el1;

	quantum_int_t *qbit = bit_of_int(el2, bit);

	ins->Q1 = qbit;
	ins->routine = void_seq;
}

void qtstbit(quantum_int_t *res, quantum_int_t *integer, int bit) {
	instruction_t *ins = init_instruction();
	ins->name = "qtestbit ";
	ins->Q0 = res; // return value

	quantum_int_t *qbit = bit_of_int(integer, bit);

	ins->Q1 = qbit;
	ins->routine = cx_gate;
}

void cqtstbit(quantum_int_t *res, quantum_int_t *integer, quantum_int_t *ctrl, int bit) {
	// inputs are boolean variables
	instruction_t *ins = init_instruction();
	ins->name = "cqtestbit ";
	ins->Q0 = res; // return value

	quantum_int_t *qbit = bit_of_int(integer, bit);

	ins->Q1 = qbit;
	ins->Q2 = ctrl;
	ins->routine = ccx_gate;
}

void inv() {
	instruction_list[instruction_counter].invert = INVERTED;
}

void jmp() {
	int *cint = malloc(sizeof(int));
	cint[0] = 0;
	jez(cint);
}

void jez(int *bool1) {
	// jumps are purely classical

	instruction_t *ins = init_instruction();
	ins->R0 = bool1;
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
