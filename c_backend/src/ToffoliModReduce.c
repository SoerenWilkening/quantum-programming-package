/**
 * @file ToffoliModReduce.c
 * @brief Toffoli-based modular arithmetic (Phase 92: Beauregard modular add/sub/mul).
 *
 * Implements Beauregard 8-step modular addition with clean ancilla uncomputation,
 * replacing the broken add+reduce approach from Phase 91 that leaked persistent
 * comparison ancillae.
 *
 * The Beauregard sequence exploits the structure of modular addition:
 * after adding and then subtracting the original operand, the sign of the
 * intermediate result reveals whether reduction occurred, enabling clean
 * ancilla reset.
 *
 * Functions:
 *   toffoli_mod_reduce      -- general modular reduction (Phase 91, persistent ancilla)
 *   toffoli_cmod_reduce     -- controlled modular reduction (Phase 91, persistent ancilla)
 *   toffoli_mod_add_cq      -- Beauregard CQ modular addition (clean ancilla)
 *   toffoli_cmod_add_cq     -- controlled Beauregard CQ modular addition
 *   toffoli_mod_sub_cq      -- CQ modular subtraction via complement
 *   toffoli_cmod_sub_cq     -- controlled CQ modular subtraction
 *   toffoli_mod_add_qq      -- Beauregard QQ modular addition (clean ancilla)
 *   toffoli_cmod_add_qq     -- controlled Beauregard QQ modular addition
 *   toffoli_mod_sub_qq      -- QQ modular subtraction via complement-and-add
 *   toffoli_cmod_sub_qq     -- controlled QQ modular subtraction
 *   toffoli_mod_mul_cq      -- CQ modular multiplication via controlled mod adds
 *   toffoli_cmod_mul_cq     -- controlled CQ modular multiplication
 *   toffoli_mod_mul_qq      -- QQ modular multiplication (product + bit-decomposition)
 *   toffoli_cmod_mul_qq     -- controlled QQ modular multiplication
 *
 * References:
 *   Beauregard (2003) "Circuit for Shor's algorithm using 2n+3 qubits"
 *   Bennett (1973) reversible computation trick
 */

#include "Integer.h"
#include "circuit.h"
#include "execution.h"
#include "gate.h"
#include "optimizer.h"
#include "qubit_allocator.h"
#include "toffoli_arithmetic_ops.h"

#include <stdlib.h>
#include <string.h>

/* ========================================================================== */
/* Helpers                                                                     */
/* ========================================================================== */

static void mod_emit_ccx(circuit_t *circ, qubit_t target, qubit_t ctrl1, qubit_t ctrl2) {
    if (circ->toffoli_decompose) {
        emit_ccx_clifford_t(circ, target, ctrl1, ctrl2);
    } else {
        gate_t g;
        memset(&g, 0, sizeof(gate_t));
        ccx(&g, target, ctrl1, ctrl2);
        add_gate(circ, &g);
    }
}

static void mod_emit_cx(circuit_t *circ, qubit_t target, qubit_t control) {
    gate_t g;
    memset(&g, 0, sizeof(gate_t));
    cx(&g, target, control);
    add_gate(circ, &g);
}

static void mod_emit_x(circuit_t *circ, qubit_t target) {
    gate_t g;
    memset(&g, 0, sizeof(gate_t));
    x(&g, target);
    add_gate(circ, &g);
}

/**
 * @brief CQ add helper: reg += value using CDKM adder.
 *
 * Allocates temp register and carry internally, calls toffoli_CQ_add.
 * Forces RCA (CDKM) -- does NOT use hot_path dispatch.
 */
static int mod_cq_add(circuit_t *circ, const unsigned int *reg_qubits, int reg_bits,
                      int64_t value) {
    if (reg_bits == 1) {
        sequence_t *seq = toffoli_CQ_add(1, value);
        if (seq == NULL)
            return -1;
        unsigned int tqa[1];
        tqa[0] = reg_qubits[0];
        run_instruction(seq, tqa, 0, circ, 0);
        toffoli_sequence_free(seq);
        return 0;
    }

    qubit_t temp_start = allocator_alloc(circ->allocator, reg_bits, true);
    if (temp_start == (qubit_t)-1)
        return -1;

    qubit_t carry = allocator_alloc(circ->allocator, 1, true);
    if (carry == (qubit_t)-1) {
        allocator_free(circ->allocator, temp_start, reg_bits);
        return -1;
    }

    unsigned int tqa[256];
    for (int i = 0; i < reg_bits; i++) {
        tqa[i] = temp_start + i;
    }
    for (int i = 0; i < reg_bits; i++) {
        tqa[reg_bits + i] = reg_qubits[i];
    }
    tqa[2 * reg_bits] = carry;

    sequence_t *seq = toffoli_CQ_add(reg_bits, value);
    if (seq == NULL) {
        allocator_free(circ->allocator, carry, 1);
        allocator_free(circ->allocator, temp_start, reg_bits);
        return -1;
    }
    run_instruction(seq, tqa, 0, circ, 0);
    toffoli_sequence_free(seq);

    allocator_free(circ->allocator, carry, 1);
    allocator_free(circ->allocator, temp_start, reg_bits);
    return 0;
}

