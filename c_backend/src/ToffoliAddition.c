/**
 * @file ToffoliAddition.c
 * @brief CDKM ripple-carry adder implementation (Phase 66-67).
 *
 * Implements the Cuccaro-Draper-Kutin-Moulton (CDKM) ripple-carry adder
 * using MAJ (Majority) and UMA (UnMajority-and-Add) gate chains.
 *
 * The CDKM adder uses only Toffoli (CCX) and CNOT (CX) gates, making it
 * suitable for fault-tolerant quantum computation where T-gate count matters.
 *
 * Phase 66: Uncontrolled QQ and CQ adders.
 * Phase 67: Controlled variants (cQQ and cCQ) using CCX + MCX gates.
 *
 * References:
 *   Cuccaro et al., "A new quantum ripple-carry addition circuit" (2004)
 *   arXiv:quant-ph/0410184
 */

#include "Integer.h"
#include "gate.h"
#include "toffoli_arithmetic_ops.h"
#include <stdint.h>
#include <stdlib.h>

// ============================================================================
// Precompiled caches for Toffoli addition (separate from QFT cache)
// ============================================================================
static sequence_t *precompiled_toffoli_QQ_add[65] = {NULL};
static sequence_t *precompiled_toffoli_cQQ_add[65] = {NULL};
static sequence_t *precompiled_toffoli_QQ_add_bk[65] = {NULL};

// No cache for CQ/cCQ: value-dependent sequences, generated fresh each call.

// ============================================================================
// MAJ / UMA helper functions
// ============================================================================

/**
 * @brief Emit MAJ (Majority) gate triplet.
 *
 * MAJ(a, b, c):
 *   1. CNOT(target=b, control=c)     -- b ^= c
 *   2. CNOT(target=a, control=c)     -- a ^= c
 *   3. Toffoli(target=c, ctrl=a, ctrl=b) -- c ^= (a AND b)
 *
 * After MAJ: c holds the carry, a and b are in superposition.
 *
 * @param seq   Sequence to emit gates into
 * @param layer Pointer to current layer index (incremented by 3)
 * @param a     Qubit index for 'a' (carry-in / previous carry)
 * @param b     Qubit index for 'b' (source bit)
 * @param c     Qubit index for 'c' (target bit, becomes carry-out)
 */
static void emit_MAJ(sequence_t *seq, int *layer, int a, int b, int c) {
    // Step 1: CNOT(target=b, control=c)
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, c);
    (*layer)++;

    // Step 2: CNOT(target=a, control=c)
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c);
    (*layer)++;

    // Step 3: Toffoli(target=c, ctrl1=a, ctrl2=b)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
    (*layer)++;
}

/**
 * @brief Emit UMA (UnMajority-and-Add) gate triplet.
 *
 * UMA(a, b, c):
 *   1. Toffoli(target=c, ctrl=a, ctrl=b) -- undoes MAJ's Toffoli
 *   2. CNOT(target=a, control=c)          -- restores a
 *   3. CNOT(target=b, control=a)          -- b = sum bit
 *
 * After UMA: a is restored, b holds the sum bit, c is restored.
 *
 * @param seq   Sequence to emit gates into
 * @param layer Pointer to current layer index (incremented by 3)
 * @param a     Qubit index for 'a'
 * @param b     Qubit index for 'b' (becomes sum bit)
 * @param c     Qubit index for 'c'
 */
static void emit_UMA(sequence_t *seq, int *layer, int a, int b, int c) {
    // Step 1: Toffoli(target=c, ctrl1=a, ctrl2=b)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, a, b);
    (*layer)++;

    // Step 2: CNOT(target=a, control=c)
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c);
    (*layer)++;

    // Step 3: CNOT(target=b, control=a)
    cx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, a);
    (*layer)++;
}

// ============================================================================
// Controlled MAJ / UMA helper functions (Phase 67)
// ============================================================================

