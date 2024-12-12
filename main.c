#include <stdio.h>
#include <time.h>
#include "AssemblyOperations.h"
#include "AssemblyReader.h"
#include "execution.h"

instruction_t instruction_list[MAXINSTRUCTIONS];
int instruction_counter = 0;
instruction_t *QPU_state;
circuit_t *circuit;

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
	circuit = init_circuit();
	instruction_counter = 0;
	QPU_state = instruction_list;

	element_t *A = QINT();
	element_t *B = QINT();
	element_t *C = QINT();
	element_t *D = QBOOL();
	element_t *klass = INT(123);

//	qnot(A);
//	cqnot(A, D);

//	qxor(A, klass);
//	qqxor(A, B);
//	cqqxor(A, B, D);

//	qor(A, B, klass);
//	qqor(A, B, C);
//	cqqor(A, B, C, D);

//	qand(A, B, klass);
//	qqand(A, B, C);
//	cqqand(A, B, C, D);

//	AsmbFromFile();

	// ._execute
	clock_t t1 = clock();
	execute();

	CircuitToOPANQASM(circuit, "..");

	print_circuit(circuit);

	printf("%f\n", (double) (clock() - t1) / CLOCKS_PER_SEC);
	return 0;
}
