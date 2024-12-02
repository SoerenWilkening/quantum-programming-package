//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyBasics.h"

void init_instruction(instruction_t *instr) {
	instr->el1 = malloc(sizeof(element_t));
	instr->el1->c_address = malloc(sizeof(int64_t));
	instr->el1->type = UNINITIALIZED;

	instr->el2 = malloc(sizeof(element_t));
	instr->el2->c_address = malloc(sizeof(int64_t));
	instr->el2->type = UNINITIALIZED;

	instr->el3 = malloc(sizeof(element_t));
	instr->el3->c_address = malloc(sizeof(int64_t));
	instr->el3->type = UNINITIALIZED;

	instr->control = malloc(sizeof(element_t));
	instr->control->c_address = malloc(sizeof(int64_t));
	instr->control->type = UNINITIALIZED;

	instr->routine = NULL;
	instr->invert = NOTINVERTED;
	instr->next_instruction = NULL;
	if (stack.instruction_counter == 0) return;

	instruction_t *prev = instr;
	prev--;
	MOV(instr->control, active_label[active_label_counter].ctrl, POINTER);
}

void MOV(element_t *el1, element_t *el2, int pov) {
    if (el2 == NULL) return;
	memcpy(el1, el2, sizeof(element_t));

    if (el2->qualifier == Qu) {
        if (pov == POINTER)
            if (el2->type == BOOLEAN)
                memcpy(el1->q_address, el2->q_address, sizeof(int)); // memcopy qubits
            else
                memcpy(el1->q_address, el2->q_address, INTEGERSIZE * sizeof(int)); // memcopy qubits
        else; // create copy sequence
    }
}

void TSTBIT(element_t *el1, element_t *el2, int bit) {
    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);
	ins->name = "testbit ";
    MOV(ins->el1, el1, POINTER); // return value

    element_t *qbit = bit_of_int(el2, bit);

    MOV(ins->el2, qbit, POINTER);
    ins->routine = cx_gate;
    stack.instruction_counter++;
}

void IF(element_t *el1) {
    MOV(stack.instruction_list[stack.instruction_counter].control, el1, POINTER);
}

void INV() {
    stack.instruction_list[stack.instruction_counter].invert = INVERTED;
}

void LABEL(char label[]){
	if (active_label_counter > 1){
		AND(active_label[active_label_counter].ctrl, active_label[active_label_counter - 1].ctrl, active_label[active_label_counter - 1].step);
		printf("ands = %d\n", active_label[active_label_counter].ctrl[0].q_address[0]);
		free_element(active_label[active_label_counter].ctrl);
	}
	if (stack.instruction_counter > 0) active_label_counter--;

	labels[label_counter].label = label;
	labels[label_counter++].ins_ptr = &stack.instruction_list[stack.instruction_counter];

	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);
	ins->name = "label ";
	ins->routine = void_seq;
	stack.instruction_counter++;
}

void JMP(){
	element_t *cb = BOOL(0);
	JEZ(cb);
}

void JEZ(element_t *bool1){ // Jump if bool1 is not 0 (1)
	// proper jump, only if bool is classical
	element_t *step;
	if (active_label_counter > 0) {
		printf("do and\n");
		step = QBOOL();
		AND(step, active_label[active_label_counter].ctrl, bool1);
		MOV(active_label[active_label_counter].step, bool1, POINTER);
	} else step = bool1;

	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);
	ins->name = "jez ";
	if (step->qualifier == Qu) {
		MOV(active_label[active_label_counter + 1].ctrl, step, POINTER);
		active_label_counter++;
	}
	ins->routine = void_seq;
	stack.instruction_counter++;

}

void BRANCH(element_t *el1, int bit) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);
	ins->name = "branch ";
	element_t *qbit = bit_of_int(el1, bit);

	MOV(ins->el1, qbit, POINTER);

	ins->routine = branch;
	stack.instruction_counter++;
}

void NOT(element_t *el1) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);
	ins->name = "not ";
	MOV(ins->el1, el1, POINTER);

	ins->routine = not_seq;
	stack.instruction_counter++;
}

void AND(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);
	ins->name = "and ";
	MOV(ins->el1, bool_res, POINTER);
	MOV(ins->el2, bool_1, POINTER);
	MOV(ins->el3, bool_2, POINTER);

	ins->routine = and_sequence;

	ins->invert = NOTINVERTED;
	stack.instruction_counter++;
}