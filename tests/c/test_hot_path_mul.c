/**
 * @file test_hot_path_mul.c
 * @brief Unit tests for hot_path_mul C implementation (Phase 60, Plan 02).
 *
 * Tests that hot_path_mul_cq and hot_path_mul_qq correctly build qubit
 * layouts and produce gates in the circuit.
 */

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "circuit.h"
#include "hot_path_mul.h"

/* Helper: check that circuit has gates (used_layer > 0) */
static int circuit_has_gates(circuit_t *circ) {
    /* circuit_t is struct circuit_s in circuit.h */
    return circ->used_layer > 0;
}

/* ------------------------------------------------------------------ */
/* Test: CQ multiplication (classical * quantum) produces gates       */
/* ------------------------------------------------------------------ */
static void test_cq_mul_4bit(void) {
    printf("test_cq_mul_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    /* 4-bit multiplication: ret(4) + self(4) = 8 qubits minimum */
    unsigned int ret_q[4] = {0, 1, 2, 3};
    unsigned int self_q[4] = {4, 5, 6, 7};
    unsigned int ancilla[2] = {20, 21};

    hot_path_mul_cq(circ, ret_q, 4, self_q, 4, 3, /* classical_value = 3 */
                    0,                            /* not controlled */
                    0,                            /* control_qubit (unused) */
                    ancilla, 2);

    assert(circuit_has_gates(circ) && "CQ mul 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

static void test_cq_mul_8bit(void) {
    printf("test_cq_mul_8bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int ret_q[8], self_q[8];
    for (int i = 0; i < 8; i++) {
        ret_q[i] = (unsigned int)i;
        self_q[i] = (unsigned int)(8 + i);
    }
    unsigned int ancilla[2] = {30, 31};

    hot_path_mul_cq(circ, ret_q, 8, self_q, 8, 7, /* classical_value = 7 */
                    0, 0, ancilla, 2);

    assert(circuit_has_gates(circ) && "CQ mul 8-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: CQ controlled multiplication produces gates                  */
/* ------------------------------------------------------------------ */
static void test_cq_mul_controlled_4bit(void) {
    printf("test_cq_mul_controlled_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int ret_q[4] = {0, 1, 2, 3};
    unsigned int self_q[4] = {4, 5, 6, 7};
    unsigned int ancilla[2] = {20, 21};

    hot_path_mul_cq(circ, ret_q, 4, self_q, 4, 5, /* classical_value = 5 */
                    1,                            /* controlled */
                    19,                           /* control_qubit */
                    ancilla, 2);

    assert(circuit_has_gates(circ) && "Controlled CQ mul 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: QQ multiplication (quantum * quantum) produces gates         */
/* ------------------------------------------------------------------ */
static void test_qq_mul_4bit(void) {
    printf("test_qq_mul_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int ret_q[4] = {0, 1, 2, 3};
    unsigned int self_q[4] = {4, 5, 6, 7};
    unsigned int other_q[4] = {8, 9, 10, 11};
    unsigned int ancilla[2] = {20, 21};

    hot_path_mul_qq(circ, ret_q, 4, self_q, 4, other_q, 4, 0, 0, /* not controlled */
                    ancilla, 2);

    assert(circuit_has_gates(circ) && "QQ mul 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

static void test_qq_mul_8bit(void) {
    printf("test_qq_mul_8bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int ret_q[8], self_q[8], other_q[8];
    for (int i = 0; i < 8; i++) {
        ret_q[i] = (unsigned int)i;
        self_q[i] = (unsigned int)(8 + i);
        other_q[i] = (unsigned int)(16 + i);
    }
    unsigned int ancilla[2] = {30, 31};

    hot_path_mul_qq(circ, ret_q, 8, self_q, 8, other_q, 8, 0, 0, ancilla, 2);

    assert(circuit_has_gates(circ) && "QQ mul 8-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: QQ controlled multiplication produces gates                  */
/* ------------------------------------------------------------------ */
static void test_qq_mul_controlled_4bit(void) {
    printf("test_qq_mul_controlled_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int ret_q[4] = {0, 1, 2, 3};
    unsigned int self_q[4] = {4, 5, 6, 7};
    unsigned int other_q[4] = {8, 9, 10, 11};
    unsigned int ancilla[2] = {20, 21};

    hot_path_mul_qq(circ, ret_q, 4, self_q, 4, other_q, 4, 1, /* controlled */
                    19,                                       /* control_qubit */
                    ancilla, 2);

    assert(circuit_has_gates(circ) && "Controlled QQ mul 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: CQ with classical_value = 0 still works (edge case)         */
/* ------------------------------------------------------------------ */
static void test_cq_mul_zero(void) {
    printf("test_cq_mul_zero... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int ret_q[4] = {0, 1, 2, 3};
    unsigned int self_q[4] = {4, 5, 6, 7};
    unsigned int ancilla[2] = {20, 21};

    /* Multiplying by 0 -- should still produce a circuit (the mul sequence
     * with all-zero classical bits still goes through QFT + inverse QFT) */
    hot_path_mul_cq(circ, ret_q, 4, self_q, 4, 0, 0, 0, ancilla, 2);

    /* CQ_mul(4, 0) returns a valid sequence with QFT layers */
    assert(circuit_has_gates(circ) && "CQ mul with value=0 should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

int main(void) {
    printf("=== hot_path_mul C unit tests ===\n\n");

    test_cq_mul_4bit();
    test_cq_mul_8bit();
    test_cq_mul_controlled_4bit();
    test_qq_mul_4bit();
    test_qq_mul_8bit();
    test_qq_mul_controlled_4bit();
    test_cq_mul_zero();

    printf("\n=== ALL TESTS PASSED ===\n");
    return 0;
}
