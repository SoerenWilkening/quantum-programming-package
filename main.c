#include <stdio.h>
#include <time.h>
#include "AssemblyOperations.h"
#include "AssemblyReader.h"
#include "execution.h"

int main(int argc, char *argv[]) {
	// initialize the rest of the stack
	// prepare exerything for the execution
	instruction_counter = 0;
    
    int num_qubits;
    int run;
    if (argc > 2) {
        num_qubits = (int) strtol(argv[1], NULL, 10);
        run = (int) strtol(argv[2], NULL, 10);
    }
    else {
        num_qubits = 64;
        run = 1;
    }
	clock_t t1 = clock();

	sequence_t  *seq = QQ_add();
	clock_t t2 = clock();

	if (run) {
		QPU_state = instruction_list;
		// ._execute
		circuit_t *circ = init_circuit();
//        printf("%d\n", INTEGERSIZE);
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