/**
 * @brief Controlled CQ add helper: reg += value, controlled by ctrl.
 *
 * Allocates temp register, carry, and AND-ancilla internally.
 * Calls toffoli_cCQ_add. Forces RCA (CDKM).
 */
static int mod_ccq_add(circuit_t *circ, const unsigned int *reg_qubits, int reg_bits, int64_t value,
                       unsigned int ctrl) {
    if (reg_bits == 1) {
        if (value & 1) {
            mod_emit_cx(circ, reg_qubits[0], ctrl);
        }
        return 0;
    }

    qubit_t temp_start = allocator_alloc(circ->allocator, reg_bits, true);
    if (temp_start == (qubit_t)-1)
        return -1;

    qubit_t carry = allocator_alloc(circ->allocator, 1, true);
    if (carry == (qubit_t)-1) {
        allocator_free(circ->allocator, temp_start, reg_bits);
        return -1;
    }

    qubit_t and_anc = allocator_alloc(circ->allocator, 1, true);
    if (and_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, carry, 1);
        allocator_free(circ->allocator, temp_start, reg_bits);
        return -1;
    }

    unsigned int tqa[256];
    for (int i = 0; i < reg_bits; i++) {
        tqa[i] = temp_start + i;
    }
    for (int i = 0; i < reg_bits; i++) {
        tqa[reg_bits + i] = reg_qubits[i];
    }
    tqa[2 * reg_bits] = carry;
    tqa[2 * reg_bits + 1] = ctrl;
    tqa[2 * reg_bits + 2] = and_anc;

    sequence_t *seq = toffoli_cCQ_add(reg_bits, value);
    if (seq == NULL) {
        allocator_free(circ->allocator, and_anc, 1);
        allocator_free(circ->allocator, carry, 1);
        allocator_free(circ->allocator, temp_start, reg_bits);
        return -1;
    }
    run_instruction(seq, tqa, 0, circ, 0);
    toffoli_sequence_free(seq);

    allocator_free(circ->allocator, and_anc, 1);
    allocator_free(circ->allocator, carry, 1);
    allocator_free(circ->allocator, temp_start, reg_bits);
    return 0;
}

/**
 * @brief QQ add helper: target += source using CDKM adder.
 *
 * Allocates carry ancilla internally. Forces RCA (CDKM).
 * For target_bits > source_bits, pads source with zero ancillae.
 *
 * @param invert  0 = forward (add), 1 = inverse (subtract)
 */
static int mod_qq_add(circuit_t *circ, const unsigned int *target_qubits, int target_bits,
                      const unsigned int *source_qubits, int source_bits, int invert) {
    int bits = target_bits; /* use target width for the addition */

    if (bits == 1) {
        /* 1-bit QQ add: just CNOT */
        sequence_t *seq = toffoli_QQ_add(1);
        if (seq == NULL)
            return -1;
        unsigned int tqa[2];
        tqa[0] = target_qubits[0];
        tqa[1] = source_qubits[0];
        run_instruction(seq, tqa, invert, circ, 0);
        /* QQ_add(1) is cached, do NOT free */
        return 0;
    }

    /* Need to pad source if shorter than target */
    int need_pad = (source_bits < target_bits);
    int pad_count = need_pad ? (target_bits - source_bits) : 0;

    qubit_t pad_start = 0;
    if (need_pad) {
        pad_start = allocator_alloc(circ->allocator, pad_count, true);
        if (pad_start == (qubit_t)-1)
            return -1;
    }

    qubit_t carry = allocator_alloc(circ->allocator, 1, true);
    if (carry == (qubit_t)-1) {
        if (need_pad)
            allocator_free(circ->allocator, pad_start, pad_count);
        return -1;
    }

    /* CDKM QQ layout: [a[0..bits-1], b[0..bits-1], carry]
     * a = source (preserved)
     * b = target (modified: b += a, i.e. target += source) */
    unsigned int tqa[256];
    /* a-register: source (preserved) */
    for (int i = 0; i < source_bits; i++) {
        tqa[i] = source_qubits[i];
    }
    /* Pad remaining a-positions with zero ancillae */
    for (int i = source_bits; i < bits; i++) {
        tqa[i] = pad_start + (i - source_bits);
    }
    /* b-register: target (modified) */
    for (int i = 0; i < bits; i++) {
        tqa[bits + i] = target_qubits[i];
    }
    tqa[2 * bits] = carry;

    sequence_t *seq = toffoli_QQ_add(bits);
    if (seq == NULL) {
        allocator_free(circ->allocator, carry, 1);
        if (need_pad)
            allocator_free(circ->allocator, pad_start, pad_count);
        return -1;
    }
    run_instruction(seq, tqa, invert, circ, 0);
    /* QQ_add is cached, do NOT free */

    allocator_free(circ->allocator, carry, 1);
    if (need_pad)
        allocator_free(circ->allocator, pad_start, pad_count);
    return 0;
}

/**
 * @brief Controlled QQ add helper: target += source, controlled by ctrl.
 *
 * @param invert  0 = forward (add), 1 = inverse (subtract)
 */
