/**
 * @file hot_path_add_toffoli.c
 * @brief Toffoli-specific CLA/RCA dispatch logic for addition.
 *
 * Extracted from hot_path_add.c (Phase 74) to separate Toffoli dispatch
 * (CLA threshold, BK/KS variant selection, RCA fallback) from the
 * QFT addition path.
 *
 * Two dispatch functions:
 *   toffoli_dispatch_qq  -- Toffoli QQ addition (CLA + RCA, controlled + uncontrolled)
 *   toffoli_dispatch_cq  -- Toffoli CQ addition (CLA + RCA, controlled + uncontrolled)
 *
 * Phase 74: Extracted during hot_path_add.c refactoring.
 */

#include "execution.h"
#include "hot_path_add.h"
#include "qubit_allocator.h"
#include "toffoli_arithmetic_ops.h"

/* CLA is used for widths >= this threshold */
#define CLA_THRESHOLD 2

/**
 * @brief Compute Kogge-Stone CLA ancilla count.
 *
 * @param bits Width of operands
 * @return Number of CLA ancilla qubits for KS variant
 */
static int ks_cla_ancilla_estimate(int bits) {
    int log_n = 0;
    int tmp = bits;
    while (tmp > 1) {
        log_n++;
        tmp = (tmp + 1) >> 1;
    }
    return (bits - 1) + (bits - 1) * log_n;
}

/**
 * @brief Compute CLA ancilla count based on variant selection.
 *
 * @param circ Circuit (qubit_saving field selects BK vs KS)
 * @param bits Width of operands
 * @return Number of CLA ancilla qubits
 */
static int compute_cla_ancilla_count(circuit_t *circ, int bits) {
    if (circ->qubit_saving) {
        return bk_cla_ancilla_count(bits);
    } else {
        return ks_cla_ancilla_estimate(bits);
    }
}

/* ============================================================================
 * Toffoli QQ dispatch (uncontrolled + controlled)
 * ============================================================================ */

/**
 * @brief Uncontrolled Toffoli QQ addition: try CLA, fallback to RCA.
 *
 * Handles CLA dispatch (forward-only, BK/KS variant selection) with
 * silent fallback to RCA (CDKM) if CLA fails.
 */
static void toffoli_qq_uncont(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                              const unsigned int *other_qubits, int other_bits, int invert,
                              const unsigned int *qa, int result_bits) {
    unsigned int tqa[256];
    sequence_t *toff_seq;
    int i;

    if (result_bits == 1) {
        /* 1-bit: CNOT, symmetric XOR. Use original qubit array directly. */
        toff_seq = toffoli_QQ_add(result_bits);
        if (toff_seq == NULL)
            return;
        run_instruction(toff_seq, qa, invert, circ);
        return;
    }

    /* n >= 2: swap register positions for CDKM adder layout */
    /* a-register [0..bits-1] = other (source, preserved) */
    for (i = 0; i < other_bits; i++) {
        tqa[i] = other_qubits[i];
    }
    /* b-register [bits..2*bits-1] = self (target, gets sum) */
    for (i = 0; i < self_bits; i++) {
        tqa[result_bits + i] = self_qubits[i];
    }

    /* CLA dispatch: forward only (BK CLA carry-copy not fully uncomputed).
     * Subtraction (invert=1) falls through to RCA. */
    if (!invert && circ->cla_override == 0 && result_bits >= CLA_THRESHOLD) {
        int cla_ancilla_count = compute_cla_ancilla_count(circ, result_bits);
        qubit_t cla_ancilla = allocator_alloc(circ->allocator, cla_ancilla_count, true);
        if (cla_ancilla != (qubit_t)-1) {
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
            /* CLA sequence failed -- fall through to RCA */
            allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count);
        }
        /* Silent fallback to RCA */
    }

    /* RCA (CDKM) path: 1 ancilla qubit */
    qubit_t ancilla_qubit = allocator_alloc(circ->allocator, 1, true);
    if (ancilla_qubit == (qubit_t)-1)
        return;

    tqa[2 * result_bits] = ancilla_qubit;

    toff_seq = toffoli_QQ_add(result_bits);
    if (toff_seq == NULL) {
        allocator_free(circ->allocator, ancilla_qubit, 1);
        return;
    }
    run_instruction(toff_seq, tqa, invert, circ);
    allocator_free(circ->allocator, ancilla_qubit, 1);
}

