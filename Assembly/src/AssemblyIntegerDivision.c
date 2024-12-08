//
// Created by Sören Wilkening on 08.12.24.
//

#include "AssemblyOperations.h"

// include functionality for unsigned integers
//void udiv(element_t *el1, element_t *el2, element_t *remainder) {
//	// include functionality
//}
//void qudiv(element_t *el1, element_t *el2, element_t *remainder) {
//	// create qqsdiv sequence to Divide Aq / Bq
//	// increase size of Y to unsigned operations
//
//	element_t *Y = malloc(sizeof(element_t));
//	memcpy(Y, el1, sizeof(element_t));
//	for (int i = 2; i < INTEGERSIZE; ++i) {
//		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
//		memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));
//
//		qsub(Y, el2); // subtract Bq from Aq
//
//		element_t *bit = bit_of_int(remainder, i - 1);
//
//		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Cq
//
//		jez(bit);
//		qadd(Y, el2); // Add bq back to Aq (controlled by Cq)
//		label("internal_ctrl_add1");
//
//		qnot(bit); // Invert Cq
//	}
//	qsub(el1, el2); // subtract Bq from Aq
//	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);
//
//	qtstbit(bit, el1, 0); // check if Aq is negative, stored in Cq
//
//	jez(bit);
//	qadd(el1, el2); // Add bq back to Aq (controlled by Cq)
//	label("internal_ctrl_add2");
//
//	qnot(bit); // Invert Cq
//}
//void qqudiv(element_t *el1, element_t *el2, element_t *remainder) {
//	// create qqsdiv sequence to Divide Aq / Bq
//	// increase size of Y to unsigned operations
//
//	element_t *Y = malloc(sizeof(element_t));
//	memcpy(Y, el1, sizeof(element_t));
//	for (int i = 2; i < INTEGERSIZE; ++i) {
//		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
//		memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));
//
//		qqsub(Y, el2); // subtract Bq from Aq
//
//		element_t *bit = bit_of_int(remainder, i - 1);
//
//		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Cq
//
//		jez(bit);
//		qqadd(Y, el2); // Add bq back to Aq (controlled by Cq)
//		label("internal_ctrl_add1");
//
//		qnot(bit); // Invert Cq
//	}
//	qqsub(el1, el2); // subtract Bq from Aq
//	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);
//
//	qtstbit(bit, el1, 0); // check if Aq is negative, stored in Cq
//
//	jez(bit);
//	qqadd(el1, el2); // Add bq back to Aq (controlled by Cq)
//	label("internal_ctrl_add2");
//
//	qnot(bit); // Invert Cq
//}
//void cqudiv(element_t *el1, element_t *el2, element_t *remainder, element_t *ctrl) {
//	// create qqsdiv sequence to Divide Aq / Bq
//	// increase size of Y to unsigned operations
//
//	element_t *Y = malloc(sizeof(element_t));
//	memcpy(Y, el1, sizeof(element_t));
//	for (int i = 2; i < INTEGERSIZE; ++i) {
//		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
//		memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));
//
//		qsub(Y, el2); // subtract Bq from Aq
//
//		element_t *bit = bit_of_int(remainder, i - 1);
//
//		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Cq
//
//		jez(bit);
//		qadd(Y, el2); // Add bq back to Aq (controlled by Cq)
//		label("internal_ctrl_add1");
//
//		qnot(bit); // Invert Cq
//	}
//	qsub(el1, el2); // subtract Bq from Aq
//	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);
//
//	qtstbit(bit, el1, 0); // check if Aq is negative, stored in Cq
//
//	jez(bit);
//	qadd(el1, el2); // Add bq back to Aq (controlled by Cq)
//	label("internal_ctrl_add2");
//
//	qnot(bit); // Invert Cq
//}
//void cqqudiv(element_t *el1, element_t *el2, element_t *remainder, element_t *ctrl) {
//	// create qqsdiv sequence to Divide Aq / Bq
//	// increase size of Y to unsigned operations
//
//	element_t *Y = malloc(sizeof(element_t));
//	memcpy(Y, el1, sizeof(element_t));
//	for (int i = 2; i < INTEGERSIZE; ++i) {
//		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
//		memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));
//
//		qqsub(Y, el2); // subtract Bq from Aq
//
//		element_t *bit = bit_of_int(remainder, i - 1);
//
//		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Cq
//
//		jez(bit);
//		qqadd(Y, el2); // Add bq back to Aq (controlled by Cq)
//		label("internal_ctrl_add1");
//
//		qnot(bit); // Invert Cq
//	}
//	qqsub(el1, el2); // subtract Bq from Aq
//	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);
//
//	qtstbit(bit, el1, 0); // check if Aq is negative, stored in Cq
//
//	jez(bit);
//	qqadd(el1, el2); // Add bq back to Aq (controlled by Cq)
//	label("internal_ctrl_add2");
//
//	qnot(bit); // Invert Cq
//}

