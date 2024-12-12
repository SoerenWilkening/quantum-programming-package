#include "AssemblyOperations.h"

sequence_t *udiv_seq(){
	*(QPU_state->R0) /= *(QPU_state->R1);
	return NULL;
}
sequence_t *sdiv_seq(){
	*(QPU_state->R0) /= *(QPU_state->R1);
	return NULL;
}
sequence_t *umod_seq(){
	*(QPU_state->R0) %= *(QPU_state->R1);
	return NULL;
}
sequence_t *smod_seq(){
	*(QPU_state->R0) %= *(QPU_state->R1);
	return NULL;
}

void udiv(int *R0, int *R1) {
	instruction_t *ins = init_instruction();
	ins->R0 = R0;
	ins->R1 = R1;
	ins->name = "udiv ";
	ins->routine = udiv_seq;
}
void qudiv(quantum_int_t *A, int *B, quantum_int_t *remainder) {
	// create qqsdiv sequence to Divide Aq / Bq
	// increase size of Y to unsigned operations

	for (int i = 1; i < INTEGERSIZE + 1; ++i) {
		quantum_int_t *Y = malloc(sizeof(quantum_int_t));
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		// for comparing two unsigned integers we proceed as follows, target = bit:
		// XOR MSB(Y) MSB(B) -> bool1 // Y and B have different MSBs
		// cnot MSB(Y) -> bool2
		// Y - B
		// cnot MSB(Y) -> bool2 // did a bit flip occour
		// if bool1 && MSB(Y) == 1 -> flip bit
		// not bool1
		// if bool1 && bool2 -> flip bit
		// not bool1
		// cnot MSB(Y) -> bool2
		// if bit -> Y + B
		// cnot MSB(Y) -> bool2
		// XOR MSB(Y) MSB(B) -> bool1
		quantum_int_t *bit = bit_of_int(remainder, i - 1);
		quantum_int_t *MSB_Y = bit_of_int(Y, i - 1);
//		quantum_int_t *MSB_B = bit_of_int(B, i - 1);

		quantum_int_t *bool1 = QBOOL();
		quantum_int_t *bool2 = QBOOL();
		quantum_int_t *step = QBOOL();

		cqnot(bool1, MSB_Y); // XOR
//		cqnot(bool1, MSB_B); // XOR
		cqnot(bool2, MSB_Y); // MSB before subtraction

		qsub(Y, B); // subtract Bq from Aq

		qtstbit(bool1, Y, 0); // MSB after subtraction
		qqand(step, bool1, MSB_Y); // if bool1 && MSB(Y) == 1 -> flip bit
		cqnot(bit, step);
		qqand(step, bool1, MSB_Y); // uncompute

		qnot(bool1);
		qqand(step, bool1, bool2); // if !bool1 && bool2 -> flip bit
		cqnot(bit, step);
		qqand(step, bool1, bool2); // if !bool1 && bool2 -> flip bit
		qnot(bool1);

		cqadd(Y, B, bit); // Add bq back to Aq (controlled by bit)

		cqnot(bool2, MSB_Y); // uncomputation
		cqnot(bool1, MSB_Y); // uncomputation
//		cqnot(bool1, MSB_B); // uncomputation

		qnot(bit); // Invert Cq
	}
}
void qqudiv(quantum_int_t *A, quantum_int_t *B, quantum_int_t *remainder) {
	// create qqsdiv sequence to Divide Aq / Bq
	// increase size of Y to unsigned operations

	for (int i = 1; i < INTEGERSIZE + 1; ++i) {
		quantum_int_t *Y = malloc(sizeof(quantum_int_t));
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		// for comparing two unsigned integers we proceed as follows, target = bit:
		// XOR MSB(Y) MSB(B) -> bool1 // Y and B have different MSBs
		// cnot MSB(Y) -> bool2
		// Y - B
		// cnot MSB(Y) -> bool2 // did a bit flip occour
		// if bool1 && MSB(Y) == 1 -> flip bit
		// not bool1
		// if bool1 && bool2 -> flip bit
		// not bool1
		// cnot MSB(Y) -> bool2
		// if bit -> Y + B
		// cnot MSB(Y) -> bool2
		// XOR MSB(Y) MSB(B) -> bool1
		quantum_int_t *bit = bit_of_int(remainder, i - 1);
		quantum_int_t *MSB_Y = bit_of_int(Y, i - 1);
		quantum_int_t *MSB_B = bit_of_int(B, i - 1);

		quantum_int_t *bool1 = QBOOL();
		quantum_int_t *bool2 = QBOOL();
		quantum_int_t *step = QBOOL();

		cqnot(bool1, MSB_Y); // XOR
		cqnot(bool1, MSB_B); // XOR
		cqnot(bool2, MSB_Y); // MSB before subtraction

		qqsub(Y, B); // subtract Bq from Aq

		qtstbit(bool1, Y, 0); // MSB after subtraction
		qqand(step, bool1, MSB_Y); // if bool1 && MSB(Y) == 1 -> flip bit
		cqnot(bit, step);
		qqand(step, bool1, MSB_Y); // uncompute

		qnot(bool1);
		qqand(step, bool1, bool2); // if !bool1 && bool2 -> flip bit
		cqnot(bit, step);
		qqand(step, bool1, bool2); // if !bool1 && bool2 -> flip bit
		qnot(bool1);

		cqqadd(Y, B, bit); // Add bq back to Aq (controlled by bit)

		cqnot(bool2, MSB_Y); // uncomputation
		cqnot(bool1, MSB_Y); // uncomputation
		cqnot(bool1, MSB_B); // uncomputation

		qnot(bit); // Invert Cq

		free_element(bool1);
		free_element(bool2);
		free_element(step);
	}
}
void cqudiv(quantum_int_t *A, int *B, quantum_int_t *remainder, quantum_int_t *ctrl) {
	// create qqsdiv sequence to Divide Aq / Bq
	// increase size of Y to unsigned operations

	for (int i = 1; i < INTEGERSIZE + 1; ++i) {
		quantum_int_t *Y = malloc(sizeof(quantum_int_t));
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		// for comparing two unsigned integers we proceed as follows, target = bit:
		// XOR MSB(Y) MSB(B) -> bool1 // Y and B have different MSBs
		// cnot MSB(Y) -> bool2
		// Y - B
		// cnot MSB(Y) -> bool2 // did a bit flip occour
		// if bool1 && MSB(Y) == 1 -> flip bit
		// not bool1
		// if bool1 && bool2 -> flip bit
		// not bool1
		// cnot MSB(Y) -> bool2
		// if bit -> Y + B
		// cnot MSB(Y) -> bool2
		// XOR MSB(Y) MSB(B) -> bool1
		quantum_int_t *bit = bit_of_int(remainder, i - 1);
		quantum_int_t *MSB_Y = bit_of_int(Y, i - 1);
//		quantum_int_t *MSB_B = bit_of_int(B, i - 1);

		quantum_int_t *bool1 = QBOOL();
		quantum_int_t *bool2 = QBOOL();
		quantum_int_t *step = QBOOL();

		cqnot(bool1, MSB_Y); // XOR
//		cqnot(bool1, MSB_B); // XOR
		cqnot(bool2, MSB_Y); // MSB before subtraction

		cqsub(Y, B, ctrl); // subtract Bq from Aq

		qtstbit(bool1, Y, 0); // MSB after subtraction
		qqand(step, bool1, MSB_Y); // if bool1 && MSB(Y) == 1 -> flip bit
		cqnot(bit, step);
		qqand(step, bool1, MSB_Y); // uncompute

		qnot(bool1);
		qqand(step, bool1, bool2); // if !bool1 && bool2 -> flip bit
		cqnot(bit, step);
		qqand(step, bool1, bool2); // if !bool1 && bool2 -> flip bit
		qnot(bool1);

		quantum_int_t *step2 = QBOOL();
		qqand(step2, bit, ctrl);
		cqadd(Y, B, step2); // Add bq back to Aq (controlled by step2)
		qqand(step2, bit, ctrl);

		cqnot(bool2, MSB_Y); // uncomputation
		cqnot(bool1, MSB_Y); // uncomputation
//		cqnot(bool1, MSB_B); // uncomputation

		cqnot(bit, ctrl); // Invert Cq
	}
}
void cqqudiv(quantum_int_t *A, quantum_int_t *B, quantum_int_t *remainder, quantum_int_t *ctrl) {
	// create qqsdiv sequence to Divide Aq / Bq
	// increase size of Y to unsigned operations

	for (int i = 1; i < INTEGERSIZE + 1; ++i) {
		quantum_int_t *Y = malloc(sizeof(quantum_int_t));
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));


		// for comparing two unsigned integers we proceed as follows, target = bit:
		// XOR MSB(Y) MSB(B) -> bool1 // Y and B have different MSBs
		// cnot MSB(Y) -> bool2
		// Y - B
		// cnot MSB(Y) -> bool2 // did a bit flip occour
		// if bool1 && MSB(Y) == 1 -> flip bit
		// not bool1
		// if bool1 && bool2 -> flip bit
		// not bool1
		// cnot MSB(Y) -> bool2
		// if bit -> Y + B
		// cnot MSB(Y) -> bool2
		// XOR MSB(Y) MSB(B) -> bool1
		quantum_int_t *bit = bit_of_int(remainder, i - 1);
		quantum_int_t *MSB_Y = bit_of_int(Y, i - 1);
		quantum_int_t *MSB_B = bit_of_int(B, i - 1);

		quantum_int_t *bool1 = QBOOL();
		quantum_int_t *bool2 = QBOOL();
		quantum_int_t *step = QBOOL();

		cqnot(bool1, MSB_Y); // XOR
		cqnot(bool1, MSB_B); // XOR
		cqnot(bool2, MSB_Y); // MSB before subtraction

		cqqsub(Y, B, ctrl); // subtract Bq from Aq

		qtstbit(bool1, Y, 0); // MSB after subtraction
		qqand(step, bool1, MSB_Y); // if bool1 && MSB(Y) == 1 -> flip bit
		cqnot(bit, step);
		qqand(step, bool1, MSB_Y); // uncompute

		qnot(bool1);
		qqand(step, bool1, bool2); // if !bool1 && bool2 -> flip bit
		cqnot(bit, step);
		qqand(step, bool1, bool2); // if !bool1 && bool2 -> flip bit
		qnot(bool1);

		quantum_int_t *step2 = QBOOL();
		qqand(step2, bit, ctrl);
		cqqadd(Y, B, step2); // Add bq back to Aq (controlled by step2)
		qqand(step2, bit, ctrl);

		cqnot(bool2, MSB_Y); // uncomputation
		cqnot(bool1, MSB_Y); // uncomputation
		cqnot(bool1, MSB_B); // uncomputation

		cqnot(bit, ctrl); // Invert Cq
	}
}