/**
 * @brief Emit controlled MAJ (Majority) gate triplet.
 *
 * cMAJ(a, b, c, ext_ctrl):
 *   1. CCX(target=b, ctrl1=c, ctrl2=ext_ctrl)     -- controlled b ^= c
 *   2. CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)     -- controlled a ^= c
 *   3. MCX(target=c, controls=[a, b, ext_ctrl])   -- controlled c ^= (a AND b)
 *
 * Each operation conditioned on ext_ctrl being |1>.
 *
 * @param seq      Sequence to emit gates into
 * @param layer    Pointer to current layer index (incremented by 3)
 * @param a        Qubit index for 'a' (carry-in / previous carry)
 * @param b        Qubit index for 'b' (source bit)
 * @param c        Qubit index for 'c' (target bit, becomes carry-out)
 * @param ext_ctrl Qubit index for external control qubit
 */
static void emit_cMAJ(sequence_t *seq, int *layer, int a, int b, int c, int ext_ctrl) {
    // Step 1: CCX(target=b, ctrl1=c, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, c, ext_ctrl);
    (*layer)++;

    // Step 2: CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c, ext_ctrl);
    (*layer)++;

    // Step 3: MCX(target=c, controls=[a, b, ext_ctrl]) -- 3 controls
    {
        qubit_t ctrls[3] = {(qubit_t)a, (qubit_t)b, (qubit_t)ext_ctrl};
        mcx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, ctrls, 3);
    }
    (*layer)++;
}

/**
 * @brief Emit controlled UMA (UnMajority-and-Add) gate triplet.
 *
 * cUMA(a, b, c, ext_ctrl):
 *   1. MCX(target=c, controls=[a, b, ext_ctrl])   -- undoes cMAJ's MCX
 *   2. CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)     -- controlled restore a
 *   3. CCX(target=b, ctrl1=a, ctrl2=ext_ctrl)     -- controlled b = sum bit
 *
 * Each operation conditioned on ext_ctrl being |1>.
 *
 * @param seq      Sequence to emit gates into
 * @param layer    Pointer to current layer index (incremented by 3)
 * @param a        Qubit index for 'a'
 * @param b        Qubit index for 'b' (becomes sum bit)
 * @param c        Qubit index for 'c'
 * @param ext_ctrl Qubit index for external control qubit
 */
static void emit_cUMA(sequence_t *seq, int *layer, int a, int b, int c, int ext_ctrl) {
    // Step 1: MCX(target=c, controls=[a, b, ext_ctrl]) -- 3 controls
    {
        qubit_t ctrls[3] = {(qubit_t)a, (qubit_t)b, (qubit_t)ext_ctrl};
        mcx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], c, ctrls, 3);
    }
    (*layer)++;

    // Step 2: CCX(target=a, ctrl1=c, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], a, c, ext_ctrl);
    (*layer)++;

    // Step 3: CCX(target=b, ctrl1=a, ctrl2=ext_ctrl)
    ccx(&seq->seq[*layer][seq->gates_per_layer[*layer]++], b, a, ext_ctrl);
    (*layer)++;
}

// ============================================================================
// Sequence allocation helper
// ============================================================================

/**
 * @brief Allocate a sequence with given number of layers, 1 gate per layer.
 */
static sequence_t *alloc_sequence(int num_layers) {
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL)
        return NULL;

    seq->num_layer = num_layers;
    seq->used_layer = 0;
    seq->gates_per_layer = calloc(num_layers, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(seq);
        return NULL;
    }

    seq->seq = calloc(num_layers, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(seq);
        return NULL;
    }

    for (int i = 0; i < num_layers; i++) {
        seq->seq[i] = calloc(1, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; j++) {
                free(seq->seq[j]);
            }
            free(seq->seq);
            free(seq->gates_per_layer);
            free(seq);
            return NULL;
        }
    }

    return seq;
}

// ============================================================================
// Public API
// ============================================================================

