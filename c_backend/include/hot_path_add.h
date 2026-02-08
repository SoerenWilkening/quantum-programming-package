/**
 * @file hot_path_add.h
 * @brief C hot path for addition_inplace (Phase 60, Plan 03).
 *
 * Replaces the Cython addition_inplace method body with pure C,
 * eliminating Python/C boundary crossings for the #2 hot path.
 *
 * Two entry points:
 *   hot_path_add_qq  -- quantum-quantum addition (self += other)
 *   hot_path_add_cq  -- classical-quantum addition (self += classical_value)
 *
 * The caller (thin Cython wrapper) extracts qubit indices from Python objects
 * and passes flat C arrays. These functions build the qubit_array layout,
 * call the sequence generator (QQ_add / cQQ_add / CQ_add / cCQ_add),
 * and execute the instruction on the circuit -- all without returning to Python.
 *
 * Dependencies: QPU.h (circuit_t), types.h (qubit_t, sequence_t),
 *               arithmetic_ops.h (add generators), execution.h (run_instruction)
 */

#ifndef HOT_PATH_ADD_H
#define HOT_PATH_ADD_H

#include "QPU.h"
#include "types.h"
#include <stdint.h>

/**
 * @brief Quantum-quantum addition: self += other (quantum operands).
 *
 * Builds the qubit layout expected by QQ_add / cQQ_add and executes it.
 *
 * Qubit layout (matching Cython addition_inplace for QQ path):
 *   Uncontrolled:
 *     [0 .. self_bits-1]                       : self qubits (target, modified in place)
 *     [self_bits .. self_bits+other_bits-1]     : other qubits
 *     [start .. start+num_ancilla-1]            : ancilla (start = self_bits + other_bits)
 *     Calls QQ_add(result_bits)
 *   Controlled:
 *     [0 .. self_bits-1]                        : self qubits (target)
 *     [self_bits .. self_bits+other_bits-1]      : other qubits
 *     [2*result_bits]                           : control_qubit
 *     [2*result_bits+1 .. ]                     : ancilla
 *     Calls cQQ_add(result_bits)
 *
 * @param circ          Active circuit
 * @param self_qubits   Array of self qubit indices (length self_bits)
 * @param self_bits     Width of self register
 * @param other_qubits  Array of other qubit indices (length other_bits)
 * @param other_bits    Width of other register
 * @param invert        Non-zero to invert the operation (for subtraction)
 * @param controlled    Non-zero if controlled operation
 * @param control_qubit Control qubit index (ignored if !controlled)
 * @param ancilla       Array of ancilla qubit indices
 * @param num_ancilla   Number of ancilla qubits
 */
void hot_path_add_qq(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                     const unsigned int *other_qubits, int other_bits, int invert, int controlled,
                     unsigned int control_qubit, const unsigned int *ancilla, int num_ancilla);

/**
 * @brief Classical-quantum addition: self += classical_value.
 *
 * Builds the qubit layout expected by CQ_add / cCQ_add and executes it.
 *
 * Qubit layout (matching Cython addition_inplace for CQ path):
 *   Uncontrolled:
 *     [0 .. self_bits-1]                       : self qubits (target)
 *     [self_bits .. self_bits+num_ancilla-1]    : ancilla
 *     Calls CQ_add(self_bits, value)
 *   Controlled:
 *     [0 .. self_bits-1]                        : self qubits (target)
 *     [self_bits]                               : control_qubit
 *     [self_bits+1 .. ]                         : ancilla
 *     Calls cCQ_add(self_bits, value)
 *
 * @param circ            Active circuit
 * @param self_qubits     Array of self qubit indices (length self_bits)
 * @param self_bits       Width of self register
 * @param classical_value Classical integer value to add
 * @param invert          Non-zero to invert the operation (for subtraction)
 * @param controlled      Non-zero if controlled operation
 * @param control_qubit   Control qubit index (ignored if !controlled)
 * @param ancilla         Array of ancilla qubit indices
 * @param num_ancilla     Number of ancilla qubits
 */
void hot_path_add_cq(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                     int64_t classical_value, int invert, int controlled,
                     unsigned int control_qubit, const unsigned int *ancilla, int num_ancilla);

#endif /* HOT_PATH_ADD_H */
