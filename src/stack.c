//
// Created by Sören Wilkening on 26.10.24.
//

#include "../QPU.h"


void MOV(element_t *el1, element_t *el2, int pov) {
    if (el2 == NULL) return;
    *el1 = *el2;

    if (el2->qualifier == Qu){
        if (pov == POINTER) ; // memcopy qubits
        else ; // create copy sequence
    }

}

void init_instruction(instruction_t *instr){
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

}

void execute(instruction_t *instr){
    if (instr->el1->type != UNINITIALIZED) MOV(stack.GPR1, instr->el1, POINTER);
    if (instr->el2->type != UNINITIALIZED) MOV(stack.GPR2, instr->el2, POINTER);
    if (instr->el3->type != UNINITIALIZED) MOV(stack.GPR3, instr->el3, POINTER);

    if (instr->control->type != UNINITIALIZED) MOV(stack.GPC, instr->control, POINTER);

    sequence_t *res = instr->routine();

    printf("%p\n", res);
    stack.GPR1[0].type = UNINITIALIZED;
    stack.GPR2[0].type = UNINITIALIZED;
    stack.GPR3[0].type = UNINITIALIZED;
    stack.GPC[0].type = UNINITIALIZED;
}