/**
 * @file ToffoliMultiplication.c
 * @brief Toffoli-based schoolbook multiplication (Phase 68, 69, 72).
 *
 * Implements shift-and-add multiplication using the CDKM ripple-carry adders
 * from ToffoliAddition.c as subroutines. Each multiplier bit controls whether
 * a shifted copy of the multiplicand is added to the result accumulator.
 *
 * Phase 72 optimization (MUL-05): QQ multiplication uses AND-ancilla
 * decomposition of MCX(3-control) gates. Instead of calling the cached
 * toffoli_cQQ_add() sequence (which contains MCX gates with 3 controls),
 * the controlled CDKM adder is built inline with each MCX decomposed into
 * 3 CCX gates via AND-ancilla. This eliminates ALL 3-control gates from
 * uncontrolled QQ multiplication.
 *
 * Four variants:
 *   toffoli_mul_qq   -- quantum * quantum (AND-decomposed controlled additions)
 *   toffoli_mul_cq   -- quantum * classical (uncontrolled additions for set bits)
 *   toffoli_cmul_qq  -- controlled quantum * quantum (AND-ancilla + cQQ adder)
 *   toffoli_cmul_cq  -- controlled quantum * classical (cQQ adder with ext_ctrl)
 *
 * Qubit arrays use LSB-first convention from the C hot path perspective:
 *   index 0 = LSB (weight 2^0), index n-1 = MSB (weight 2^(n-1)).
 * This matches the CDKM adder's internal convention.
 *
 * References:
 *   Schoolbook multiplication: sum_{j=0}^{n-1} a * b[j] * 2^j
 *   CDKM adder: Cuccaro et al., arXiv:quant-ph/0410184
 *   AND-ancilla decomposition: Beauregard (2003), Haner et al. (2018)
 */

#include "Integer.h"
#include "QPU.h"
#include "execution.h"
#include "gate.h"
#include "optimizer.h"
#include "qubit_allocator.h"
#include "toffoli_arithmetic_ops.h"

#include <stdlib.h>
#include <string.h>

// ============================================================================
// AND-ancilla MCX decomposition helpers (Phase 72, MUL-05)
// ============================================================================

/**
 * @brief Emit decomposed cMAJ using AND-ancilla to eliminate MCX(3-control).
 *
 * Original cMAJ(a, b, c, ext_ctrl):
 *   1. CCX(target=b, ctrl1=c, ctrl2=ext_ctrl)
 *   2. CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)
 *   3. MCX(target=c, controls=[a, b, ext_ctrl])  <-- 3-control gate
 *
 * Decomposed cMAJ replaces MCX(c, [a,b,ext]) with:
 *   3a. CCX(target=and_anc, ctrl1=a, ctrl2=b)       -- compute partial AND
 *   3b. CCX(target=c, ctrl1=and_anc, ctrl2=ext_ctrl) -- apply via AND-ancilla
 *   3c. CCX(target=and_anc, ctrl1=a, ctrl2=b)       -- uncompute AND
 *
 * Total: 5 CCX gates, zero MCX(3-control) gates.
 *
 * @param circ     Active circuit (gates emitted directly via add_gate)
 * @param a        Qubit index for 'a' (carry-in / previous carry)
 * @param b        Qubit index for 'b' (source bit)
 * @param c        Qubit index for 'c' (target bit, becomes carry-out)
 * @param ext_ctrl Qubit index for external control qubit
 * @param and_anc  Qubit index for AND-ancilla (reused, starts and ends at |0>)
 */
