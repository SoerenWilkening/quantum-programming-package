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

    /* Toffoli CDKM dispatch (uncontrolled and controlled) */
    if (circ->arithmetic_mode == ARITH_TOFFOLI) {
        unsigned int tqa[256];
        sequence_t *toff_seq;

        if (controlled) {
            /* Controlled Toffoli QQ path */
            if (result_bits == 1) {
                /* 1-bit controlled: CCX(target=a[0], ctrl1=b[0], ctrl2=control)
                 * Layout: [0]=self(target), [1]=other(source), [2]=control
                 * For 1-bit XOR is symmetric so no swap needed */
                tqa[0] = self_qubits[0];
                tqa[1] = other_qubits[0];
                tqa[2] = control_qubit;

                toff_seq = toffoli_cQQ_add(result_bits);
                if (toff_seq == NULL)
                    return;
                run_instruction(toff_seq, tqa, invert, circ);
            } else {
                /* n >= 2: swap registers (same as uncontrolled Toffoli) + ancilla + control */
                /* a-register [0..bits-1] = other (source, preserved) */
                for (i = 0; i < other_bits; i++) {
                    tqa[i] = other_qubits[i];
                }
                /* b-register [bits..2*bits-1] = self (target, gets sum) */
                for (i = 0; i < self_bits; i++) {
                    tqa[result_bits + i] = self_qubits[i];
                }

                /* Controlled CLA dispatch: try CLA for width >= threshold.
                 * Same variant selection as uncontrolled path.
                 * Layout: [0..bits-1] a, [bits..2*bits-1] b,
                 *         [2*bits..] CLA ancilla, [after ancilla] ext_ctrl
                 */
#define CLA_THRESHOLD 4
                if (circ->cla_override == 0 && result_bits >= CLA_THRESHOLD) {
                    int cla_ancilla_count;
                    if (circ->qubit_saving) {
                        /* Brent-Kung: 2*(n-1) ancilla */
                        cla_ancilla_count = 2 * (result_bits - 1);
                    } else {
                        /* Kogge-Stone: ~n*ceil(log2(n)) ancilla */
                        int log_n = 0;
                        int tmp = result_bits;
                        while (tmp > 1) {
                            log_n++;
                            tmp = (tmp + 1) >> 1;
                        }
                        cla_ancilla_count = (result_bits - 1) + (result_bits - 1) * log_n;
                    }
                    qubit_t cla_ancilla = allocator_alloc(circ->allocator, cla_ancilla_count, true);
                    if (cla_ancilla != (qubit_t)-1) {
                        /* CLA ancilla at [2*bits..] */
                        for (i = 0; i < cla_ancilla_count; i++) {
                            tqa[2 * result_bits + i] = cla_ancilla + i;
                        }
                        /* ext_ctrl after CLA ancilla */
                        tqa[2 * result_bits + cla_ancilla_count] = control_qubit;

                        if (circ->qubit_saving) {
                            toff_seq = toffoli_cQQ_add_bk(result_bits);
                        } else {
                            toff_seq = toffoli_cQQ_add_ks(result_bits);
                        }
                        if (toff_seq != NULL) {
                            run_instruction(toff_seq, tqa, invert, circ);
                            allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count);
                            return;
                        }
                        /* CLA sequence failed -- fall through to controlled RCA */
                        allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count);
                    }
                    /* Silent fallback to controlled RCA */
                }
#undef CLA_THRESHOLD

                /* Controlled RCA (CDKM) path: 1 ancilla for carry */
                qubit_t ancilla_qubit = allocator_alloc(circ->allocator, 1, true);
                if (ancilla_qubit == (qubit_t)-1)
                    return;

                /* Ancilla at 2*result_bits, control at 2*result_bits+1 */
                tqa[2 * result_bits] = ancilla_qubit;
                tqa[2 * result_bits + 1] = control_qubit;

                toff_seq = toffoli_cQQ_add(result_bits);
                if (toff_seq == NULL) {
                    allocator_free(circ->allocator, ancilla_qubit, 1);
                    return;
                }
                run_instruction(toff_seq, tqa, invert, circ);
                allocator_free(circ->allocator, ancilla_qubit, 1);
            }
        } else {
            /*
             * Uncontrolled Toffoli QQ path:
             * CDKM adder layout:
             *   [0..bits-1]       = register a (source operand, preserved)
             *   [bits..2*bits-1]  = register b (target, receives a+b)
             *   [2*bits]          = ancilla carry (bits >= 2)
             *
             * Since self is the target (should receive the sum), we need:
             *   a-register (indices 0..bits-1) = other_qubits (source)
             *   b-register (indices bits..2*bits-1) = self_qubits (target)
             *
             * Build a swapped qubit array for the Toffoli path.
             */
            if (result_bits == 1) {
                /* 1-bit: CNOT(target=a[0], control=b[0]) -> a[0] ^= b[0]
                 * For 1-bit, CNOT is symmetric in terms of "a += b" since
                 * it's just XOR. self at [0], other at [1] works fine. */
                toff_seq = toffoli_QQ_add(result_bits);
                if (toff_seq == NULL)
                    return;
                run_instruction(toff_seq, qa, invert, circ);
            } else {
                /* n >= 2: swap register positions for adder */
                /* a-register [0..bits-1] = other (source, preserved) */
                for (i = 0; i < other_bits; i++) {
                    tqa[i] = other_qubits[i];
                }
                /* b-register [bits..2*bits-1] = self (target, gets sum) */
                for (i = 0; i < self_bits; i++) {
                    tqa[result_bits + i] = self_qubits[i];
                }

                /* CLA dispatch: use CLA for width >= threshold.
                 * Variant selection: qubit_saving=1 -> Brent-Kung (fewer ancilla),
                 *                    qubit_saving=0 -> Kogge-Stone (fewer depth levels).
                 */
#define CLA_THRESHOLD 4
                if (circ->cla_override == 0 && result_bits >= CLA_THRESHOLD) {
                    int cla_ancilla_count;
                    if (circ->qubit_saving) {
                        /* Brent-Kung: 2*(n-1) ancilla */
                        cla_ancilla_count = 2 * (result_bits - 1);
                    } else {
                        /* Kogge-Stone: ~n*ceil(log2(n)) ancilla (approximate) */
                        int log_n = 0;
                        int tmp = result_bits;
                        while (tmp > 1) {
                            log_n++;
                            tmp = (tmp + 1) >> 1;
                        }
                        /* n-1 generates + (n-1)*levels propagate products */
                        cla_ancilla_count = (result_bits - 1) + (result_bits - 1) * log_n;
                    }
                    qubit_t cla_ancilla = allocator_alloc(circ->allocator, cla_ancilla_count, true);
                    if (cla_ancilla != (qubit_t)-1) {
                        /* CLA ancilla at [2*bits..] */
                        for (i = 0; i < cla_ancilla_count; i++) {
                            tqa[2 * result_bits + i] = cla_ancilla + i;
                        }
                        if (circ->qubit_saving) {
                            toff_seq = toffoli_QQ_add_bk(result_bits);
                        } else {
                            toff_seq = toffoli_QQ_add_ks(result_bits);
                        }
                        if (toff_seq != NULL) {
                            run_instruction(toff_seq, tqa, invert, circ);
                            allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count);
                            return;
                        }
                        /* CLA sequence generation failed -- fall through to RCA */
                        allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count);
                    }
                    /* Silent fallback to RCA (ancilla allocation failed or sequence failed) */
                }
