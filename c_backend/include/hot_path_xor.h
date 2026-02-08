/**
 * @file hot_path_xor.h
 * @brief C hot path for __ixor__ / __xor__ (Phase 60, Plan 04).
 *
 * Replaces the Cython __ixor__ method body with pure C,
 * eliminating Python/C boundary crossings for the #3 hot path.
 *
 * Two entry points:
 *   hot_path_ixor_qq  -- quantum-quantum XOR: self ^= other
 *   hot_path_ixor_cq  -- classical-quantum XOR: self ^= classical_value
 *
 * The caller (thin Cython wrapper) extracts qubit indices from Python objects
 * and passes flat C arrays. These functions build the qubit_array layout,
 * call the sequence generator (Q_xor / Q_not), and execute the instruction
 * on the circuit -- all without returning to Python.
 *
 * Dependencies: QPU.h (circuit_t), types.h (qubit_t, sequence_t),
 *               bitwise_ops.h (Q_xor, Q_not), execution.h (run_instruction)
 */

#ifndef HOT_PATH_XOR_H
#define HOT_PATH_XOR_H

#include "QPU.h"
#include "types.h"
#include <stdint.h>

/**
 * @brief Quantum-quantum in-place XOR: self ^= other.
 *
 * Builds the qubit layout expected by Q_xor and executes it.
 *
 * Qubit layout (matching Cython __ixor__ for QQ path):
 *   [0 .. xor_bits-1]                    : self qubits (target, modified in place)
 *   [xor_bits .. 2*xor_bits-1]           : other qubits (source)
 *   where xor_bits = min(self_bits, other_bits)
 *
 * @param circ          Active circuit
 * @param self_qubits   Array of self qubit indices (length self_bits)
 * @param self_bits     Width of self register
 * @param other_qubits  Array of other qubit indices (length other_bits)
 * @param other_bits    Width of other register
 */
void hot_path_ixor_qq(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                      const unsigned int *other_qubits, int other_bits);

/**
 * @brief Classical-quantum in-place XOR: self ^= classical_value.
 *
 * For each set bit in classical_value, applies Q_not(1) to the corresponding
 * qubit in self. This is equivalent to conditional X gates.
 *
 * @param circ            Active circuit
 * @param self_qubits     Array of self qubit indices (length self_bits)
 * @param self_bits       Width of self register
 * @param classical_value Classical integer value to XOR with
 */
void hot_path_ixor_cq(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                      int64_t classical_value);

#endif /* HOT_PATH_XOR_H */
