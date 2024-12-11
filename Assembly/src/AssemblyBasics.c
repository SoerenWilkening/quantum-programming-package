//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyOperations.h"

instruction_t *init_instruction() {
	instruction_t *instr = &stack.instruction_list[stack.instruction_counter];
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
	stack.instruction_counter++;

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
	stack.instruction_list[stack.instruction_counter].invert = INVERTED;
}

void jmp() {
	element_t *cb = BOOL(0);
	jez(cb);
}

void jez(element_t *bool1) { // Jump if bool1 is qnot 0 (1)
	// proper jump, only if bool is classical
	element_t *step;
//	if (active_label_counter > 0) {
//		step = QBOOL();
//		qqand(step, active_label[active_label_counter].ctrl, bool1);
//		mov(active_label[active_label_counter].step, bool1, POINTER);
//	} else step = bool1;

	instruction_t *ins = init_instruction();
	ins->name = "jez ";
//	if (step->qualifier == Qu) {
//		mov(active_label[active_label_counter + 1].ctrl, step, POINTER);
//		active_label_counter++;
//	}
	ins->routine = void_seq;

}

void label(char label[]) {
//	if (active_label_counter > 1){
//		qqand(active_label[active_label_counter].ctrl, active_label[active_label_counter - 1].ctrl,
//		      active_label[active_label_counter - 1].step);
//		free_element(active_label[active_label_counter].ctrl);
//	}
//	if (stack.instruction_counter > 0) active_label_counter--;
//
//	labels[label_counter].label = label;
//	labels[label_counter++].ins_ptr = &stack.instruction_list[stack.instruction_counter];

	instruction_t *ins = init_instruction();
	ins->name = "label ";
	ins->routine = void_seq;
}
