//
// Created by Sören Wilkening on 26.10.24.
//
#include "QPU.h"
#include <stdint.h>

quantum_int_t *QBOOL() {
    quantum_int_t *integer = malloc(sizeof(quantum_int_t));

    integer->MSB = INTEGERSIZE - 1;
    integer->q_address[INTEGERSIZE - 1] = circuit->used_qubit_indices;

    circuit->ancilla += 1;
    circuit->used_qubit_indices += 1;
    return integer;
}

quantum_int_t *QINT() {
    quantum_int_t *integer = malloc(sizeof(quantum_int_t));

    integer->MSB = 0;
    circuit->ancilla += INTEGERSIZE;

    for (int i = 0; i < INTEGERSIZE; ++i) {
        integer->q_address[i] = circuit->used_qubit_indices;
        circuit->used_qubit_indices++;
    }
    return integer;
}

quantum_int_t *INT(int64_t intg) {
    quantum_int_t *integer = malloc(sizeof(integer));
    //    integer->c_address = malloc(sizeof(int64_t));
    //    *integer->c_address = intg;
    return integer;
}
quantum_int_t *BOOL(bool intg) {
    quantum_int_t *integer = malloc(sizeof(integer));
    //    integer->c_address = malloc(sizeof(int64_t));
    //    *integer->c_address = intg;
    return integer;
}
quantum_int_t *bit_of_int(quantum_int_t *el1, int bit) {
    quantum_int_t *b = malloc(sizeof(quantum_int_t));
    b->MSB = INTEGERSIZE - 1;
    b->q_address[INTEGERSIZE - 1] = el1->q_address[bit];
    return b;
}

// Function to compute n-bit two's complement bit representation of x
int *two_complement(int64_t x, int n) {
    // Print the n-bit two's complement bit representation
    uint64_t mask = 1ULL << (n - 1); // Start from the highest bit
    int *bin = calloc(n, sizeof(int));

    for (int i = 0; i < n; ++i) {
        // Check each bit using mask and print '1' or '0'
        bin[i] = (x & mask) ? 1 : 0;
        mask >>= 1; // Shift the mask right
    }
    return bin;
}

void free_element(quantum_int_t *el1) {
    circuit->ancilla--;
    circuit->used_qubit_indices--;
}

sequence_t *setting_seq() {
    int *bin = two_complement(*QPU_state->R0, INTEGERSIZE);
    sequence_t *seq;
    seq = malloc(sizeof(sequence_t));
    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer[0] = 0;
    for (int i = QPU_state->Q0->MSB; i < INTEGERSIZE; ++i) {
        if (bin[i])
            x(&seq->seq[0][seq->gates_per_layer[0]++], i);
    }

    free(bin);
    return seq;
}