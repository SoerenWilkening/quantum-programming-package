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

int main(int argc, char *argv[]) {
	// initialize the rest of the stack
	// prepare exerything for the execution
//	instruction_counter = 0;
	QPU_state = instruction_list;
	printf("%d\n", INTEGERSIZE);
	clock_t t1 = clock();
	sequence_t  *seq = QFT(NULL);
	clock_t t2 = clock();

	// ._execute
	circuit = init_circuit();
	qubit_t qubit_array[6 * INTEGERSIZE];
	qubit_mapping(qubit_array);

	run_instruction(seq, qubit_array, false);
	printf("%f %f\n", (double) (clock() - t1) / CLOCKS_PER_SEC, (double) (t2 - t1) / CLOCKS_PER_SEC);

	free(seq);
//	print_circuit(circuit);


	return 0;
}
