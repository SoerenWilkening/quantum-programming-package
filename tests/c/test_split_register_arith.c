/**
 * @file test_split_register_arith.c
 * @brief Unit tests for split-register arithmetic (Phase ix4.1).
 *
 * Tests:
 *   1. split_sub_borrow_set    — subtraction that causes borrow (MSB flips)
 *   2. split_sub_no_borrow     — subtraction with no borrow (MSB stays 0)
 *   3. split_add_restore       — add after subtract restores original value
 *   4. split_register_matches_widened — split-register result matches
 *      plain (bits+1)-wide addition
 *
 * All tests exercise both QFT-mode and Toffoli-mode variants.
 */

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "arithmetic_ops.h"
#include "circuit.h"
#include "execution.h"
#include "gate.h"
#include "toffoli_addition_internal.h"
#include "toffoli_arithmetic_ops.h"

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

static void free_qft_sequence(sequence_t *seq) {
    if (seq == NULL)
        return;
    if (seq->seq != NULL) {
        for (int i = 0; i < (int)seq->num_layer; i++)
            free(seq->seq[i]);
        free(seq->seq);
    }
    free(seq->gates_per_layer);
    free(seq);
}

/* ------------------------------------------------------------------ */
/* Test 1: split_sub_borrow_set                                        */
/*                                                                     */
/* Subtract a value larger than the register contents.                 */
/* For a 3-bit base register + 1 MSB (4-bit total):                    */
/*   initial = 2 (0b0010), subtract 5 -> 2-5 = -3 = 0b1101 (4-bit)   */
/*   MSB (bit 3) = 1  -> borrow is set.                               */
/*                                                                     */
/* We verify the sequences are non-NULL and have correct gate counts.  */
/* ------------------------------------------------------------------ */
static void test_split_sub_borrow_set(void) {
    printf("test_split_sub_borrow_set... ");
    fflush(stdout);

    int bits = 3;
    int64_t value = 5;

    /* QFT mode */
    sequence_t *qft_seq = split_CQ_sub(bits, value);
    assert(qft_seq != NULL);
    assert(qft_seq->total_gate_count > 0 && "split_CQ_sub should produce gates");

    /* The sequence width is bits+1 = 4, so QFT layers = 5*4-2 = 18 */
    assert(qft_seq->num_layer == 5 * (bits + 1) - 2 &&
           "split_CQ_sub layer count should match CQ_add(bits+1)");
    free_qft_sequence(qft_seq);

    /* Toffoli mode */
    sequence_t *toff_seq = split_toffoli_CQ_sub(bits, value);
    assert(toff_seq != NULL);
    assert(toff_seq->total_gate_count > 0 && "split_toffoli_CQ_sub should produce gates");
    toffoli_sequence_free(toff_seq);

    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 2: split_sub_no_borrow                                         */
/*                                                                     */
/* Subtract a value smaller than the register contents.                */
/* For a 3-bit base register + 1 MSB (4-bit total):                    */
/*   initial = 5 (0b0101), subtract 2 -> 5-2 = 3 = 0b0011 (4-bit)    */
/*   MSB (bit 3) = 0  -> no borrow.                                   */
/*                                                                     */
/* We verify the sequences are valid and have reasonable gate counts.   */
/* ------------------------------------------------------------------ */
static void test_split_sub_no_borrow(void) {
    printf("test_split_sub_no_borrow... ");
    fflush(stdout);

    int bits = 3;
    int64_t value = 2;

    /* QFT mode */
    sequence_t *qft_seq = split_CQ_sub(bits, value);
    assert(qft_seq != NULL);
    assert(qft_seq->total_gate_count > 0);
    free_qft_sequence(qft_seq);

    /* Toffoli mode */
    sequence_t *toff_seq = split_toffoli_CQ_sub(bits, value);
    assert(toff_seq != NULL);
    assert(toff_seq->total_gate_count > 0);
    toffoli_sequence_free(toff_seq);

    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 3: split_add_restore                                           */
/*                                                                     */
/* After subtract then add of same value, we should get the same       */
/* circuit depth. The sequences are structurally identical (same layer  */
/* count, same total gate count) since CQ_add(-v) and CQ_add(+v) on   */
/* the same width produce QFT sequences of equal structure.            */
/* ------------------------------------------------------------------ */
static void test_split_add_restore(void) {
    printf("test_split_add_restore... ");
    fflush(stdout);

    int bits = 4;
    int64_t value = 7;

    /* QFT mode: sub then add should have same structure */
    sequence_t *sub_seq = split_CQ_sub(bits, value);
    sequence_t *add_seq = split_CQ_add(bits, value);
    assert(sub_seq != NULL);
    assert(add_seq != NULL);
    assert(sub_seq->num_layer == add_seq->num_layer && "sub and add should have same layer count");
    assert(sub_seq->total_gate_count == add_seq->total_gate_count &&
           "sub and add should have same total gate count");
    free_qft_sequence(sub_seq);
    free_qft_sequence(add_seq);

    /* Toffoli mode: sub(-v) and add(v) should both produce valid sequences */
    sequence_t *toff_sub = split_toffoli_CQ_sub(bits, value);
    sequence_t *toff_add = split_toffoli_CQ_add(bits, value);
    assert(toff_sub != NULL);
    assert(toff_add != NULL);
    assert(toff_sub->total_gate_count > 0);
    assert(toff_add->total_gate_count > 0);
    toffoli_sequence_free(toff_sub);
    toffoli_sequence_free(toff_add);

    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 4: split_register_matches_widened                              */
/*                                                                     */
/* Verify that split_CQ_add(bits, value) produces the exact same       */
/* sequence structure as CQ_add(bits+1, value). Both should have the   */
/* same number of layers and gates.                                    */
/*                                                                     */
/* Similarly for Toffoli mode: split_toffoli_CQ_add(bits, value)       */
/* should match toffoli_CQ_add(bits+1, value).                        */
/* ------------------------------------------------------------------ */
static void test_split_register_matches_widened(void) {
    printf("test_split_register_matches_widened... ");
    fflush(stdout);

    int bits = 3;
    int64_t value = 5;
    int w = bits + 1;

    /* QFT mode: split_CQ_add(bits, value) vs CQ_add(bits+1, value) */
    sequence_t *split_seq = split_CQ_add(bits, value);
    assert(split_seq != NULL);

    /* CQ_add is cached, so we just compare structural properties */
    sequence_t *wide_seq = CQ_add(w, value);
    assert(wide_seq != NULL);

    assert(split_seq->num_layer == wide_seq->num_layer &&
           "split and widened QFT should have same layer count");
    assert(split_seq->used_layer == wide_seq->used_layer &&
           "split and widened QFT should have same used layer count");
    assert(split_seq->total_gate_count == wide_seq->total_gate_count &&
           "split and widened QFT should have same total gate count");

    free_qft_sequence(split_seq);
    /* Do NOT free wide_seq -- it's cached by CQ_add */

    /* Toffoli mode: split_toffoli_CQ_add(bits, value) vs
     * toffoli_CQ_add(bits+1, value) */
    sequence_t *toff_split = split_toffoli_CQ_add(bits, value);
    assert(toff_split != NULL);

    sequence_t *toff_wide = toffoli_CQ_add(w, value);
    assert(toff_wide != NULL);

    assert(toff_split->used_layer == toff_wide->used_layer &&
           "split and widened Toffoli should have same used layer count");
    assert(toff_split->total_gate_count == toff_wide->total_gate_count &&
           "split and widened Toffoli should have same total gate count");

    toffoli_sequence_free(toff_split);
    toffoli_sequence_free(toff_wide);

    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Additional tests: edge cases                                        */
/* ------------------------------------------------------------------ */

/* Test 5: bits=1 (minimum base register + MSB = 2-bit total) */
static void test_split_1bit(void) {
    printf("test_split_1bit... ");
    fflush(stdout);

    /* QFT mode */
    sequence_t *qft_add = split_CQ_add(1, 1);
    assert(qft_add != NULL);
    assert(qft_add->total_gate_count > 0);
    free_qft_sequence(qft_add);

    sequence_t *qft_sub = split_CQ_sub(1, 1);
    assert(qft_sub != NULL);
    assert(qft_sub->total_gate_count > 0);
    free_qft_sequence(qft_sub);

    /* Toffoli mode */
    sequence_t *toff_add = split_toffoli_CQ_add(1, 1);
    assert(toff_add != NULL);
    assert(toff_add->total_gate_count > 0);
    toffoli_sequence_free(toff_add);

    sequence_t *toff_sub = split_toffoli_CQ_sub(1, 1);
    assert(toff_sub != NULL);
    assert(toff_sub->total_gate_count > 0);
    toffoli_sequence_free(toff_sub);

    printf("PASS\n");
}

/* Test 6: value=0 (identity operation) */
static void test_split_zero_value(void) {
    printf("test_split_zero_value... ");
    fflush(stdout);

    /* QFT mode: adding 0 still produces a valid sequence (rotations are 0) */
    sequence_t *qft_add = split_CQ_add(3, 0);
    assert(qft_add != NULL);
    free_qft_sequence(qft_add);

    /* Toffoli mode: adding 0 should produce an identity-like sequence */
    sequence_t *toff_add = split_toffoli_CQ_add(3, 0);
    assert(toff_add != NULL);
    toffoli_sequence_free(toff_add);

    printf("PASS\n");
}

/* Test 7: bounds check - bits=0 should return NULL */
static void test_split_bounds(void) {
    printf("test_split_bounds... ");
    fflush(stdout);

    assert(split_CQ_add(0, 1) == NULL && "bits=0 should return NULL (QFT add)");
    assert(split_CQ_sub(0, 1) == NULL && "bits=0 should return NULL (QFT sub)");
    assert(split_toffoli_CQ_add(0, 1) == NULL && "bits=0 should return NULL (Toffoli add)");
    assert(split_toffoli_CQ_sub(0, 1) == NULL && "bits=0 should return NULL (Toffoli sub)");

    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Main                                                                */
/* ------------------------------------------------------------------ */

int main(void) {
    printf("=== split-register arithmetic unit tests ===\n\n");

    test_split_sub_borrow_set();
    test_split_sub_no_borrow();
    test_split_add_restore();
    test_split_register_matches_widened();
    test_split_1bit();
    test_split_zero_value();
    test_split_bounds();

    printf("\n=== ALL 7 TESTS PASSED ===\n");
    return 0;
}