// TODO :
//  for signed implementation include
void sdiv(element_t *el1, element_t *el2, element_t *remainder) {
	// include functionality
}
void qsdiv(element_t *A, element_t *B, element_t *remainder) {
	// create qqsdiv sequence to Divide Aq / Bq

	element_t *Y = malloc(sizeof(element_t));
	memcpy(Y, A, sizeof(element_t));
	for (int i = 2; i < INTEGERSIZE; ++i) {
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		qsub(Y, B); // subtract Bq from Y
		element_t *bit = bit_of_int(remainder, i - 1);
		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Cq
		cqadd(Y, B, bit); // Add bq back to Y (controlled by bit)
		qnot(bit); // Invert Cq
	}
	qsub(A, B); // subtract Bq from Aq
	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);
	qtstbit(bit, A, 0); // check if Aq is negative, stored in Cq
	cqadd(A, B, bit); // Add bq back to Aq (controlled by bit)
	qnot(bit); // Invert Cq
}
void qqsdiv(element_t *A, element_t *B, element_t *remainder) {
	// create qqsdiv sequence to Divide Aq / Bq

	element_t *Y = malloc(sizeof(element_t));
	memcpy(Y, A, sizeof(element_t));
	for (int i = 2; i < INTEGERSIZE; ++i) {
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		qqsub(Y, B); // subtract B from Y
		element_t *bit = bit_of_int(remainder, i - 1);
		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Y
		cqqadd(Y, B, bit); // Add B back to Y (controlled by bit)
		qnot(bit); // Invert bit
	}
	qqsub(A, B); // subtract Bq from Aq
	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);
	qtstbit(bit, A, 0); // check if Aq is negative, stored in Y
	cqqadd(A, B, bit); // Add bq back to Aq (controlled by bit)

	qnot(bit); // Invert Cq
}
void cqsdiv(element_t *A, element_t *B, element_t *remainder, element_t *ctrl) {
	// create qqsdiv sequence to Divide Aq / Bq

	element_t *Y = malloc(sizeof(element_t));
	memcpy(Y, A, sizeof(element_t));
	for (int i = 2; i < INTEGERSIZE; ++i) {
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		cqsub(Y, B, ctrl); // subtract B from Y

		element_t *bit = bit_of_int(remainder, i - 1);
		cqtstbit(bit, Y, ctrl, 0); // check if Y is negative, stored in bit

		// store double control in step and controll addition by step
		element_t *step = QBOOL();
		qqand(step, bit, ctrl);
		cqadd(Y, B, step); // Add bq back to Aq (controlled by Cq)
		qqand(step, bit, ctrl);
		free_element(step); // free the qubit for step again

		cqnot(bit, ctrl); // Invert Cq
	}
	cqsub(A, B, ctrl); // subtract Bq from Aq
	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);

	cqtstbit(bit, A, ctrl, 0); // check if Aq is negative, stored in Cq

	// store double control in step and controll addition by step
	element_t *step = QBOOL();
	qqand(step, bit, ctrl);
	cqadd(A, B, step); // Add bq back to Aq (controlled by Cq)
	qqand(step, bit, ctrl);
	free_element(step); // free the qubit for step again---

	cqnot(bit, ctrl); // Invert Cq
}
void cqqsdiv(element_t *A, element_t *B, element_t *remainder, element_t *ctrl) {
	// create qqsdiv sequence to Divide Aq / Bq

	element_t *Y = malloc(sizeof(element_t));
	memcpy(Y, A, sizeof(element_t));
	for (int i = 2; i < INTEGERSIZE; ++i) {
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], A->q_address, i * sizeof(int));

		cqqsub(Y, B, ctrl); // subtract Bq from Y

		element_t *bit = bit_of_int(remainder, i - 1);
		cqtstbit(bit, Y, ctrl, 0); // check if Aq is negative, stored in Cq

		// store double control in step and controll addition by step
		element_t *step = QBOOL();
		qqand(step, bit, ctrl);
		cqqadd(Y, B, step); // Add bq back to Aq (controlled by Cq)
		qqand(step, bit, ctrl);
		free_element(step); // free the qubit for step again---

		cqnot(bit, ctrl); // Invert Cq
	}
	cqqsub(A, B, ctrl); // subtract Bq from Aq
	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);

	qtstbit(bit, A, 0); // check if Aq is negative, stored in Cq

	// store double control in step and controll addition by step
	element_t *step = QBOOL();
	qqand(step, bit, ctrl);
	cqqadd(A, B, step); // Add bq back to Aq (controlled by Cq)
	qqand(step, bit, ctrl);
	free_element(step); // free the qubit for step again---

	cqnot(bit, ctrl); // Invert Cq
}

void umod(element_t *mod, element_t *el1, element_t *el2) {
	udiv(el1, el2, mod);
}
void qumod(element_t *mod, element_t *el1, element_t *el2) {
	qudiv(el1, el2, mod);
}
void qqumod(element_t *mod, element_t *el1, element_t *el2) {
	qqudiv(el1, el2, mod);
}
void cqumod(element_t *mod, element_t *el1, element_t *el2, element_t *ctrl) {
	cqudiv(el1, el2, mod, ctrl);
}
void cqqumod(element_t *mod, element_t *el1, element_t *el2, element_t *ctrl) {
	cqqudiv(el1, el2, mod, ctrl);
}

void smod(element_t *mod, element_t *el1, element_t *el2) {
	sdiv(el1, el2, mod);
}
void qsmod(element_t *mod, element_t *el1, element_t *el2) {
	qsdiv(el1, el2, mod);
}
void qqsmod(element_t *mod, element_t *el1, element_t *el2) {
	qqsdiv(el1, el2, mod);
}
void cqsmod(element_t *mod, element_t *el1, element_t *el2, element_t *ctrl) {
	cqsdiv(el1, el2, mod, ctrl);
}
void cqqsmod(element_t *mod, element_t *el1, element_t *el2, element_t *ctrl) {
	cqqsdiv(el1, el2, mod, ctrl);
}
