/**
 * @file comparison_ops.h
 * @brief Width-parameterized comparison operations for quantum integers.
 *
 * This header provides comparison operations (==, <, >, <=, >=).
 * Supports variable-width quantum integers (1-64 bits).
 *
 * Dependencies: types.h
 * Part of CODE-04 reorganization to establish clear module boundaries.
 */

#ifndef QUANTUM_COMPARISON_OPS_H
#define QUANTUM_COMPARISON_OPS_H

#include "types.h"
#include <stdint.h>

// ======================================================
// Legacy Comparison Operations (INTEGERSIZE-based)
// ======================================================

// CC_equal removed (Phase 11) - purely classical, no quantum gate generation

// CQ_equal() and cCQ_equal() removed (Phase 11-04) - used QPU_state->R0 for classical value
// Use CQ_equal_width(bits, value) instead with explicit parameters

// ======================================================
// Width-Parameterized Comparison Operations (Phase 7)
// ======================================================

/**
 * @brief Optimized equality comparison: A == B.
 *
 * Uses XOR-based circuit (O(n) gates) instead of subtraction (O(n^2) gates).
 * Much more efficient than subtraction-based approach.
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence, NULL if invalid bits - DO NOT FREE
 *
 * Qubit layout: [0] = result qbool, [1:bits+1] = ancilla,
 *               [bits+1:2*bits+1] = operand A, [2*bits+1:3*bits+1] = operand B
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *QQ_equal(int bits);

/**
 * @brief Less-than comparison: A < B.
 *
 * Uses subtraction and MSB check to determine if A < B.
 * Result is stored in a quantum boolean (single qubit).
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence, NULL if invalid bits - DO NOT FREE
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *QQ_less_than(int bits);

/**
 * @brief Classical-quantum equality: A == value.
 *
 * Compares quantum register with classical integer value.
 * Width-parameterized for variable-width integers.
 *
 * @param bits Width of quantum operand (1-64)
 * @param value Classical value to compare against
 * @return Sequence for equality comparison
 *
 * OWNERSHIP: Caller owns returned sequence_t*
 */
sequence_t *CQ_equal_width(int bits, int64_t value);

/**
 * @brief Classical-quantum less-than: A < value.
 *
 * Compares quantum register with classical integer value.
 * Width-parameterized for variable-width integers.
 *
 * @param bits Width of quantum operand (1-64)
 * @param value Classical value to compare against
 * @return Sequence for comparison
 *
 * OWNERSHIP: Caller owns returned sequence_t*
 */
sequence_t *CQ_less_than(int bits, int64_t value);

#endif // QUANTUM_COMPARISON_OPS_H