static int mod_cqq_add(circuit_t *circ, const unsigned int *target_qubits, int target_bits,
                       const unsigned int *source_qubits, int source_bits, unsigned int ctrl,
                       int invert) {
    int bits = target_bits;

    if (bits == 1) {
        /* 1-bit controlled QQ add: CCX */
        sequence_t *seq = toffoli_cQQ_add(1);
        if (seq == NULL)
            return -1;
        unsigned int tqa[3];
        tqa[0] = target_qubits[0];
        tqa[1] = source_qubits[0];
        tqa[2] = ctrl;
        run_instruction(seq, tqa, invert, circ, 0);
        return 0;
    }

    int need_pad = (source_bits < target_bits);
    int pad_count = need_pad ? (target_bits - source_bits) : 0;

    qubit_t pad_start = 0;
    if (need_pad) {
        pad_start = allocator_alloc(circ->allocator, pad_count, true);
        if (pad_start == (qubit_t)-1)
            return -1;
    }

    qubit_t carry = allocator_alloc(circ->allocator, 1, true);
    if (carry == (qubit_t)-1) {
        if (need_pad)
            allocator_free(circ->allocator, pad_start, pad_count);
        return -1;
    }

    qubit_t and_anc = allocator_alloc(circ->allocator, 1, true);
    if (and_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, carry, 1);
        if (need_pad)
            allocator_free(circ->allocator, pad_start, pad_count);
        return -1;
    }

    /* cQQ layout: [a[0..bits-1], b[0..bits-1], carry, ext_ctrl, and_anc]
     * a = source (preserved), b = target (modified: b += a) */
    unsigned int tqa[256];
    /* a-register: source (preserved) */
    for (int i = 0; i < source_bits; i++) {
        tqa[i] = source_qubits[i];
    }
    for (int i = source_bits; i < bits; i++) {
        tqa[i] = pad_start + (i - source_bits);
    }
    /* b-register: target (modified) */
    for (int i = 0; i < bits; i++) {
        tqa[bits + i] = target_qubits[i];
    }
    tqa[2 * bits] = carry;
    tqa[2 * bits + 1] = ctrl;
    tqa[2 * bits + 2] = and_anc;

    sequence_t *seq = toffoli_cQQ_add(bits);
    if (seq == NULL) {
        allocator_free(circ->allocator, and_anc, 1);
        allocator_free(circ->allocator, carry, 1);
        if (need_pad)
            allocator_free(circ->allocator, pad_start, pad_count);
        return -1;
    }
    run_instruction(seq, tqa, invert, circ, 0);

    allocator_free(circ->allocator, and_anc, 1);
    allocator_free(circ->allocator, carry, 1);
    if (need_pad)
        allocator_free(circ->allocator, pad_start, pad_count);
    return 0;
}

/* ========================================================================== */
/* Modular Reduction (Phase 91 -- kept for backward compatibility)             */
/* ========================================================================== */

void toffoli_mod_reduce(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                        int64_t modulus) {
    if (modulus <= 0)
        return;
    int n = value_bits;
    int wide = n + 1;

    qubit_t temp_start = allocator_alloc(circ->allocator, wide, true);
    if (temp_start == (qubit_t)-1)
        return;

    qubit_t cmp_anc = allocator_alloc(circ->allocator, 1, true);
    if (cmp_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, temp_start, wide);
        return;
    }

    unsigned int temp_arr[64];
    for (int i = 0; i < wide; i++) {
        temp_arr[i] = temp_start + i;
    }

    for (int i = 0; i < n; i++) {
        mod_emit_cx(circ, temp_arr[i], value_qubits[i]);
    }

    mod_cq_add(circ, temp_arr, wide, -modulus);

    mod_emit_cx(circ, cmp_anc, temp_arr[n]);

    mod_cq_add(circ, temp_arr, wide, modulus);
    for (int i = 0; i < n; i++) {
        mod_emit_cx(circ, temp_arr[i], value_qubits[i]);
    }

    allocator_free(circ->allocator, temp_start, wide);

    mod_emit_x(circ, cmp_anc);
    mod_ccq_add(circ, value_qubits, n, -modulus, cmp_anc);
    mod_emit_x(circ, cmp_anc);

    /* cmp_anc: persistent ancilla (not freed) -- Phase 91 limitation */
    (void)cmp_anc;
}

