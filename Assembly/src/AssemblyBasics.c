//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyBasics.h"

void MOV(element_t *el1, element_t *el2, int pov) {
    if (el2 == NULL) return;
//    *el1 = *el2;
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
	labels[label_counter].label = label;
	labels[label_counter++].ins_ptr = &stack.instruction_list[stack.instruction_counter];
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);
	ins->name = "label ";
	ins->routine = void_seq;
	if (stack.instruction_counter != 0) stack.instruction_list[stack.instruction_counter].control->type = UNINITIALIZED;
	stack.instruction_counter++;
}

void JMP(){
	element_t *cb = BOOL(1);
	JEZ(cb);
}

void JEZ(element_t *bool1){ // Jump if bool1 is not 0 (1)
	// proper jump, only if bool is classical
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);
	ins->name = "jnz ";
	if (bool1->qualifier == Qu) MOV(ins->control, bool1, POINTER);
	MOV(ins->el1, bool1, POINTER);

	ins->routine = void_seq;
	stack.instruction_counter++;
}