void sdiv(int *A, int *B) {
	instruction_t *ins = init_instruction();
	ins->R0 = A;
	ins->R1 = B;
	ins->name = "sdiv ";
	ins->routine = sdiv_seq;
}
void qsdiv(quantum_int_t *A, int *B, quantum_int_t *remainder) {
	// create qqsdiv sequence to Divide Aq / Bq
	quantum_int_t *sign_A = QBOOL();
	qtstbit(sign_A, A, 0);
	cqneg(A, sign_A);


	for (int i = 2; i < INTEGERSIZE + 1; ++i) {
		quantum_int_t *Y = malloc(sizeof(quantum_int_t));
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		qsub(Y, B); // subtract Bq from Y
		quantum_int_t *bit = bit_of_int(remainder, i - 1);
		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Cq
		cqadd(Y, B, bit); // Add bq back to Y (controlled by bit)
		qnot(bit); // Invert Cq
	}
	cqneg(A, sign_A);
	cqneg(remainder, sign_A);
	qtstbit(sign_A, A, 0);

	free_element(sign_A);
}
void qqsdiv(quantum_int_t *A, quantum_int_t *B, quantum_int_t *remainder) {
	// create qqsdiv sequence to Divide Aq / Bq
	quantum_int_t *sign_A = QBOOL();
	quantum_int_t *sign_B = QBOOL();

	qtstbit(sign_A, A, 0);
	qtstbit(sign_B, B, 0);

	cqneg(A, sign_A);
	cqneg(B, sign_B);

	for (int i = 2; i < INTEGERSIZE + 1; ++i) {
		quantum_int_t *Y = malloc(sizeof(quantum_int_t));
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		qqsub(Y, B); // subtract B from Y
		quantum_int_t *bit = bit_of_int(remainder, i - 1);
		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Y
		cqqadd(Y, B, bit); // Add B back to Y (controlled by bit)
		qnot(bit); // Invert bit
	}

	cqnot(sign_A, sign_B);
	cqneg(A, sign_A);
	cqneg(remainder, sign_A);
	cqneg(B, sign_B);
	cqnot(sign_A, sign_B);

	qtstbit(sign_A, A, 0);
	qtstbit(sign_B, B, 0);

	free_element(sign_A);
	free_element(sign_B);

}
void cqsdiv(quantum_int_t *A, int *B, quantum_int_t *remainder, quantum_int_t *ctrl) {
	// create qqsdiv sequence to Divide Aq / Bq
	quantum_int_t *sign_A = QBOOL();
	qtstbit(sign_A, A, 0);
	cqneg(A, sign_A);

	for (int i = 2; i < INTEGERSIZE + 1; ++i) {
		quantum_int_t *Y = malloc(sizeof(quantum_int_t));
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		cqsub(Y, B, ctrl); // subtract B from Y

		quantum_int_t *bit = bit_of_int(remainder, i - 1);
		cqtstbit(bit, Y, ctrl, 0); // check if Y is negative, stored in bit

		// store double control in step and controll addition by step
		quantum_int_t *step = QBOOL();
		qqand(step, bit, ctrl);
		cqadd(Y, B, step); // Add bq back to Aq (controlled by Cq)
		qqand(step, bit, ctrl);
		free_element(step); // free the qubit for step again

		cqnot(bit, ctrl); // Invert Cq
	}
	cqneg(A, sign_A);
	cqneg(remainder, sign_A);
	qtstbit(sign_A, A, 0);

	free_element(sign_A);
}
void cqqsdiv(quantum_int_t *A, quantum_int_t *B, quantum_int_t *remainder, quantum_int_t *ctrl) {
	// create qqsdiv sequence to Divide Aq / Bq
	quantum_int_t *sign_A = QBOOL();
	quantum_int_t *sign_B = QBOOL();

	qtstbit(sign_A, A, 0);
	qtstbit(sign_B, B, 0);

	cqneg(A, sign_A);
	cqneg(B, sign_B);

	for (int i = 2; i < INTEGERSIZE + 1; ++i) {
		quantum_int_t *Y = malloc(sizeof(quantum_int_t));
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		cqqsub(Y, B, ctrl); // subtract Bq from Y

		quantum_int_t *bit = bit_of_int(remainder, i - 1);
		cqtstbit(bit, Y, ctrl, 0); // check if Aq is negative, stored in Cq

		// store double control in step and controll addition by step
		quantum_int_t *step = QBOOL();
		qqand(step, bit, ctrl);
		cqqadd(Y, B, step); // Add bq back to Aq (controlled by Cq)
		qqand(step, bit, ctrl);
		free_element(step); // free the qubit for step again---

		cqnot(bit, ctrl); // Invert Cq
	}

	cqnot(sign_A, sign_B);
	cqneg(A, sign_A);
	cqneg(remainder, sign_A);
	cqneg(B, sign_B);
	cqnot(sign_A, sign_B);

	qtstbit(sign_A, A, 0);
	qtstbit(sign_B, B, 0);

	free_element(sign_A);
	free_element(sign_B);
}

