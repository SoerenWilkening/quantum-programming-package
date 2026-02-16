/**
 * @file toffoli_arithmetic_ops.h
 * @brief Toffoli-based arithmetic operations (CDKM ripple-carry adder).
 *
 * Provides Toffoli-based addition using the CDKM (Cuccaro-Draper-Kutin-Moulton)
 * ripple-carry adder circuit. Uses MAJ/UMA gate chains instead of QFT rotations.
 *
 * Phase 66: Core CDKM adder implementation (QQ, CQ).
 * Phase 67: Controlled variants (cQQ, cCQ) using CCX + MCX gates.
 *
 * Dependencies: types.h, QPU.h (for circuit_t in multiplication functions)
 */

#ifndef TOFFOLI_ARITHMETIC_OPS_H
#define TOFFOLI_ARITHMETIC_OPS_H

#include "QPU.h"
#include "types.h"
#include <stdint.h>

/**
 * @brief Quantum-quantum Toffoli addition: a += b (CDKM ripple-carry).
 *
 * Generates a CDKM adder sequence using MAJ/UMA chain.
 * For bits >= 2, requires 1 ancilla qubit at virtual index 2*bits.
 * For bits == 1, uses a single CNOT (no ancilla needed).
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE (NULL on invalid input)
 *
 * Qubit layout:
 *   [0..bits-1]       = register a (target, modified in place)
 *   [bits..2*bits-1]   = register b (source, unchanged)
 *   [2*bits]           = ancilla carry (bits >= 2 only, returned to |0>)
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *toffoli_QQ_add(int bits);

/**
 * @brief Classical-quantum Toffoli addition: self += classical_value (CDKM-based).
 *
 * Uses temp-register approach: initializes a temp register to the classical value
 * via X gates, runs the proven QQ CDKM adder, then undoes the X gates.
 * For bits >= 2, requires bits+1 ancilla qubits (bits for temp + 1 carry).
 * For bits == 1, uses a single X gate if LSB=1, or identity if LSB=0.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return Fresh sequence - CALLER MUST FREE via toffoli_sequence_free()
 *
 * Qubit layout:
 *   [0..bits-1]       = temp register (initialized to classical value, cleaned to |0>)
 *   [bits..2*bits-1]  = self register (target, modified: self += value)
 *   [2*bits]          = carry ancilla (bits >= 2 only, returned to |0>)
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 */
sequence_t *toffoli_CQ_add(int bits, int64_t value);

/**
 * @brief Controlled quantum-quantum Toffoli addition: a += b, controlled by ext_ctrl.
 *
 * Generates a controlled CDKM adder sequence using cMAJ/cUMA chains (CCX + MCX).
 * The addition only occurs when the external control qubit is |1>.
 * For bits >= 2, requires 1 ancilla qubit at virtual index 2*bits.
 * For bits == 1, uses a single CCX (no ancilla needed).
 *
 * @param bits Width of operands (1-64)
 * @return Cached sequence - DO NOT FREE (NULL on invalid input)
 *
 * Qubit layout:
 *   [0..bits-1]       = register a (target, modified in place: a += b)
 *   [bits..2*bits-1]   = register b (source, unchanged)
 *   [2*bits]           = ancilla carry (bits >= 2 only, returned to |0>)
 *   [2*bits+1]         = external control qubit
 *
 * For bits == 1: [0]=a, [1]=b, [2]=ext_control. Total qubits: 3.
 * For bits >= 2: Total qubits: 2*bits + 2.
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *toffoli_cQQ_add(int bits);

/**
 * @brief Controlled classical-quantum Toffoli addition: self += value, controlled.
 *
 * Uses controlled temp-register approach: CX(target=temp[i], control=ext_ctrl)
 * for initialization (only sets temp when control is |1>), controlled CDKM adder
 * core using cMAJ/cUMA, then CX cleanup.
 *
 * For bits >= 2, requires bits+1 ancilla qubits (bits for temp + 1 carry).
 * For bits == 1: CX(target=self, control=ext_ctrl) if value LSB=1, else empty.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return Fresh sequence - CALLER MUST FREE via toffoli_sequence_free()
 *
 * Qubit layout:
 *   [0..bits-1]       = temp register (controlled init to classical value, controlled cleanup)
 *   [bits..2*bits-1]  = self register (target, modified: self += value)
 *   [2*bits]          = carry ancilla (bits >= 2 only, returned to |0>)
 *   [2*bits+1]        = external control qubit
 *
 * For bits == 1: [0]=self, [1]=ext_control. Total qubits: 2.
 * For bits >= 2: Total qubits: 2*bits + 2.
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 * NOT cached (value-dependent).
 */
