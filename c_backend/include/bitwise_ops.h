/**
 * @file bitwise_ops.h
 * @brief Width-parameterized bitwise operations for quantum integers.
 *
 * This header provides width-parameterized bitwise operations for quantum integers.
 * These operations support variable-width quantum integers (1-64 bits) introduced in Phase 5.
 *
 * Operations:
 * - NOT: Bitwise complement via X gates
 * - XOR: Bitwise exclusive-OR via CNOT gates
 * - AND: Bitwise conjunction via Toffoli gates
 * - OR:  Bitwise disjunction via XOR+AND identity
 *
 * Each operation comes in quantum-quantum (Q_*) and classical-quantum (CQ_*) variants.
 * Controlled versions (cQ_*, cCQ_*) add control qubits for conditional operations.
 *
 * Dependencies: types.h
 * Part of Phase 9 (CODE-04) reorganization - extracted from LogicOperations.h
 */

#ifndef QUANTUM_BITWISE_OPS_H
#define QUANTUM_BITWISE_OPS_H

#include "types.h"
#include <stdint.h>

// ======================================================
// Width-parameterized NOT operations
// ======================================================

/**
 * @brief Bitwise NOT using parallel X gates.
 *
 * Applies NOT operation to all bits in parallel using X gates.
 * Circuit depth: O(1) - all X gates in parallel.
 *
 * @param bits Width of target operand (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0, bits-1] = target operand
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *Q_not(int bits);

/**
 * @brief Controlled bitwise NOT using sequential CX gates.
 *
 * Applies NOT operation conditionally based on control qubit.
 * Circuit depth: O(bits) - sequential CX gates.
 *
 * @param bits Width of target operand (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0] = control, [1, bits] = target operand
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *cQ_not(int bits);

// ======================================================
// Width-parameterized XOR operations
// ======================================================

/**
 * @brief Bitwise XOR using parallel CNOT gates.
 *
 * Applies XOR operation in-place on target A using operand B.
 * Circuit depth: O(1) - all CNOT gates in parallel.
 * Result: A := A XOR B (in-place on A)
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0, bits-1] = target A (result), [bits, 2*bits-1] = operand B
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *Q_xor(int bits);

/**
 * @brief Controlled bitwise XOR using Toffoli gates.
 *
 * Applies XOR operation conditionally based on control qubit.
 * Circuit depth: O(bits) - sequential Toffoli gates.
 * Result: A := A XOR B when control=1
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0] = control, [1, bits] = target A, [bits+1, 2*bits] = operand B
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *cQ_xor(int bits);

// ======================================================
// Width-parameterized AND operations
// ======================================================

/**
 * @brief Bitwise AND using parallel Toffoli gates.
 *
 * Computes result := A AND B using parallel Toffoli gates.
 * Circuit depth: O(1) - all Toffoli gates in parallel.
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = A, [2*bits, 3*bits-1] = B
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *Q_and(int bits);

/**
 * @brief Classical-quantum AND.
 *
 * Computes result := classical_value AND quantum_operand.
 * For each bit i: if value[i] == 1 then CNOT(quantum[i], result[i]), else skip (0 AND x = 0).
 * Circuit depth: O(1) - parallel CNOT gates for 1-bits in classical value.
 *
 * @param bits Width of operands (1-64)
 * @param value Classical value to AND with
 * @return Dynamically allocated sequence - CALLER MUST FREE
 *
 * Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = quantum operand
 *
 * OWNERSHIP: Returns dynamically allocated sequence - CALLER MUST FREE
 */
sequence_t *CQ_and(int bits, int64_t value);

/**
 * @brief Controlled bitwise AND using sequential 3-controlled X gates.
 *
 * Adds one external control qubit to Q_and. Each Toffoli becomes MCX(3).
 * Circuit depth: O(bits) - sequential MCX gates.
 *
 * @param bits Width of operands (1-64)
 * @return Dynamically allocated sequence - CALLER MUST FREE
 *
 * Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = A,
 *               [2*bits, 3*bits-1] = B, [3*bits] = control
 *
 * OWNERSHIP: Returns dynamically allocated sequence - CALLER MUST FREE
 */
sequence_t *cQ_and(int bits);

/**
 * @brief Controlled classical-quantum AND using sequential Toffoli gates.
 *
 * Adds one external control qubit to CQ_and. Each CNOT becomes Toffoli.
 * Circuit depth: O(popcount(value)) - sequential Toffoli gates.
 *
 * @param bits Width of operands (1-64)
 * @param value Classical value to AND with
 * @return Dynamically allocated sequence - CALLER MUST FREE
 *
 * Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = quantum operand,
 *               [2*bits] = control
 *
 * OWNERSHIP: Returns dynamically allocated sequence - CALLER MUST FREE
 */
sequence_t *cCQ_and(int bits, int64_t value);

// ======================================================
// Width-parameterized OR operations
// ======================================================

/**
 * @brief Bitwise OR using XOR+AND identity: A OR B = A XOR B XOR (A AND B).
 *
 * Computes result := A OR B using three sequential layers.
 * Circuit depth: O(3) - three sequential layers (XOR, AND, XOR).
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = A, [2*bits, 3*bits-1] = B
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *Q_or(int bits);

/**
 * @brief Classical-quantum OR.
 *
 * Computes result := classical_value OR quantum_operand.
 * For each bit i: if value[i] == 1 then X(result[i]) (1 OR x = 1),
 *                 else CNOT(quantum[i], result[i]) (0 OR x = x).
 * Circuit depth: O(1) - parallel gates (X for 1-bits, CNOT for 0-bits).
 *
 * @param bits Width of operands (1-64)
 * @param value Classical value to OR with
 * @return Dynamically allocated sequence - CALLER MUST FREE
 *
 * Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = quantum operand
 *
 * OWNERSHIP: Returns dynamically allocated sequence - CALLER MUST FREE
 */
sequence_t *CQ_or(int bits, int64_t value);

/**
 * @brief Controlled bitwise OR using sequential Toffoli and MCX gates.
 *
 * Adds one external control qubit to Q_or. CNOTs become Toffolis,
 * Toffolis become MCX(3).
 * Circuit depth: O(3*bits) - sequential gates across three phases.
 *
 * @param bits Width of operands (1-64)
 * @return Dynamically allocated sequence - CALLER MUST FREE
 *
 * Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = A,
 *               [2*bits, 3*bits-1] = B, [3*bits] = control
 *
 * OWNERSHIP: Returns dynamically allocated sequence - CALLER MUST FREE
 */
sequence_t *cQ_or(int bits);

/**
 * @brief Controlled classical-quantum OR using sequential CX and Toffoli gates.
 *
 * Adds one external control qubit to CQ_or. X gates become CX,
 * CNOT gates become Toffoli.
 * Circuit depth: O(bits) - sequential gates.
 *
 * @param bits Width of operands (1-64)
 * @param value Classical value to OR with
 * @return Dynamically allocated sequence - CALLER MUST FREE
 *
 * Qubit layout: [0, bits-1] = result, [bits, 2*bits-1] = quantum operand,
 *               [2*bits] = control
 *
 * OWNERSHIP: Returns dynamically allocated sequence - CALLER MUST FREE
 */
sequence_t *cCQ_or(int bits, int64_t value);

#endif // QUANTUM_BITWISE_OPS_H
