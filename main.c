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
label_t labels[3];

int main(int argc, char *argv[]) {
	// initialize the rest of the stack
	// prepare exerything for the execution
//	instruction_counter = 0;

//	int num_qubits = (int) strtol(argv[1], NULL, 10);
//	int run = (int) strtol(argv[2], NULL, 10);
	int num_qubits = 5;
	int run = 1;
	clock_t t1 = clock();
//
//	circuit_t *circ = init_circuit();
//	gate_t g;
//	h(&g, 0);
//	add_gate(circ, &g);
//
//	h(&g, 1);
//	add_gate(circ, &g);
//
////	h(&g, 2);
////	add_gate(circ, &g);
//
//	cp(&g, 0, 2, 1);
////	cx(&g, 0, 2);
//	add_gate(circ, &g);
//
//	p(&g, 3, 1);
//	add_gate(circ, &g);
//
//
//	for (int i = 0; i < 4; ++i) {
//		printf("qubit %d ", i);
//		for (int j = 0; j < 2; ++j) {
//			printf("%d ", circ->layer_on_qubit[i][j]);
//		}
//		printf("\n");
//	}
//
////	cp(&g, 3, 2, 1);
////	cx(&g, 3, 2);
////	add_gate(circ, &g);
////
////	p(&g, 2, 1);
////	x(&g, 3);
////	add_gate(circ, &g);
////	print_circuit(circ);

	sequence_t  *seq = QFT(NULL, num_qubits);
	clock_t t2 = clock();

	if (run) {
		QPU_state = instruction_list;
		// ._execute
		circuit_t *circ = init_circuit();
		qubit_t qubit_array[6 * INTEGERSIZE];
		qubit_mapping(qubit_array, circ);
		run_instruction(seq, qubit_array, false, circ);
		print_circuit(circ);
		printf("%f\n", (double) (clock() - t1) / CLOCKS_PER_SEC);
	}else{
		printf("%f\n", (double) (t2 - t1) / CLOCKS_PER_SEC);
	}

	free(seq);

	return 0;
}