#undef CLA_THRESHOLD

                /* RCA (CDKM) path: 1 ancilla qubit */
                qubit_t ancilla_qubit = allocator_alloc(circ->allocator, 1, true);
                if (ancilla_qubit == (qubit_t)-1)
                    return; /* allocation failed */

                /* Ancilla at virtual index 2*result_bits (after both registers) */
                tqa[2 * result_bits] = ancilla_qubit;

                toff_seq = toffoli_QQ_add(result_bits);
                if (toff_seq == NULL) {
                    allocator_free(circ->allocator, ancilla_qubit, 1);
                    return;
                }
                run_instruction(toff_seq, tqa, invert, circ);

                /* Free ancilla (CDKM guarantees return to |0>) */
                allocator_free(circ->allocator, ancilla_qubit, 1);
            }
        }
        return;
    }

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

    /* Toffoli CDKM dispatch (uncontrolled and controlled) */
    if (circ->arithmetic_mode == ARITH_TOFFOLI) {
        sequence_t *toff_seq;

        if (controlled) {
            /* Controlled Toffoli CQ path */
            if (self_bits == 1) {
                /* 1-bit controlled CQ: CX(target=self[0], ctrl=control) if value&1 */
                unsigned int tqa[2];
                tqa[0] = self_qubits[0];
                tqa[1] = control_qubit;
                toff_seq = toffoli_cCQ_add(self_bits, classical_value);
                if (toff_seq == NULL)
                    return;
                run_instruction(toff_seq, tqa, invert, circ);
                toffoli_sequence_free(toff_seq);
            } else {
                /* Controlled CQ CLA dispatch: try CLA for width >= threshold.
                 * Layout: [0..bits-1] temp, [bits..2*bits-1] self,
                 *         [2*bits..] CLA ancilla, [after ancilla] ext_ctrl
                 * Total allocation: bits (temp) + CLA ancilla count
                 */
#define CLA_THRESHOLD 4
                if (circ->cla_override == 0 && self_bits >= CLA_THRESHOLD) {
                    int cla_ancilla_count;
                    if (circ->qubit_saving) {
                        /* Brent-Kung: 2*(n-1) CLA ancilla */
                        cla_ancilla_count = 2 * (self_bits - 1);
                    } else {
                        /* Kogge-Stone: ~n*ceil(log2(n)) CLA ancilla */
                        int log_n = 0;
                        int tmp = self_bits;
                        while (tmp > 1) {
                            log_n++;
                            tmp = (tmp + 1) >> 1;
                        }
                        cla_ancilla_count = (self_bits - 1) + (self_bits - 1) * log_n;
                    }
                    int total_cla_ancilla = self_bits + cla_ancilla_count;
                    qubit_t cla_start = allocator_alloc(circ->allocator, total_cla_ancilla, true);
                    if (cla_start != (qubit_t)-1) {
                        unsigned int cla_qa[256];
                        /* [0..self_bits-1] = temp (from allocated block) */
                        for (i = 0; i < self_bits; i++) {
                            cla_qa[i] = cla_start + i;
                        }
                        /* [self_bits..2*self_bits-1] = self qubits (target) */
                        for (i = 0; i < self_bits; i++) {
                            cla_qa[self_bits + i] = self_qubits[i];
                        }
                        /* [2*self_bits..] = CLA ancilla (after temp) */
                        for (i = 0; i < cla_ancilla_count; i++) {
                            cla_qa[2 * self_bits + i] = cla_start + self_bits + i;
                        }
                        /* ext_ctrl after CLA ancilla */
                        cla_qa[2 * self_bits + cla_ancilla_count] = control_qubit;

                        if (circ->qubit_saving) {
                            toff_seq = toffoli_cCQ_add_bk(self_bits, classical_value);
                        } else {
                            toff_seq = toffoli_cCQ_add_ks(self_bits, classical_value);
                        }
                        if (toff_seq != NULL) {
                            run_instruction(toff_seq, cla_qa, invert, circ);
                            toffoli_sequence_free(toff_seq);
                            allocator_free(circ->allocator, cla_start, total_cla_ancilla);
                            goto ccq_toffoli_done;
                        }
                        /* CLA CQ failed -- fall through to controlled RCA CQ */
                        allocator_free(circ->allocator, cla_start, total_cla_ancilla);
                    }
                    /* Silent fallback to controlled RCA CQ */
                }
#undef CLA_THRESHOLD

                {
                    /* n >= 2: controlled RCA (CDKM) CQ path:
                     * self_bits + 1 ancilla (temp + carry) */
                    qubit_t temp_start = allocator_alloc(circ->allocator, self_bits + 1, true);
                    if (temp_start == (qubit_t)-1)
                        return;

                    unsigned int tqa[256];
                    /* [0..self_bits-1] = temp ancilla qubits */
                    for (i = 0; i < self_bits; i++) {
                        tqa[i] = temp_start + i;
                    }
                    /* [self_bits..2*self_bits-1] = self qubits (target) */
                    for (i = 0; i < self_bits; i++) {
                        tqa[self_bits + i] = self_qubits[i];
                    }
                    /* [2*self_bits] = carry ancilla */
                    tqa[2 * self_bits] = temp_start + self_bits;
                    /* [2*self_bits+1] = external control */
                    tqa[2 * self_bits + 1] = control_qubit;

                    toff_seq = toffoli_cCQ_add(self_bits, classical_value);
                    if (toff_seq == NULL) {
                        allocator_free(circ->allocator, temp_start, self_bits + 1);
                        return;
                    }
                    run_instruction(toff_seq, tqa, invert, circ);
                    toffoli_sequence_free(toff_seq);
                    allocator_free(circ->allocator, temp_start, self_bits + 1);
                }
            ccq_toffoli_done:;
            }
        } else {
            /* Uncontrolled Toffoli CQ path */
            if (self_bits == 1) {
                /* 1-bit: no ancilla needed */
                toff_seq = toffoli_CQ_add(self_bits, classical_value);
                if (toff_seq == NULL)
                    return;
                run_instruction(toff_seq, qa, invert, circ);
                toffoli_sequence_free(toff_seq); /* CQ sequences are not cached */
            } else {
                /* CQ CLA dispatch: try CLA for width >= threshold.
                 * CQ CLA uses temp-register approach internally:
                 *   [0..bits-1]       = temp (from allocated block)
                 *   [bits..2*bits-1]  = self (target)
                 *   [2*bits..]        = CLA ancilla
                 * Total allocation: bits (temp) + CLA ancilla count
                 */
#define CLA_THRESHOLD 4
                if (circ->cla_override == 0 && self_bits >= CLA_THRESHOLD) {
                    int cla_ancilla_count;
                    if (circ->qubit_saving) {
                        /* Brent-Kung: 2*(n-1) CLA ancilla */
                        cla_ancilla_count = 2 * (self_bits - 1);
                    } else {
                        /* Kogge-Stone: ~n*ceil(log2(n)) CLA ancilla */
                        int log_n = 0;
                        int tmp = self_bits;
                        while (tmp > 1) {
                            log_n++;
                            tmp = (tmp + 1) >> 1;
                        }
                        cla_ancilla_count = (self_bits - 1) + (self_bits - 1) * log_n;
                    }
                    /* Total: self_bits (temp) + cla_ancilla_count */
                    int total_ancilla = self_bits + cla_ancilla_count;
                    qubit_t cq_cla_ancilla = allocator_alloc(circ->allocator, total_ancilla, true);
                    if (cq_cla_ancilla != (qubit_t)-1) {
                        unsigned int tqa[256];
                        /* [0..self_bits-1] = temp ancilla (from allocated block) */
                        for (i = 0; i < self_bits; i++) {
                            tqa[i] = cq_cla_ancilla + i;
                        }
                        /* [self_bits..2*self_bits-1] = self qubits (target) */
                        for (i = 0; i < self_bits; i++) {
                            tqa[self_bits + i] = self_qubits[i];
                        }
                        /* [2*self_bits..] = CLA ancilla (after temp) */
                        for (i = 0; i < cla_ancilla_count; i++) {
                            tqa[2 * self_bits + i] = cq_cla_ancilla + self_bits + i;
                        }
                        if (circ->qubit_saving) {
                            toff_seq = toffoli_CQ_add_bk(self_bits, classical_value);
                        } else {
                            toff_seq = toffoli_CQ_add_ks(self_bits, classical_value);
                        }
                        if (toff_seq != NULL) {
                            run_instruction(toff_seq, tqa, invert, circ);
                            toffoli_sequence_free(toff_seq);
                            allocator_free(circ->allocator, cq_cla_ancilla, total_ancilla);
                            goto cq_toffoli_done;
                        }
                        /* CLA CQ failed -- fall through to RCA CQ */
                        allocator_free(circ->allocator, cq_cla_ancilla, total_ancilla);
                    }
                    /* Silent fallback to RCA CQ */
                }
#undef CLA_THRESHOLD

                /* RCA (CDKM) CQ path: self_bits + 1 ancilla
                 * (self_bits for temp register + 1 for carry)
                 *
                 * toffoli_CQ_add layout:
                 *   [0..self_bits-1]       = temp register (ancilla, initialized to classical
                 * value) [self_bits..2*self_bits-1] = self register (target, gets sum)
                 *   [2*self_bits]          = carry ancilla
                 */
                qubit_t temp_start = allocator_alloc(circ->allocator, self_bits + 1, true);
                if (temp_start == (qubit_t)-1)
                    return; /* allocation failed */

                {
                    unsigned int tqa[256];
                    /* [0..self_bits-1] = temp ancilla qubits */
                    for (i = 0; i < self_bits; i++) {
                        tqa[i] = temp_start + i;
                    }
                    /* [self_bits..2*self_bits-1] = self qubits (target, gets sum) */
                    for (i = 0; i < self_bits; i++) {
                        tqa[self_bits + i] = self_qubits[i];
                    }
                    /* [2*self_bits] = carry ancilla */
                    tqa[2 * self_bits] = temp_start + self_bits;

                    toff_seq = toffoli_CQ_add(self_bits, classical_value);
                    if (toff_seq == NULL) {
                        allocator_free(circ->allocator, temp_start, self_bits + 1);
                        return;
                    }
                    run_instruction(toff_seq, tqa, invert, circ);
                    toffoli_sequence_free(toff_seq); /* CQ sequences are not cached */

                    /* Free all ancilla (CDKM guarantees return to |0>) */
                    allocator_free(circ->allocator, temp_start, self_bits + 1);
                } /* end RCA CQ block scope */
            }
        }
    cq_toffoli_done:
        return;
    }

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
