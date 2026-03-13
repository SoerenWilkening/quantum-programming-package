/**
 * @file hot_path_add_toffoli.c
 * @brief Toffoli-specific CLA/RCA dispatch logic for addition and subtraction.
 *
 * Extracted from hot_path_add.c (Phase 74) to separate Toffoli dispatch
 * (CLA threshold, BK/KS variant selection, RCA fallback) from the
 * QFT addition path.
 *
 * Two dispatch functions:
 *   toffoli_dispatch_qq  -- Toffoli QQ addition (CLA + RCA, controlled + uncontrolled)
 *   toffoli_dispatch_cq  -- Toffoli CQ addition (CLA + RCA, controlled + uncontrolled)
 *
 * CLA subtraction limitation (Phase 93):
 *   The Brent-Kung CLA adder's carry-copy ancilla are not properly uncomputed
 *   when the sequence runs in reverse (invert=1). Therefore, direct CLA
 *   subtraction is not supported. In min_depth mode (tradeoff_min_depth=1),
 *   subtraction is implemented via two's complement:
 *     QQ: a -= b  ===  X(b) + CLA(a += b) + CQ(a += 1) + X(b)
 *     CQ: a -= v  ===  CLA(a += (2^width - v))
 *   This achieves O(log n) depth for subtraction at the cost of additional
 *   gates for the X-gate negation and +1 increment.
 *
 * Phase 74: Extracted during hot_path_add.c refactoring.
 */

#include "execution.h"
#include "hot_path_add.h"
#include "qubit_allocator.h"
#include "toffoli_addition_internal.h"
#include "toffoli_arithmetic_ops.h"
#include "toffoli_sequences.h"

/* CLA is used for widths >= this threshold */
#define CLA_THRESHOLD 2