void toffoli_cmod_reduce(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                         int64_t modulus, unsigned int ext_ctrl) {
    if (modulus <= 0)
        return;
    int n = value_bits;
    int wide = n + 1;

    qubit_t temp_start = allocator_alloc(circ->allocator, wide, true);
    if (temp_start == (qubit_t)-1)
        return;

    qubit_t cmp_anc = allocator_alloc(circ->allocator, 1, true);
    if (cmp_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, temp_start, wide);
        return;
    }

    unsigned int temp_arr[64];
    for (int i = 0; i < wide; i++) {
        temp_arr[i] = temp_start + i;
    }

    for (int i = 0; i < n; i++) {
        mod_emit_ccx(circ, temp_arr[i], value_qubits[i], ext_ctrl);
    }

    mod_ccq_add(circ, temp_arr, wide, -modulus, ext_ctrl);
    mod_emit_cx(circ, cmp_anc, temp_arr[n]);

    mod_ccq_add(circ, temp_arr, wide, modulus, ext_ctrl);
    for (int i = 0; i < n; i++) {
        mod_emit_ccx(circ, temp_arr[i], value_qubits[i], ext_ctrl);
    }

    allocator_free(circ->allocator, temp_start, wide);

    mod_emit_x(circ, cmp_anc);

    qubit_t and_anc = allocator_alloc(circ->allocator, 1, true);
    if (and_anc == (qubit_t)-1) {
        (void)cmp_anc;
        return;
    }

    mod_emit_ccx(circ, and_anc, cmp_anc, ext_ctrl);
    mod_ccq_add(circ, value_qubits, n, -modulus, and_anc);
    mod_emit_ccx(circ, and_anc, cmp_anc, ext_ctrl);

    allocator_free(circ->allocator, and_anc, 1);
    mod_emit_x(circ, cmp_anc);

    (void)cmp_anc;
}

/* ========================================================================== */
/* Beauregard 8-step Modular CQ Addition (Phase 92)                            */
/* ========================================================================== */

/**
 * @brief Beauregard modular CQ addition: value = (value + addend) mod modulus.
 *
 * Implements the 8-step Beauregard sequence with clean ancilla uncomputation.
 * Both value and addend must be in [0, N-1]. Allocates 1 high_bit + 1 cmp_anc
 * ancilla and frees both after the operation.
 *
 * Steps:
 *   1. value += a
 *   2. value -= N
 *   3. cmp_anc = sign(value) [copy high bit]
 *   4. if cmp_anc: value += N
 *   5. value -= a  (undo step 1)
 *   6. X(cmp_anc)
 *   7. CNOT(cmp_anc, sign) [resets cmp_anc using sign after step 5]
 *   8. value += a  (redo step 1)
 *
 * After step 8: value = (orig + a) mod N, cmp_anc = 0, high_bit = 0.
 */
void toffoli_mod_add_cq(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                        int64_t addend, int64_t modulus) {
    if (modulus <= 0)
        return;
    int n = value_bits;

    /* Classically reduce addend to [0, N-1] */
    int64_t a = addend % modulus;
    if (a < 0)
        a += modulus;
    if (a == 0)
        return; /* No-op */

    /* Allocate ancillae */
    qubit_t high_bit = allocator_alloc(circ->allocator, 1, true);
    if (high_bit == (qubit_t)-1)
        return;

    qubit_t cmp_anc = allocator_alloc(circ->allocator, 1, true);
    if (cmp_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, high_bit, 1);
        return;
    }

    /* Build (n+1)-bit wide register: [value_qubits[0..n-1], high_bit] */
    unsigned int wide_reg[64];
    for (int i = 0; i < n; i++)
        wide_reg[i] = value_qubits[i];
    wide_reg[n] = high_bit;

    /* Step 1: value += a */
    mod_cq_add(circ, wide_reg, n + 1, a);

    /* Step 2: value -= N */
    mod_cq_add(circ, wide_reg, n + 1, -modulus);

    /* Step 3: Copy sign (high_bit) to cmp_anc */
    mod_emit_cx(circ, cmp_anc, wide_reg[n]);

    /* Step 4: if cmp_anc=1: value += N (controlled) */
    mod_ccq_add(circ, wide_reg, n + 1, modulus, cmp_anc);

    /* Step 5: value -= a (undo step 1) */
    mod_cq_add(circ, wide_reg, n + 1, -a);

    /* Step 6: X(cmp_anc) */
    mod_emit_x(circ, cmp_anc);

    /* Step 7: CNOT(cmp_anc, sign) -- resets cmp_anc to 0 */
    mod_emit_cx(circ, cmp_anc, wide_reg[n]);

    /* Step 8: value += a (redo step 1) */
    mod_cq_add(circ, wide_reg, n + 1, a);

    /* Both ancillae are now clean (|0>) */
    allocator_free(circ->allocator, cmp_anc, 1);
    allocator_free(circ->allocator, high_bit, 1);
}

/**
 * @brief Controlled Beauregard modular CQ addition.
 *
 * Same 8 steps but ALL additions are controlled by ext_ctrl.
 * Step 4 becomes doubly-controlled (cmp_anc AND ext_ctrl) using AND-ancilla.
 * Steps 3,7 become CCX (controlled CNOT). Step 6 becomes CX (controlled X).
 */