static void emit_cMAJ_decomposed(circuit_t *circ, int a, int b, int c, int ext_ctrl, int and_anc) {
    gate_t g;

    /* Step 1: CCX(target=b, ctrl1=c, ctrl2=ext_ctrl) */
    memset(&g, 0, sizeof(gate_t));
    ccx(&g, (qubit_t)b, (qubit_t)c, (qubit_t)ext_ctrl);
    add_gate(circ, &g);

    /* Step 2: CCX(target=a, ctrl1=c, ctrl2=ext_ctrl) */
    memset(&g, 0, sizeof(gate_t));
    ccx(&g, (qubit_t)a, (qubit_t)c, (qubit_t)ext_ctrl);
    add_gate(circ, &g);

    /* Step 3a: CCX(target=and_anc, ctrl1=a, ctrl2=b) -- compute AND */
    memset(&g, 0, sizeof(gate_t));
    ccx(&g, (qubit_t)and_anc, (qubit_t)a, (qubit_t)b);
    add_gate(circ, &g);

    /* Step 3b: CCX(target=c, ctrl1=and_anc, ctrl2=ext_ctrl) */
    memset(&g, 0, sizeof(gate_t));
    ccx(&g, (qubit_t)c, (qubit_t)and_anc, (qubit_t)ext_ctrl);
    add_gate(circ, &g);

    /* Step 3c: CCX(target=and_anc, ctrl1=a, ctrl2=b) -- uncompute AND */
    memset(&g, 0, sizeof(gate_t));
    ccx(&g, (qubit_t)and_anc, (qubit_t)a, (qubit_t)b);
    add_gate(circ, &g);
}

/**
 * @brief Emit decomposed cUMA using AND-ancilla to eliminate MCX(3-control).
 *
 * Original cUMA(a, b, c, ext_ctrl):
 *   1. MCX(target=c, controls=[a, b, ext_ctrl])  <-- 3-control gate
 *   2. CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)
 *   3. CCX(target=b, ctrl1=a, ctrl2=ext_ctrl)
 *
 * Decomposed cUMA replaces MCX(c, [a,b,ext]) with:
 *   1a. CCX(target=and_anc, ctrl1=a, ctrl2=b)       -- compute partial AND
 *   1b. CCX(target=c, ctrl1=and_anc, ctrl2=ext_ctrl) -- apply via AND-ancilla
 *   1c. CCX(target=and_anc, ctrl1=a, ctrl2=b)       -- uncompute AND
 *
 * Total: 5 CCX gates, zero MCX(3-control) gates.
 *
 * @param circ     Active circuit (gates emitted directly via add_gate)
 * @param a        Qubit index for 'a'
 * @param b        Qubit index for 'b' (becomes sum bit)
 * @param c        Qubit index for 'c'
 * @param ext_ctrl Qubit index for external control qubit
 * @param and_anc  Qubit index for AND-ancilla (reused, starts and ends at |0>)
 */
static void emit_cUMA_decomposed(circuit_t *circ, int a, int b, int c, int ext_ctrl, int and_anc) {
    gate_t g;

    /* Step 1a: CCX(target=and_anc, ctrl1=a, ctrl2=b) -- compute AND */
    memset(&g, 0, sizeof(gate_t));
    ccx(&g, (qubit_t)and_anc, (qubit_t)a, (qubit_t)b);
    add_gate(circ, &g);

    /* Step 1b: CCX(target=c, ctrl1=and_anc, ctrl2=ext_ctrl) */
    memset(&g, 0, sizeof(gate_t));
    ccx(&g, (qubit_t)c, (qubit_t)and_anc, (qubit_t)ext_ctrl);
    add_gate(circ, &g);

    /* Step 1c: CCX(target=and_anc, ctrl1=a, ctrl2=b) -- uncompute AND */
    memset(&g, 0, sizeof(gate_t));
    ccx(&g, (qubit_t)and_anc, (qubit_t)a, (qubit_t)b);
    add_gate(circ, &g);

    /* Step 2: CCX(target=a, ctrl1=c, ctrl2=ext_ctrl) */
    memset(&g, 0, sizeof(gate_t));
    ccx(&g, (qubit_t)a, (qubit_t)c, (qubit_t)ext_ctrl);
    add_gate(circ, &g);

    /* Step 3: CCX(target=b, ctrl1=a, ctrl2=ext_ctrl) */
    memset(&g, 0, sizeof(gate_t));
    ccx(&g, (qubit_t)b, (qubit_t)a, (qubit_t)ext_ctrl);
    add_gate(circ, &g);
}