/**
 * @brief Controlled Toffoli QQ addition: try CLA, fallback to RCA.
 */
static void toffoli_qq_cont(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                            const unsigned int *other_qubits, int other_bits, int invert,
                            unsigned int control_qubit, int result_bits) {
    unsigned int tqa[256];
    sequence_t *toff_seq;
    int i;

    if (result_bits == 1) {
        /* 1-bit controlled: CCX(target=a[0], ctrl1=b[0], ctrl2=control) */
        tqa[0] = self_qubits[0];
        tqa[1] = other_qubits[0];
        tqa[2] = control_qubit;

        toff_seq = toffoli_cQQ_add(result_bits);
        if (toff_seq == NULL)
            return;
        run_instruction(toff_seq, tqa, invert, circ);
        return;
    }

    /* n >= 2: swap registers + ancilla + control */
    for (i = 0; i < other_bits; i++) {
        tqa[i] = other_qubits[i];
    }
    for (i = 0; i < self_bits; i++) {
        tqa[result_bits + i] = self_qubits[i];
    }

    /* Controlled CLA dispatch: forward only */
    if (!invert && circ->cla_override == 0 && result_bits >= CLA_THRESHOLD) {
        int cla_ancilla_count = compute_cla_ancilla_count(circ, result_bits);
        qubit_t cla_ancilla = allocator_alloc(circ->allocator, cla_ancilla_count, true);
        if (cla_ancilla != (qubit_t)-1) {
            for (i = 0; i < cla_ancilla_count; i++) {
                tqa[2 * result_bits + i] = cla_ancilla + i;
            }
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
            allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count);
        }
    }

    /* Controlled RCA (CDKM) path: 1 ancilla for carry */
    qubit_t ancilla_qubit = allocator_alloc(circ->allocator, 1, true);
    if (ancilla_qubit == (qubit_t)-1)
        return;

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

/**
 * @brief Toffoli QQ dispatch: routes to uncontrolled or controlled path.
 *
 * Called from hot_path_add_qq when arithmetic_mode == ARITH_TOFFOLI.
 *
 * @param circ          Active circuit
 * @param self_qubits   Array of self qubit indices
 * @param self_bits     Width of self register
 * @param other_qubits  Array of other qubit indices
 * @param other_bits    Width of other register
 * @param invert        Non-zero for subtraction
 * @param controlled    Non-zero if controlled operation
 * @param control_qubit Control qubit index (ignored if !controlled)
 * @param qa            Pre-built qubit array with self+other layout
 * @param result_bits   max(self_bits, other_bits)
 */
void toffoli_dispatch_qq(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                         const unsigned int *other_qubits, int other_bits, int invert,
                         int controlled, unsigned int control_qubit, const unsigned int *qa,
                         int result_bits) {
    if (controlled) {
        toffoli_qq_cont(circ, self_qubits, self_bits, other_qubits, other_bits, invert,
                        control_qubit, result_bits);
    } else {
        toffoli_qq_uncont(circ, self_qubits, self_bits, other_qubits, other_bits, invert, qa,
                          result_bits);
    }
}

/* ============================================================================
 * Toffoli CQ dispatch (uncontrolled + controlled)
 * ============================================================================ */

/**
 * @brief Uncontrolled Toffoli CQ addition: try CLA, fallback to RCA.
 */
