/**
 * @file hot_path_add.c
 * @brief Split-register arithmetic: addition and subtraction across a qint
 *        register plus an external qbool acting as the MSB.
 *
 * The split-register pattern treats [a_0..a_{n-1}, ancilla_qubit] as an
 * (n+1)-bit register. The ancilla acts as the MSB. This is the building block
 * for in-place comparison operators (Phase 4).
 *
 * Provides both QFT-mode and Toffoli-mode implementations:
 *   - split_CQ_add  / split_CQ_sub  (QFT Draper)
 *   - split_toffoli_CQ_add / split_toffoli_CQ_sub (CDKM ripple-carry)
 *
 * Phase ix4.1: Initial implementation.
 */

#include "Integer.h"
#include "execution.h"
#include "gate.h"
#include "toffoli_addition_internal.h"
#include "toffoli_arithmetic_ops.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ============================================================================
// QFT-mode split-register arithmetic
// ============================================================================

/**
 * @brief Split-register QFT addition: [a, msb] += classical value.
 *
 * Treats [a_0..a_{bits-1}, msb_qubit] as an (bits+1)-bit register and adds
 * a classical value using the Draper QFT adder on the full (bits+1) width.
 *
 * Qubit layout:
 *   [0..bits-1] = register a (lower bits)
 *   [bits]      = msb qubit (external qbool acting as MSB)
 *
 * @param bits  Width of the base register a (1-63)
 * @param value Classical value to add (interpreted as (bits+1)-bit two's complement)
 * @return Fresh sequence - CALLER MUST FREE
 */
sequence_t *split_CQ_add(int bits, int64_t value) {
    // The full width is bits+1 (the base register + the MSB ancilla).
    // We simply delegate to CQ_add with width = bits+1.
    // However, CQ_add caches by width and mutates rotation values in-place,
    // so we must build a fresh (non-cached) sequence.
    //
    // The qubit layout of CQ_add(w) is [0..w-1] = target register.
    // For split-register: [0..bits-1] = a, [bits] = msb.
    // This matches CQ_add(bits+1) exactly.

    int w = bits + 1;
    if (w < 2 || w > 64) {
        return NULL;
    }

    // Compute rotation angles for (bits+1)-bit addition
    int *bin = two_complement(value, w);
    if (bin == NULL) {
        return NULL;
    }

    double *rotations = calloc(w, sizeof(double));
    if (rotations == NULL) {
        free(bin);
        return NULL;
    }
    for (int bit_idx = 0; bit_idx < w; ++bit_idx) {
        for (int qubit = bit_idx; qubit < w; ++qubit) {
            rotations[qubit] += bin[w - 1 - bit_idx] * 2 * M_PI / pow(2, qubit - bit_idx + 1);
        }
    }
    free(bin);

    // Build sequence: QFT(w) + rotations(w) + IQFT(w)
    // Total layers: (2*w - 1) + w + (2*w - 1) = 5*w - 2
    int num_layers = 5 * w - 2;

    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(rotations);
        return NULL;
    }
    seq->used_layer = 0;
    seq->num_layer = num_layers;
    seq->total_gate_count = 0;
    seq->gates_per_layer = calloc(num_layers, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(rotations);
        free(seq);
        return NULL;
    }
    memset(seq->gates_per_layer, 0, num_layers * sizeof(num_t));
    seq->seq = calloc(num_layers, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(rotations);
        free(seq);
        return NULL;
    }
    for (int i = 0; i < num_layers; ++i) {
        seq->seq[i] = calloc(2 * w, sizeof(gate_t));
        if (seq->seq[i] == NULL) {
            for (int j = 0; j < i; ++j)
                free(seq->seq[j]);
            free(seq->seq);
            free(seq->gates_per_layer);
            free(rotations);
            free(seq);
            return NULL;
        }
    }

    QFT(seq, w);
    int start_layer = 2 * w - 1;
    for (int i = 0; i < w; ++i) {
        p(&seq->seq[start_layer + i][seq->gates_per_layer[start_layer + i]++], i, rotations[i]);
    }
    free(rotations);
    seq->used_layer += w;
    QFT_inverse(seq, w);

    sequence_compute_total_gate_count(seq);
    return seq;
}

/**
 * @brief Split-register QFT subtraction: [a, msb] -= classical value.
 *
 * Equivalent to split_CQ_add(bits, -value).
 *
 * @param bits  Width of the base register a (1-63)
 * @param value Classical value to subtract
 * @return Fresh sequence - CALLER MUST FREE
 */
sequence_t *split_CQ_sub(int bits, int64_t value) {
    return split_CQ_add(bits, -value);
}

// ============================================================================
// Toffoli-mode split-register arithmetic (CDKM ripple-carry)
// ============================================================================

/**
 * @brief Split-register Toffoli addition: [a, msb] += classical value.
 *
 * Uses the CDKM ripple-carry adder on (bits+1) qubits where:
 *   [0..bits-1] = base register a (lower bits)
 *   [bits]      = msb qubit (external qbool)
 *
 * The implementation delegates to toffoli_CQ_add(bits+1, value) which
 * generates an inline CQ CDKM sequence. The qubit layout of
 * toffoli_CQ_add(w) is:
 *   [0..w-1]   = temp register
 *   [w..2w-1]  = self register (target)
 *   [2w]       = carry ancilla
 *
 * For the split-register case, we remap: the caller provides qubits
 * [0..bits-1, bits] as the target. The temp and carry are internal.
 *
 * @param bits  Width of the base register a (1-63)
 * @param value Classical value to add
 * @return Fresh sequence - CALLER MUST FREE via toffoli_sequence_free()
 */
sequence_t *split_toffoli_CQ_add(int bits, int64_t value) {
    int w = bits + 1;
    if (w < 2 || w > 64) {
        return NULL;
    }
    return toffoli_CQ_add(w, value);
}

/**
 * @brief Split-register Toffoli subtraction: [a, msb] -= classical value.
 *
 * For two's complement subtraction, subtracting `value` from a `w`-bit
 * register is equivalent to adding `(2^w - value)` which is the same as
 * adding the two's complement negation. Since toffoli_CQ_add already
 * handles two's complement via two_complement(), we pass -value.
 *
 * @param bits  Width of the base register a (1-63)
 * @param value Classical value to subtract
 * @return Fresh sequence - CALLER MUST FREE via toffoli_sequence_free()
 */
sequence_t *split_toffoli_CQ_sub(int bits, int64_t value) {
    return split_toffoli_CQ_add(bits, -value);
}