/**
 * @brief Emit a decomposed controlled CDKM addition inline (no MCX(3+) gates).
 *
 * Replaces toffoli_cQQ_add(width) by emitting the controlled CDKM adder
 * directly into the circuit using decomposed cMAJ/cUMA helpers. Each MCX
 * with 3 controls is decomposed into 3 CCX gates via AND-ancilla.
 *
 * Uses the same qubit semantics as the CDKM adder:
 *   - Forward sweep: decomposed-cMAJ on each bit position
 *   - Reverse sweep: decomposed-cUMA on each bit position (reverse order)
 *
 * @param circ     Active circuit
 * @param a_qubits Source register (preserved), length = width
 * @param b_qubits Target register (gets sum), length = width
 * @param carry    Carry ancilla qubit (starts and ends at |0>)
 * @param ext_ctrl External control qubit
 * @param and_anc  AND-ancilla qubit (starts and ends at |0>)
 * @param width    Number of bits in the addition (>= 2)
 */
static void emit_controlled_add_decomposed(circuit_t *circ, const unsigned int *a_qubits,
                                           const unsigned int *b_qubits, unsigned int carry,
                                           unsigned int ext_ctrl, unsigned int and_anc, int width) {
    /* Forward cMAJ sweep */
    /* First: cMAJ(carry, b[0], a[0], ext_ctrl) */
    emit_cMAJ_decomposed(circ, (int)carry, (int)b_qubits[0], (int)a_qubits[0], (int)ext_ctrl,
                         (int)and_anc);

    /* Remaining: cMAJ(a[i-1], b[i], a[i], ext_ctrl) for i = 1..width-1 */
    for (int i = 1; i < width; i++) {
        emit_cMAJ_decomposed(circ, (int)a_qubits[i - 1], (int)b_qubits[i], (int)a_qubits[i],
                             (int)ext_ctrl, (int)and_anc);
    }

    /* Reverse cUMA sweep */
    for (int i = width - 1; i >= 1; i--) {
        emit_cUMA_decomposed(circ, (int)a_qubits[i - 1], (int)b_qubits[i], (int)a_qubits[i],
                             (int)ext_ctrl, (int)and_anc);
    }

    /* Last: cUMA(carry, b[0], a[0], ext_ctrl) */
    emit_cUMA_decomposed(circ, (int)carry, (int)b_qubits[0], (int)a_qubits[0], (int)ext_ctrl,
                         (int)and_anc);
}

/**
 * @brief Toffoli schoolbook QQ multiplication: ret = self * other.
 *
 * Uses AND-ancilla decomposed controlled CDKM adders (Phase 72 optimization):
 * for each bit j of the multiplier (other), performs a controlled addition of
 * self[0..width-1] into ret[j..j+width-1], controlled by other[j].
 *
 * The controlled addition is emitted inline with each MCX(3-control) gate
 * decomposed into 3 CCX gates via an AND-ancilla. This eliminates ALL
 * 3-control gates from the multiplication circuit.
 *
 * Ancilla budget: 1 carry + 1 AND = 2 ancilla (allocated before loop, reused
 * per iteration -- both CDKM carry and AND-ancilla return to |0> each iteration).
 *
 * The shift is implicit: adding into ret[j..] effectively multiplies by 2^j.
 * Each iteration uses progressively smaller addition width (n-j).
 *
 * LSB-first convention: index 0 = LSB, index n-1 = MSB.
 *
 * @param circ          Active circuit
 * @param ret_qubits    Result register (accumulator, starts at |0>)
 * @param ret_bits      Width of result register (n)
 * @param self_qubits   Multiplicand register (preserved)
 * @param self_bits     Width of multiplicand
 * @param other_qubits  Multiplier register (preserved, each bit used as control)
 * @param other_bits    Width of multiplier
 */
