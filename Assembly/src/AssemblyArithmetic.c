//
// Created by Sören Wilkening on 21.11.24.
//

#include "AssemblyOperations.h"

void add(element_t *el1, element_t *el2) {
	instruction_t *ins = init_instruction();
	MOV(ins->el1, el1, POINTER);
	MOV(ins->el2, el2, POINTER);
	ins->name = "CC_add ";
	ins->routine = CC_add;
}

void qadd(element_t *el1, element_t *el2) {
	instruction_t *ins = init_instruction();
	MOV(ins->el1, el1, POINTER);
	MOV(ins->el2, el2, POINTER);

	if (ins->control->type != UNINITIALIZED) {
		ins->name = "cCQ_add ";
		ins->routine = cCQ_add;
	} else {
		ins->name = "CQ_add ";
		ins->routine = CQ_add;
	}
}

void qqadd(element_t *el1, element_t *el2) {
	instruction_t *ins = init_instruction();
	MOV(ins->el1, el1, POINTER);
	MOV(ins->el2, el2, POINTER);

	// routine assignments
	ins->routine = NULL;
	if (ins->control->type != UNINITIALIZED) {
		ins->name = "cQQ_add ";
		ins->routine = cQQ_add;
	} else {
		ins->name = "QQ_add ";
		ins->routine = QQ_add;
	}
}

void sub(element_t *el1, element_t *el2) {
	add(el1, el2);
	stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void qsub(element_t *el1, element_t *el2) {
	qadd(el1, el2);
	stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void qqsub(element_t *el1, element_t *el2) {
	qqadd(el1, el2);
	stack.instruction_list[stack.instruction_counter - 1].invert = INVERTED;
}

void inc(element_t *el1) {
	element_t *cint = INT(1);
	add(el1, cint);
}

void qinc(element_t *el1) {
	element_t *cint = INT(1);
	qadd(el1, cint);
}

void dcr(element_t *el1) {
	element_t *cint = INT(1);
	sub(el1, cint);
}

void qdcr(element_t *el1) {
	element_t *cint = INT(1);
	qsub(el1, cint);
}

void mul(element_t *el1, element_t *el2, element_t *res) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	MOV(ins->el1, res, POINTER);
	MOV(ins->el2, el1, POINTER);
	MOV(ins->el3, el2, POINTER);

	ins->routine = void_seq; // replace with actual multiplication
}

void qmul(element_t *el1, element_t *el2, element_t *res) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	MOV(ins->el1, res, POINTER);
	MOV(ins->el2, el1, POINTER);
	MOV(ins->el3, el2, POINTER);

	if (ins->control->type != UNINITIALIZED) ins->routine = cCQ_mul;
	else ins->routine = CQ_mul;
}

void qqmul(element_t *el1, element_t *el2, element_t *res) {
	instruction_t *ins = &stack.instruction_list[stack.instruction_counter];
	init_instruction();

	// copy values instruction registers
	MOV(ins->el1, res, POINTER);
	MOV(ins->el2, el1, POINTER);
	MOV(ins->el3, el2, POINTER);

	if (ins->control->type != UNINITIALIZED) ins->routine = cQQ_mul;
	else ins->routine = QQ_mul;
}

void udiv(element_t *el1, element_t *el2, element_t *remainder) {
	// include functionality
}

void sdiv(element_t *el1, element_t *el2, element_t *remainder) {
	// include functionality
}

void qudiv(element_t *el1, element_t *el2, element_t *remainder) {
	// create qqsdiv sequence to Divide Aq / Bq
	// increase size of Y to unsigned operations

	element_t *Y = malloc(sizeof(element_t));
	memcpy(Y, el1, sizeof(element_t));
	for (int i = 2; i < INTEGERSIZE; ++i) {
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));

		qsub(Y, el2); // subtract Bq from Aq

		element_t *bit = bit_of_int(remainder, i - 1);

		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Cq

		JEZ(bit);
		qadd(Y, el2); // Add bq back to Aq (controlled by Cq)
		LABEL("internal_ctrl_add1");

		qnot(bit); // Invert Cq
	}
	qsub(el1, el2); // subtract Bq from Aq
	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);

	qtstbit(bit, el1, 0); // check if Aq is negative, stored in Cq

	JEZ(bit);
	qadd(el1, el2); // Add bq back to Aq (controlled by Cq)
	LABEL("internal_ctrl_add2");

	qnot(bit); // Invert Cq
}

