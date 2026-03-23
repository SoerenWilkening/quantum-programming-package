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

// CQ_equal() and cCQ_equal() removed (Phase 11-04) - used global state for classical value
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
 * @brief QQ less-than: result = (A < B).
 *
 * Borrow-ancilla pattern via (n+1)-bit QQ addition.
 *
 * Qubit layout:
 *   [0]=result, [1..bits]=A, [bits+1..2*bits]=B,
 *   [2*bits+1]=borrow, [2*bits+2]=zero_ext
 *
 * @param bits Width of operands (1-63)
 * @return Fresh sequence. CALLER MUST FREE.
 */
sequence_t *QQ_less_than(int bits);

/**
 * @brief Controlled QQ less-than: result = (A < B), controlled.
 *
 * Qubit layout:
 *   [0]=result, [1..bits]=A, [bits+1..2*bits]=B,
 *   [2*bits+1]=borrow, [2*bits+2]=zero_ext, [2*bits+3]=control
 *
 * @param bits Width of operands (1-63)
 * @return Fresh sequence. CALLER MUST FREE.
 */
sequence_t *cQQ_less_than(int bits);

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
 * @brief Controlled classical-quantum equality: A == value (controlled).
 *
 * Compares quantum register with classical integer value, controlled by a qubit.
 * Comparison gates only applied when control qubit is |1>.
 *
 * @param bits Width of quantum operand (1-64)
 * @param value Classical value to compare against
 * @return Sequence for controlled equality comparison, NULL if invalid bits
 *
 * Qubit layout: [0] = result qbool, [1:bits+1] = operand, [bits+1] = control
 *
 * OWNERSHIP: Caller owns returned sequence_t*
 */
sequence_t *cCQ_equal_width(int bits, int64_t value);

/**
 * @brief Classical-quantum less-than: A < value.
 *
 * Borrow-ancilla comparison: subtract, copy borrow, restore.
 *
 * Qubit layout: [0]=result, [1..bits]=A, [bits+1]=borrow_ancilla
 *
 * @param bits Width of quantum operand (1-63)
 * @param value Classical value to compare against
 * @return Sequence for comparison, NULL on error
 *
 * OWNERSHIP: Caller owns returned sequence_t*
 */
sequence_t *CQ_less_than(int bits, int64_t value);

/**
 * @brief Controlled classical-quantum less-than: A < value (controlled).
 *
 * Qubit layout: [0]=result, [1..bits]=A, [bits+1]=borrow, [bits+2]=control
 *
 * @param bits Width of quantum operand (1-63)
 * @param value Classical value to compare against
 * @return Sequence for controlled comparison, NULL on error
 *
 * OWNERSHIP: Caller owns returned sequence_t*
 */
sequence_t *cCQ_less_than(int bits, int64_t value);

/**
 * @brief Classical-quantum greater-than: A > value.
 *
 * Delegates to CQ_less_than(bits, value + 1).
 *
 * Qubit layout: [0]=result, [1..bits]=A, [bits+1]=borrow_ancilla
 *
 * @param bits Width of quantum operand (1-63)
 * @param value Classical value to compare against
 * @return Sequence for comparison, NULL on error
 *
 * OWNERSHIP: Caller owns returned sequence_t*
 */
sequence_t *CQ_greater_than(int bits, int64_t value);

/**
 * @brief Controlled classical-quantum greater-than: A > value (controlled).
 *
 * Qubit layout: [0]=result, [1..bits]=A, [bits+1]=borrow, [bits+2]=control
 *
 * @param bits Width of quantum operand (1-63)
 * @param value Classical value to compare against
 * @return Sequence for controlled comparison, NULL on error
 *
 * OWNERSHIP: Caller owns returned sequence_t*
 */
sequence_t *cCQ_greater_than(int bits, int64_t value);

#endif // QUANTUM_COMPARISON_OPS_H