sequence_t *toffoli_QQ_add(int bits) {
    // OWNERSHIP: Returns cached sequence - DO NOT FREE
    //
    // Qubit layout for toffoli_QQ_add(bits):
    //   [0..bits-1]       = register a (target, modified in place: a += b)
    //   [bits..2*bits-1]   = register b (source, unchanged)
    //   [2*bits]           = ancilla carry (bits >= 2 only)

    // Bounds check
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Check cache
    if (precompiled_toffoli_QQ_add[bits] != NULL) {
        return precompiled_toffoli_QQ_add[bits];
    }

    // 1-bit special case: single CNOT, no ancilla
    if (bits == 1) {
        sequence_t *seq = alloc_sequence(1);
        if (seq == NULL)
            return NULL;

        // a[0] ^= b[0]: CNOT(target=0, control=1)
        cx(&seq->seq[0][seq->gates_per_layer[0]++], 0, 1);
        seq->used_layer = 1;

        precompiled_toffoli_QQ_add[bits] = seq;
        return seq;
    }

    // General case (bits >= 2): CDKM ripple-carry adder
    // Forward sweep: n MAJ calls (3n layers)
    // Reverse sweep: n UMA calls (3n layers)
    // Total: 6n layers
    int num_layers = 6 * bits;

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL)
        return NULL;

    int layer = 0;
    int ancilla = 2 * bits; // ancilla carry qubit index

    // Forward MAJ sweep
    // First: MAJ(ancilla, b[0], a[0])
    emit_MAJ(seq, &layer, ancilla, bits + 0, 0);

    // Remaining: MAJ(a[i-1], b[i], a[i]) for i = 1..bits-1
    for (int i = 1; i < bits; i++) {
        emit_MAJ(seq, &layer, i - 1, bits + i, i);
    }

    // Reverse UMA sweep
    // First (innermost): UMA(a[bits-2], b[bits-1], a[bits-1])
    for (int i = bits - 1; i >= 1; i--) {
        emit_UMA(seq, &layer, i - 1, bits + i, i);
    }

    // Last: UMA(ancilla, b[0], a[0])
    emit_UMA(seq, &layer, ancilla, bits + 0, 0);

    seq->used_layer = layer;

    // Cache and return
    precompiled_toffoli_QQ_add[bits] = seq;
    return seq;
}