void toffoli_mul_qq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                    const unsigned int *self_qubits, int self_bits,
                    const unsigned int *other_qubits, int other_bits) {
    int n = ret_bits;

    /* Allocate 1 carry ancilla before the loop (reused, CDKM returns to |0>) */
    qubit_t carry = allocator_alloc(circ->allocator, 1, true);
    if (carry == (qubit_t)-1)
        return;

    /* Allocate 1 AND-ancilla for MCX decomposition (reused, uncomputed each step) */
    qubit_t and_anc = allocator_alloc(circ->allocator, 1, true);
    if (and_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, carry, 1);
        return;
    }

    for (int j = 0; j < n; j++) {
        int width = n - j; /* Addition width for this iteration */
        if (width < 1)
            break;

        if (width == 1) {
            /* 1-bit controlled addition: CCX (2 controls, no MCX needed)
             * ret[n-1] ^= self[0] AND other[j]
             *
             * LSB-first: ret[n-1] = MSB of ret, self[0] = LSB of self,
             *            other[j] = multiplier bit with weight 2^j.
             * For j = n-1: adds self[0] (LSB) into ret[n-1] (MSB). */
            gate_t g;
            memset(&g, 0, sizeof(gate_t));
            ccx(&g, ret_qubits[n - 1], self_qubits[0], other_qubits[j]);
            add_gate(circ, &g);
        } else {
            /* General case: AND-decomposed controlled addition of width bits.
             *
             * Uses decomposed cMAJ/cUMA that replace MCX(3-control) with
             * 3 CCX gates each via AND-ancilla pattern.
             *
             * Qubit mapping:
             *   a-register = self[0..width-1] (multiplicand, preserved)
             *   b-register = ret[j..j+width-1] (accumulator, gets sum)
             *   carry      = carry ancilla (reused)
             *   ext_ctrl   = other[j] (multiplier bit with weight 2^j)
             *   and_anc    = AND-ancilla (reused)
             */
            emit_controlled_add_decomposed(circ, self_qubits, &ret_qubits[j], carry,
                                           other_qubits[j], and_anc, width);
        }
    }

    allocator_free(circ->allocator, and_anc, 1);
    allocator_free(circ->allocator, carry, 1);
}

/**
 * @brief Toffoli schoolbook CQ multiplication: ret = self * classical_value.
 *
 * Decomposes classical_value into binary. For each set bit j (weight 2^j),
 * performs an uncontrolled addition of self[0..width-1] into ret[j..j+width-1].
 *
 * Only adds for set bits of the classical value (compile-time decision),
 * so uses cheaper uncontrolled CDKM adders (toffoli_QQ_add).
 *
 * LSB-first convention: index 0 = LSB, index n-1 = MSB.
 *
 * @param circ            Active circuit
 * @param ret_qubits      Result register (accumulator, starts at |0>)
 * @param ret_bits        Width of result register (n)
 * @param self_qubits     Multiplicand register (preserved)
 * @param self_bits       Width of multiplicand
 * @param classical_value Classical integer to multiply by
 */
