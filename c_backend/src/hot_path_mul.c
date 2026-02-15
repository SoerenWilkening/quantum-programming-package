/**
 * @file hot_path_mul.c
 * @brief C hot path for multiplication_inplace (Phase 60, Plan 02).
 *
 * Implements the core loop of multiplication_inplace entirely in C,
 * removing all Python/C boundary crossings from the inner path.
 *
 * The qubit layout built here MUST match the Cython multiplication_inplace
 * exactly (see qint_arithmetic.pxi).
 */

#include "hot_path_mul.h"
#include "arithmetic_ops.h"
#include "execution.h"
#include "qubit_allocator.h"
#include "toffoli_arithmetic_ops.h"

void hot_path_mul_qq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                     const unsigned int *self_qubits, int self_bits,
                     const unsigned int *other_qubits, int other_bits, int controlled,
                     unsigned int control_qubit, const unsigned int *ancilla, int num_ancilla) {
    /* Toffoli schoolbook multiplication dispatch (controlled and uncontrolled). */
    if (circ->arithmetic_mode == ARITH_TOFFOLI) {
        if (controlled) {
            toffoli_cmul_qq(circ, ret_qubits, ret_bits, self_qubits, self_bits, other_qubits,
                            other_bits, control_qubit);
        } else {
            toffoli_mul_qq(circ, ret_qubits, ret_bits, self_qubits, self_bits, other_qubits,
                           other_bits);
        }
        return;
    }

    /* Build the qubit_array on the stack.
     * Layout (matches Cython multiplication_inplace for QQ path):
     *   [0 .. ret_bits-1]                        : ret qubits
     *   [ret_bits .. ret_bits+self_bits-1]        : self qubits
     *   [start .. start+other_bits-1]             : other qubits
     *   if controlled: control_qubit, then ancilla
     *   else: ancilla
     */
    unsigned int qa[256];
    int pos = 0;
    int i;

    /* ret qubits at position 0 */
    for (i = 0; i < ret_bits; i++) {
        qa[pos++] = ret_qubits[i];
    }

    /* self qubits at position ret_bits */
    for (i = 0; i < self_bits; i++) {
        qa[pos++] = self_qubits[i];
    }

    /* other qubits */
    for (i = 0; i < other_bits; i++) {
        qa[pos++] = other_qubits[i];
    }

    /* control + ancilla */
    sequence_t *seq;
    if (controlled) {
        qa[pos++] = control_qubit;
        for (i = 0; i < num_ancilla; i++) {
            qa[pos++] = ancilla[i];
        }
        seq = cQQ_mul(ret_bits);
    } else {
        for (i = 0; i < num_ancilla; i++) {
            qa[pos++] = ancilla[i];
        }
        seq = QQ_mul(ret_bits);
    }

    /* NULL check -- caller (Cython) will raise if needed */
    if (seq == NULL) {
        return;
    }

    run_instruction(seq, qa, 0, circ);
}

void hot_path_mul_cq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                     const unsigned int *self_qubits, int self_bits, int64_t classical_value,
                     int controlled, unsigned int control_qubit, const unsigned int *ancilla,
                     int num_ancilla) {
    /* Toffoli schoolbook CQ multiplication dispatch (controlled and uncontrolled). */
    if (circ->arithmetic_mode == ARITH_TOFFOLI) {
        if (controlled) {
            toffoli_cmul_cq(circ, ret_qubits, ret_bits, self_qubits, self_bits, classical_value,
                            control_qubit);
        } else {
            toffoli_mul_cq(circ, ret_qubits, ret_bits, self_qubits, self_bits, classical_value);
        }
        return;
    }

    /* Build the qubit_array on the stack.
     * Layout (matches Cython multiplication_inplace for CQ path):
     *   [0 .. ret_bits-1]                        : ret qubits
     *   [ret_bits .. ret_bits+self_bits-1]        : self qubits
     *   if controlled: control_qubit, then ancilla
     *   else: ancilla
     */
    unsigned int qa[256];
    int pos = 0;
    int i;

    /* ret qubits at position 0 */
    for (i = 0; i < ret_bits; i++) {
        qa[pos++] = ret_qubits[i];
    }

    /* self qubits at position ret_bits */
    for (i = 0; i < self_bits; i++) {
        qa[pos++] = self_qubits[i];
    }

    /* control + ancilla */
    sequence_t *seq;
    if (controlled) {
        qa[pos++] = control_qubit;
        for (i = 0; i < num_ancilla; i++) {
            qa[pos++] = ancilla[i];
        }
        seq = cCQ_mul(ret_bits, classical_value);
    } else {
        for (i = 0; i < num_ancilla; i++) {
            qa[pos++] = ancilla[i];
        }
        seq = CQ_mul(ret_bits, classical_value);
    }

    /* NULL check -- caller (Cython) will raise if needed */
    if (seq == NULL) {
        return;
    }

    run_instruction(seq, qa, 0, circ);
}
