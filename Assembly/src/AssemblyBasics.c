//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyBasics.h"

void MOV(element_t *el1, element_t *el2, int pov) {
    if (el2 == NULL) return;
    *el1 = *el2;

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
    MOV(ins->el1, el1, POINTER); // return value

    element_t *qbit = bit_of_int(el2, bit);

    MOV(ins->el2, qbit, POINTER);
    ins->routine = cx_gate;
    ins->invert = NOTINVERTED;
    stack.instruction_counter++;
}

void IF(element_t *el1) {
    MOV(stack.instruction_list[stack.instruction_counter].control, el1, POINTER);
}

void INV() {
    stack.instruction_list[stack.instruction_counter].invert = INVERTED;
}