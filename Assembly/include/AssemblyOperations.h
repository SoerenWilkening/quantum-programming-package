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

void inv();
//void tstbit(bool *res, int *integer, int bit);
void qtstbit(quantum_int_t *res, quantum_int_t *integer, int bit);
void cqtstbit(quantum_int_t *res, quantum_int_t *integer, quantum_int_t *ctrl, int bit);

void jez(int *bool1);
void jmp();
void label(char label[]);

void branch(quantum_int_t *Q0, int bit);
void not(int *R0);
void qnot(quantum_int_t *Q0);
void cqnot(quantum_int_t *Q0, quantum_int_t *ctrl);

void and(int *R0, int *R1, int *R2);
void qand(quantum_int_t *Q0, quantum_int_t *Q1, int *R0);
void qqand(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2);
void cqand(quantum_int_t *Q0, quantum_int_t *Q1, int *R0, quantum_int_t *ctrl);
void cqqand(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl);

void or(int *R0, int *R1);
void qor(quantum_int_t *Q0, quantum_int_t *Q1, int *R0);
void qqor(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2);
void cqor(quantum_int_t *Q0, quantum_int_t *Q1, int *R0, quantum_int_t *ctrl);
void cqqor(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl);

void xor(int *R0, int *R1);
void qxor(quantum_int_t *Q0, int *R0);
void qqxor(quantum_int_t *Q0, quantum_int_t *Q1);
void cqxor(quantum_int_t *Q0, int *R0, quantum_int_t *ctrl);
void cqqxor(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *ctrl);

void eq(int *bool_res, int *bool_1, int *bool_2);
void qeq(quantum_int_t *Q0, quantum_int_t *Q1, int *R0);
void qqeq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2);
void cqeq(quantum_int_t *Q0, quantum_int_t *Q1, int *R0, quantum_int_t *ctrl);
void cqqeq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl);

void geq(int *bool_res, int *bool_1, int *bool_2);
void qgeq(quantum_int_t *Q0, int *R0, quantum_int_t *Q1);
void qqgeq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2);
void cqgeq(quantum_int_t *Q0, int *R0, quantum_int_t *Q1, quantum_int_t *ctrl);
void cqqgeq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl);

void leq(int *R0, int *R1, int *R2);
void qleq(quantum_int_t *Q0, quantum_int_t *Q1, int *R0);
void qqleq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2);
void cqleq(quantum_int_t *Q0, quantum_int_t *Q1, int *R0, quantum_int_t *ctrl);
void cqqleq(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl);

// integer arithmetic
void inc(int *R0);
void qinc(quantum_int_t *Q0);
void cqinc(quantum_int_t *Q0, quantum_int_t *ctrl);
void dcr(int *R0);
void qdcr(quantum_int_t *Q0);
void cqdcr(quantum_int_t *Q0, quantum_int_t *ctrl);

// phase operations
void padd(quantum_int_t *Q0, int *phase);
void cpadd(quantum_int_t *Q0, int *phase, quantum_int_t *ctrl);

void add(int *R0, int *R1);
void qadd(quantum_int_t *Q0, int *R0);
void qqadd(quantum_int_t *Q0, quantum_int_t *Q1);
void cqadd(quantum_int_t *Q0, int *R0, quantum_int_t *ctrl);
void cqqadd(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *ctrl);

void sub(int *R0, int *R1);
void qsub(quantum_int_t *Q0, int *R0);
void qqsub(quantum_int_t *Q0, quantum_int_t *Q1);
void cqsub(quantum_int_t *Q0, int *R0, quantum_int_t *ctrl);
void cqqsub(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *ctrl);

void mul(int *R0, int *R1, int *R2);
void qmul(quantum_int_t *Q0, quantum_int_t *Q1, int *R0);
void qqmul(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2);
void cqmul(quantum_int_t *Q0, quantum_int_t *Q1, int *R0, quantum_int_t *ctrl);
void cqqmul(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl);

void qneg(quantum_int_t *Q0);
void cqneg(quantum_int_t *Q0, quantum_int_t *ctrl);

void sdiv(int *A, int *B);
void qsdiv(quantum_int_t *A, int *B, quantum_int_t *remainder);
void qqsdiv(quantum_int_t *A, quantum_int_t *B, quantum_int_t *remainder);
void cqsdiv(quantum_int_t *A, int *B, quantum_int_t *remainder, quantum_int_t *ctrl);
void cqqsdiv(quantum_int_t *A, quantum_int_t *B, quantum_int_t *remainder, quantum_int_t *ctrl);

void udiv(int *R0, int *R1);
void qudiv(quantum_int_t *A, int *B, quantum_int_t *remainder);
void qqudiv(quantum_int_t *A, quantum_int_t *B, quantum_int_t *remainder);
void cqudiv(quantum_int_t *A, int *B, quantum_int_t *remainder, quantum_int_t *ctrl);
void cqqudiv(quantum_int_t *A, quantum_int_t *B, quantum_int_t *remainder, quantum_int_t *ctrl);

void smod(int *R0, int *R1);
void qsmod(quantum_int_t *mod, quantum_int_t *Q0, int *R0);
void qqsmod(quantum_int_t *mod, quantum_int_t *Q0, quantum_int_t *Q1);
void cqsmod(quantum_int_t *mod, quantum_int_t *Q0, int *R0, quantum_int_t *ctrl);
void cqqsmod(quantum_int_t *mod, quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *ctrl);

void umod(int *R0, int *R1);
void qumod(quantum_int_t *mod, quantum_int_t *el1, int *R0);
void qqumod(quantum_int_t *mod, quantum_int_t *el1, quantum_int_t *el2);
void cqumod(quantum_int_t *mod, quantum_int_t *el1, int *R0, quantum_int_t *ctrl);
void cqqumod(quantum_int_t *mod, quantum_int_t *el1, quantum_int_t *el2, quantum_int_t *ctrl);

#endif //CQ_BACKEND_IMPROVED_ASSEMBLYOPERATIONS_H
