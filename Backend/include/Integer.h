//
// Created by Sören Wilkening on 05.11.24.
//
// Integer.h - Integer type operations and allocation
//
// This header provides integer allocation and conversion functions.
// Arithmetic operations (addition, multiplication) are now in arithmetic_ops.h
//

#ifndef CQ_BACKEND_IMPROVED_INTEGER_H
#define CQ_BACKEND_IMPROVED_INTEGER_H

#include "QPU.h"
#include "arithmetic_ops.h"
#include "definition.h"
#include "gate.h"

#define _USE_MATH_DEFINES
#include <math.h>
#include <stdint.h>

// Ensure M_PI is defined on all platforms
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

int *two_complement(int64_t x, int n);

// Quantum integer allocation/deallocation (uses circuit's qubit allocator)
// OWNERSHIP: Returned quantum_int_t* must be freed with free_element()
// Qubits are borrowed from circuit and tracked through allocator
quantum_int_t *QINT(circuit_t *circ, int width); // width: 1-64 bits
quantum_int_t *QBOOL(circuit_t *circ);           // Convenience: calls QINT(circ, 1)
quantum_int_t *INT(int64_t intg);
quantum_int_t *BOOL(bool intg);

// Backward compatibility macro for C code that calls QINT without width
#define QINT_DEFAULT(circ) QINT(circ, INTEGERSIZE)
quantum_int_t *bit_of_int(quantum_int_t *el1, int bit);
sequence_t *setting_seq();
void free_element(circuit_t *circ, quantum_int_t *el1);

// Note: Arithmetic operations (addition, multiplication) are now in arithmetic_ops.h
// Subtraction is implemented at Python level via two's complement negation

#endif // CQ_BACKEND_IMPROVED_INTEGER_H