void toffoli_mul_cq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                    const unsigned int *self_qubits, int self_bits, int64_t classical_value) {
    int n = ret_bits;

    /* Convert classical value to binary (MSB-first: bin[0]=MSB, bin[n-1]=LSB) */
    int *bin = two_complement(classical_value, n);
    if (bin == NULL)
        return;

    for (int j = 0; j < n; j++) {
        /* bin is MSB-first: bin[0]=MSB, bin[n-1]=LSB
         * Bit j (weight 2^j) is at bin[n-1-j] */
        if (bin[n - 1 - j] == 0)
            continue; /* Skip zero bits */

        int width = n - j;
        if (width < 1)
            break;

        unsigned int tqa[256];
        sequence_t *toff_seq;

        if (width == 1) {
            /* 1-bit uncontrolled addition: CNOT
             * toffoli_QQ_add(1) layout: [0]=target, [1]=source
             *
             * LSB-first: ret[n-1] = MSB of ret, self[0] = LSB of self */
            tqa[0] = ret_qubits[n - 1];
            tqa[1] = self_qubits[0];

            toff_seq = toffoli_QQ_add(1);
            if (toff_seq == NULL) {
                free(bin);
                return;
            }
            run_instruction(toff_seq, tqa, 0, circ);
        } else {
            /* General case: uncontrolled addition of width bits */
            qubit_t ancilla = allocator_alloc(circ->allocator, 1, true);
            if (ancilla == (qubit_t)-1) {
                free(bin);
                return;
            }

            /* CDKM convention (matching hot_path_add.c):
             *   a-register [0..width-1]       = source (preserved)
             *   b-register [width..2*width-1]  = target (gets sum)
             *   [2*width]                      = carry ancilla
             *
             * For classical bit j (weight 2^j):
             *   self slice: self[0..width-1] (the lower width=n-j bits of multiplicand)
             *   ret slice:  ret[j..j+width-1] (shifted by j positions in result)
             */

            /* a-register = self[0..width-1] (multiplicand lower bits, preserved) */
            for (int i = 0; i < width; i++) {
                tqa[i] = self_qubits[i];
            }
            /* b-register = ret[j..j+width-1] (accumulator, shifted, modified) */
            for (int i = 0; i < width; i++) {
                tqa[width + i] = ret_qubits[j + i];
            }
            /* carry ancilla */
            tqa[2 * width] = ancilla;

            toff_seq = toffoli_QQ_add(width);
            if (toff_seq == NULL) {
                allocator_free(circ->allocator, ancilla, 1);
                free(bin);
                return;
            }
            run_instruction(toff_seq, tqa, 0, circ);
            allocator_free(circ->allocator, ancilla, 1);
        }
    }

    free(bin);
}

// ============================================================================
// Controlled Toffoli Multiplication (Phase 69)
// ============================================================================

/**
 * @brief Controlled Toffoli QQ multiplication: ret = self * other, controlled by ext_ctrl.
 *
 * Uses the AND-ancilla pattern: for each multiplier bit other[j], computes
 * and_ancilla = other[j] AND ext_ctrl via CCX, then uses and_ancilla as the
 * single control for toffoli_cQQ_add. Uncomputes AND after each adder call
 * (CCX is self-inverse; other[j] and ext_ctrl are preserved by the adder).
 *
 * For width 1 (j == n-1): emits a single MCX with 3 controls
 * (self[0], other[j], ext_ctrl) targeting ret[n-1], avoiding the AND-ancilla
 * overhead for the trivial case.
 *
 * Ancilla budget: 1 carry + 1 AND = 2 ancilla allocated before loop, freed after.
 *
 * @param circ          Active circuit
 * @param ret_qubits    Result register (accumulator, starts at |0>)
 * @param ret_bits      Width of result register (n)
 * @param self_qubits   Multiplicand register (preserved)
 * @param self_bits     Width of multiplicand
 * @param other_qubits  Multiplier register (preserved)
 * @param other_bits    Width of multiplier
 * @param ext_ctrl      External control qubit
 */
