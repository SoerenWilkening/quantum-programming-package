//
// Created by Sören Wilkening on 21.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_ASSEMBLYBASICS_H
#define CQ_BACKEND_IMPROVED_ASSEMBLYBASICS_H

#include "Integer.h"
#include "gate.h"
#include "QPU.h"
#include "LogicOperations.h"
#include "IntegerComparison.h"
#include "AssemblyBasics.h"

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

void NEG(element_t *el1);

void TSTBIT(element_t *el1, element_t *el2, int bit);

// program functionality
void IF(element_t *el1);

void ELSE(element_t *el1);

void INV();

void LABEL(char label[]);

void JMP();

void JEZ(element_t *bool1);

void BRANCH(element_t *el1, int bit);

void NOT(element_t *el1);

void AND(element_t *bool_res, element_t *bool_1, element_t *bool_2);

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYBASICS_H
