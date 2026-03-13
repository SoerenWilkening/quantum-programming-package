/**
 * @file test_tracking_only.c
 * @brief Unit tests for tracking_only parameter in run_instruction().
 *
 * Tests:
 * 1. gate_count initialized to 0 in init_circuit
 * 2. tracking_only=1 increments gate_count without building the circuit
 * 3. tracking_only=0 builds the circuit and increments gate_count
 * 4. tracking_only=1 does not modify circuit structure
 * 5. gate_count is cumulative across multiple run_instruction calls
 * 6. tracking_only works correctly with inverted sequences
 */

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "circuit.h"
#include "execution.h"
#include "gate.h"

/* Helper: count total gates in the circuit structure */
static int total_gate_count(circuit_t *circ) {
    int count = 0;
    for (int layer = 0; layer < (int)circ->used_layer; ++layer) {
        count += (int)circ->used_gates_per_layer[layer];
    }
    return count;
}

/* Helper: create a simple 2-layer CX sequence for testing */
static sequence_t *make_cx_sequence(void) {
    sequence_t *seq = malloc(sizeof(sequence_t));
    if (seq == NULL)
        return NULL;

    seq->num_layer = 2;
    seq->used_layer = 2;
    seq->gates_per_layer = calloc(2, sizeof(num_t));
    seq->seq = malloc(2 * sizeof(gate_t *));

    for (int i = 0; i < 2; i++) {
        seq->seq[i] = malloc(1 * sizeof(gate_t));
        seq->gates_per_layer[i] = 1;
    }

    /* Layer 0: X gate on virtual qubit 0 */
    memset(&seq->seq[0][0], 0, sizeof(gate_t));
    x(&seq->seq[0][0], 0);

    /* Layer 1: CX gate on virtual qubit 1, controlled by virtual qubit 0 */
    memset(&seq->seq[1][0], 0, sizeof(gate_t));
    cx(&seq->seq[1][0], 1, 0);

    return seq;
}

static void free_test_sequence(sequence_t *seq) {
    if (seq == NULL)
        return;
    for (int i = 0; i < (int)seq->num_layer; i++) {
        free(seq->seq[i]);
    }
    free(seq->seq);
    free(seq->gates_per_layer);
    free(seq);
}