void toffoli_cmod_add_cq(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                         int64_t addend, int64_t modulus, unsigned int ext_ctrl) {
    if (modulus <= 0)
        return;
    int n = value_bits;

    int64_t a = addend % modulus;
    if (a < 0)
        a += modulus;
    if (a == 0)
        return;

    qubit_t high_bit = allocator_alloc(circ->allocator, 1, true);
    if (high_bit == (qubit_t)-1)
        return;

    qubit_t cmp_anc = allocator_alloc(circ->allocator, 1, true);
    if (cmp_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, high_bit, 1);
        return;
    }

    unsigned int wide_reg[64];
    for (int i = 0; i < n; i++)
        wide_reg[i] = value_qubits[i];
    wide_reg[n] = high_bit;

    /* Step 1: controlled value += a */
    mod_ccq_add(circ, wide_reg, n + 1, a, ext_ctrl);

    /* Step 2: controlled value -= N */
    mod_ccq_add(circ, wide_reg, n + 1, -modulus, ext_ctrl);

    /* Step 3: controlled copy sign -- CCX(cmp_anc, high_bit, ext_ctrl) */
    mod_emit_ccx(circ, cmp_anc, wide_reg[n], ext_ctrl);

    /* Step 4: doubly-controlled add N (cmp_anc AND ext_ctrl) */
    {
        qubit_t and_anc = allocator_alloc(circ->allocator, 1, true);
        if (and_anc == (qubit_t)-1) {
            allocator_free(circ->allocator, cmp_anc, 1);
            allocator_free(circ->allocator, high_bit, 1);
            return;
        }
        mod_emit_ccx(circ, and_anc, cmp_anc, ext_ctrl);
        mod_ccq_add(circ, wide_reg, n + 1, modulus, and_anc);
        mod_emit_ccx(circ, and_anc, cmp_anc, ext_ctrl);
        allocator_free(circ->allocator, and_anc, 1);
    }

    /* Step 5: controlled value -= a */
    mod_ccq_add(circ, wide_reg, n + 1, -a, ext_ctrl);

    /* Step 6: controlled X(cmp_anc) = CX(cmp_anc, ext_ctrl) */
    mod_emit_cx(circ, cmp_anc, ext_ctrl);

    /* Step 7: controlled copy sign -- CCX(cmp_anc, high_bit, ext_ctrl) */
    mod_emit_ccx(circ, cmp_anc, wide_reg[n], ext_ctrl);

    /* Step 8: controlled value += a */
    mod_ccq_add(circ, wide_reg, n + 1, a, ext_ctrl);

    allocator_free(circ->allocator, cmp_anc, 1);
    allocator_free(circ->allocator, high_bit, 1);
}

/* ========================================================================== */
/* Modular CQ Subtraction (Phase 92)                                           */
/* ========================================================================== */

void toffoli_mod_sub_cq(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                        int64_t subtrahend, int64_t modulus) {
    /* (value - b) mod N = (value + (N - b)) mod N */
    int64_t b = subtrahend % modulus;
    if (b < 0)
        b += modulus;
    int64_t complement = (modulus - b) % modulus;
    toffoli_mod_add_cq(circ, value_qubits, value_bits, complement, modulus);
}

void toffoli_cmod_sub_cq(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                         int64_t subtrahend, int64_t modulus, unsigned int ext_ctrl) {
    int64_t b = subtrahend % modulus;
    if (b < 0)
        b += modulus;
    int64_t complement = (modulus - b) % modulus;
    toffoli_cmod_add_cq(circ, value_qubits, value_bits, complement, modulus, ext_ctrl);
}

/* ========================================================================== */
/* Beauregard 8-step Modular QQ Addition (Phase 92)                            */
/* ========================================================================== */

/**
 * @brief Beauregard modular QQ addition: value = (value + other) mod modulus.
 *
 * Same 8-step sequence as CQ, but using QQ adders for steps involving
 * the quantum operand. CDKM QQ add preserves the source register,
 * so `other` can be used directly in steps 5 and 8.
 */
void toffoli_mod_add_qq(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                        const unsigned int *other_qubits, int other_bits, int64_t modulus) {
    if (modulus <= 0)
        return;
    int n = value_bits;

    qubit_t high_bit = allocator_alloc(circ->allocator, 1, true);
    if (high_bit == (qubit_t)-1)
        return;

    qubit_t cmp_anc = allocator_alloc(circ->allocator, 1, true);
    if (cmp_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, high_bit, 1);
        return;
    }

    unsigned int wide_reg[64];
    for (int i = 0; i < n; i++)
        wide_reg[i] = value_qubits[i];
    wide_reg[n] = high_bit;

    /* Step 1: value += other (QQ add, (n+1)-bit target, other_bits source) */
    mod_qq_add(circ, wide_reg, n + 1, other_qubits, other_bits, 0);

    /* Step 2: value -= N (CQ add of -N) */
    mod_cq_add(circ, wide_reg, n + 1, -modulus);

    /* Step 3: Copy sign to cmp_anc */
    mod_emit_cx(circ, cmp_anc, wide_reg[n]);

    /* Step 4: if cmp_anc=1: value += N (controlled CQ add) */
    mod_ccq_add(circ, wide_reg, n + 1, modulus, cmp_anc);

    /* Step 5: value -= other (inverse QQ add) */
    mod_qq_add(circ, wide_reg, n + 1, other_qubits, other_bits, 1);

    /* Step 6: X(cmp_anc) */
    mod_emit_x(circ, cmp_anc);

    /* Step 7: CNOT(cmp_anc, sign) */
    mod_emit_cx(circ, cmp_anc, wide_reg[n]);

    /* Step 8: value += other (QQ add) */
    mod_qq_add(circ, wide_reg, n + 1, other_qubits, other_bits, 0);

    allocator_free(circ->allocator, cmp_anc, 1);
    allocator_free(circ->allocator, high_bit, 1);
}

