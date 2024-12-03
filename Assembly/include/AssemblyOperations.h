//
// Created by Sören Wilkening on 03.12.24.
//

#ifndef CQ_BACKEND_IMPROVED_ASSEMBLYOPERATIONS_H
#define CQ_BACKEND_IMPROVED_ASSEMBLYOPERATIONS_H

#include "Integer.h"
#include "gate.h"
#include "QPU.h"
#include "LogicOperations.h"
#include "IntegerComparison.h"

typedef struct {
	char *label;
	instruction_t *ins_ptr;
} label_t;

typedef struct {
	element_t ctrl[1];
	element_t step[1];
	char *label;
} active_label_t;

extern active_label_t active_label[20];
extern int active_label_counter;

extern int label_counter;
extern label_t labels[3000];

void init_instruction(instruction_t *instr);

void MOV(element_t *el1, element_t *el2, int pov);
void TSTBIT(element_t *el1, element_t *el2, int bit);
void INV();

void JEZ(element_t *bool1);
void JMP();
void LABEL(char label[]);

void BRANCH(element_t *el1, int bit);
void NOT(element_t *el1);
void AND(element_t *bool_res, element_t *bool_1, element_t *bool_2);

void EQ(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void GEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void LEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2);

// integer arithmetic
void NEG(element_t *el1);
void INC(element_t *el1);
void DCR(element_t *el1);
void IADD(element_t *el1, element_t *el2);
void ISUB(element_t *el1, element_t *el2);
void IMUL(element_t *el1, element_t *el2, element_t *res);
void IDIV(element_t *el1, element_t *el2, element_t *remainder);
void MOD(element_t *mod, element_t *el1, element_t *el2);
// phase operations
void PADD(element_t *el1, element_t *phase);

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYOPERATIONS_H
