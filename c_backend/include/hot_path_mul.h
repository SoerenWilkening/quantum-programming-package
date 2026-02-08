/**
 * @file hot_path_mul.h
 * @brief C hot path for multiplication_inplace (Phase 60, Plan 02).
 *
 * Replaces the Cython multiplication_inplace method body with pure C,
 * eliminating Python/C boundary crossings for the #1 hot path.
 *
 * Two entry points:
 *   hot_path_mul_qq  -- quantum-quantum multiplication (self * other)
 *   hot_path_mul_cq  -- classical-quantum multiplication (self * classical_value)
 *
 * The caller (thin Cython wrapper) extracts qubit indices from Python objects
 * and passes flat C arrays. These functions build the qubit_array layout,
 * call the sequence generator (QQ_mul / cQQ_mul / CQ_mul / cCQ_mul),
 * and execute the instruction on the circuit -- all without returning to Python.
 *
 * Dependencies: QPU.h (circuit_t), types.h (qubit_t, sequence_t),
 *               arithmetic_ops.h (mul generators), execution.h (run_instruction)
 */

#ifndef HOT_PATH_MUL_H
#define HOT_PATH_MUL_H

#include "QPU.h"
#include "types.h"
#include <stdint.h>

/**
 * @brief Quantum-quantum multiplication: ret = self * other (quantum operands).
 *
 * Builds the qubit layout expected by QQ_mul / cQQ_mul and executes it.
 *
 * Qubit layout (matching Cython multiplication_inplace):
 *   [0 .. ret_bits-1]                       : ret (accumulator)
 *   [ret_bits .. ret_bits+self_bits-1]       : self (multiplicand)
 *   [ret_bits+self_bits .. +other_bits-1]    : other (multiplier)
 *   controlled: control_qubit, then ancilla
 *   uncontrolled: ancilla
 *
 * @param circ          Active circuit
 * @param ret_qubits    Array of ret qubit indices (length ret_bits)
 * @param ret_bits      Width of result register
 * @param self_qubits   Array of self qubit indices (length self_bits)
 * @param self_bits     Width of self register
 * @param other_qubits  Array of other qubit indices (length other_bits)
 * @param other_bits    Width of other register
 * @param controlled    Non-zero if controlled operation
 * @param control_qubit Control qubit index (ignored if !controlled)
 * @param ancilla       Array of ancilla qubit indices
 * @param num_ancilla   Number of ancilla qubits
 */
void hot_path_mul_qq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                     const unsigned int *self_qubits, int self_bits,
                     const unsigned int *other_qubits, int other_bits, int controlled,
                     unsigned int control_qubit, const unsigned int *ancilla, int num_ancilla);

/**
 * @brief Classical-quantum multiplication: ret = self * classical_value.
 *
 * Builds the qubit layout expected by CQ_mul / cCQ_mul and executes it.
 *
 * Qubit layout (matching Cython multiplication_inplace):
 *   [0 .. ret_bits-1]                       : ret (accumulator)
 *   [ret_bits .. ret_bits+self_bits-1]       : self (multiplicand)
 *   controlled: control_qubit, then ancilla
 *   uncontrolled: ancilla
 *
 * @param circ            Active circuit
 * @param ret_qubits      Array of ret qubit indices (length ret_bits)
 * @param ret_bits        Width of result register
 * @param self_qubits     Array of self qubit indices (length self_bits)
 * @param self_bits       Width of self register
 * @param classical_value Classical integer to multiply by
 * @param controlled      Non-zero if controlled operation
 * @param control_qubit   Control qubit index (ignored if !controlled)
 * @param ancilla         Array of ancilla qubit indices
 * @param num_ancilla     Number of ancilla qubits
 */
void hot_path_mul_cq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                     const unsigned int *self_qubits, int self_bits, int64_t classical_value,
                     int controlled, unsigned int control_qubit, const unsigned int *ancilla,
                     int num_ancilla);

#endif /* HOT_PATH_MUL_H */
