//
// Created by Sören Wilkening on 26.10.24.
//
#include "QPU.h"

element_t *QBOOL(){
    element_t *integer = malloc(sizeof(element_t));
    integer->type = BOOLEAN;
    integer->qualifier = Qu;
    integer->q_address[0] = stack.circuit->used_qubit_indices;
    stack.circuit->ancilla += 1;
    stack.circuit->used_qubit_indices += 1;
    return integer;
}

element_t *QINT(){
    element_t *integer = malloc(sizeof(element_t));
    integer->type = SIGNED;
    integer->qualifier = Qu;
    stack.circuit->ancilla += INTEGERSIZE;
    integer->c_address = NULL;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        integer->q_address[i] = stack.circuit->used_qubit_indices;
        stack.circuit->used_qubit_indices++;
    }
    return integer;
}

element_t *QUINT(){
    element_t *integer = malloc(sizeof(element_t));
    integer->type = UNSIGNED;
    integer->qualifier = Qu;
    for (int i = 0; i < INTEGERSIZE; ++i) {
//        printf("%d %d\n", i, stack.circuit->used_qubit_indices + 1);
        integer->q_address[i] = (qubit_t) stack.circuit->used_qubit_indices;
        stack.circuit->used_qubit_indices++;
    }
    stack.circuit->used_qubit_indices++; // allocate one more qubit
    stack.circuit->ancilla += INTEGERSIZE + 1;
//    integer->c_address = NULL;
    return integer;
}

element_t *INT(int64_t intg){
    element_t *integer = malloc(sizeof(integer));
    integer->qualifier = Cl;
    integer->type = SIGNED;
    integer->c_address = malloc(sizeof(int64_t));
    *integer->c_address = intg;
    return integer;
}

element_t *BOOL(int64_t intg){
    element_t *integer = malloc(sizeof(integer));
    integer->qualifier = Cl;
    integer->type = BOOLEAN;
    integer->c_address = malloc(sizeof(int64_t));
    *integer->c_address = intg;
    return integer;
}

element_t *bit_of_int(element_t *el1, int bit){
    element_t *b = malloc(sizeof(element_t));
    b->type = Qu;
    b->qualifier = BOOLEAN;
    b->q_address[0] = el1->q_address[bit];
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