static void toffoli_cq_uncont(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                              int64_t classical_value, int invert, const unsigned int *qa) {
    sequence_t *toff_seq;
    int i;

    if (self_bits == 1) {
        /* 1-bit: no ancilla needed */
        toff_seq = toffoli_CQ_add(self_bits, classical_value);
        if (toff_seq == NULL)
            return;
        run_instruction(toff_seq, qa, invert, circ);
        toffoli_sequence_free(toff_seq);
        return;
    }

    /* CQ CLA dispatch: forward only */
    if (!invert && circ->cla_override == 0 && self_bits >= CLA_THRESHOLD) {
        int cla_ancilla_count = compute_cla_ancilla_count(circ, self_bits);
        int total_ancilla = self_bits + cla_ancilla_count;
        qubit_t cq_cla_ancilla = allocator_alloc(circ->allocator, total_ancilla, true);
        if (cq_cla_ancilla != (qubit_t)-1) {
            unsigned int tqa[256];
            for (i = 0; i < self_bits; i++) {
                tqa[i] = cq_cla_ancilla + i;
            }
            for (i = 0; i < self_bits; i++) {
                tqa[self_bits + i] = self_qubits[i];
            }
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
                return;
            }
            allocator_free(circ->allocator, cq_cla_ancilla, total_ancilla);
        }
    }

    /* RCA (CDKM) CQ path: self_bits + 1 ancilla */
    qubit_t temp_start = allocator_alloc(circ->allocator, self_bits + 1, true);
    if (temp_start == (qubit_t)-1)
        return;

    {
        unsigned int tqa[256];
        for (i = 0; i < self_bits; i++) {
            tqa[i] = temp_start + i;
        }
        for (i = 0; i < self_bits; i++) {
            tqa[self_bits + i] = self_qubits[i];
        }
        tqa[2 * self_bits] = temp_start + self_bits;

        toff_seq = toffoli_CQ_add(self_bits, classical_value);
        if (toff_seq == NULL) {
            allocator_free(circ->allocator, temp_start, self_bits + 1);
            return;
        }
        run_instruction(toff_seq, tqa, invert, circ);
        toffoli_sequence_free(toff_seq);
        allocator_free(circ->allocator, temp_start, self_bits + 1);
    }
}

/**
 * @brief Controlled Toffoli CQ addition: try CLA, fallback to RCA.
 */
static void toffoli_cq_cont(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                            int64_t classical_value, int invert, unsigned int control_qubit) {
    sequence_t *toff_seq;
    int i;

    if (self_bits == 1) {
        unsigned int tqa[2];
        tqa[0] = self_qubits[0];
        tqa[1] = control_qubit;
        toff_seq = toffoli_cCQ_add(self_bits, classical_value);
        if (toff_seq == NULL)
            return;
        run_instruction(toff_seq, tqa, invert, circ);
        toffoli_sequence_free(toff_seq);
        return;
    }

    /* Controlled CQ CLA dispatch: forward only */
    if (!invert && circ->cla_override == 0 && self_bits >= CLA_THRESHOLD) {
        int cla_ancilla_count = compute_cla_ancilla_count(circ, self_bits);
        int total_cla_ancilla = self_bits + cla_ancilla_count;
        qubit_t cla_start = allocator_alloc(circ->allocator, total_cla_ancilla, true);
        if (cla_start != (qubit_t)-1) {
            unsigned int cla_qa[256];
            for (i = 0; i < self_bits; i++) {
                cla_qa[i] = cla_start + i;
            }
            for (i = 0; i < self_bits; i++) {
                cla_qa[self_bits + i] = self_qubits[i];
            }
            for (i = 0; i < cla_ancilla_count; i++) {
                cla_qa[2 * self_bits + i] = cla_start + self_bits + i;
            }
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
                return;
            }
            allocator_free(circ->allocator, cla_start, total_cla_ancilla);
        }
    }

    /* Controlled RCA (CDKM) CQ path: self_bits + 1 ancilla */
    {
        qubit_t temp_start = allocator_alloc(circ->allocator, self_bits + 1, true);
        if (temp_start == (qubit_t)-1)
            return;

        unsigned int tqa[256];
        for (i = 0; i < self_bits; i++) {
            tqa[i] = temp_start + i;
        }
        for (i = 0; i < self_bits; i++) {
            tqa[self_bits + i] = self_qubits[i];
        }
        tqa[2 * self_bits] = temp_start + self_bits;
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
}

/**
 * @brief Toffoli CQ dispatch: routes to uncontrolled or controlled path.
 *
 * Called from hot_path_add_cq when arithmetic_mode == ARITH_TOFFOLI.
 *
 * @param circ            Active circuit
 * @param self_qubits     Array of self qubit indices
 * @param self_bits       Width of self register
 * @param classical_value Classical integer value to add
 * @param invert          Non-zero for subtraction
 * @param controlled      Non-zero if controlled operation
 * @param control_qubit   Control qubit index (ignored if !controlled)
 * @param qa              Pre-built qubit array with self layout
 */
void toffoli_dispatch_cq(circuit_t *circ, const unsigned int *self_qubits, int self_bits,
                         int64_t classical_value, int invert, int controlled,
                         unsigned int control_qubit, const unsigned int *qa) {
    if (controlled) {
        toffoli_cq_cont(circ, self_qubits, self_bits, classical_value, invert, control_qubit);
    } else {
        toffoli_cq_uncont(circ, self_qubits, self_bits, classical_value, invert, qa);
    }
}