void umod(int *R0, int *R1) {
	instruction_t *ins = init_instruction();
	ins->R0 = R0;
	ins->R1 = R1;
	ins->name = "umod ";
	ins->routine = umod_seq;
}
void qumod(quantum_int_t *mod, quantum_int_t *Q0, int *R0) {
	qudiv(Q0, R0, mod);
}
void qqumod(quantum_int_t *mod, quantum_int_t *Q0, quantum_int_t *Q1) {
	qqudiv(Q0, Q1, mod);
}
void cqumod(quantum_int_t *mod, quantum_int_t *Q0, int *R0, quantum_int_t *ctrl) {
	cqudiv(Q0, R0, mod, ctrl);
}
void cqqumod(quantum_int_t *mod, quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *ctrl) {
	cqqudiv(Q0, Q1, mod, ctrl);
}

void smod(int *R0, int *R1) {
	instruction_t *ins = init_instruction();
	ins->R0 = R0;
	ins->R1 = R1;
	ins->name = "smod ";
	ins->routine = smod_seq;
}
void qsmod(quantum_int_t *mod, quantum_int_t *Q0, int *R0) {
	qsdiv(Q0, R0, mod);
}
void qqsmod(quantum_int_t *mod, quantum_int_t *Q0, quantum_int_t *Q1) {
	qqsdiv(Q0, Q1, mod);
}
void cqsmod(quantum_int_t *mod, quantum_int_t *Q0, int *R0, quantum_int_t *ctrl) {
	cqsdiv(Q0, R0, mod, ctrl);
}
void cqqsmod(quantum_int_t *mod, quantum_int_t *Q0, quantum_int_t *Q1, quantum_int_t *ctrl) {
	cqqsdiv(Q0, Q1, mod, ctrl);
}
