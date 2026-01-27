//
// arithmetic_ops.h
//
// Arithmetic Operations Module
//
// This header consolidates all arithmetic operation functions (addition, multiplication).
// Subtraction is not included here - it is implemented at the Python level using addition
// with two's complement negation (i.e., a - b uses QQ_add with the second operand negated
// via two_complement()). This is standard quantum arithmetic practice.
//
// Dependencies: types.h
// Part of CODE-04 reorganization (Phase 9)
//

#ifndef QUANTUM_ARITHMETIC_OPS_H
#define QUANTUM_ARITHMETIC_OPS_H

#include "types.h"
#include <stdint.h>

// ============================================================================
// Addition Operations
// ============================================================================

/**
 * Classical-classical addition (performs classical computation only)
 * OWNERSHIP: No sequence returned (performs classical computation only)
 */
sequence_t *CC_add();

/**
 * Classical-quantum addition: target += value
 * Width-parameterized version (1-64 bits)
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical value to add
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = target (modified in place)
 */
sequence_t *CQ_add(int bits, int64_t value);

/**
 * Quantum-quantum addition: result = a + b
 * Width-parameterized version (1-64 bits)
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result, [bits:2*bits-1] = a, [2*bits:3*bits-1] = b
 */
sequence_t *QQ_add(int bits);

/**
 * Controlled classical-quantum addition: if control then target += value
 * Width-parameterized version (1-64 bits)
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical value to add
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = target, [3*bits-1] = control
 */
sequence_t *cCQ_add(int bits, int64_t value);

/**
 * Controlled quantum-quantum addition: if control then result = a + b
 * Width-parameterized version (1-64 bits)
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result, [bits:2*bits-1] = a, [2*bits:3*bits-1] = b, [4*bits-1] =
 * control
 */
sequence_t *cQQ_add(int bits);

/**
 * Probabilistic addition (special operation)
 */
sequence_t *P_add();

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

/**
 * Classical-classical multiplication (performs classical computation only)
 * OWNERSHIP: No sequence returned (performs classical computation only)
 */
sequence_t *CC_mul();

/**
 * Classical-quantum multiplication: result = target * value
 * Width-parameterized version (1-64 bits)
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical value to multiply
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result/target
 */
sequence_t *CQ_mul(int bits, int64_t value);

/**
 * Quantum-quantum multiplication: result = a * b
 * Width-parameterized version (1-64 bits)
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result, [bits:2*bits-1] = a, [2*bits:3*bits-1] = b
 */
sequence_t *QQ_mul(int bits);

/**
 * Controlled classical-quantum multiplication: if control then result = target * value
 * Width-parameterized version (1-64 bits)
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical value to multiply
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result/target, [3*bits-1] = control
 */
sequence_t *cCQ_mul(int bits, int64_t value);

/**
 * Controlled quantum-quantum multiplication: if control then result = a * b
 * Width-parameterized version (1-64 bits)
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE
 *
 * Qubit layout: [0:bits-1] = result, [bits:2*bits-1] = a, [2*bits:3*bits-1] = b, [4*bits-1] =
 * control
 */
sequence_t *cQQ_mul(int bits);

// Legacy globals for backward compatibility (point to INTEGERSIZE versions)
extern sequence_t *precompiled_QQ_mul;
extern sequence_t *precompiled_cQQ_mul;

// Width-parameterized precompiled caches (index 0 unused, 1-64 valid)
extern sequence_t *precompiled_QQ_mul_width[65];
extern sequence_t *precompiled_cQQ_mul_width[65];

#endif // QUANTUM_ARITHMETIC_OPS_H