void qsdiv(element_t *el1, element_t *el2, element_t *remainder) {
	// create qqsdiv sequence to Divide Aq / Bq

	element_t *Y = malloc(sizeof(element_t));
	memcpy(Y, el1, sizeof(element_t));
	for (int i = 2; i < INTEGERSIZE; ++i) {
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));

		qqsub(Y, el2); // subtract Bq from Aq

		element_t *bit = bit_of_int(remainder, i - 1);

		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Cq

		JEZ(bit);
		qqadd(Y, el2); // Add bq back to Aq (controlled by Cq)
		LABEL("internal_ctrl_add1");

		qnot(bit); // Invert Cq
	}
	qqsub(el1, el2); // subtract Bq from Aq
	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);

	qtstbit(bit, el1, 0); // check if Aq is negative, stored in Cq

	JEZ(bit);
	qqadd(el1, el2); // Add bq back to Aq (controlled by Cq)
	LABEL("internal_ctrl_add2");

	qnot(bit); // Invert Cq
}

void qqudiv(element_t *el1, element_t *el2, element_t *remainder) {
	// create qqsdiv sequence to Divide Aq / Bq
	// increase size of Y to unsigned operations

	element_t *Y = malloc(sizeof(element_t));
	memcpy(Y, el1, sizeof(element_t));
	for (int i = 2; i < INTEGERSIZE; ++i) {
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));

		qqsub(Y, el2); // subtract Bq from Aq

		element_t *bit = bit_of_int(remainder, i - 1);

		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Cq

		JEZ(bit);
		qqadd(Y, el2); // Add bq back to Aq (controlled by Cq)
		LABEL("internal_ctrl_add1");

		qnot(bit); // Invert Cq
	}
	qqsub(el1, el2); // subtract Bq from Aq
	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);

	qtstbit(bit, el1, 0); // check if Aq is negative, stored in Cq

	JEZ(bit);
	qqadd(el1, el2); // Add bq back to Aq (controlled by Cq)
	LABEL("internal_ctrl_add2");

	qnot(bit); // Invert Cq
}

void qqsdiv(element_t *el1, element_t *el2, element_t *remainder) {
	// create qqsdiv sequence to Divide Aq / Bq

	element_t *Y = malloc(sizeof(element_t));
	memcpy(Y, el1, sizeof(element_t));
	for (int i = 2; i < INTEGERSIZE; ++i) {
		memcpy(Y->q_address, &remainder->q_address[i], (INTEGERSIZE - i) * sizeof(int));
		memcpy(&Y->q_address[(INTEGERSIZE - i)], el1->q_address, i * sizeof(int));

		qqsub(Y, el2); // subtract Bq from Y

		element_t *bit = bit_of_int(remainder, i - 1);

		qtstbit(bit, Y, 0); // check if Aq is negative, stored in Cq

		JEZ(bit);
		qqadd(Y, el2); // Add bq back to Aq (controlled by Cq)
		LABEL("internal_ctrl_add1");

		qnot(bit); // Invert Cq
	}
	qqsub(el1, el2); // subtract Bq from Aq
	element_t *bit = bit_of_int(remainder, INTEGERSIZE - 1);

	qtstbit(bit, el1, 0); // check if Aq is negative, stored in Cq

	JEZ(bit);
	qqadd(el1, el2); // Add bq back to Aq (controlled by Cq)
	LABEL("internal_ctrl_add2");

	qnot(bit); // Invert Cq
}

void umod(element_t *mod, element_t *el1, element_t *el2) {
	qudiv(el1, el2, mod);
}

void smod(element_t *mod, element_t *el1, element_t *el2) {
	qsdiv(el1, el2, mod);
}

void qumod(element_t *mod, element_t *el1, element_t *el2) {
	qudiv(el1, el2, mod);
}

void qsmod(element_t *mod, element_t *el1, element_t *el2) {
	qsdiv(el1, el2, mod);
}

void qqumod(element_t *mod, element_t *el1, element_t *el2) {
	qqudiv(el1, el2, mod);
}

void qqsmod(element_t *mod, element_t *el1, element_t *el2) {
	qqsdiv(el1, el2, mod);
}

void PADD(element_t *el1, element_t *phase) {
	instruction_t *ins = init_instruction();
	MOV(ins->el1, el1, POINTER);
	MOV(ins->el2, phase, POINTER);

	ins->routine = P_add;
}

void NEG(element_t *el1) {
	element_t *ctrl = stack.instruction_list[stack.instruction_counter].control;
	element_t *constant = INT(1);
	JEZ(ctrl);
	qnot(el1);
	qqsub(el1, constant);
	LABEL("");
}

