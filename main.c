#include "LogicOperations.h"
#include "circuit.h"
#include "execution.h"
#include <stdio.h>
#include <time.h>

int main(int argc, char *argv[]) {
    int num_qubits = 64;
    int run = 1;

    if (argc > 2) {
        num_qubits = (int)strtol(argv[1], NULL, 10);
        run = (int)strtol(argv[2], NULL, 10);
    }

    clock_t t1 = clock();
    sequence_t *seq = NULL;
    clock_t t2 = clock();

    if (run) {
        // Generate sequence (qq_or_seq doesn't use QPU_state)
        seq = qq_or_seq();

        // Initialize circuit and qubit array directly (no QPU_state)
        circuit_t *circ = init_circuit();
        qubit_t qubit_array[6 * INTEGERSIZE];
        for (int i = 0; i < 6 * INTEGERSIZE; i++) {
            qubit_array[i] = i;
        }

        run_instruction(seq, qubit_array, true, circ);
        print_circuit(circ);

        printf("%f\n", (double)(clock() - t1) / CLOCKS_PER_SEC);
        free_circuit(circ);
    } else {
        printf("%f\n", (double)(t2 - t1) / CLOCKS_PER_SEC);
    }

    if (seq != NULL) {
        free(seq);
    }
    return 0;
}
