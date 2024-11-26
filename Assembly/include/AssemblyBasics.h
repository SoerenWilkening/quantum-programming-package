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

extern int label_counter;
extern label_t labels[100];

void MOV(element_t *el1, element_t *el2, int pov);

void NEG(element_t *el1);

void TSTBIT(element_t *el1, element_t *el2, int bit);

// program functionality
void IF(element_t *el1);
void ELSE(element_t *el1);
void INV();

void LABEL(char label[]);

void JNZ(element_t *bool1);

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYBASICS_H
