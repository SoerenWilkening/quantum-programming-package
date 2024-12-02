//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyLogic.h"

//void BRANCH(element_t *el1, int bit) {
//    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
//	init_instruction(ins);
//	ins->name = "branch ";
//    element_t *qbit = bit_of_int(el1, bit);
//
//    MOV(ins->el1, qbit, POINTER);
//
//    ins->routine = branch;
//    stack.instruction_counter++;
//}
//
//void NOT(element_t *el1) {
//    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
//	init_instruction(ins);
//	ins->name = "not ";
//    MOV(ins->el1, el1, POINTER);
//
//    ins->routine = not_seq;
//    stack.instruction_counter++;
//}
//
//void AND(element_t *bool_res, element_t *bool_1, element_t *bool_2) {
//    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
//	init_instruction(ins);
//	ins->name = "and ";
//    MOV(ins->el1, bool_res, POINTER);
//    MOV(ins->el2, bool_1, POINTER);
//    MOV(ins->el3, bool_2, POINTER);
//
//    ins->routine = and_sequence;
//
//    ins->invert = NOTINVERTED;
//    stack.instruction_counter++;
//}