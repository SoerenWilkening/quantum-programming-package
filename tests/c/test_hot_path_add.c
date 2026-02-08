/**
 * @file test_hot_path_add.c
 * @brief Unit tests for hot_path_add C implementation (Phase 60, Plan 03).
 *
 * Tests that hot_path_add_cq and hot_path_add_qq correctly build qubit
 * layouts and produce gates in the circuit.
 */

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "circuit.h"
#include "hot_path_add.h"

/* Helper: check that circuit has gates (used_layer > 0) */
static int circuit_has_gates(circuit_t *circ) {
    /* circuit_t is struct circuit_s in circuit.h */
    return circ->used_layer > 0;
}

/* ------------------------------------------------------------------ */
/* Test: CQ addition (classical + quantum) produces gates             */
/* ------------------------------------------------------------------ */
static void test_cq_add_4bit(void) {
    printf("test_cq_add_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[4] = {0, 1, 2, 3};
    unsigned int ancilla[2] = {10, 11};

    hot_path_add_cq(circ, self_q, 4, 5, /* classical_value = 5 */
                    0,                  /* invert = 0 (addition) */
                    0,                  /* not controlled */
                    0,                  /* control_qubit (unused) */
                    ancilla, 2);

    assert(circuit_has_gates(circ) && "CQ add 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

static void test_cq_add_8bit(void) {
    printf("test_cq_add_8bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[8];
    for (int i = 0; i < 8; i++) {
        self_q[i] = (unsigned int)i;
    }
    unsigned int ancilla[2] = {20, 21};

    hot_path_add_cq(circ, self_q, 8, 42, /* classical_value = 42 */
                    0,                   /* invert = 0 */
                    0, 0, ancilla, 2);

    assert(circuit_has_gates(circ) && "CQ add 8-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: CQ controlled addition produces gates                        */
/* ------------------------------------------------------------------ */
static void test_cq_add_controlled_4bit(void) {
    printf("test_cq_add_controlled_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[4] = {0, 1, 2, 3};
    unsigned int ancilla[2] = {10, 11};

    hot_path_add_cq(circ, self_q, 4, 3, /* classical_value = 3 */
                    0,                  /* invert = 0 */
                    1,                  /* controlled */
                    9,                  /* control_qubit */
                    ancilla, 2);

    assert(circuit_has_gates(circ) && "Controlled CQ add 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: CQ addition with invert (subtraction) produces gates         */
/* ------------------------------------------------------------------ */
static void test_cq_add_invert_4bit(void) {
    printf("test_cq_add_invert_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[4] = {0, 1, 2, 3};
    unsigned int ancilla[2] = {10, 11};

    hot_path_add_cq(circ, self_q, 4, 5, 1, /* invert = 1 (subtraction) */
                    0, 0, ancilla, 2);

    assert(circuit_has_gates(circ) && "CQ add inverted 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: QQ addition (quantum + quantum) produces gates               */
/* ------------------------------------------------------------------ */
static void test_qq_add_4bit(void) {
    printf("test_qq_add_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[4] = {0, 1, 2, 3};
    unsigned int other_q[4] = {4, 5, 6, 7};
    unsigned int ancilla[2] = {20, 21};

    hot_path_add_qq(circ, self_q, 4, other_q, 4, 0, /* invert = 0 */
                    0, 0,                           /* not controlled */
                    ancilla, 2);

    assert(circuit_has_gates(circ) && "QQ add 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

static void test_qq_add_8bit(void) {
    printf("test_qq_add_8bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[8], other_q[8];
    for (int i = 0; i < 8; i++) {
        self_q[i] = (unsigned int)i;
        other_q[i] = (unsigned int)(8 + i);
    }
    unsigned int ancilla[2] = {30, 31};

    hot_path_add_qq(circ, self_q, 8, other_q, 8, 0, 0, 0, ancilla, 2);

    assert(circuit_has_gates(circ) && "QQ add 8-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: QQ controlled addition produces gates                        */
/* ------------------------------------------------------------------ */
static void test_qq_add_controlled_4bit(void) {
    printf("test_qq_add_controlled_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[4] = {0, 1, 2, 3};
    unsigned int other_q[4] = {4, 5, 6, 7};
    unsigned int ancilla[2] = {20, 21};

    hot_path_add_qq(circ, self_q, 4, other_q, 4, 0, /* invert = 0 */
                    1,                              /* controlled */
                    8,                              /* control_qubit = 2*result_bits = 8 */
                    ancilla, 2);

    assert(circuit_has_gates(circ) && "Controlled QQ add 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: QQ addition with invert (subtraction) produces gates         */
/* ------------------------------------------------------------------ */
static void test_qq_add_invert_8bit(void) {
    printf("test_qq_add_invert_8bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[8], other_q[8];
    for (int i = 0; i < 8; i++) {
        self_q[i] = (unsigned int)i;
        other_q[i] = (unsigned int)(8 + i);
    }
    unsigned int ancilla[2] = {30, 31};

    hot_path_add_qq(circ, self_q, 8, other_q, 8, 1, /* invert = 1 (subtraction) */
                    0, 0, ancilla, 2);

    assert(circuit_has_gates(circ) && "QQ add inverted 8-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: CQ addition with classical_value = 0 (edge case)            */
/* ------------------------------------------------------------------ */
static void test_cq_add_zero(void) {
    printf("test_cq_add_zero... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[4] = {0, 1, 2, 3};
    unsigned int ancilla[2] = {10, 11};

    /* Adding 0 -- should still produce a circuit (QFT + inverse QFT) */
    hot_path_add_cq(circ, self_q, 4, 0, 0, 0, 0, ancilla, 2);

    assert(circuit_has_gates(circ) && "CQ add with value=0 should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

int main(void) {
    printf("=== hot_path_add C unit tests ===\n\n");

    test_cq_add_4bit();
    test_cq_add_8bit();
    test_cq_add_controlled_4bit();
    test_cq_add_invert_4bit();
    test_qq_add_4bit();
    test_qq_add_8bit();
    test_qq_add_controlled_4bit();
    test_qq_add_invert_8bit();
    test_cq_add_zero();

    printf("\n=== ALL TESTS PASSED ===\n");
    return 0;
}