sequence_t *toffoli_cCQ_add(int bits, int64_t value);

// ============================================================================
// Carry Look-Ahead Addition (Phase 71)
// ============================================================================

/**
 * @brief Brent-Kung CLA QQ addition: b += a (O(log n) depth).
 *
 * STUB: Returns NULL -- ancilla uncomputation impossibility (see Phase 71-01).
 * Dispatch silently falls through to CDKM RCA adder.
 *
 * @param bits Width of operands (2-64; returns NULL for bits < 2)
 * @return NULL (CLA not yet implemented; falls through to RCA)
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *toffoli_QQ_add_bk(int bits);

/**
 * @brief Kogge-Stone CLA QQ addition: b += a (O(log n) depth).
 *
 * STUB: Returns NULL -- same ancilla uncomputation impossibility as BK.
 * Dispatch silently falls through to CDKM RCA adder.
 *
 * @param bits Width of operands (2-64; returns NULL for bits < 2)
 * @return NULL (CLA not yet implemented; falls through to RCA)
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *toffoli_QQ_add_ks(int bits);

/**
 * @brief Brent-Kung CLA CQ addition: self += classical_value.
 *
 * STUB: Returns NULL -- BK QQ CLA not implemented.
 * Dispatch silently falls through to CDKM RCA CQ adder.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return NULL (falls through to RCA CQ)
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 */
sequence_t *toffoli_CQ_add_bk(int bits, int64_t value);

/**
 * @brief Kogge-Stone CLA CQ addition: self += classical_value.
 *
 * STUB: Returns NULL -- KS QQ CLA not implemented.
 * Dispatch silently falls through to CDKM RCA CQ adder.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return NULL (falls through to RCA CQ)
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 */
sequence_t *toffoli_CQ_add_ks(int bits, int64_t value);

// ============================================================================
// Controlled Carry Look-Ahead Addition (Phase 71, Plan 03)
// ============================================================================

/**
 * @brief Controlled Brent-Kung CLA QQ addition: b += a, controlled.
 *
 * STUB: Returns NULL -- same ancilla uncomputation impossibility as uncontrolled BK.
 * Dispatch silently falls through to controlled CDKM RCA adder.
 *
 * @param bits Width of operands (2-64; returns NULL for bits < 2)
 * @return NULL (controlled CLA not yet implemented; falls through to RCA)
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *toffoli_cQQ_add_bk(int bits);

/**
 * @brief Controlled Kogge-Stone CLA QQ addition: b += a, controlled.
 *
 * STUB: Returns NULL -- same ancilla uncomputation impossibility as uncontrolled KS.
 * Dispatch silently falls through to controlled CDKM RCA adder.
 *
 * @param bits Width of operands (2-64; returns NULL for bits < 2)
 * @return NULL (controlled CLA not yet implemented; falls through to RCA)
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 */
sequence_t *toffoli_cQQ_add_ks(int bits);

/**
 * @brief Controlled Brent-Kung CLA CQ addition: self += classical_value, controlled.
 *
 * STUB: Returns NULL -- controlled BK CLA not implemented.
 * Dispatch silently falls through to controlled CDKM RCA CQ adder.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return NULL (falls through to controlled RCA CQ)
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 */
sequence_t *toffoli_cCQ_add_bk(int bits, int64_t value);

/**
 * @brief Controlled Kogge-Stone CLA CQ addition: self += classical_value, controlled.
 *
 * STUB: Returns NULL -- controlled KS CLA not implemented.
 * Dispatch silently falls through to controlled CDKM RCA CQ adder.
 *
 * @param bits Width of target operand (1-64)
 * @param value Classical integer value to add
 * @return NULL (falls through to controlled RCA CQ)
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free via toffoli_sequence_free()
 */
sequence_t *toffoli_cCQ_add_ks(int bits, int64_t value);

// ============================================================================
// Toffoli Multiplication (Phase 68)
// ============================================================================

