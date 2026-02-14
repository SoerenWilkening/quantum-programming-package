/**
 * @file hot_path_add.c
 * @brief C hot path for addition_inplace (Phase 60, Plan 03).
 *
 * Implements the core logic of addition_inplace entirely in C,
 * removing all Python/C boundary crossings from the inner path.
 *
 * The qubit layout built here MUST match the Cython addition_inplace
 * exactly (see qint_arithmetic.pxi).
 */

#include "hot_path_add.h"
#include "arithmetic_ops.h"
#include "execution.h"
#include "qubit_allocator.h"
#include "toffoli_arithmetic_ops.h"

void hot_path_add_qq(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                     const unsigned int *other_qubits, int other_bits, int invert, int controlled,
                     unsigned int control_qubit, const unsigned int *ancilla, int num_ancilla) {
    /* Build the qubit_array on the stack.
     * Layout (matches Cython addition_inplace for QQ path):
     *
     * Uncontrolled:
     *   [0 .. self_bits-1]           : self qubits (target)
     *   [self_bits .. +other_bits-1] : other qubits
     *   [start .. +num_ancilla-1]    : ancilla  (start = self_bits + other_bits)
     *
     * Controlled (cQQ_add):
     *   [0 .. self_bits-1]                : self qubits (target)
     *   [self_bits .. +other_bits-1]      : other qubits
     *   [2*result_bits]                   : control_qubit
     *   [2*result_bits+1 .. ]             : ancilla
     */
    unsigned int qa[256];
    int pos = 0;
    int i;
    int result_bits = self_bits > other_bits ? self_bits : other_bits;

    /* self qubits at position 0 */
    for (i = 0; i < self_bits; i++) {
        qa[pos++] = self_qubits[i];
    }

    /* other qubits at position self_bits */
    for (i = 0; i < other_bits; i++) {
        qa[pos++] = other_qubits[i];
    }

    /* Toffoli CDKM dispatch (uncontrolled only; controlled falls through to QFT) */
    if (circ->arithmetic_mode == ARITH_TOFFOLI && !controlled) {
        sequence_t *toff_seq;
        if (result_bits == 1) {
            /* 1-bit: no ancilla needed */
            toff_seq = toffoli_QQ_add(result_bits);
            if (toff_seq == NULL)
                return;
            run_instruction(toff_seq, qa, invert, circ);
        } else {
            /* n >= 2: allocate 1 ancilla qubit */
            qubit_t ancilla_qubit = allocator_alloc(circ->allocator, 1, true);
            if (ancilla_qubit == (qubit_t)-1)
                return; /* allocation failed */

            /* Ancilla at virtual index 2*result_bits (after both registers) */
            qa[2 * result_bits] = ancilla_qubit;

            toff_seq = toffoli_QQ_add(result_bits);
            if (toff_seq == NULL) {
                allocator_free(circ->allocator, ancilla_qubit, 1);
                return;
            }
            run_instruction(toff_seq, qa, invert, circ);

            /* Free ancilla (CDKM guarantees return to |0>) */
            allocator_free(circ->allocator, ancilla_qubit, 1);
        }
        return;
    }
    /* Toffoli mode with controlled: fall back to QFT path below */

    /* control + ancilla (QFT path) */
    sequence_t *seq;
    if (controlled) {
        /* Control qubit goes at position 2*result_bits (NOT at pos/start) */
        qa[2 * result_bits] = control_qubit;
        for (i = 0; i < num_ancilla; i++) {
            qa[2 * result_bits + 1 + i] = ancilla[i];
        }
        seq = cQQ_add(result_bits);
    } else {
        /* Ancilla goes right after other qubits */
        for (i = 0; i < num_ancilla; i++) {
            qa[pos + i] = ancilla[i];
        }
        seq = QQ_add(result_bits);
    }

    /* NULL check -- caller (Cython) will raise if needed */
    if (seq == NULL) {
        return;
    }

    run_instruction(seq, qa, invert, circ);
}

void hot_path_add_cq(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                     int64_t classical_value, int invert, int controlled,
                     unsigned int control_qubit, const unsigned int *ancilla, int num_ancilla) {
    /* Build the qubit_array on the stack.
     * Layout (matches Cython addition_inplace for CQ path):
     *
     * Uncontrolled:
     *   [0 .. self_bits-1]                     : self qubits (target)
     *   [self_bits .. self_bits+num_ancilla-1]  : ancilla
     *
     * Controlled (cCQ_add):
     *   [0 .. self_bits-1]         : self qubits (target)
     *   [self_bits]                : control_qubit
     *   [self_bits+1 .. ]          : ancilla
     */
    unsigned int qa[256];
    int pos = 0;
    int i;

    /* self qubits at position 0 */
    for (i = 0; i < self_bits; i++) {
        qa[pos++] = self_qubits[i];
    }

    /* Toffoli CDKM dispatch (uncontrolled only; controlled falls through to QFT) */
    if (circ->arithmetic_mode == ARITH_TOFFOLI && !controlled) {
        sequence_t *toff_seq;
        if (self_bits == 1) {
            /* 1-bit: no ancilla needed */
            toff_seq = toffoli_CQ_add(self_bits, classical_value);
            if (toff_seq == NULL)
                return;
            run_instruction(toff_seq, qa, invert, circ);
            toffoli_sequence_free(toff_seq); /* CQ sequences are not cached */
        } else {
            /* n >= 2: allocate 1 ancilla qubit */
            qubit_t ancilla_qubit = allocator_alloc(circ->allocator, 1, true);
            if (ancilla_qubit == (qubit_t)-1)
                return; /* allocation failed */

            /* Ancilla at virtual index self_bits (right after target register) */
            qa[self_bits] = ancilla_qubit;

            toff_seq = toffoli_CQ_add(self_bits, classical_value);
            if (toff_seq == NULL) {
                allocator_free(circ->allocator, ancilla_qubit, 1);
                return;
            }
            run_instruction(toff_seq, qa, invert, circ);
            toffoli_sequence_free(toff_seq); /* CQ sequences are not cached */

            /* Free ancilla (CDKM guarantees return to |0>) */
            allocator_free(circ->allocator, ancilla_qubit, 1);
        }
        return;
    }
    /* Toffoli mode with controlled: fall back to QFT path below */

    /* control + ancilla (QFT path) */
    sequence_t *seq;
    if (controlled) {
        qa[pos++] = control_qubit;
        for (i = 0; i < num_ancilla; i++) {
            qa[pos++] = ancilla[i];
        }
        seq = cCQ_add(self_bits, classical_value);
    } else {
        for (i = 0; i < num_ancilla; i++) {
            qa[pos++] = ancilla[i];
        }
        seq = CQ_add(self_bits, classical_value);
    }

    /* NULL check -- caller (Cython) will raise if needed */
    if (seq == NULL) {
        return;
    }

    run_instruction(seq, qa, invert, circ);
}
