/**
 * @file arithmetic_ops.h
 * @brief Width-parameterized arithmetic operations for quantum integers.
 *
 * This header consolidates all arithmetic operation functions (addition, multiplication).
 * Supports variable-width quantum integers (1-64 bits) introduced in Phase 5.
 *
 * Subtraction is not included here - it is implemented at the Python level using addition
 * with two's complement negation (i.e., a - b uses QQ_add with the second operand negated
 * via two_complement()). This is standard quantum arithmetic practice.
 *
 * Dependencies: types.h
 * Part of CODE-04 reorganization (Phase 9)
 */

#ifndef QUANTUM_ARITHMETIC_OPS_H
#define QUANTUM_ARITHMETIC_OPS_H

#include "types.h"
#include <stdint.h>

// ============================================================================
// Addition Operations
// ============================================================================

// CC_add removed (Phase 11) - purely classical, no quantum gate generation

/**
 * @brief Classical-quantum addition: target += value.
 *
 * Width-parameterized version (1-64 bits). Adds a classical integer value to
 * a quantum register in place using Draper adder circuit.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical value to add
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = target (modified in place)
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *CQ_add(int bits, int64_t value);

/**
 * @brief Quantum-quantum addition: result = a + b.
 *
 * Width-parameterized version (1-64 bits). Implements Draper quantum adder
 * for adding two quantum registers using QFT-based arithmetic.
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result, [bits:2*bits-1] = a, [2*bits:3*bits-1] = b
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *QQ_add(int bits);

/**
 * @brief Controlled classical-quantum addition: if control then target += value.
 *
 * Width-parameterized version (1-64 bits). Conditional addition controlled by a
 * single qubit. Uses controlled phase rotations.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical value to add
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = target, [3*bits-1] = control
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *cCQ_add(int bits, int64_t value);

/**
 * @brief Controlled quantum-quantum addition: if control then result = a + b.
 *
 * Width-parameterized version (1-64 bits). Conditional quantum adder controlled
 * by a single qubit.
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result, [bits:2*bits-1] = a, [2*bits:3*bits-1] = b, [4*bits-1] =
 * control
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *cQQ_add(int bits);

// ============================================================================
// Phase Gate Operations
// ============================================================================

/**
 * @brief Phase gate with explicit parameter (no global state).
 *
 * Applies a phase rotation to qubit 0 using the provided phase value.
 *
 * @param phase_value Phase rotation angle in radians
 * @return Sequence containing single phase gate - caller must free
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
 */
sequence_t *P_add_param(double phase_value);

/**
 * @brief Controlled phase gate with explicit parameter (no global state).
 *
 * Applies a controlled phase rotation from qubit 1 to qubit 0 using the provided phase value.
 *
 * @param phase_value Phase rotation angle in radians
 * @return Sequence containing single controlled phase gate - caller must free
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free gates_per_layer, seq arrays, and seq
 */
sequence_t *cP_add_param(double phase_value);

// P_add() and cP_add() removed (Phase 11-04) - deprecated wrappers that used global state
// Use P_add_param(phase_value) and cP_add_param(phase_value) instead

// Legacy globals for backward compatibility (point to INTEGERSIZE versions)
extern sequence_t *precompiled_QQ_add;
extern sequence_t *precompiled_cQQ_add;
extern sequence_t *precompiled_CQ_add[64];
extern sequence_t *precompiled_cCQ_add[64];

// Width-parameterized precompiled caches (index 0 unused, 1-64 valid)
extern sequence_t *precompiled_QQ_add_width[65];
extern sequence_t *precompiled_cQQ_add_width[65];

// ============================================================================
// Multiplication Operations
// ============================================================================

// CC_mul removed (Phase 11) - purely classical, no quantum gate generation

