//
// Created by Sören Wilkening on 26.10.24.
//
#include "QPU.h"

element_t *QBOOL(){
    element_t *integer = malloc(sizeof(element_t));
	integer->MSB = INTEGERSIZE - 1;
    integer->q_address[INTEGERSIZE - 1] = circuit->used_qubit_indices;
    circuit->ancilla += 1;
    circuit->used_qubit_indices += 1;
    return integer;
}
element_t *QINT(){
    element_t *integer = malloc(sizeof(element_t));

	integer->MSB = 0;
    circuit->ancilla += INTEGERSIZE;
	integer->c_address = NULL;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        integer->q_address[i] = circuit->used_qubit_indices;
        circuit->used_qubit_indices++;
    }
    return integer;
}
element_t *INT(int64_t intg){
    element_t *integer = malloc(sizeof(integer));
    integer->c_address = malloc(sizeof(int64_t));
    *integer->c_address = intg;
    return integer;
}
element_t *BOOL(bool intg){
    element_t *integer = malloc(sizeof(integer));
    integer->c_address = malloc(sizeof(int64_t));
    *integer->c_address = intg;
    return integer;
}
element_t *bit_of_int(element_t *el1, int bit){
    element_t *b = malloc(sizeof(element_t));
    b->q_address[INTEGERSIZE - 1] = el1->q_address[bit];
    return b;
}

// Function to compute n-bit two's complement bit representation of x
int *two_complement(int64_t x, int n) {
    // Print the n-bit two's complement bit representation
    uint64_t mask = 1ULL << (n - 1);  // Start from the highest bit
    int *bin = calloc(n, sizeof(int));

    for (int i = 0; i < n; ++i) {
        // Check each bit using mask and print '1' or '0'
        bin[i] = (x & mask) ? 1 : 0;
        mask >>= 1;  // Shift the mask right
    }
    return bin;
}

void free_element(element_t *el1){
	circuit->ancilla--;
	circuit->used_qubit_indices--;
}