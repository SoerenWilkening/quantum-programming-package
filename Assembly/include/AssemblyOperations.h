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

instruction_t *init_instruction();

void MOV(element_t *el1, element_t *el2, int pov);
void tstbit(element_t *el1, element_t *el2, int bit);
void qtstbit(element_t *el1, element_t *el2, int bit);
void INV();

void JEZ(element_t *bool1);
void JMP();
void LABEL(char label[]);

void branch(element_t *el1, int bit);
void qnot(element_t *el1);
void qqand(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void OR();
void XOR();

void EQ(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void GEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void LEQ(element_t *bool_res, element_t *bool_1, element_t *bool_2);

// integer arithmetic
void NEG(element_t *el1);
void inc(element_t *el1);
void dcr(element_t *el1);
void qqadd(element_t *el1, element_t *el2);
void qqsub(element_t *el1, element_t *el2);
void qqmul(element_t *el1, element_t *el2, element_t *res);
void qqsdiv(element_t *el1, element_t *el2, element_t *remainder);
void qqsmod(element_t *mod, element_t *el1, element_t *el2);
// phase operations
void PADD(element_t *el1, element_t *phase);

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYOPERATIONS_H