// ============================================================================
// Clifford+T sequence caches (Phase 75)
// First call: dispatch returns static const pointer -> store in array
// Subsequent calls: direct array lookup (O(1))
// ============================================================================
static const sequence_t *precompiled_toffoli_clifft_QQ_add[9] = {0};
static const sequence_t *precompiled_toffoli_clifft_cQQ_add[9] = {0};
static const sequence_t *precompiled_toffoli_clifft_CQ_inc[9] = {0};
static const sequence_t *precompiled_toffoli_clifft_cCQ_inc[9] = {0};
static const sequence_t *precompiled_toffoli_clifft_cla_QQ_add[9] = {0};
static const sequence_t *precompiled_toffoli_clifft_cla_cQQ_add[9] = {0};
static const sequence_t *precompiled_toffoli_clifft_cla_CQ_inc[9] = {0};
static const sequence_t *precompiled_toffoli_clifft_cla_cCQ_inc[9] = {0};

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
        /* 1-bit: CNOT, symmetric XOR. Use original qubit array directly.
         * Phase 75: Clifford+T 1-bit QQ is also just a CX, same sequence. */
        toff_seq = toffoli_QQ_add(result_bits);
        if (toff_seq == NULL)
            return;
        run_instruction(toff_seq, qa, invert, circ, 0);
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

    /* Phase 75: Clifford+T hardcoded dispatch (toffoli_decompose=1, widths 1-8).
     * Same qubit layout as non-decomposed -- CCX expansion only adds gates, not qubits. */
    if (circ->toffoli_decompose && result_bits <= TOFFOLI_HARDCODED_MAX_WIDTH) {
        /* CLA Clifford+T path (forward only) */
        if (!invert && circ->cla_override == 0 && result_bits >= circ->tradeoff_auto_threshold) {
            int cla_ancilla_count = compute_cla_ancilla_count(circ, result_bits);
            qubit_t cla_ancilla = allocator_alloc(circ->allocator, cla_ancilla_count, true);
            if (cla_ancilla != (qubit_t)-1) {
                for (i = 0; i < cla_ancilla_count; i++) {
                    tqa[2 * result_bits + i] = cla_ancilla + i;
                }
                const sequence_t *seq = precompiled_toffoli_clifft_cla_QQ_add[result_bits];
                if (!seq) {
                    seq = get_hardcoded_toffoli_clifft_cla_QQ_add(result_bits);
                    precompiled_toffoli_clifft_cla_QQ_add[result_bits] = seq;
                }
                if (seq) {
                    run_instruction((sequence_t *)seq, tqa, invert, circ, 0);
                    allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count);
                    return;
                }
                allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count);
            }
        }
        /* RCA Clifford+T path */
        qubit_t ct_ancilla = allocator_alloc(circ->allocator, 1, true);
        if (ct_ancilla != (qubit_t)-1) {
            tqa[2 * result_bits] = ct_ancilla;
            const sequence_t *seq = precompiled_toffoli_clifft_QQ_add[result_bits];
            if (!seq) {
                seq = get_hardcoded_toffoli_clifft_QQ_add(result_bits);
                precompiled_toffoli_clifft_QQ_add[result_bits] = seq;
            }
            if (seq) {
                run_instruction((sequence_t *)seq, tqa, invert, circ, 0);
                allocator_free(circ->allocator, ct_ancilla, 1);
                return;
            }
            allocator_free(circ->allocator, ct_ancilla, 1);
        }
        /* Clifford+T dispatch returned NULL -- fall through to non-decomposed */
    }

    /* Phase 93: Two's complement CLA subtraction for min_depth mode.
     * a -= b  ===  X(b) + CLA(a += b) + CQ(a += 1) + X(b)
     * This enables O(log n) depth subtraction using CLA instead of O(n) RCA. */
    if (invert && circ->tradeoff_min_depth && circ->cla_override == 0 &&
        result_bits >= circ->tradeoff_auto_threshold) {
        int cla_ancilla_count = compute_cla_ancilla_count(circ, result_bits);
        qubit_t cla_ancilla = allocator_alloc(circ->allocator, cla_ancilla_count, true);
        if (cla_ancilla != (qubit_t)-1) {
            /* Step 1: X-gate each bit of other (one's complement negation) */
            for (i = 0; i < other_bits; i++) {
                gate_t xg;
                memset(&xg, 0, sizeof(gate_t));
                x(&xg, other_qubits[i]);
                add_gate(circ, &xg);
            }

            /* Step 2: CLA forward addition a += ~b */
            for (i = 0; i < cla_ancilla_count; i++) {
                tqa[2 * result_bits + i] = cla_ancilla + i;
            }
            if (circ->qubit_saving) {
                toff_seq = toffoli_QQ_add_bk(result_bits);
            } else {
                toff_seq = toffoli_QQ_add_ks(result_bits);
            }
            if (toff_seq != NULL) {
                run_instruction(toff_seq, tqa, 0, circ, 0); /* invert=0: forward */
                allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count);

                /* Step 3: CQ increment a += 1 (two's complement correction) */
                qubit_t inc_ancilla = allocator_alloc(circ->allocator, self_bits + 1, true);
                if (inc_ancilla != (qubit_t)-1) {
                    unsigned int inc_qa[256];
                    for (i = 0; i < self_bits; i++) {
                        inc_qa[i] = inc_ancilla + i;
                    }
                    for (i = 0; i < self_bits; i++) {
                        inc_qa[self_bits + i] = self_qubits[i];
                    }
                    inc_qa[2 * self_bits] = inc_ancilla + self_bits;
                    sequence_t *inc_seq = toffoli_CQ_add(self_bits, 1);
                    if (inc_seq != NULL) {
                        run_instruction(inc_seq, inc_qa, 0, circ, 0);
                        toffoli_sequence_free(inc_seq);
                    }
                    allocator_free(circ->allocator, inc_ancilla, self_bits + 1);
                }

                /* Step 4: Restore other register via X gates */
                for (i = 0; i < other_bits; i++) {
                    gate_t xg;
                    memset(&xg, 0, sizeof(gate_t));
                    x(&xg, other_qubits[i]);
                    add_gate(circ, &xg);
                }
                return;
            }
            /* CLA failed -- undo X gates and fall through to RCA */
            allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count);
            for (i = 0; i < other_bits; i++) {
                gate_t xg;
                memset(&xg, 0, sizeof(gate_t));
                x(&xg, other_qubits[i]);
                add_gate(circ, &xg);
            }
        }
    }

    /* CLA dispatch: forward only (BK CLA carry-copy not fully uncomputed).
     * Subtraction (invert=1) falls through to RCA. */
    if (!invert && circ->cla_override == 0 && result_bits >= circ->tradeoff_auto_threshold) {
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
                run_instruction(toff_seq, tqa, invert, circ, 0);
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
    run_instruction(toff_seq, tqa, invert, circ, 0);
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
        /* 1-bit controlled: CCX(target=a[0], ctrl1=b[0], ctrl2=control).
         * Phase 75: Clifford+T 1-bit cQQ is H+T+Tdg+CX sequence. */
        tqa[0] = self_qubits[0];
        tqa[1] = other_qubits[0];
        tqa[2] = control_qubit;

        if (circ->toffoli_decompose) {
            const sequence_t *seq = precompiled_toffoli_clifft_cQQ_add[1];
            if (!seq) {
                seq = get_hardcoded_toffoli_clifft_cQQ_add(1);
                precompiled_toffoli_clifft_cQQ_add[1] = seq;
            }
            if (seq) {
                run_instruction((sequence_t *)seq, tqa, invert, circ, 0);
                return;
            }
        }

        toff_seq = toffoli_cQQ_add(result_bits);
        if (toff_seq == NULL)
            return;
        run_instruction(toff_seq, tqa, invert, circ, 0);
        return;
    }

    /* n >= 2: swap registers + ancilla + control */
    for (i = 0; i < other_bits; i++) {
        tqa[i] = other_qubits[i];
    }
    for (i = 0; i < self_bits; i++) {
        tqa[result_bits + i] = self_qubits[i];
    }

    /* Phase 75: Clifford+T hardcoded dispatch for controlled QQ.
     * Same qubit layout as non-decomposed (CCX expansion only adds gates, not qubits). */
    if (circ->toffoli_decompose && result_bits <= TOFFOLI_HARDCODED_MAX_WIDTH) {
        /* Controlled CLA Clifford+T path (forward only) */
        if (!invert && circ->cla_override == 0 && result_bits >= circ->tradeoff_auto_threshold) {
            int cla_ancilla_count = compute_cla_ancilla_count(circ, result_bits);
            /* CLA ancilla + 1 AND-ancilla (same layout as non-decomposed controlled CLA) */
            qubit_t cla_ancilla = allocator_alloc(circ->allocator, cla_ancilla_count + 1, true);
            if (cla_ancilla != (qubit_t)-1) {
                for (i = 0; i < cla_ancilla_count; i++) {
                    tqa[2 * result_bits + i] = cla_ancilla + i;
                }
                tqa[2 * result_bits + cla_ancilla_count] = control_qubit;
                tqa[2 * result_bits + cla_ancilla_count + 1] = cla_ancilla + cla_ancilla_count;

                const sequence_t *seq = precompiled_toffoli_clifft_cla_cQQ_add[result_bits];
                if (!seq) {
                    seq = get_hardcoded_toffoli_clifft_cla_cQQ_add(result_bits);
                    precompiled_toffoli_clifft_cla_cQQ_add[result_bits] = seq;
                }
                if (seq) {
                    run_instruction((sequence_t *)seq, tqa, invert, circ, 0);
                    allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count + 1);
                    return;
                }
                allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count + 1);
            }
        }
        /* Controlled RCA Clifford+T path */
        qubit_t ct_ancilla = allocator_alloc(circ->allocator, 2, true);
        if (ct_ancilla != (qubit_t)-1) {
            tqa[2 * result_bits] = ct_ancilla;         /* carry ancilla */
            tqa[2 * result_bits + 1] = control_qubit;  /* ext_ctrl */
            tqa[2 * result_bits + 2] = ct_ancilla + 1; /* AND-ancilla */

            const sequence_t *seq = precompiled_toffoli_clifft_cQQ_add[result_bits];
            if (!seq) {
                seq = get_hardcoded_toffoli_clifft_cQQ_add(result_bits);
                precompiled_toffoli_clifft_cQQ_add[result_bits] = seq;
            }
            if (seq) {
                run_instruction((sequence_t *)seq, tqa, invert, circ, 0);
                allocator_free(circ->allocator, ct_ancilla, 2);
                return;
            }
            allocator_free(circ->allocator, ct_ancilla, 2);
        }
        /* Clifford+T dispatch returned NULL -- fall through to non-decomposed */
    }

    /* Phase 93: Controlled two's complement CLA subtraction for min_depth mode.
     * ctrl: a -= b  ===  CX(ctrl,b) + cCLA(ctrl: a += b) + cCQ(ctrl: a += 1) + CX(ctrl,b) */
    if (invert && circ->tradeoff_min_depth && circ->cla_override == 0 &&
        result_bits >= circ->tradeoff_auto_threshold) {
        int cla_ancilla_count = compute_cla_ancilla_count(circ, result_bits);
        qubit_t cla_ancilla = allocator_alloc(circ->allocator, cla_ancilla_count + 1, true);
        if (cla_ancilla != (qubit_t)-1) {
            /* Step 1: Controlled X-gate each bit of other */
            for (i = 0; i < other_bits; i++) {
                gate_t cxg;
                memset(&cxg, 0, sizeof(gate_t));
                cx(&cxg, other_qubits[i], control_qubit);
                add_gate(circ, &cxg);
            }

            /* Step 2: Controlled CLA forward addition ctrl: a += ~b */
            for (i = 0; i < cla_ancilla_count; i++) {
                tqa[2 * result_bits + i] = cla_ancilla + i;
            }
            tqa[2 * result_bits + cla_ancilla_count] = control_qubit;
            tqa[2 * result_bits + cla_ancilla_count + 1] = cla_ancilla + cla_ancilla_count;

            if (circ->qubit_saving) {
                toff_seq = toffoli_cQQ_add_bk(result_bits);
            } else {
                toff_seq = toffoli_cQQ_add_ks(result_bits);
            }
            if (toff_seq != NULL) {
                run_instruction(toff_seq, tqa, 0, circ, 0); /* invert=0: forward */
                allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count + 1);

                /* Step 3: Controlled CQ increment ctrl: a += 1 */
                qubit_t inc_ancilla = allocator_alloc(circ->allocator, self_bits + 2, true);
                if (inc_ancilla != (qubit_t)-1) {
                    unsigned int inc_qa[256];
                    for (i = 0; i < self_bits; i++) {
                        inc_qa[i] = inc_ancilla + i;
                    }
                    for (i = 0; i < self_bits; i++) {
                        inc_qa[self_bits + i] = self_qubits[i];
                    }
                    inc_qa[2 * self_bits] = inc_ancilla + self_bits;
                    inc_qa[2 * self_bits + 1] = control_qubit;
                    inc_qa[2 * self_bits + 2] = inc_ancilla + self_bits + 1;
                    sequence_t *inc_seq = toffoli_cCQ_add(self_bits, 1);
                    if (inc_seq != NULL) {
                        run_instruction(inc_seq, inc_qa, 0, circ, 0);
                        toffoli_sequence_free(inc_seq);
                    }
                    allocator_free(circ->allocator, inc_ancilla, self_bits + 2);
                }

                /* Step 4: Restore other register via controlled X gates */
                for (i = 0; i < other_bits; i++) {
                    gate_t cxg;
                    memset(&cxg, 0, sizeof(gate_t));
                    cx(&cxg, other_qubits[i], control_qubit);
                    add_gate(circ, &cxg);
                }
                return;
            }
            /* CLA failed -- undo CX gates and fall through */
            allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count + 1);
            for (i = 0; i < other_bits; i++) {
                gate_t cxg;
                memset(&cxg, 0, sizeof(gate_t));
                cx(&cxg, other_qubits[i], control_qubit);
                add_gate(circ, &cxg);
            }
        }
    }

    /* Controlled CLA dispatch: forward only.
     * Phase 74-03: +1 AND-ancilla for MCX decomposition in controlled CLA. */
    if (!invert && circ->cla_override == 0 && result_bits >= circ->tradeoff_auto_threshold) {
        int cla_ancilla_count = compute_cla_ancilla_count(circ, result_bits);
        /* Allocate CLA ancilla + 1 AND-ancilla */
        qubit_t cla_ancilla = allocator_alloc(circ->allocator, cla_ancilla_count + 1, true);
        if (cla_ancilla != (qubit_t)-1) {
            for (i = 0; i < cla_ancilla_count; i++) {
                tqa[2 * result_bits + i] = cla_ancilla + i;
            }
            tqa[2 * result_bits + cla_ancilla_count] = control_qubit;
            tqa[2 * result_bits + cla_ancilla_count + 1] = cla_ancilla + cla_ancilla_count;

            if (circ->qubit_saving) {
                toff_seq = toffoli_cQQ_add_bk(result_bits);
            } else {
                toff_seq = toffoli_cQQ_add_ks(result_bits);
            }
            if (toff_seq != NULL) {
                run_instruction(toff_seq, tqa, invert, circ, 0);
                allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count + 1);
                return;
            }
            allocator_free(circ->allocator, cla_ancilla, cla_ancilla_count + 1);
        }
    }

    /* Controlled RCA (CDKM) path: 1 carry ancilla + 1 AND-ancilla (Phase 74-03) */
    qubit_t ancilla_qubit = allocator_alloc(circ->allocator, 2, true);
    if (ancilla_qubit == (qubit_t)-1)
        return;

    tqa[2 * result_bits] = ancilla_qubit;         /* carry ancilla */
    tqa[2 * result_bits + 1] = control_qubit;     /* ext_ctrl */
    tqa[2 * result_bits + 2] = ancilla_qubit + 1; /* AND-ancilla */

    toff_seq = toffoli_cQQ_add(result_bits);
    if (toff_seq == NULL) {
        allocator_free(circ->allocator, ancilla_qubit, 2);
        return;
    }
    run_instruction(toff_seq, tqa, invert, circ, 0);
    allocator_free(circ->allocator, ancilla_qubit, 2);
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
        run_instruction(toff_seq, qa, invert, circ, 0);
        toffoli_sequence_free(toff_seq);
        return;
    }

    /* Phase 75: Clifford+T CQ increment dispatch (value==1, widths 1-8).
     * CQ Clifford+T sequences are static const, need copy_hardcoded_sequence.
     * For general values (value != 1) or width > 8: fall through to dynamic path
     * (which already handles Clifford+T via inline CCX emission from Phase 74-04). */
    if (circ->toffoli_decompose && classical_value == 1 &&
        self_bits <= TOFFOLI_HARDCODED_MAX_WIDTH) {
        /* CLA Clifford+T CQ increment (forward only) */
        if (!invert && circ->cla_override == 0 && self_bits >= circ->tradeoff_auto_threshold) {
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
                const sequence_t *seq = precompiled_toffoli_clifft_cla_CQ_inc[self_bits];
                if (!seq) {
                    seq = get_hardcoded_toffoli_clifft_cla_CQ_inc(self_bits);
                    precompiled_toffoli_clifft_cla_CQ_inc[self_bits] = seq;
                }
                if (seq) {
                    sequence_t *copy = copy_hardcoded_sequence(seq);
                    if (copy) {
                        run_instruction(copy, tqa, invert, circ, 0);
                        toffoli_sequence_free(copy);
                        allocator_free(circ->allocator, cq_cla_ancilla, total_ancilla);
                        return;
                    }
                }
                allocator_free(circ->allocator, cq_cla_ancilla, total_ancilla);
            }
        }
        /* RCA Clifford+T CQ increment */
        qubit_t ct_temp = allocator_alloc(circ->allocator, self_bits + 1, true);
        if (ct_temp != (qubit_t)-1) {
            unsigned int tqa[256];
            for (i = 0; i < self_bits; i++) {
                tqa[i] = ct_temp + i;
            }
            for (i = 0; i < self_bits; i++) {
                tqa[self_bits + i] = self_qubits[i];
            }
            tqa[2 * self_bits] = ct_temp + self_bits;

            const sequence_t *seq = precompiled_toffoli_clifft_CQ_inc[self_bits];
            if (!seq) {
                seq = get_hardcoded_toffoli_clifft_CQ_inc(self_bits);
                precompiled_toffoli_clifft_CQ_inc[self_bits] = seq;
            }
            if (seq) {
                sequence_t *copy = copy_hardcoded_sequence(seq);
                if (copy) {
                    run_instruction(copy, tqa, invert, circ, 0);
                    toffoli_sequence_free(copy);
                    allocator_free(circ->allocator, ct_temp, self_bits + 1);
                    return;
                }
            }
            allocator_free(circ->allocator, ct_temp, self_bits + 1);
        }
        /* Clifford+T dispatch returned NULL -- fall through to non-decomposed */
    }

    /* Phase 93: CQ two's complement CLA subtraction for min_depth mode.
     * a -= v  ===  a += (2^width - v)  (classical negation, then forward CLA add) */
    if (invert && circ->tradeoff_min_depth && circ->cla_override == 0 &&
        self_bits >= circ->tradeoff_auto_threshold) {
        int64_t negated = ((int64_t)1 << self_bits) - classical_value;
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
                toff_seq = toffoli_CQ_add_bk(self_bits, negated);
            } else {
                toff_seq = toffoli_CQ_add_ks(self_bits, negated);
            }
            if (toff_seq != NULL) {
                run_instruction(toff_seq, tqa, 0, circ, 0); /* invert=0: forward */
                toffoli_sequence_free(toff_seq);
                allocator_free(circ->allocator, cq_cla_ancilla, total_ancilla);
                return;
            }
            allocator_free(circ->allocator, cq_cla_ancilla, total_ancilla);
        }
    }

    /* CQ CLA dispatch: forward only */
    if (!invert && circ->cla_override == 0 && self_bits >= circ->tradeoff_auto_threshold) {
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
                run_instruction(toff_seq, tqa, invert, circ, 0);
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
        run_instruction(toff_seq, tqa, invert, circ, 0);
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
        run_instruction(toff_seq, tqa, invert, circ, 0);
        toffoli_sequence_free(toff_seq);
        return;
    }

    /* Phase 75: Clifford+T cCQ increment dispatch (value==1, widths 1-8).
     * cCQ Clifford+T sequences are static const, need copy_hardcoded_sequence. */
    if (circ->toffoli_decompose && classical_value == 1 &&
        self_bits <= TOFFOLI_HARDCODED_MAX_WIDTH) {
        /* Controlled CLA Clifford+T cCQ increment (forward only) */
        if (!invert && circ->cla_override == 0 && self_bits >= circ->tradeoff_auto_threshold) {
            int cla_ancilla_count = compute_cla_ancilla_count(circ, self_bits);
            int total_cla_ancilla = self_bits + cla_ancilla_count + 1;
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
                cla_qa[2 * self_bits + cla_ancilla_count + 1] =
                    cla_start + self_bits + cla_ancilla_count;

                const sequence_t *seq = precompiled_toffoli_clifft_cla_cCQ_inc[self_bits];
                if (!seq) {
                    seq = get_hardcoded_toffoli_clifft_cla_cCQ_inc(self_bits);
                    precompiled_toffoli_clifft_cla_cCQ_inc[self_bits] = seq;
                }
                if (seq) {
                    sequence_t *copy = copy_hardcoded_sequence(seq);
                    if (copy) {
                        run_instruction(copy, cla_qa, invert, circ, 0);
                        toffoli_sequence_free(copy);
                        allocator_free(circ->allocator, cla_start, total_cla_ancilla);
                        return;
                    }
                }
                allocator_free(circ->allocator, cla_start, total_cla_ancilla);
            }
        }
        /* Controlled RCA Clifford+T cCQ increment */
        qubit_t ct_temp = allocator_alloc(circ->allocator, self_bits + 2, true);
        if (ct_temp != (qubit_t)-1) {
            unsigned int tqa[256];
            for (i = 0; i < self_bits; i++) {
                tqa[i] = ct_temp + i;
            }
            for (i = 0; i < self_bits; i++) {
                tqa[self_bits + i] = self_qubits[i];
            }
            tqa[2 * self_bits] = ct_temp + self_bits;         /* carry ancilla */
            tqa[2 * self_bits + 1] = control_qubit;           /* ext_ctrl */
            tqa[2 * self_bits + 2] = ct_temp + self_bits + 1; /* AND-ancilla */

            const sequence_t *seq = precompiled_toffoli_clifft_cCQ_inc[self_bits];
            if (!seq) {
                seq = get_hardcoded_toffoli_clifft_cCQ_inc(self_bits);
                precompiled_toffoli_clifft_cCQ_inc[self_bits] = seq;
            }
            if (seq) {
                sequence_t *copy = copy_hardcoded_sequence(seq);
                if (copy) {
                    run_instruction(copy, tqa, invert, circ, 0);
                    toffoli_sequence_free(copy);
                    allocator_free(circ->allocator, ct_temp, self_bits + 2);
                    return;
                }
            }
            allocator_free(circ->allocator, ct_temp, self_bits + 2);
        }
        /* Clifford+T dispatch returned NULL -- fall through to non-decomposed */
    }

    /* Phase 93: Controlled CQ two's complement CLA subtraction for min_depth mode.
     * ctrl: a -= v  ===  ctrl: a += (2^width - v) */
    if (invert && circ->tradeoff_min_depth && circ->cla_override == 0 &&
        self_bits >= circ->tradeoff_auto_threshold) {
        int64_t negated = ((int64_t)1 << self_bits) - classical_value;
        int cla_ancilla_count = compute_cla_ancilla_count(circ, self_bits);
        int total_cla_ancilla = self_bits + cla_ancilla_count + 1;
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
            cla_qa[2 * self_bits + cla_ancilla_count + 1] =
                cla_start + self_bits + cla_ancilla_count;

            if (circ->qubit_saving) {
                toff_seq = toffoli_cCQ_add_bk(self_bits, negated);
            } else {
                toff_seq = toffoli_cCQ_add_ks(self_bits, negated);
            }
            if (toff_seq != NULL) {
                run_instruction(toff_seq, cla_qa, 0, circ, 0); /* invert=0: forward */
                toffoli_sequence_free(toff_seq);
                allocator_free(circ->allocator, cla_start, total_cla_ancilla);
                return;
            }
            allocator_free(circ->allocator, cla_start, total_cla_ancilla);
        }
    }

    /* Controlled CQ CLA dispatch: forward only.
     * Phase 74-03: cCQ BK CLA copies from cQQ BK which now has decomposed MCX.
     * The cCQ BK simplified phases (A, E, F) don't produce MCX because
     * classical-bit simplification eliminates them. Only phases B-D (copied from
     * cQQ BK) contain decomposed gates, and the AND-ancilla qubit position
     * is ext_ctrl + 1 = 2*bits + cla_ancilla + 1. We need to allocate it. */
    if (!invert && circ->cla_override == 0 && self_bits >= circ->tradeoff_auto_threshold) {
        int cla_ancilla_count = compute_cla_ancilla_count(circ, self_bits);
        /* +1 AND-ancilla for MCX decomposition in cQQ BK phases B-D */
        int total_cla_ancilla = self_bits + cla_ancilla_count + 1;
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
            cla_qa[2 * self_bits + cla_ancilla_count + 1] =
                cla_start + self_bits + cla_ancilla_count;

            if (circ->qubit_saving) {
                toff_seq = toffoli_cCQ_add_bk(self_bits, classical_value);
            } else {
                toff_seq = toffoli_cCQ_add_ks(self_bits, classical_value);
            }
            if (toff_seq != NULL) {
                run_instruction(toff_seq, cla_qa, invert, circ, 0);
                toffoli_sequence_free(toff_seq);
                allocator_free(circ->allocator, cla_start, total_cla_ancilla);
                return;
            }
            allocator_free(circ->allocator, cla_start, total_cla_ancilla);
        }
    }

    /* Controlled RCA (CDKM) CQ path: self_bits + 2 ancilla (Phase 74-03: +1 for AND-ancilla) */
    {
        qubit_t temp_start = allocator_alloc(circ->allocator, self_bits + 2, true);
        if (temp_start == (qubit_t)-1)
            return;

        unsigned int tqa[256];
        for (i = 0; i < self_bits; i++) {
            tqa[i] = temp_start + i;
        }
        for (i = 0; i < self_bits; i++) {
            tqa[self_bits + i] = self_qubits[i];
        }
        tqa[2 * self_bits] = temp_start + self_bits;         /* carry ancilla */
        tqa[2 * self_bits + 1] = control_qubit;              /* ext_ctrl */
        tqa[2 * self_bits + 2] = temp_start + self_bits + 1; /* AND-ancilla */

        toff_seq = toffoli_cCQ_add(self_bits, classical_value);
        if (toff_seq == NULL) {
            allocator_free(circ->allocator, temp_start, self_bits + 2);
            return;
        }
        run_instruction(toff_seq, tqa, invert, circ, 0);
        toffoli_sequence_free(toff_seq);
        allocator_free(circ->allocator, temp_start, self_bits + 2);
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