sequence_t *toffoli_CQ_add(int bits, int64_t value) {
    // OWNERSHIP: Caller owns returned sequence, must free via toffoli_sequence_free()
    //
    // Qubit layout for toffoli_CQ_add(bits, value):
    //   [0..bits-1]       = temp register (initialized to classical value, cleaned to |0>)
    //   [bits..2*bits-1]  = self register (target, modified: self += value)
    //   [2*bits]          = carry ancilla (bits >= 2 only)
    //
    // Uses temp-register approach: initialize temp to classical value via X gates,
    // run the proven QQ CDKM adder (which preserves temp), then undo the X gates.
    // This avoids the buggy 2-qubit MAJ/UMA CQ simplification entirely.

    // Bounds check
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Convert value to binary (MSB-first: bin[0]=MSB, bin[bits-1]=LSB)
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    // 1-bit special case
    if (bits == 1) {
        if (bin[0] == 1) {
            // X(target=0)
            sequence_t *seq = alloc_sequence(1);
            if (seq == NULL) {
                free(bin);
                return NULL;
            }
            x(&seq->seq[0][seq->gates_per_layer[0]++], 0);
            seq->used_layer = 1;
            free(bin);
            return seq;
        } else {
            // Identity: 0-layer sequence
            sequence_t *seq = malloc(sizeof(sequence_t));
            if (seq == NULL) {
                free(bin);
                return NULL;
            }
            seq->num_layer = 0;
            seq->used_layer = 0;
            seq->gates_per_layer = NULL;
            seq->seq = NULL;
            free(bin);
            return seq;
        }
    }

    // General case (bits >= 2): temp-register + QQ CDKM adder
    //
    // Phase 1: X-init temp register (x_count X gates)
    // Phase 2: QQ CDKM adder (6*bits layers)
    // Phase 3: X-cleanup temp register (x_count X gates)
    //
    // Total layers = 2 * x_count + 6 * bits

    // Count number of 1-bits in classical value
    int x_count = 0;
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) { // LSB-first: bit i
            x_count++;
        }
    }

    int num_layers = 2 * x_count + 6 * bits;

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    int layer = 0;
    int carry = 2 * bits; // carry ancilla qubit index

    // Phase 1: X-init temp register
    // For each bit i (LSB-first), if classical bit is 1, apply X to temp qubit i
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) {
            x(&seq->seq[layer][seq->gates_per_layer[layer]++], i);
            layer++;
        }
    }

    // Phase 2: QQ CDKM adder on temp (a-register) and self (b-register)
    // a-register = [0..bits-1] (temp), b-register = [bits..2*bits-1] (self)
    // Same MAJ/UMA chain as toffoli_QQ_add

    // Forward MAJ sweep
    emit_MAJ(seq, &layer, carry, bits + 0, 0);
    for (int i = 1; i < bits; i++) {
        emit_MAJ(seq, &layer, i - 1, bits + i, i);
    }

    // Reverse UMA sweep
    for (int i = bits - 1; i >= 1; i--) {
        emit_UMA(seq, &layer, i - 1, bits + i, i);
    }
    emit_UMA(seq, &layer, carry, bits + 0, 0);

    // Phase 3: X-cleanup temp register (same X gates as Phase 1, X is self-inverse)
    // CDKM preserves a-register, so temp still holds classical value -> X undoes it
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) {
            x(&seq->seq[layer][seq->gates_per_layer[layer]++], i);
            layer++;
        }
    }

    seq->used_layer = layer;

    free(bin);
    return seq;
}

sequence_t *toffoli_cQQ_add(int bits) {
    // OWNERSHIP: Returns cached sequence - DO NOT FREE
    //
    // Qubit layout for toffoli_cQQ_add(bits):
    //   [0..bits-1]       = register a (target, modified in place: a += b)
    //   [bits..2*bits-1]   = register b (source, unchanged)
    //   [2*bits]           = ancilla carry (bits >= 2 only)
    //   [2*bits+1]         = external control qubit
    //
    // For bits == 1: no ancilla. [0]=a, [1]=b, [2]=ext_control.
    //   Single CCX(target=0, ctrl1=1, ctrl2=2). Total qubits: 3.

    // Bounds check
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Check cache
    if (precompiled_toffoli_cQQ_add[bits] != NULL) {
        return precompiled_toffoli_cQQ_add[bits];
    }

    // 1-bit special case: single CCX, no ancilla
    if (bits == 1) {
        sequence_t *seq = alloc_sequence(1);
        if (seq == NULL)
            return NULL;

        // controlled a[0] ^= b[0]: CCX(target=0, ctrl1=1, ctrl2=2)
        ccx(&seq->seq[0][seq->gates_per_layer[0]++], 0, 1, 2);
        seq->used_layer = 1;

        precompiled_toffoli_cQQ_add[bits] = seq;
        return seq;
    }

    // General case (bits >= 2): controlled CDKM ripple-carry adder
    // Forward sweep: n cMAJ calls (3n layers)
    // Reverse sweep: n cUMA calls (3n layers)
    // Total: 6n layers
    int num_layers = 6 * bits;

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL)
        return NULL;

    int layer = 0;
    int ancilla = 2 * bits;      // ancilla carry qubit index
    int ext_ctrl = 2 * bits + 1; // external control qubit

    // Forward cMAJ sweep
    // First: cMAJ(ancilla, b[0], a[0], ext_ctrl)
    emit_cMAJ(seq, &layer, ancilla, bits + 0, 0, ext_ctrl);

    // Remaining: cMAJ(a[i-1], b[i], a[i], ext_ctrl) for i = 1..bits-1
    for (int i = 1; i < bits; i++) {
        emit_cMAJ(seq, &layer, i - 1, bits + i, i, ext_ctrl);
    }

    // Reverse cUMA sweep
    for (int i = bits - 1; i >= 1; i--) {
        emit_cUMA(seq, &layer, i - 1, bits + i, i, ext_ctrl);
    }

    // Last: cUMA(ancilla, b[0], a[0], ext_ctrl)
    emit_cUMA(seq, &layer, ancilla, bits + 0, 0, ext_ctrl);

    seq->used_layer = layer;

    // Cache and return
    precompiled_toffoli_cQQ_add[bits] = seq;
    return seq;
}