/**
 * @brief Controlled Beauregard modular QQ addition.
 */
void toffoli_cmod_add_qq(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                         const unsigned int *other_qubits, int other_bits, int64_t modulus,
                         unsigned int ext_ctrl) {
    if (modulus <= 0)
        return;
    int n = value_bits;

    qubit_t high_bit = allocator_alloc(circ->allocator, 1, true);
    if (high_bit == (qubit_t)-1)
        return;

    qubit_t cmp_anc = allocator_alloc(circ->allocator, 1, true);
    if (cmp_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, high_bit, 1);
        return;
    }

    unsigned int wide_reg[64];
    for (int i = 0; i < n; i++)
        wide_reg[i] = value_qubits[i];
    wide_reg[n] = high_bit;

    /* Step 1: controlled value += other */
    mod_cqq_add(circ, wide_reg, n + 1, other_qubits, other_bits, ext_ctrl, 0);

    /* Step 2: controlled value -= N */
    mod_ccq_add(circ, wide_reg, n + 1, -modulus, ext_ctrl);

    /* Step 3: controlled copy sign -- CCX */
    mod_emit_ccx(circ, cmp_anc, wide_reg[n], ext_ctrl);

    /* Step 4: doubly-controlled add N */
    {
        qubit_t and_anc = allocator_alloc(circ->allocator, 1, true);
        if (and_anc == (qubit_t)-1) {
            allocator_free(circ->allocator, cmp_anc, 1);
            allocator_free(circ->allocator, high_bit, 1);
            return;
        }
        mod_emit_ccx(circ, and_anc, cmp_anc, ext_ctrl);
        mod_ccq_add(circ, wide_reg, n + 1, modulus, and_anc);
        mod_emit_ccx(circ, and_anc, cmp_anc, ext_ctrl);
        allocator_free(circ->allocator, and_anc, 1);
    }

    /* Step 5: controlled value -= other */
    mod_cqq_add(circ, wide_reg, n + 1, other_qubits, other_bits, ext_ctrl, 1);

    /* Step 6: CX(cmp_anc, ext_ctrl) */
    mod_emit_cx(circ, cmp_anc, ext_ctrl);

    /* Step 7: CCX(cmp_anc, high_bit, ext_ctrl) */
    mod_emit_ccx(circ, cmp_anc, wide_reg[n], ext_ctrl);

    /* Step 8: controlled value += other */
    mod_cqq_add(circ, wide_reg, n + 1, other_qubits, other_bits, ext_ctrl, 0);

    allocator_free(circ->allocator, cmp_anc, 1);
    allocator_free(circ->allocator, high_bit, 1);
}

/* ========================================================================== */
/* Modular QQ Subtraction (Phase 92)                                           */
/* ========================================================================== */

/**
 * @brief QQ modular subtraction: value = (value - other) mod modulus.
 *
 * Computes temp = N - other, then mod_add_qq(value, temp, N), then
 * uncomputes temp. This avoids modifying the other register.
 *
 * temp computation: temp = 0, temp += N (CQ), temp -= other (QQ inverse).
 * temp uncomputation: temp += other (QQ), temp -= N (CQ), now temp = 0.
 */
void toffoli_mod_sub_qq(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                        const unsigned int *other_qubits, int other_bits, int64_t modulus) {
    if (modulus <= 0)
        return;
    int n = value_bits;

    /* Allocate temp register for N - other */
    qubit_t temp_start = allocator_alloc(circ->allocator, n, true);
    if (temp_start == (qubit_t)-1)
        return;

    unsigned int temp_qa[64];
    for (int i = 0; i < n; i++)
        temp_qa[i] = temp_start + i;

    /* Compute temp = N - other:
     * temp starts at |0>
     * temp += N  (CQ add)
     * temp -= other (inverse QQ add: temp = N - other) */
    mod_cq_add(circ, temp_qa, n, modulus);
    mod_qq_add(circ, temp_qa, n, other_qubits, other_bits, 1); /* temp -= other */

    /* Now temp = (N - other) mod 2^n. Since other in [0, N-1], temp in [1, N] */
    /* But we want temp in [0, N-1] for the mod_add. If other=0, temp=N.
     * (N - 0) mod N = 0, which mod_add_cq handles via the a==0 check.
     * For the QQ version, temp = N which is n+1 bits, but we only have n bits.
     * When other=0: temp = N mod 2^n. If N < 2^n (which it must be since
     * value_bits >= N.bit_length()), then temp = N in n bits.
     * mod_add_qq(value, temp, N): value += N mod N = value + 0 = value. Correct.
     * Actually no: mod_add_qq adds temp (=N) to value. (value + N) mod N = value. Correct.
     */

    /* Modular add: value += temp mod N = value + (N - other) mod N = (value - other) mod N */
    toffoli_mod_add_qq(circ, value_qubits, value_bits, temp_qa, n, modulus);

    /* Uncompute temp: reverse the computation
     * temp += other (QQ add: temp = N - other + other = N)
     * temp -= N (CQ add: temp = N - N = 0) */
    mod_qq_add(circ, temp_qa, n, other_qubits, other_bits, 0); /* temp += other */
    mod_cq_add(circ, temp_qa, n, -modulus);                    /* temp -= N */

    allocator_free(circ->allocator, temp_start, n);
}