/**
 * @brief Toffoli schoolbook QQ multiplication: ret = self * other.
 *
 * Uses controlled CDKM adders in a shift-and-add loop. For each bit j of
 * the multiplier (other), performs a controlled addition of self[0..n-1-j]
 * into ret[j..n-1], controlled by other[j].
 *
 * @param circ          Active circuit
 * @param ret_qubits    Result register qubits (accumulator, starts at |0>)
 * @param ret_bits      Width of result register (n)
 * @param self_qubits   Multiplicand register qubits (preserved)
 * @param self_bits     Width of multiplicand
 * @param other_qubits  Multiplier register qubits (preserved)
 * @param other_bits    Width of multiplier
 */
void toffoli_mul_qq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                    const unsigned int *self_qubits, int self_bits,
                    const unsigned int *other_qubits, int other_bits);

/**
 * @brief Toffoli schoolbook CQ multiplication: ret = self * classical_value.
 *
 * Decomposes classical_value into binary. For each set bit j, performs an
 * uncontrolled addition of self[0..n-1-j] into ret[j..n-1].
 *
 * @param circ            Active circuit
 * @param ret_qubits      Result register qubits (accumulator, starts at |0>)
 * @param ret_bits        Width of result register (n)
 * @param self_qubits     Multiplicand register qubits (preserved)
 * @param self_bits       Width of multiplicand
 * @param classical_value Classical integer to multiply by
 */
void toffoli_mul_cq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                    const unsigned int *self_qubits, int self_bits, int64_t classical_value);

// ============================================================================
// Controlled Toffoli Multiplication (Phase 69)
// ============================================================================

/**
 * @brief Controlled Toffoli QQ multiplication: ret = self * other, controlled.
 *
 * Uses the AND-ancilla pattern: for each multiplier bit other[j], computes
 * and_ancilla = other[j] AND ext_ctrl via CCX, uses and_ancilla as the single
 * control for toffoli_cQQ_add, then uncomputes AND via a second CCX.
 *
 * For width 1: emits a single MCX with 3 controls (self[0], other[j], ext_ctrl).
 * Ancilla: 1 carry + 1 AND = 2 ancilla (allocated before loop, freed after).
 *
 * @param circ          Active circuit
 * @param ret_qubits    Result register qubits (accumulator, starts at |0>)
 * @param ret_bits      Width of result register (n)
 * @param self_qubits   Multiplicand register qubits (preserved)
 * @param self_bits     Width of multiplicand
 * @param other_qubits  Multiplier register qubits (preserved)
 * @param other_bits    Width of multiplier
 * @param ext_ctrl      External control qubit
 */
void toffoli_cmul_qq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                     const unsigned int *self_qubits, int self_bits,
                     const unsigned int *other_qubits, int other_bits, unsigned int ext_ctrl);

/**
 * @brief Controlled Toffoli CQ multiplication: ret = self * classical_value, controlled.
 *
 * For each set bit j of classical_value, performs a controlled addition of
 * self[0..width-1] into ret[j..j+width-1] using toffoli_cQQ_add with ext_ctrl.
 *
 * No AND-ancilla needed: classical bit selection is compile-time; only the
 * runtime ext_ctrl gates each addition.
 *
 * For width 1: uses toffoli_cQQ_add(1) with ext_ctrl as control (CCX).
 * Ancilla: 1 carry (allocated before loop, freed after).
 *
 * @param circ            Active circuit
 * @param ret_qubits      Result register qubits (accumulator, starts at |0>)
 * @param ret_bits        Width of result register (n)
 * @param self_qubits     Multiplicand register qubits (preserved)
 * @param self_bits       Width of multiplicand
 * @param classical_value Classical integer to multiply by
 * @param ext_ctrl        External control qubit
 */
void toffoli_cmul_cq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                     const unsigned int *self_qubits, int self_bits, int64_t classical_value,
                     unsigned int ext_ctrl);

/**
 * @brief Free a Toffoli addition sequence.
 *
 * Frees all internal arrays including large_control arrays for MCX gates
 * with 3+ controls (prevents memory leaks from controlled adder sequences).
 * CQ/cCQ sequences are value-dependent and cannot be cached, so they must
 * be freed after use.
 *
 * @param seq Sequence to free (can be NULL)
 */
void toffoli_sequence_free(sequence_t *seq);

#endif // TOFFOLI_ARITHMETIC_OPS_H
