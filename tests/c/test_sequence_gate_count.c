/**
 * @file test_sequence_gate_count.c
 * @brief Unit tests for total_gate_count field on sequence_t.
 *
 * Tests:
 * 1. alloc_sequence initializes total_gate_count to 0
 * 2. sequence_compute_total_gate_count sums gates_per_layer
 * 3. sequence with total_gate_count set works correctly in run_instruction
 * 4. sequence_compute_total_gate_count handles multi-gate layers
 * 5. copy_hardcoded_sequence copies total_gate_count
 * 6. sequence_compute_total_gate_count handles NULL
 * 7. sequence_compute_total_gate_count handles empty sequence (0 used layers)
 */

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "circuit.h"
#include "execution.h"
#include "gate.h"
#include "toffoli_addition_internal.h"

/* Helper: free a sequence allocated via alloc_sequence */
static void free_test_sequence(sequence_t *seq) {
    if (seq == NULL)
        return;
    for (int i = 0; i < (int)seq->num_layer; i++)
        free(seq->seq[i]);
    free(seq->seq);
    free(seq->gates_per_layer);
    free(seq);
}

/* ------------------------------------------------------------------ */
/* Test 1: alloc_sequence initializes total_gate_count to 0            */
/* ------------------------------------------------------------------ */
static void test_alloc_sequence_initializes_total(void) {
    printf("test_alloc_sequence_initializes_total... ");
    fflush(stdout);

    sequence_t *seq = alloc_sequence(5);
    assert(seq != NULL);
    assert(seq->total_gate_count == 0 && "alloc_sequence should init total_gate_count to 0");

    free_test_sequence(seq);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 2: sequence_compute_total_gate_count sums gates_per_layer      */
/* ------------------------------------------------------------------ */
static void test_compute_total_sums_layers(void) {
    printf("test_compute_total_sums_layers... ");
    fflush(stdout);

    sequence_t *seq = alloc_sequence(3);
    assert(seq != NULL);

    /* Populate 3 layers with 1 gate each */
    seq->used_layer = 3;
    for (int i = 0; i < 3; i++) {
        memset(&seq->seq[i][0], 0, sizeof(gate_t));
        x(&seq->seq[i][0], (qubit_t)i);
        seq->gates_per_layer[i] = 1;
    }

    assert(seq->total_gate_count == 0 && "total_gate_count should be 0 before compute");
    sequence_compute_total_gate_count(seq);
    assert(seq->total_gate_count == 3 && "total_gate_count should be 3 after compute");

    free_test_sequence(seq);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 3: run_instruction works correctly with total_gate_count set   */
/* ------------------------------------------------------------------ */
static void test_run_instruction_with_total(void) {
    printf("test_run_instruction_with_total... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);
    circ->simulate = 0;

    /* Build a 2-layer sequence and compute total */
    sequence_t *seq = alloc_sequence(2);
    assert(seq != NULL);
    seq->used_layer = 2;
    for (int i = 0; i < 2; i++) {
        memset(&seq->seq[i][0], 0, sizeof(gate_t));
        x(&seq->seq[i][0], (qubit_t)i);
        seq->gates_per_layer[i] = 1;
    }
    sequence_compute_total_gate_count(seq);
    assert(seq->total_gate_count == 2);

    qubit_t qa[2] = {0, 1};
    run_instruction(seq, qa, 0, circ);

    assert(circ->gate_count == 2 && "run_instruction should count 2 gates");

    free_test_sequence(seq);
    free_circuit(circ);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 4: sequence_compute_total_gate_count with multi-gate layers    */
/* ------------------------------------------------------------------ */
static void test_compute_total_multi_gate_layers(void) {
    printf("test_compute_total_multi_gate_layers... ");
    fflush(stdout);

    /* Manually build a sequence with varying gates per layer */
    sequence_t *seq = malloc(sizeof(sequence_t));
    assert(seq != NULL);
    seq->num_layer = 3;
    seq->used_layer = 3;
    seq->total_gate_count = 0;
    seq->gates_per_layer = calloc(3, sizeof(num_t));
    seq->seq = calloc(3, sizeof(gate_t *));

    /* Layer 0: 2 gates, Layer 1: 3 gates, Layer 2: 1 gate => total 6 */
    seq->gates_per_layer[0] = 2;
    seq->gates_per_layer[1] = 3;
    seq->gates_per_layer[2] = 1;

    for (int i = 0; i < 3; i++) {
        seq->seq[i] = calloc(seq->gates_per_layer[i], sizeof(gate_t));
        assert(seq->seq[i] != NULL);
    }

    sequence_compute_total_gate_count(seq);
    assert(seq->total_gate_count == 6 &&
           "total should be sum of multi-gate layers (2+3+1=6)");

    /* Clean up */
    for (int i = 0; i < 3; i++)
        free(seq->seq[i]);
    free(seq->seq);
    free(seq->gates_per_layer);
    free(seq);

    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 5: copy_hardcoded_sequence copies total_gate_count             */
/* ------------------------------------------------------------------ */
static void test_copy_preserves_total(void) {
    printf("test_copy_preserves_total... ");
    fflush(stdout);

    sequence_t *src = alloc_sequence(2);
    assert(src != NULL);
    src->used_layer = 2;
    for (int i = 0; i < 2; i++) {
        memset(&src->seq[i][0], 0, sizeof(gate_t));
        x(&src->seq[i][0], (qubit_t)i);
        src->gates_per_layer[i] = 1;
    }
    sequence_compute_total_gate_count(src);
    assert(src->total_gate_count == 2);

    sequence_t *dst = copy_hardcoded_sequence(src);
    assert(dst != NULL);
    assert(dst->total_gate_count == 2 && "copy should preserve total_gate_count");

    free_test_sequence(src);
    free_test_sequence(dst);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 6: sequence_compute_total_gate_count handles NULL              */
/* ------------------------------------------------------------------ */
static void test_compute_total_null(void) {
    printf("test_compute_total_null... ");
    fflush(stdout);

    /* Should not crash */
    sequence_compute_total_gate_count(NULL);

    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 7: sequence_compute_total_gate_count with 0 used layers        */
/* ------------------------------------------------------------------ */
static void test_compute_total_empty(void) {
    printf("test_compute_total_empty... ");
    fflush(stdout);

    sequence_t *seq = alloc_sequence(5);
    assert(seq != NULL);
    assert(seq->used_layer == 0);

    sequence_compute_total_gate_count(seq);
    assert(seq->total_gate_count == 0 && "empty sequence should have total_gate_count 0");

    free_test_sequence(seq);
    printf("PASS\n");
}

int main(void) {
    printf("=== sequence_t total_gate_count unit tests ===\n\n");

    test_alloc_sequence_initializes_total();
    test_compute_total_sums_layers();
    test_run_instruction_with_total();
    test_compute_total_multi_gate_layers();
    test_copy_preserves_total();
    test_compute_total_null();
    test_compute_total_empty();

    printf("\n=== ALL 7 TESTS PASSED ===\n");
    return 0;
}