/**
 * @brief Controlled QQ modular subtraction.
 */
void toffoli_cmod_sub_qq(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                         const unsigned int *other_qubits, int other_bits, int64_t modulus,
                         unsigned int ext_ctrl) {
    if (modulus <= 0)
        return;
    int n = value_bits;

    qubit_t temp_start = allocator_alloc(circ->allocator, n, true);
    if (temp_start == (qubit_t)-1)
        return;

    unsigned int temp_qa[64];
    for (int i = 0; i < n; i++)
        temp_qa[i] = temp_start + i;

    /* Compute temp = N - other (controlled) */
    mod_ccq_add(circ, temp_qa, n, modulus, ext_ctrl);
    mod_cqq_add(circ, temp_qa, n, other_qubits, other_bits, ext_ctrl, 1);

    /* Controlled modular add: value += temp mod N */
    toffoli_cmod_add_qq(circ, value_qubits, value_bits, temp_qa, n, modulus, ext_ctrl);

    /* Uncompute temp (controlled) */
    mod_cqq_add(circ, temp_qa, n, other_qubits, other_bits, ext_ctrl, 0);
    mod_ccq_add(circ, temp_qa, n, -modulus, ext_ctrl);

    allocator_free(circ->allocator, temp_start, n);
}

/* ========================================================================== */
/* Modular CQ Multiplication (Phase 92)                                        */
/* ========================================================================== */

/**
 * @brief Modular CQ multiplication: result = value * multiplier mod modulus.
 *
 * Uses schoolbook approach: for each bit j of value (quantum), performs a
 * controlled modular addition of (multiplier * 2^j) mod N to result,
 * controlled by value[j].
 *
 * result register must be pre-allocated and initialized to |0>.
 */
void toffoli_mod_mul_cq(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                        const unsigned int *result_qubits, int result_bits, int64_t multiplier,
                        int64_t modulus) {
    if (modulus <= 0)
        return;
    int n = value_bits;

    int64_t c = multiplier % modulus;
    if (c < 0)
        c += modulus;
    if (c == 0)
        return; /* result stays |0> */

    /* Special case: multiply by 1 = copy value to result via CX */
    if (c == 1) {
        for (int i = 0; i < n && i < result_bits; i++) {
            mod_emit_cx(circ, result_qubits[i], value_qubits[i]);
        }
        return;
    }

    /* Precompute shifted values: a_j = (c * 2^j) mod N */
    int64_t shifted = c;
    for (int j = 0; j < n; j++) {
        if (shifted != 0) {
            toffoli_cmod_add_cq(circ, result_qubits, result_bits, shifted, modulus,
                                value_qubits[j]);
        }
        shifted = (shifted * 2) % modulus;
    }
}

/**
 * @brief Controlled modular CQ multiplication.
 *
 * Each toffoli_cmod_add_cq must be controlled by BOTH value[j] AND ext_ctrl.
 * Uses AND-ancilla pattern for double control.
 */
void toffoli_cmod_mul_cq(circuit_t *circ, const unsigned int *value_qubits, int value_bits,
                         const unsigned int *result_qubits, int result_bits, int64_t multiplier,
                         int64_t modulus, unsigned int ext_ctrl) {
    if (modulus <= 0)
        return;
    int n = value_bits;

    int64_t c = multiplier % modulus;
    if (c < 0)
        c += modulus;
    if (c == 0)
        return;

    /* Allocate AND-ancilla for double control (reused per iteration) */
    qubit_t and_anc = allocator_alloc(circ->allocator, 1, true);
    if (and_anc == (qubit_t)-1)
        return;

    int64_t shifted = c;
    for (int j = 0; j < n; j++) {
        if (shifted != 0) {
            /* Double control: value[j] AND ext_ctrl -> and_anc */
            mod_emit_ccx(circ, and_anc, value_qubits[j], ext_ctrl);
            toffoli_cmod_add_cq(circ, result_qubits, result_bits, shifted, modulus, and_anc);
            mod_emit_ccx(circ, and_anc, value_qubits[j], ext_ctrl);
        }
        shifted = (shifted * 2) % modulus;
    }

    allocator_free(circ->allocator, and_anc, 1);
}

/* ========================================================================== */
/* Modular QQ Multiplication (Phase 92)                                        */
/* ========================================================================== */

/**
 * @brief power_mod: compute (base^exp) mod modulus.
 * Classical helper for precomputing 2^k mod N.
 */
static int64_t power_mod(int64_t base, int exp, int64_t mod) {
    int64_t result = 1;
    base = base % mod;
    for (int i = 0; i < exp; i++) {
        result = (result * base) % mod;
    }
    return result;
}