/**
 * @brief Classical-quantum multiplication: result = target * value.
 *
 * Width-parameterized version (1-64 bits). Multiplies a quantum register by a
 * classical integer using repeated controlled additions.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical value to multiply
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result/target
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *CQ_mul(int bits, int64_t value);

/**
 * @brief Quantum-quantum multiplication: result = a * b.
 *
 * Width-parameterized version (1-64 bits). Implements quantum multiplier using
 * repeated controlled additions. Circuit complexity is O(bits^2).
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result, [bits:2*bits-1] = a, [2*bits:3*bits-1] = b
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *QQ_mul(int bits);

/**
 * @brief Controlled classical-quantum multiplication: if control then result = target * value.
 *
 * Width-parameterized version (1-64 bits). Conditional multiplication controlled
 * by a single qubit.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical value to multiply
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result/target, [3*bits-1] = control
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *cCQ_mul(int bits, int64_t value);

/**
 * @brief Controlled quantum-quantum multiplication: if control then result = a * b.
 *
 * Width-parameterized version (1-64 bits). Conditional quantum multiplier controlled
 * by a single qubit.
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result, [bits:2*bits-1] = a, [2*bits:3*bits-1] = b, [4*bits-1] =
 * control
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *cQQ_mul(int bits);

// Legacy globals for backward compatibility (point to INTEGERSIZE versions)
extern sequence_t *precompiled_QQ_mul;
extern sequence_t *precompiled_cQQ_mul;

// Width-parameterized precompiled caches (index 0 unused, 1-64 valid)
extern sequence_t *precompiled_QQ_mul_width[65];
extern sequence_t *precompiled_cQQ_mul_width[65];

// ============================================================================
// Split-Register Arithmetic (Phase 4: In-Place Comparison Operators)
// ============================================================================

/**
 * @brief Split-register QFT addition: [a, msb] += classical value.
 *
 * Treats [a_0..a_{bits-1}, msb_qubit] as an (bits+1)-bit register and adds
 * a classical value using the Draper QFT adder on the full (bits+1) width.
 *
 * @param bits  Width of the base register a (1-63)
 * @param value Classical value to add
 * @return Fresh sequence - CALLER MUST FREE
 *
 * Qubit layout: [0..bits-1] = register a, [bits] = msb qubit
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free
 */
sequence_t *split_CQ_add(int bits, int64_t value);

/**
 * @brief Split-register QFT subtraction: [a, msb] -= classical value.
 *
 * Equivalent to split_CQ_add(bits, -value).
 *
 * @param bits  Width of the base register a (1-63)
 * @param value Classical value to subtract
 * @return Fresh sequence - CALLER MUST FREE
 *
 * Qubit layout: [0..bits-1] = register a, [bits] = msb qubit
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free
 */
sequence_t *split_CQ_sub(int bits, int64_t value);

/**
 * @brief Split-register Toffoli addition: [a, msb] += classical value.
 *
 * Uses CDKM ripple-carry adder on (bits+1) qubits. The temp register and
 * carry ancilla are internal to the sequence.
 *
 * @param bits  Width of the base register a (1-63)
 * @param value Classical value to add
 * @return Fresh sequence - CALLER MUST FREE via toffoli_sequence_free()
 *
 * Qubit layout (of returned sequence, same as toffoli_CQ_add(bits+1)):
 *   [0..bits]        = temp register
 *   [bits+1..2*bits+1] = target register [a, msb]
 *   [2*(bits+1)]     = carry ancilla
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 */
sequence_t *split_toffoli_CQ_add(int bits, int64_t value);

/**
 * @brief Split-register Toffoli subtraction: [a, msb] -= classical value.
 *
 * Equivalent to split_toffoli_CQ_add(bits, -value).
 *
 * @param bits  Width of the base register a (1-63)
 * @param value Classical value to subtract
 * @return Fresh sequence - CALLER MUST FREE via toffoli_sequence_free()
 *
 * Qubit layout: same as split_toffoli_CQ_add
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 */
sequence_t *split_toffoli_CQ_sub(int bits, int64_t value);

#endif // QUANTUM_ARITHMETIC_OPS_H
