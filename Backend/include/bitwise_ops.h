//
// bitwise_ops.h - Width-parameterized bitwise operations
// Dependencies: types.h
//
// This header provides width-parameterized bitwise operations for quantum integers.
// These operations support variable-width quantum integers (1-64 bits) introduced in Phase 5.
//
// Operations:
// - NOT: Bitwise complement via X gates
// - XOR: Bitwise exclusive-OR via CNOT gates
// - AND: Bitwise conjunction via Toffoli gates
// - OR:  Bitwise disjunction via XOR+AND identity
//
// Each operation comes in quantum-quantum (Q_*) and classical-quantum (CQ_*) variants.
// Controlled versions (cQ_*, cCQ_*) add control qubits for conditional operations.
//
// Part of Phase 9 (CODE-04) reorganization - extracted from LogicOperations.h
//

#ifndef QUANTUM_BITWISE_OPS_H
#define QUANTUM_BITWISE_OPS_H

#include "types.h"
#include <stdint.h>

// ======================================================
// Width-parameterized NOT operations
// ======================================================

// Q_not: Bitwise NOT using parallel X gates
// Qubit layout: [0, bits-1] = target operand
// Circuit depth: O(1) - all X gates in parallel
// OWNERSHIP: Returns cached sequence - DO NOT FREE
sequence_t *Q_not(int bits);

// cQ_not: Controlled bitwise NOT using sequential CX gates
// Qubit layout: [0] = control, [1, bits] = target operand
// Circuit depth: O(bits) - sequential CX gates
// OWNERSHIP: Returns cached sequence - DO NOT FREE
sequence_t *cQ_not(int bits);

// ======================================================
// Width-parameterized XOR operations
// ======================================================

// Q_xor: Bitwise XOR using parallel CNOT gates
// Qubit layout: [0, bits-1] = target A (result), [bits, 2*bits-1] = operand B
// Circuit depth: O(1) - all CNOT gates in parallel
// Result: A := A XOR B (in-place on A)
// OWNERSHIP: Returns cached sequence - DO NOT FREE
sequence_t *Q_xor(int bits);

// cQ_xor: Controlled bitwise XOR using Toffoli gates
// Qubit layout: [0] = control, [1, bits] = target A, [bits+1, 2*bits] = operand B
// Circuit depth: O(bits) - sequential Toffoli gates
// Result: A := A XOR B when control=1
// OWNERSHIP: Returns cached sequence - DO NOT FREE
sequence_t *cQ_xor(int bits);

// ======================================================
// Width-parameterized AND operations
// ======================================================

// Q_and: Bitwise AND using parallel Toffoli gates
// Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = A, [2*bits, 3*bits-1] = B
// Circuit depth: O(1) - all Toffoli gates in parallel
// Result: result := A AND B
// OWNERSHIP: Returns cached sequence - DO NOT FREE
sequence_t *Q_and(int bits);

// CQ_and: Classical-quantum AND
// Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = quantum operand
// Circuit depth: O(1) - parallel CNOT gates for 1-bits in classical value
// Result: result := classical_value AND quantum_operand
// For each bit i: if value[i] == 1 then CNOT(quantum[i], result[i]), else skip (0 AND x = 0)
// OWNERSHIP: Returns dynamically allocated sequence - CALLER MUST FREE
sequence_t *CQ_and(int bits, int64_t value);

// ======================================================
// Width-parameterized OR operations
// ======================================================

// Q_or: Bitwise OR using XOR+AND identity: A OR B = A XOR B XOR (A AND B)
// Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = A, [2*bits, 3*bits-1] = B
// Circuit depth: O(3) - three sequential layers (XOR, AND, XOR)
// Result: result := A OR B
// OWNERSHIP: Returns cached sequence - DO NOT FREE
sequence_t *Q_or(int bits);

// CQ_or: Classical-quantum OR
// Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = quantum operand
// Circuit depth: O(1) - parallel gates (X for 1-bits, CNOT for 0-bits)
// Result: result := classical_value OR quantum_operand
// For each bit i: if value[i] == 1 then X(result[i]) (1 OR x = 1), else CNOT(quantum[i], result[i])
// (0 OR x = x) OWNERSHIP: Returns dynamically allocated sequence - CALLER MUST FREE
sequence_t *CQ_or(int bits, int64_t value);

#endif // QUANTUM_BITWISE_OPS_H