/**
 * @brief Modular QQ multiplication: result = a * b mod N.
 *
 * Algorithm:
 * 1. Compute non-modular product into 2n-bit register using toffoli_mul_qq
 * 2. For each bit k of the product (0 to 2n-1):
 *    - controlled modular add of (2^k mod N) to result, controlled by product[k]
 *    This gives: result = sum_{k where product[k]=1} (2^k mod N) = product mod N
 * 3. Uncompute product register using inverse toffoli_mul_qq
 *
 * result register must be pre-allocated and initialized to |0>.
 */
void toffoli_mod_mul_qq(circuit_t *circ, const unsigned int *a_qubits, int a_bits,
                        const unsigned int *b_qubits, int b_bits, const unsigned int *result_qubits,
                        int result_bits, int64_t modulus) {
    if (modulus <= 0)
        return;
    int n = a_bits;
    int product_bits = 2 * n;

    /* Allocate product register (2n bits, init |0>) */
    qubit_t product_start = allocator_alloc(circ->allocator, product_bits, true);
    if (product_start == (qubit_t)-1)
        return;

    unsigned int product_qa[128];
    for (int i = 0; i < product_bits; i++) {
        product_qa[i] = product_start + i;
    }

    /* Step 1: Compute non-modular product: product = a * b */
    toffoli_mul_qq(circ, product_qa, product_bits, a_qubits, a_bits, b_qubits, b_bits);

    /* Step 2: For each bit k, controlled modular add of (2^k mod N) */
    for (int k = 0; k < product_bits; k++) {
        int64_t val_k = power_mod(2, k, modulus);
        if (val_k != 0) {
            toffoli_cmod_add_cq(circ, result_qubits, result_bits, val_k, modulus, product_qa[k]);
        }
    }

    /* Step 3: Uncompute product (inverse multiply) */
    /* We need to run toffoli_mul_qq in reverse. Since it uses run_instruction
     * internally, we need to reverse the circuit range.
     * Alternative: use reverse_circuit_range on the section we emitted.
     *
     * Actually, the cleanest approach: re-run toffoli_mul_qq and then
     * reverse the section. But that's expensive.
     *
     * Better approach: since product = a * b and both a and b are preserved,
     * we can compute a * b again and XOR with product to zero it.
     * But toffoli_mul_qq does product += a * b (accumulates), so running it
     * again would give product = 2 * a * b, not 0.
     *
     * The correct uncomputation: for each bit j of b (in reverse order),
     * undo the controlled addition. This is the inverse of the multiply.
     *
     * Simplest correct approach: Record circuit position before multiply,
     * then use reverse_circuit_range to create the inverse.
     */
    int start_layer = circ->used_layer;
    toffoli_mul_qq(circ, product_qa, product_bits, a_qubits, a_bits, b_qubits, b_bits);
    int end_layer = circ->used_layer;
    reverse_circuit_range(circ, start_layer, end_layer);

    allocator_free(circ->allocator, product_start, product_bits);
}

/**
 * @brief Controlled modular QQ multiplication.
 */
void toffoli_cmod_mul_qq(circuit_t *circ, const unsigned int *a_qubits, int a_bits,
                         const unsigned int *b_qubits, int b_bits,
                         const unsigned int *result_qubits, int result_bits, int64_t modulus,
                         unsigned int ext_ctrl) {
    if (modulus <= 0)
        return;
    int n = a_bits;
    int product_bits = 2 * n;

    qubit_t product_start = allocator_alloc(circ->allocator, product_bits, true);
    if (product_start == (qubit_t)-1)
        return;

    unsigned int product_qa[128];
    for (int i = 0; i < product_bits; i++) {
        product_qa[i] = product_start + i;
    }

    /* Controlled multiply: product = a * b (controlled by ext_ctrl) */
    toffoli_cmul_qq(circ, product_qa, product_bits, a_qubits, a_bits, b_qubits, b_bits, ext_ctrl);

    /* Allocate AND-ancilla for double control */
    qubit_t and_anc = allocator_alloc(circ->allocator, 1, true);
    if (and_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, product_start, product_bits);
        return;
    }

    /* For each bit k, doubly-controlled modular add (product[k] AND ext_ctrl) */
    for (int k = 0; k < product_bits; k++) {
        int64_t val_k = power_mod(2, k, modulus);
        if (val_k != 0) {
            mod_emit_ccx(circ, and_anc, product_qa[k], ext_ctrl);
            toffoli_cmod_add_cq(circ, result_qubits, result_bits, val_k, modulus, and_anc);
            mod_emit_ccx(circ, and_anc, product_qa[k], ext_ctrl);
        }
    }

    allocator_free(circ->allocator, and_anc, 1);

    /* Uncompute product (controlled inverse multiply) */
    int start_layer = circ->used_layer;
    toffoli_cmul_qq(circ, product_qa, product_bits, a_qubits, a_bits, b_qubits, b_bits, ext_ctrl);
    int end_layer = circ->used_layer;
    reverse_circuit_range(circ, start_layer, end_layer);

    allocator_free(circ->allocator, product_start, product_bits);
}
