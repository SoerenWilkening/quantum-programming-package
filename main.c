#include <stdio.h>
#include <time.h>
#include "AssemblyOperations.h"
#include "AssemblyReader.h"
#include "execution.h"

hybrid_stack_t stack;

sequence_t *precompiled_QQ_add = NULL;
sequence_t *precompiled_cQQ_add = NULL;
sequence_t *precompiled_CQ_add = NULL;
sequence_t *precompiled_cCQ_add = NULL;

sequence_t *precompiled_cQQ_mul = NULL;
sequence_t *precompiled_QQ_mul = NULL;

int label_counter = 0;
label_t labels[3000];

int main(void) {

    // initialize the rest of the stack
    // prepare exerything for the execution
    stack.Q0 = NULL;
    stack.Q1 = NULL;
    stack.Q2 = NULL;
    stack.Q3 = NULL;
    stack.circuit = init_circuit();
    stack.instruction_counter = 0;

	element_t *q1 = QINT();
	element_t *q2 = QINT();
	element_t *q3 = QINT();
	element_t *q4 = QBOOL();
	element_t *r0 = INT(3);
//	element_t *r0 = BOOL(1);

//	cqqadd(q1, q2, q2);
	cqmul(q1, r0, q2, q4);
//	cqneg(q1, q4);
//	qsub(q1, r0);
//	qadd(q1, r0);
//	cqadd(q1, r0, q4);
//	qqadd(q1, q2);
//	cqqadd(q1, q2, q4);
//	qqsdiv(q1, q2, q3);
//	qor(q1, q2, r0);
//	qqor(q1, q2, q3);
//	cqor(q1, q2, r0, q4);
//	cqqor(q1, q2, q3, q4);
//
//	qxor(q1, r0);
//	qqxor(q1, q3);
//	cqxor(q1, r0, q4);
//	cqqxor(q1, q3, q4);
//
//	qand(q1, q2, r0);
//	cqand(q1, q2, r0, q4);
//	qqand(q1, q2, q3);
//	cqqand(q1, q2, q3, q4);

	// ._execute
	clock_t t1 = clock();
	execute(stack.instruction_list);

	CircuitToOPANQASM(stack.circuit, "..");

    print_circuit(stack.circuit);

    printf("%f\n", (double) (clock() - t1) / CLOCKS_PER_SEC);
    return 0;
}