/* ------------------------------------------------------------------ */
/* Test 1: gate_count initialized to 0                                */
/* ------------------------------------------------------------------ */
static void test_gate_count_initialized_to_zero(void) {
    printf("test_gate_count_initialized_to_zero... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);
    assert(circ->gate_count == 0 && "gate_count should be 0 after init_circuit");

    printf("PASS\n");
    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test 2: tracking_only=1 counts gates without building circuit      */
/* ------------------------------------------------------------------ */
static void test_tracking_only_counts_without_building(void) {
    printf("test_tracking_only_counts_without_building... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    sequence_t *seq = make_cx_sequence();
    assert(seq != NULL);

    /* Map virtual qubits to physical qubits */
    qubit_t qa[2] = {0, 1};

    /* Run with tracking_only=1 */
    run_instruction(seq, qa, 0, circ, 1);

    /* gate_count should reflect the 2 gates in the sequence */
    assert(circ->gate_count == 2 && "tracking_only should count 2 gates");

    /* Circuit structure should be empty */
    int actual_gates = total_gate_count(circ);
    assert(actual_gates == 0 && "tracking_only should not add gates to circuit");
    assert(circ->used_layer == 0 && "tracking_only should not create layers");

    printf("PASS\n");
    free_test_sequence(seq);
    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test 3: tracking_only=0 builds circuit and increments gate_count   */
/* ------------------------------------------------------------------ */
static void test_normal_mode_builds_and_counts(void) {
    printf("test_normal_mode_builds_and_counts... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    sequence_t *seq = make_cx_sequence();
    assert(seq != NULL);

    qubit_t qa[2] = {0, 1};

    /* Run with tracking_only=0 (normal mode) */
    run_instruction(seq, qa, 0, circ, 0);

    /* gate_count should reflect the 2 gates */
    assert(circ->gate_count == 2 && "normal mode should count 2 gates");

    /* Circuit structure should contain the gates */
    int actual_gates = total_gate_count(circ);
    assert(actual_gates == 2 && "normal mode should add 2 gates to circuit");

    printf("PASS\n");
    free_test_sequence(seq);
    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test 4: tracking_only does not modify circuit structure             */
/* ------------------------------------------------------------------ */
static void test_tracking_only_preserves_circuit_state(void) {
    printf("test_tracking_only_preserves_circuit_state... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    /* First, add a gate normally */
    gate_t g;
    memset(&g, 0, sizeof(gate_t));
    x(&g, 0);
    add_gate(circ, &g);

    size_t used_before = circ->used;
    num_t used_layer_before = circ->used_layer;
    num_t used_qubits_before = circ->used_qubits;

    /* Now run a sequence with tracking_only=1 */
    sequence_t *seq = make_cx_sequence();
    assert(seq != NULL);

    qubit_t qa[2] = {2, 3};
    run_instruction(seq, qa, 0, circ, 1);

    /* Circuit structure should be unchanged */
    assert(circ->used == used_before && "tracking_only should not change circ->used");
    assert(circ->used_layer == used_layer_before &&
           "tracking_only should not change circ->used_layer");
    assert(circ->used_qubits == used_qubits_before &&
           "tracking_only should not change circ->used_qubits");

    /* But gate_count should have increased */
    assert(circ->gate_count == 2 && "tracking_only should still increment gate_count");

    printf("PASS\n");
    free_test_sequence(seq);
    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test 5: gate_count is cumulative across multiple calls             */
/* ------------------------------------------------------------------ */
static void test_gate_count_cumulative(void) {
    printf("test_gate_count_cumulative... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    sequence_t *seq = make_cx_sequence();
    assert(seq != NULL);

    qubit_t qa[2] = {0, 1};

    /* Run tracking_only 3 times */
    run_instruction(seq, qa, 0, circ, 1);
    run_instruction(seq, qa, 0, circ, 1);
    run_instruction(seq, qa, 0, circ, 1);

    assert(circ->gate_count == 6 && "3 runs * 2 gates = 6 total");

    /* Mix in a normal run */
    run_instruction(seq, qa, 0, circ, 0);

    assert(circ->gate_count == 8 && "6 + 2 from normal run = 8 total");

    printf("PASS\n");
    free_test_sequence(seq);
    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test 6: tracking_only with NULL sequence is a no-op                */
/* ------------------------------------------------------------------ */
static void test_tracking_only_null_sequence(void) {
    printf("test_tracking_only_null_sequence... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    qubit_t qa[2] = {0, 1};

    /* NULL sequence should be a no-op for both modes */
    run_instruction(NULL, qa, 0, circ, 1);
    assert(circ->gate_count == 0 && "NULL sequence should not increment gate_count");

    run_instruction(NULL, qa, 0, circ, 0);
    assert(circ->gate_count == 0 && "NULL sequence should not increment gate_count");

    printf("PASS\n");
    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test 7: validated_run_instruction passes tracking_only correctly   */
/* ------------------------------------------------------------------ */
static void test_validated_run_instruction_tracking(void) {
    printf("test_validated_run_instruction_tracking... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    sequence_t *seq = make_cx_sequence();
    assert(seq != NULL);

    qubit_t qa[2] = {0, 1};

    /* tracking_only=1 via validated entry point */
    int rc = validated_run_instruction(seq, qa, 0, circ, 1);
    assert(rc == QV_OK);
    assert(circ->gate_count == 2 && "validated tracking_only should count gates");
    assert(total_gate_count(circ) == 0 && "validated tracking_only should not build circuit");

    /* tracking_only=0 via validated entry point */
    rc = validated_run_instruction(seq, qa, 0, circ, 0);
    assert(rc == QV_OK);
    assert(circ->gate_count == 4 && "validated normal mode should also count gates");
    assert(total_gate_count(circ) == 2 && "validated normal mode should build circuit");

    /* NULL circuit check */
    rc = validated_run_instruction(seq, qa, 0, NULL, 1);
    assert(rc == QV_NULL_CIRC);

    printf("PASS\n");
    free_test_sequence(seq);
    free_circuit(circ);
}

int main(void) {
    printf("=== tracking_only C unit tests (Module 1) ===\n\n");

    test_gate_count_initialized_to_zero();
    test_tracking_only_counts_without_building();
    test_normal_mode_builds_and_counts();
    test_tracking_only_preserves_circuit_state();
    test_gate_count_cumulative();
    test_tracking_only_null_sequence();
    test_validated_run_instruction_tracking();

    printf("\n=== ALL 7 TESTS PASSED ===\n");
    return 0;
}
