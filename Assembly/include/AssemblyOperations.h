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

extern int label_counter;
extern label_t labels[3000];

instruction_t *init_instruction();

void mov(element_t *el1, element_t *el2, int pov);
void inv();
void tstbit(element_t *el1, element_t *el2, int bit);
void qtstbit(element_t *el1, element_t *el2, int bit);
void cqtstbit(element_t *el1, element_t *el2, element_t *ctrl, int bit);

void jez(element_t *bool1);
void jmp();
void label(char label[]);

void branch(element_t *el1, int bit);
void not(element_t *el1);
void qnot(element_t *el1);
void cqnot(element_t *el1, element_t *ctrl);

void and(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void qand(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void qqand(element_t *bool_res, element_t *bool_1, element_t *bool_2);

void or();
void qor();
void qqor();
void cqor();
void ccqqor();

void xor();
void qxor();
void qqxor();
void cqxor();
void cqqxor();

void eq(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void qeq(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void qqeq(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void cqeq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl);
void cqqeq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl);

void geq(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void qgeq(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void qqgeq(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void cqgeq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl);
void cqqgeq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl);

void leq(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void qleq(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void qqleq(element_t *bool_res, element_t *bool_1, element_t *bool_2);
void cqleq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl);
void cqqleq(element_t *bool_res, element_t *bool_1, element_t *bool_2, element_t *ctrl);

// integer arithmetic
void inc(element_t *el1);
void qinc(element_t *el1);
void cqinc(element_t *el1, element_t *ctrl);
void dcr(element_t *el1);
void qdcr(element_t *el1);
void cqdcr(element_t *el1, element_t *ctrl);

// phase operations
void padd(element_t *el1, element_t *phase);
void cpadd(element_t *el1, element_t *phase, element_t *ctrl);

void add(element_t *el1, element_t *el2);
void qadd(element_t *el1, element_t *el2);
void qqadd(element_t *el1, element_t *el2);
void cqadd(element_t *el1, element_t *el2, element_t *ctrl);
void cqqadd(element_t *el1, element_t *el2, element_t *ctrl);

void sub(element_t *el1, element_t *el2);
void qsub(element_t *el1, element_t *el2);
void qqsub(element_t *el1, element_t *el2);
void cqsub(element_t *el1, element_t *el2, element_t *ctrl);
void cqqsub(element_t *el1, element_t *el2, element_t *ctrl);

void mul(element_t *el1, element_t *el2, element_t *res);
void qmul(element_t *el1, element_t *el2, element_t *res);
void qqmul(element_t *el1, element_t *el2, element_t *res);
void cqmul(element_t *el1, element_t *el2, element_t *res, element_t *ctrl);
void cqqmul(element_t *el1, element_t *el2, element_t *res, element_t *ctrl);

void qneg(element_t *el1);
void cqneg(element_t *el1, element_t *ctrl);

void sdiv(element_t *el1, element_t *el2, element_t *remainder);
void qsdiv(element_t *A, element_t *B, element_t *remainder);
void qqsdiv(element_t *A, element_t *B, element_t *remainder);
void cqsdiv(element_t *A, element_t *B, element_t *remainder, element_t *ctrl);
void cqqsdiv(element_t *A, element_t *B, element_t *remainder, element_t *ctrl);

void udiv(element_t *el1, element_t *el2, element_t *remainder);
void qudiv(element_t *el1, element_t *el2, element_t *remainder);
void qqudiv(element_t *el1, element_t *el2, element_t *remainder);
void cqudiv(element_t *el1, element_t *el2, element_t *remainder, element_t *ctrl);
void cqqudiv(element_t *el1, element_t *el2, element_t *remainder, element_t *ctrl);

void smod(element_t *mod, element_t *el1, element_t *el2);
void qsmod(element_t *mod, element_t *el1, element_t *el2);
void qqsmod(element_t *mod, element_t *el1, element_t *el2);
void cqsmod(element_t *mod, element_t *el1, element_t *el2, element_t *ctrl);
void cqqsmod(element_t *mod, element_t *el1, element_t *el2, element_t *ctrl);

void umod(element_t *mod, element_t *el1, element_t *el2);
void qumod(element_t *mod, element_t *el1, element_t *el2);
void qqumod(element_t *mod, element_t *el1, element_t *el2);
void cqumod(element_t *mod, element_t *el1, element_t *el2, element_t *ctrl);
void cqqumod(element_t *mod, element_t *el1, element_t *el2, element_t *ctrl);

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYOPERATIONS_H
