/**
 * @file ToffoliAdditionHelpers.c
 * @brief Shared utility functions for Toffoli addition modules.
 *
 * Contains sequence allocation, deep-copy, and free functions used by
 * both CDKM and CLA Toffoli adder implementations.
 *
 * Phase 74: Extracted from ToffoliAddition.c during split refactoring.
 */

#include "circuit.h"
#include "toffoli_addition_internal.h"
#include "toffoli_arithmetic_ops.h"
#include <stdlib.h>
#include <string.h>

// ============================================================================
// Sequence allocation helper
// ============================================================================

/**
 * @brief Allocate a sequence with given number of layers, 1 gate per layer.
 */
sequence_t *alloc_sequence(int num_layers) {
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL)
        return NULL;

    seq->num_layer = num_layers;
    seq->used_layer = 0;
    seq->total_gate_count = 0;
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

/**
 * @brief Deep-copy a const (hardcoded) sequence into a fresh malloc'd sequence.
 *
 * CQ/cCQ callers free the returned sequence, so hardcoded static sequences
 * must be copied before returning. This copies large_control arrays for MCX gates.
 *
 * @param src Source sequence (typically static const from hardcoded file)
 * @return Fresh sequence_t* owned by caller, or NULL on allocation failure
 */
sequence_t *copy_hardcoded_sequence(const sequence_t *src) {
    if (src == NULL)
        return NULL;

    int n = (int)src->num_layer;
    sequence_t *dst = malloc(sizeof(sequence_t));
    if (dst == NULL)
        return NULL;

    dst->num_layer = src->num_layer;
    dst->used_layer = src->used_layer;
    dst->total_gate_count = src->total_gate_count;
    dst->gates_per_layer = calloc(n, sizeof(num_t));
    dst->seq = calloc(n, sizeof(gate_t *));
    if (dst->gates_per_layer == NULL || dst->seq == NULL) {
        free(dst->gates_per_layer);
        free(dst->seq);
        free(dst);
        return NULL;
    }

    for (int i = 0; i < n; i++) {
        dst->gates_per_layer[i] = src->gates_per_layer[i];
        int gcount = (int)src->gates_per_layer[i];
        if (gcount <= 0)
            gcount = 1; /* allocate at least 1 slot */
        dst->seq[i] = calloc(gcount, sizeof(gate_t));
        if (dst->seq[i] == NULL) {
            for (int j = 0; j < i; j++) {
                if (dst->seq[j] != NULL) {
                    for (int g = 0; g < (int)dst->gates_per_layer[j]; g++) {
                        if (dst->seq[j][g].large_control != NULL)
                            free(dst->seq[j][g].large_control);
                    }
                    free(dst->seq[j]);
                }
            }
            free(dst->seq);
            free(dst->gates_per_layer);
            free(dst);
            return NULL;
        }
        for (int g = 0; g < (int)src->gates_per_layer[i]; g++) {
            dst->seq[i][g] = src->seq[i][g];
            dst->seq[i][g].large_control = NULL;
            if (src->seq[i][g].NumControls > 2 && src->seq[i][g].large_control != NULL) {
                dst->seq[i][g].large_control = malloc(src->seq[i][g].NumControls * sizeof(qubit_t));
                if (dst->seq[i][g].large_control != NULL) {
                    for (num_t c = 0; c < src->seq[i][g].NumControls; c++)
                        dst->seq[i][g].large_control[c] = src->seq[i][g].large_control[c];
                }
            }
        }
    }

    return dst;
}

// ============================================================================
// Sequence free
// ============================================================================

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
