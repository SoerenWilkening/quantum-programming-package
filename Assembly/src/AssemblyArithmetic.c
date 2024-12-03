//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyOperations.h"

void IADD(element_t *el1, element_t *el2) {
    if (el1->qualifier == Cl && el2->qualifier == Qu) exit(5);


	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);

    // copy values instruction registers
    MOV(ins->el1, el1, POINTER);
    MOV(ins->el2, el2, POINTER);

    // routine assignments
    ins->routine = NULL;
    if (el1->qualifier == Qu && el2->qualifier == Qu) {
        if (ins->control->type != UNINITIALIZED) {
			ins->name = "cQQ_add ";
			ins->routine = cQQ_add;
		}
        else {
	        ins->name = "QQ_add ";
			ins->routine = QQ_add;
		}
    } else if (el1->qualifier == Qu && el2->qualifier == Cl) {
        if (ins->control->type != UNINITIALIZED) {
	        ins->name = "cCQ_add ";
			ins->routine = cCQ_add;
		}
        else {
	        ins->name = "CQ_add ";
			ins->routine = CQ_add;
		}
    } else if (el1->qualifier == Cl && el2->qualifier == Cl) {
	    ins->name = "CC_add ";
		ins->routine = CC_add;
	}
    else {
        printf("Cannot add quantum integer to classical integer!\n");
        exit(6);
    }
    stack.instruction_counter++;
}

void ISUB(element_t *el1, element_t *el2) {
    IADD(el1, el2);
    stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void INC(element_t *el1){
	element_t *cint = INT(1);
	IADD(el1, cint);
}

void DCR(element_t *el1){
	element_t *cint = INT(1);
	ISUB(el1, cint);
}

void IMUL(element_t *el1, element_t *el2, element_t *res) {
    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);

    // copy values instruction registers
    MOV(ins->el1, res, POINTER);
    MOV(ins->el2, el1, POINTER);
    MOV(ins->el3, el2, POINTER);

    if (el2->qualifier == Cl) {
        if (ins->control->type != UNINITIALIZED) ins->routine = cCQ_mul;
        else ins->routine = CQ_mul;
    } else {
        if (ins->control->type != UNINITIALIZED) ins->routine = cQQ_mul;
        else ins->routine = QQ_mul;
    }

    stack.instruction_counter++;
}


void IDIV(element_t *el1, element_t *el2, element_t *remainder) {
    // create IDIV sequence to Divide Aq / Bq

    element_t *Y = malloc(sizeof(element_t));
    memcpy(Y, el1, sizeof(element_t));
    for (int i = 1; i < INTEGERSIZE; ++i) {
        memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
        memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));

//        IF(ctrl);
        ISUB(Y, el2); // subtract Bq from Aq

        element_t *bit = bit_of_int(remainder, i - 1);

//        IF(ctrl);
        TSTBIT(bit, Y, 0); // check if Aq is negative, stored in Cq

//        if (ctrl->type != UNINITIALIZED) {
//            AND(bool_intermediate, ctrl, bit);
//            IF(bool_intermediate);
//        } else IF(bit); // create control for the next instruction
//	    IF(bit);
	    JEZ(bit);
        IADD(Y, el2); // Add bq back to Aq (controlled by Cq)
	    LABEL("internal_ctrl_add1");

        // Uncompute and
//        if (ctrl->type != UNINITIALIZED) AND(bool_intermediate, ctrl, bit);

//        IF(ctrl);
        NOT(bit); // Invert Cq
    }
//    IF(ctrl);
    ISUB(el1, el2); // subtract Bq from Aq
    element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);

//    IF(ctrl);
    TSTBIT(bit, el1, 0); // check if Aq is negative, stored in Cq

//    if (ctrl->type != UNINITIALIZED) {
//        AND(bool_intermediate, ctrl, bit);
//        IF(bool_intermediate);
//    } else IF(bit); // create control for the next instruction
//	IF(bit);
	JEZ(bit);
    IADD(el1, el2); // Add bq back to Aq (controlled by Cq)
	LABEL("internal_ctrl_add2");

    // Uncompute and
//    if (ctrl->type != UNINITIALIZED) AND(bool_intermediate, ctrl, bit);
//
//    IF(ctrl);
    ISUB(el1, el2);

//    IF(ctrl);
    NOT(bit); // Invert Cq

}

void MOD(element_t *mod, element_t *el1, element_t *el2) {
    IDIV(el1, el2, mod);
}

void PADD(element_t *el1, element_t *phase) {
    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction(ins);
    MOV(ins->el1, el1, POINTER);
    MOV(ins->el2, phase, POINTER);

    ins->routine = P_add;

    stack.instruction_counter++;
}

void NEG(element_t *el1){
    element_t *ctrl = stack.instruction_list[stack.instruction_counter].control;
	element_t *constant = INT(1);
	JEZ(ctrl);
	NOT(el1);
    ISUB(el1, constant);
	LABEL("");
}