sequence_t *toffoli_cCQ_add(int bits, int64_t value) {
    // OWNERSHIP: Caller owns returned sequence, must free via toffoli_sequence_free()
    //
    // Qubit layout for toffoli_cCQ_add(bits, value):
    //   [0..bits-1]       = temp register (controlled init to classical value, controlled cleanup)
    //   [bits..2*bits-1]  = self register (target, modified: self += value)
    //   [2*bits]          = carry ancilla (bits >= 2 only)
    //   [2*bits+1]        = external control qubit
    //
    // Uses controlled temp-register approach: CX(target=temp[i], control=ext_ctrl)
    // for initialization, controlled CDKM adder core, then CX cleanup.
    // NOT cached (value-dependent).

    // Bounds check
    if (bits < 1 || bits > 64) {
        return NULL;
    }

    // Convert value to binary (MSB-first: bin[0]=MSB, bin[bits-1]=LSB)
    int *bin = two_complement(value, bits);
    if (bin == NULL) {
        return NULL;
    }

    // 1-bit special case
    if (bits == 1) {
        if (bin[0] == 1) {
            // CX(target=0, control=1) where [0]=self, [1]=ext_control
            sequence_t *seq = alloc_sequence(1);
            if (seq == NULL) {
                free(bin);
                return NULL;
            }
            cx(&seq->seq[0][seq->gates_per_layer[0]++], 0, 1);
            seq->used_layer = 1;
            free(bin);
            return seq;
        } else {
            // Identity: 0-layer sequence
            sequence_t *seq = malloc(sizeof(sequence_t));
            if (seq == NULL) {
                free(bin);
                return NULL;
            }
            seq->num_layer = 0;
            seq->used_layer = 0;
            seq->gates_per_layer = NULL;
            seq->seq = NULL;
            free(bin);
            return seq;
        }
    }

    // General case (bits >= 2): controlled temp-register + controlled CDKM adder
    //
    // Phase 1: CX-init temp register (x_count CX gates, conditioned on ext_ctrl)
    // Phase 2: Controlled QQ CDKM adder (6*bits layers using cMAJ/cUMA)
    // Phase 3: CX-cleanup temp register (x_count CX gates, same as Phase 1)
    //
    // Total layers = 2 * x_count + 6 * bits

    // Count number of 1-bits in classical value
    int x_count = 0;
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) { // LSB-first: bit i
            x_count++;
        }
    }

    int num_layers = 2 * x_count + 6 * bits;
    int ext_ctrl = 2 * bits + 1; // external control qubit

    sequence_t *seq = alloc_sequence(num_layers);
    if (seq == NULL) {
        free(bin);
        return NULL;
    }

    int layer = 0;
    int carry = 2 * bits; // carry ancilla qubit index

    // Phase 1: CX-init temp register (controlled by ext_ctrl)
    // For each bit i (LSB-first), if classical bit is 1, emit CX(target=i, control=ext_ctrl)
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) {
            cx(&seq->seq[layer][seq->gates_per_layer[layer]++], i, ext_ctrl);
            layer++;
        }
    }

    // Phase 2: Controlled QQ CDKM adder on temp (a-register) and self (b-register)
    // a-register = [0..bits-1] (temp), b-register = [bits..2*bits-1] (self)
    // Same cMAJ/cUMA chain as toffoli_cQQ_add, with ext_ctrl

    // Forward cMAJ sweep
    emit_cMAJ(seq, &layer, carry, bits + 0, 0, ext_ctrl);
    for (int i = 1; i < bits; i++) {
        emit_cMAJ(seq, &layer, i - 1, bits + i, i, ext_ctrl);
    }

    // Reverse cUMA sweep
    for (int i = bits - 1; i >= 1; i--) {
        emit_cUMA(seq, &layer, i - 1, bits + i, i, ext_ctrl);
    }
    emit_cUMA(seq, &layer, carry, bits + 0, 0, ext_ctrl);

    // Phase 3: CX-cleanup temp register (same CX gates as Phase 1, CX is self-inverse
    // when temp has been preserved by CDKM)
    for (int i = 0; i < bits; i++) {
        if (bin[bits - 1 - i] == 1) {
            cx(&seq->seq[layer][seq->gates_per_layer[layer]++], i, ext_ctrl);
            layer++;
        }
    }

    seq->used_layer = layer;

    free(bin);
    return seq;
}