void toffoli_cmul_qq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                     const unsigned int *self_qubits, int self_bits,
                     const unsigned int *other_qubits, int other_bits, unsigned int ext_ctrl) {
    int n = ret_bits;

    /* Allocate 1 carry ancilla (reused per iteration, CDKM returns to |0>) */
    qubit_t carry = allocator_alloc(circ->allocator, 1, true);
    if (carry == (qubit_t)-1)
        return;

    /* Allocate 1 AND ancilla (reused per iteration, uncomputed after each adder) */
    qubit_t and_anc = allocator_alloc(circ->allocator, 1, true);
    if (and_anc == (qubit_t)-1) {
        allocator_free(circ->allocator, carry, 1);
        return;
    }

    for (int j = 0; j < n; j++) {
        int width = n - j; /* Addition width for this iteration */
        if (width < 1)
            break;

        if (width == 1) {
            /* 1-bit controlled multiplication: ret[n-1] ^= self[0] AND other[j] AND ext_ctrl.
             * Phase 74-03: Decompose MCX(3) into 3 CCX via AND-ancilla.
             *   CCX(and_anc, self[0], other[j])       -- compute partial AND
             *   CCX(ret[n-1], and_anc, ext_ctrl)      -- apply
             *   CCX(and_anc, self[0], other[j])       -- uncompute AND */
            gate_t g;

            /* Compute AND */
            memset(&g, 0, sizeof(gate_t));
            ccx(&g, and_anc, self_qubits[0], other_qubits[j]);
            add_gate(circ, &g);

            /* Apply via AND-ancilla */
            memset(&g, 0, sizeof(gate_t));
            ccx(&g, ret_qubits[n - 1], and_anc, ext_ctrl);
            add_gate(circ, &g);

            /* Uncompute AND */
            memset(&g, 0, sizeof(gate_t));
            ccx(&g, and_anc, self_qubits[0], other_qubits[j]);
            add_gate(circ, &g);
        } else {
            /* General case: AND-ancilla pattern for controlled addition.
             *
             * Step 1: Compute AND: and_anc = other[j] AND ext_ctrl
             *         CCX(target=and_anc, ctrl1=other_qubits[j], ctrl2=ext_ctrl) */
            gate_t g;
            memset(&g, 0, sizeof(gate_t));
            ccx(&g, and_anc, other_qubits[j], ext_ctrl);
            add_gate(circ, &g);

            /* Step 2: Build tqa for toffoli_cQQ_add(width) with and_anc as control.
             * Phase 74-03: cQQ_add now expects AND-ancilla at [2*width+2].
             * We allocate a second AND-ancilla for the cQQ_add sequence itself
             * (the outer and_anc is used as ext_ctrl, the inner one is for the
             * decomposed MCX gates within cQQ_add).
             *   a-register [0..width-1]       = self[0..width-1] (source, preserved)
             *   b-register [width..2*width-1]  = ret[j..j+width-1] (accumulator)
             *   [2*width]                      = carry ancilla
             *   [2*width+1]                    = and_anc (control for cQQ_add)
             *   [2*width+2]                    = inner AND-ancilla for cQQ_add MCX decomp */
            /* Allocate inner AND-ancilla for cQQ_add's decomposed MCX gates */
            qubit_t inner_and = allocator_alloc(circ->allocator, 1, true);
            if (inner_and == (qubit_t)-1) {
                allocator_free(circ->allocator, and_anc, 1);
                allocator_free(circ->allocator, carry, 1);
                return;
            }

            unsigned int tqa[256];
            for (int i = 0; i < width; i++) {
                tqa[i] = self_qubits[i];
            }
            for (int i = 0; i < width; i++) {
                tqa[width + i] = ret_qubits[j + i];
            }
            tqa[2 * width] = carry;
            tqa[2 * width + 1] = and_anc;
            tqa[2 * width + 2] = inner_and;

            sequence_t *toff_seq = toffoli_cQQ_add(width);
            if (toff_seq == NULL) {
                allocator_free(circ->allocator, inner_and, 1);
                allocator_free(circ->allocator, and_anc, 1);
                allocator_free(circ->allocator, carry, 1);
                return;
            }
            run_instruction(toff_seq, tqa, 0, circ);
            allocator_free(circ->allocator, inner_and, 1);

            /* Step 3: Uncompute AND: and_anc = 0 (CCX is self-inverse).
             * Safe because other[j] and ext_ctrl are preserved by cQQ_add. */
            memset(&g, 0, sizeof(gate_t));
            ccx(&g, and_anc, other_qubits[j], ext_ctrl);
            add_gate(circ, &g);
        }
    }

    allocator_free(circ->allocator, and_anc, 1);
    allocator_free(circ->allocator, carry, 1);
}

