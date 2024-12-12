//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyOperations.h"

void branch(quantum_int_t *Q0, int bit) {
	instruction_t *ins = init_instruction();
	ins->name = "branch_seq ";
	quantum_int_t *qbit = bit_of_int(Q0, bit);

	ins->Q0 = qbit;

	ins->routine = branch_seq;
}
//void cbranch(quantum_int_t *Q0, quantum_int_t *ctrl, int bit) {
//	instruction_t *ins = init_instruction();
//	ins->name = "branch_seq ";
//	quantum_int_t *qbit = bit_of_int(Q0, bit);
//
//	ins->Q0 = qbit;
//	ins->Q1 = ctrl;
//
//	ins->routine = cbranch_seq;
//}

void not(int *R0) {
	instruction_t *ins = init_instruction();
	ins->name = "not ";
	ins->R0 = R0;

	ins->routine = void_seq;
}
void qnot(quantum_int_t *Q0) {
	instruction_t *ins = init_instruction();
	ins->name = "qnot ";
	ins->Q0 = Q0;

	ins->routine = q_not_seq;
}
void cqnot(quantum_int_t *Q0, quantum_int_t *ctrl) {
	instruction_t *ins = init_instruction();
	ins->name = "cqnot ";
	ins->Q0 = Q0;
	ins->Q1 = ctrl;

	ins->routine = cq_not_seq;
}

void and(int *R0, int *R1, int *R2) {
	instruction_t *ins = init_instruction();
	ins->name = "and ";
	ins->R0 = R0;
	ins->R1 = R1;
	ins->R2 = R2;

	ins->routine = and_seq;

	ins->invert = NOTINVERTED;
}
void qand(quantum_int_t *Q0, quantum_int_t *Q1, int *R0) {
	instruction_t *ins = init_instruction();
	ins->name = "qand ";
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->R0 = R0;

	ins->routine = q_and_seq;

	ins->invert = NOTINVERTED;
}
void qqand(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2) {
	instruction_t *ins = init_instruction();
	ins->name = "qqand ";
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = Q2;

	ins->routine = qq_and_seq;

	ins->invert = NOTINVERTED;
}
void cqand(quantum_int_t *Q0, quantum_int_t *Q1, int *R0, quantum_int_t *ctrl) {
	instruction_t *ins = init_instruction();
	ins->name = "qand ";
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;
	ins->R0 = R0;

	ins->routine = cq_and_seq;

	ins->invert = NOTINVERTED;
}
void cqqand(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl) {
	instruction_t *ins = init_instruction();
	ins->name = "qqand ";
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = Q2;
	ins->Q3 = ctrl;

	ins->routine = cqq_and_seq;

	ins->invert = NOTINVERTED;
}

void xor(int *R0, int *R1){}
void qxor(quantum_int_t *Q0, int *R0){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->R0 = R0;
	ins->routine = q_xor_seq;
}
void qqxor(quantum_int_t *Q0, quantum_int_t *Q1){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->routine = qq_xor_seq;
}
void cqxor(quantum_int_t *Q0, int *R0, quantum_int_t *ctrl){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = ctrl;
	ins->R0 = R0;
	ins->routine = cq_xor_seq;
}
void cqqxor(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *ctrl){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;
	ins->routine = cqq_xor_seq;
}


void or(int *R0, int *R1){}
void qor(quantum_int_t *Q0, quantum_int_t *Q1, int *R0){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->R0 = R0;
	ins->routine = q_or_seq;
}
void qqor(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = Q2;
	ins->routine = qq_or_seq;
}
void cqor(quantum_int_t *Q0, quantum_int_t *Q1, int *R0, quantum_int_t *ctrl){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = ctrl;
	ins->R0 = R0;
	ins->routine = cq_or_seq;
}
void cqqor(quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *Q2, quantum_int_t *ctrl){
	instruction_t *ins = init_instruction();
	ins->Q0 = Q0;
	ins->Q1 = Q1;
	ins->Q2 = Q2;
	ins->Q3 = ctrl;
	ins->routine = cqq_or_seq;
}