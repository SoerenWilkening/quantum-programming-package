/**
 * @file hot_path_xor.c
 * @brief C hot path for __ixor__ / __xor__ (Phase 60, Plan 04).
 *
 * Implements the core logic of __ixor__ entirely in C,
 * removing all Python/C boundary crossings from the inner path.
 *
 * The qubit layout built here MUST match the Cython __ixor__
 * exactly (see qint_bitwise.pxi).
 */

#include "hot_path_xor.h"
#include "bitwise_ops.h"
#include "execution.h"

void hot_path_ixor_qq(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                      const unsigned int *other_qubits, int other_bits) {
    /* Build the qubit_array on the stack.
     * Layout (matches Cython __ixor__ for QQ path):
     *   [0 .. xor_bits-1]            : self qubits (target)
     *   [xor_bits .. 2*xor_bits-1]   : other qubits (source)
     *   where xor_bits = min(self_bits, other_bits)
     */
    unsigned int qa[256];
    int xor_bits = self_bits < other_bits ? self_bits : other_bits;
    int i;

    /* self qubits at position 0 */
    for (i = 0; i < xor_bits; i++) {
        qa[i] = self_qubits[i];
    }

    /* other qubits at position xor_bits */
    for (i = 0; i < xor_bits; i++) {
        qa[xor_bits + i] = other_qubits[i];
    }

    sequence_t *seq = Q_xor(xor_bits);

    /* NULL check -- caller (Cython) will raise if needed */
    if (seq == NULL) {
        return;
    }

    run_instruction(seq, qa, 0, circ, 0);
}

void hot_path_ixor_cq(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                      int64_t classical_value) {
    /* For each set bit in classical_value, apply Q_not(1) to the
     * corresponding self qubit.
     *
     * Layout per bit (matches Cython __ixor__ for CQ path):
     *   qubit_array[0] = self_qubits[bit_index]
     *   Then call Q_not(1) + run_instruction
     */
    unsigned int qa[1];
    int i;

    for (i = 0; i < self_bits; i++) {
        if ((classical_value >> i) & 1) {
            qa[0] = self_qubits[i];
            sequence_t *seq = Q_not(1);
            if (seq == NULL) {
                return;
            }
            run_instruction(seq, qa, 0, circ, 0);
        }
    }
}