// ============================================================================
// Brent-Kung Carry Look-Ahead Adder (Phase 71)
// ============================================================================

/**
 * @brief Brent-Kung CLA QQ adder: b += a (in-place on b-register).
 *
 * STUB: Returns NULL to fall through to RCA (CDKM) adder.
 *
 * The Brent-Kung parallel prefix CLA algorithm has a fundamental ancilla
 * uncomputation challenge for in-place quantum addition: after computing
 * carries via the prefix tree and extracting sums, the tree cannot be
 * reversed because the propagate controls (stored in b) have been modified
 * by the sum computation. This creates a chicken-and-egg problem where
 * cleaning ancilla requires original b values, but the sum computation
 * (which is the desired output) destroys those values.
 *
 * The CLA infrastructure (cla_override field, option plumbing, dispatch
 * logic in hot_path_add.c, ancilla allocation) is fully in place. When
 * this function returns NULL, the dispatch silently falls through to the
 * proven CDKM RCA adder.
 *
 * Future work: implement using a hybrid CLA-RCA approach (e.g., CLA tree
 * for carry computation + CDKM-style MAJ/UMA for sum extraction with
 * built-in uncomputation), or use Bennett's compute-copy-uncompute trick
 * with additional ancilla.
 *
 * Qubit layout (for future implementation):
 *   [0..bits-1]            = register a (source, preserved)
 *   [bits..2*bits-1]       = register b (target, gets a+b)
 *   [2*bits..4*bits-3]     = 2*(bits-1) ancilla qubits
 *   Total: 4*bits - 2 qubits
 *
 * OWNERSHIP: Returns cached sequence - DO NOT FREE
 *
 * @param bits Width of operands (2-64; returns NULL for bits < 2)
 * @return NULL (CLA not yet implemented; falls through to RCA)
 */
sequence_t *toffoli_QQ_add_bk(int bits) {
    (void)bits; // suppress unused parameter warning
    // CLA algorithm not yet implemented -- fall through to RCA
    return NULL;
}

void toffoli_sequence_free(sequence_t *seq) {
    if (seq == NULL)
        return;

    if (seq->seq != NULL) {
        for (num_t i = 0; i < seq->num_layer; i++) {
            // Free large_control arrays for MCX gates with 3+ controls
            if (seq->gates_per_layer != NULL) {
                for (num_t g = 0; g < seq->gates_per_layer[i]; g++) {
                    if (seq->seq[i][g].NumControls > 2 && seq->seq[i][g].large_control != NULL) {
                        free(seq->seq[i][g].large_control);
                    }
                }
            }
            free(seq->seq[i]);
        }
        free(seq->seq);
    }

    free(seq->gates_per_layer);
    free(seq);
}