/**
 * @brief Controlled Toffoli CQ multiplication: ret = self * classical_value, controlled.
 *
 * For each set bit j of classical_value (weight 2^j), performs a controlled
 * addition of self[0..width-1] into ret[j..j+width-1], controlled by ext_ctrl.
 *
 * Uses toffoli_cQQ_add with ext_ctrl mapped to the control slot. No AND-ancilla
 * needed because the classical bit selection is compile-time; only the runtime
 * external control needs to gate each addition.
 *
 * For width 1: uses toffoli_cQQ_add(1) layout [target, source, ext_ctrl] which
 * emits a CCX.
 *
 * @param circ            Active circuit
 * @param ret_qubits      Result register (accumulator, starts at |0>)
 * @param ret_bits        Width of result register (n)
 * @param self_qubits     Multiplicand register (preserved)
 * @param self_bits       Width of multiplicand
 * @param classical_value Classical integer to multiply by
 * @param ext_ctrl        External control qubit
 */
void toffoli_cmul_cq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                     const unsigned int *self_qubits, int self_bits, int64_t classical_value,
                     unsigned int ext_ctrl) {
    int n = ret_bits;

    /* Convert classical value to binary (MSB-first: bin[0]=MSB, bin[n-1]=LSB) */
    int *bin = two_complement(classical_value, n);
    if (bin == NULL)
        return;

    /* Allocate 1 carry ancilla before the loop (reused, CDKM returns to |0>) */
    qubit_t carry = allocator_alloc(circ->allocator, 1, true);
    if (carry == (qubit_t)-1) {
        free(bin);
        return;
    }

    for (int j = 0; j < n; j++) {
        /* bin is MSB-first: bin[0]=MSB, bin[n-1]=LSB
         * Bit j (weight 2^j) is at bin[n-1-j] */
        if (bin[n - 1 - j] == 0)
            continue; /* Skip zero bits */

        int width = n - j;
        if (width < 1)
            break;

        unsigned int tqa[256];
        sequence_t *toff_seq;

        if (width == 1) {
            /* 1-bit controlled addition: CCX via toffoli_cQQ_add(1).
             * toffoli_cQQ_add(1) layout: [0]=target, [1]=source, [2]=control
             * target=ret[n-1], source=self[0], control=ext_ctrl */
            tqa[0] = ret_qubits[n - 1];
            tqa[1] = self_qubits[0];
            tqa[2] = ext_ctrl;

            toff_seq = toffoli_cQQ_add(1);
            if (toff_seq == NULL) {
                allocator_free(circ->allocator, carry, 1);
                free(bin);
                return;
            }
            run_instruction(toff_seq, tqa, 0, circ);
        } else {
            /* General case: controlled addition using toffoli_cQQ_add.
             * Phase 74-03: cQQ_add now expects AND-ancilla at [2*width+2].
             *   a-register [0..width-1]       = self[0..width-1] (source, preserved)
             *   b-register [width..2*width-1]  = ret[j..j+width-1] (accumulator)
             *   [2*width]                      = carry ancilla
             *   [2*width+1]                    = ext_ctrl (external control)
             *   [2*width+2]                    = AND-ancilla for cQQ_add MCX decomp */
            qubit_t cq_and = allocator_alloc(circ->allocator, 1, true);
            if (cq_and == (qubit_t)-1) {
                allocator_free(circ->allocator, carry, 1);
                free(bin);
                return;
            }

            for (int i = 0; i < width; i++) {
                tqa[i] = self_qubits[i];
            }
            for (int i = 0; i < width; i++) {
                tqa[width + i] = ret_qubits[j + i];
            }
            tqa[2 * width] = carry;
            tqa[2 * width + 1] = ext_ctrl;
            tqa[2 * width + 2] = cq_and;

            toff_seq = toffoli_cQQ_add(width);
            if (toff_seq == NULL) {
                allocator_free(circ->allocator, cq_and, 1);
                allocator_free(circ->allocator, carry, 1);
                free(bin);
                return;
            }
            run_instruction(toff_seq, tqa, 0, circ);
            allocator_free(circ->allocator, cq_and, 1);
        }
    }

    allocator_free(circ->allocator, carry, 1);
    free(bin);
}
