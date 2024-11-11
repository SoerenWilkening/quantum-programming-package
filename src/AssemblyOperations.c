//
// Created by Sören Wilkening on 05.11.24.
//
#include "../include/AssemblyOperations.h"

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

    print_sequence(res);
    stack.GPR1[0].type = UNINITIALIZED;
    stack.GPR2[0].type = UNINITIALIZED;
    stack.GPR3[0].type = UNINITIALIZED;
    stack.GPC[0].type = UNINITIALIZED;
}

void MOV(element_t *el1, element_t *el2, int pov) {
    if (el2 == NULL) return;
    *el1 = *el2;

    if (el2->qualifier == Qu){
        if (pov == POINTER)
            if (el2->type == BOOL)
                memcpy(el1->q_address, el2->q_address, sizeof(int)); // memcopy qubits
            else
                memcpy(el1->q_address, el2->q_address, INTEGERSIZE * sizeof(int)); // memcopy qubits
        else ; // create copy sequence
    }
}

void ADD(element_t *el1, element_t *el2) {
    if (el1->qualifier == Cl && el2->qualifier == Qu) exit(5);

    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];

    // copy values instruction registers
    MOV(ins->el1, el1, POINTER);
    MOV(ins->el2, el2, POINTER);

    // routine assignments
    ins->routine = NULL;
    if (el1->qualifier == Qu && el2->qualifier == Qu) {
        if (ins->control->type != UNINITIALIZED) ins->routine = cQQ_add;
        else ins->routine = QQ_add;
    } else if (el1->qualifier == Qu && el2->qualifier == Cl) {
        if (ins->control->type != UNINITIALIZED) ins->routine = cCQ_add;
        else ins->routine = CQ_add;
    } else if (el1->qualifier == Cl && el2->qualifier == Cl) ins->routine = CC_add;
    else {
        printf("Cannot add quantum integer to classical integer!\n");
        exit(6);
    }
    ins->invert = NOTINVERTED;
    stack.instruction_counter++;
}

void SUB(element_t *el1, element_t *el2) {
    ADD(el1, el2);
    stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void IMUL(element_t *el1, element_t *el2, element_t *res) {
    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];

    // copy values instruction registers
    MOV(ins->el1, res, POINTER);
    MOV(ins->el2, el1, POINTER);
    MOV(ins->el3, el2, POINTER);

    if (el2->qualifier == Cl) {
        if (ins->control->type != UNINITIALIZED) ins->routine = cCQ_mul;
        else ins->routine = CQ_mul;
    }
    else {
        if (ins->control->type != UNINITIALIZED) ins->routine = cQQ_mul;
        else ins->routine = QQ_mul;
    }

    ins->invert = NOTINVERTED;
    stack.instruction_counter++;
}

void IDIV(element_t *el1, element_t *el2, element_t *remainder) {
    // create IDIV sequence to Divide Aq / Bq
//    printf("%d %d\n", stack.instruction_list[stack.instruction_counter + 1].control->type, UNINITIALIZED);

    element_t *ctrl = stack.instruction_list[stack.instruction_counter].control;
    element_t *bool_intermediate = quantum_bool();

    element_t *Y = malloc(sizeof(element_t));
    memcpy(Y, el1, sizeof(element_t));
    for (int i = 1; i < INTEGERSIZE; ++i) {
        memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
        memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));

        IF(ctrl);
        SUB(Y, el2); // subtract Bq from Aq

        element_t *bit = bit_of_int(remainder, i - 1);

        IF(ctrl);
        TSTBIT(bit, Y, 0); // check if Aq is negative, stored in Cq

        if (ctrl->type != UNINITIALIZED) {
            AND(bool_intermediate, ctrl, bit);
            IF(bool_intermediate);
        }
        else IF(bit); // create control for the next instruction
        ADD(Y, el2); // Add bq back to Aq (controlled by Cq)

        // Uncompute and
        if (ctrl->type != UNINITIALIZED) AND(bool_intermediate, ctrl, bit);

        IF(ctrl);
        NOT(bit); // Invert Cq
    }
    IF(ctrl);
    SUB(el1, el2); // subtract Bq from Aq
    element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);

    IF(ctrl);
    TSTBIT(bit, el1, 0); // check if Aq is negative, stored in Cq

    if (ctrl->type != UNINITIALIZED) {
        AND(bool_intermediate, ctrl, bit);
        IF(bool_intermediate);
    }
    else IF(bit); // create control for the next instruction
    ADD(el1, el2); // Add bq back to Aq (controlled by Cq)

    // Uncompute and
    if (ctrl->type != UNINITIALIZED) AND(bool_intermediate, ctrl, bit);

    IF(ctrl);
    SUB(el1, el2);

    IF(ctrl);
    NOT(bit); // Invert Cq

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

void NOT(element_t *el1) {
    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
    MOV(ins->el1, el1, POINTER);

    ins->routine = not_seq;
    ins->invert = NOTINVERTED;
    stack.instruction_counter++;
}

void IF(element_t *el1) {
    MOV(stack.instruction_list[stack.instruction_counter].control, el1, POINTER);
}

void ELSE(element_t *el1) {
    NOT(el1);
    MOV(stack.instruction_list[stack.instruction_counter].control, el1, POINTER);
    NOT(el1);
}

void AND(element_t *bool_res, element_t *bool_1, element_t *bool_2){
    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
    MOV(ins->el1, bool_res, POINTER);
    MOV(ins->el2, bool_1, POINTER);
    MOV(ins->el3, bool_2, POINTER);

    ins->routine = and_sequence;

    ins->invert = NOTINVERTED;
    stack.instruction_counter++;
}

void EQ(element_t *bool_res, element_t *bool_1, element_t *bool_2){
    if (bool_1->qualifier == Qu && bool_2->qualifier == Qu){
        SUB(bool_1, bool_2);
    }

    instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
    MOV(ins->el1, bool_res, POINTER);
    MOV(ins->el2, bool_1, POINTER);

    if (bool_1->qualifier == Qu && bool_2->qualifier == Qu){
        element_t *zero = classical_integer(0);
        MOV(ins->el3, zero, POINTER);
    }else {
        MOV(ins->el3, bool_2, POINTER);
    }

    if (bool_1->qualifier == Cl && bool_2->qualifier == Cl) ins->routine = CC_equal;
    else ins->routine = CQ_equal;

    ins->invert = NOTINVERTED;
    stack.instruction_counter++;

    if (bool_1->qualifier == Qu && bool_2->qualifier == Qu){
        ADD(bool_1, bool_2);
    }
}

void LEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2){

    SUB(bool_1, bool_2);

    TSTBIT(bool_res, bool_1, 0);

    ADD(bool_1, bool_2);
}

void GEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2){

    SUB(bool_2, bool_1);

    TSTBIT(bool_res, bool_2, 0);

    ADD(bool_2, bool_1);
}