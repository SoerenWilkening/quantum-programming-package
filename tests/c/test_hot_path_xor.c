/**
 * @file test_hot_path_xor.c
 * @brief Unit tests for hot_path_xor C implementation (Phase 60, Plan 04).
 *
 * Tests that hot_path_ixor_qq and hot_path_ixor_cq correctly build qubit
 * layouts and produce gates in the circuit.
 */

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "circuit.h"
#include "hot_path_xor.h"

/* Helper: check that circuit has gates (used_layer > 0) */
static int circuit_has_gates(circuit_t *circ) {
    return circ->used_layer > 0;
}

/* ------------------------------------------------------------------ */
/* Test: QQ XOR (quantum ^= quantum) produces gates                   */
/* ------------------------------------------------------------------ */
static void test_qq_xor_4bit(void) {
    printf("test_qq_xor_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[4] = {0, 1, 2, 3};
    unsigned int other_q[4] = {4, 5, 6, 7};

    hot_path_ixor_qq(circ, self_q, 4, other_q, 4);

    assert(circuit_has_gates(circ) && "QQ XOR 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

static void test_qq_xor_8bit(void) {
    printf("test_qq_xor_8bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[8], other_q[8];
    for (int i = 0; i < 8; i++) {
        self_q[i] = (unsigned int)i;
        other_q[i] = (unsigned int)(8 + i);
    }

    hot_path_ixor_qq(circ, self_q, 8, other_q, 8);

    assert(circuit_has_gates(circ) && "QQ XOR 8-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: QQ XOR with mismatched widths (uses min)                     */
/* ------------------------------------------------------------------ */
static void test_qq_xor_mismatched(void) {
    printf("test_qq_xor_mismatched... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[8] = {0, 1, 2, 3, 4, 5, 6, 7};
    unsigned int other_q[4] = {8, 9, 10, 11};

    /* self is 8-bit, other is 4-bit: should XOR only 4 bits */
    hot_path_ixor_qq(circ, self_q, 8, other_q, 4);

    assert(circuit_has_gates(circ) && "Mismatched QQ XOR should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: CQ XOR (quantum ^= classical) produces gates                 */
/* ------------------------------------------------------------------ */
static void test_cq_xor_4bit(void) {
    printf("test_cq_xor_4bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[4] = {0, 1, 2, 3};

    /* XOR with value 5 (binary 0101) - should flip bits 0 and 2 */
    hot_path_ixor_cq(circ, self_q, 4, 5);

    assert(circuit_has_gates(circ) && "CQ XOR 4-bit should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

static void test_cq_xor_8bit(void) {
    printf("test_cq_xor_8bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[8];
    for (int i = 0; i < 8; i++) {
        self_q[i] = (unsigned int)i;
    }

    /* XOR with 0xFF (all bits set) - should flip all 8 bits */
    hot_path_ixor_cq(circ, self_q, 8, 0xFF);

    assert(circuit_has_gates(circ) && "CQ XOR 8-bit all-ones should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: CQ XOR with value 0 produces no gates                        */
/* ------------------------------------------------------------------ */
static void test_cq_xor_zero(void) {
    printf("test_cq_xor_zero... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[4] = {0, 1, 2, 3};

    /* XOR with 0 - no bits set, so no gates should be produced */
    hot_path_ixor_cq(circ, self_q, 4, 0);

    /* XOR with 0 should NOT produce any gates */
    assert(!circuit_has_gates(circ) && "CQ XOR with 0 should produce no gates");
    printf("PASS (no gates produced)\n");

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: QQ XOR with 1-bit (single CNOT)                              */
/* ------------------------------------------------------------------ */
static void test_qq_xor_1bit(void) {
    printf("test_qq_xor_1bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[1] = {0};
    unsigned int other_q[1] = {1};

    hot_path_ixor_qq(circ, self_q, 1, other_q, 1);

    assert(circuit_has_gates(circ) && "QQ XOR 1-bit should produce a CNOT gate");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

/* ------------------------------------------------------------------ */
/* Test: CQ XOR with single bit set                                   */
/* ------------------------------------------------------------------ */
static void test_cq_xor_single_bit(void) {
    printf("test_cq_xor_single_bit... ");
    fflush(stdout);

    circuit_t *circ = init_circuit();
    assert(circ != NULL);

    unsigned int self_q[8];
    for (int i = 0; i < 8; i++) {
        self_q[i] = (unsigned int)i;
    }

    /* XOR with 1 (only LSB set) - should produce exactly 1 NOT gate */
    hot_path_ixor_cq(circ, self_q, 8, 1);

    assert(circuit_has_gates(circ) && "CQ XOR with 1 should produce gates");
    printf("PASS (used_layer=%u)\n", circ->used_layer);

    free_circuit(circ);
}

int main(void) {
    printf("=== hot_path_xor C unit tests ===\n\n");

    test_qq_xor_4bit();
    test_qq_xor_8bit();
    test_qq_xor_mismatched();
    test_cq_xor_4bit();
    test_cq_xor_8bit();
    test_cq_xor_zero();
    test_qq_xor_1bit();
    test_cq_xor_single_bit();

    printf("\n=== ALL TESTS PASSED ===\n");
    return 0;
}
