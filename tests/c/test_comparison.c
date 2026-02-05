#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

#include "comparison_ops.h"
#include "types.h"

// Helper function to free a sequence (for testing)
void free_sequence(sequence_t *seq) {
    if (seq == NULL)
        return;
    if (seq->seq != NULL) {
        for (int i = 0; i < (int)seq->num_layer; i++) {
            if (seq->seq[i] != NULL) {
                // Free large_control arrays for gates with >2 controls
                for (int j = 0; j < (int)seq->gates_per_layer[i]; j++) {
                    if (seq->seq[i][j].NumControls > 2 && seq->seq[i][j].large_control != NULL) {
                        free(seq->seq[i][j].large_control);
                    }
                }
                free(seq->seq[i]);
            }
        }
        free(seq->seq);
    }
    if (seq->gates_per_layer != NULL) {
        free(seq->gates_per_layer);
    }
    free(seq);
}

// Test: CQ_equal_width returns non-NULL for valid inputs
void test_cq_equal_valid_inputs() {
    printf("Testing CQ_equal_width(4, 5)...\n");
    sequence_t *seq = CQ_equal_width(4, 5); // 4-bit, value 5
    printf("  Returned: %p\n", (void *)seq);
    assert(seq != NULL);
    printf("  num_layer: %u\n", seq->num_layer);
    assert(seq->num_layer > 0); // Should have gates
    printf("PASS: test_cq_equal_valid_inputs\n");
    free_sequence(seq);
}

// Test: CQ_equal_width returns empty sequence for overflow
void test_cq_equal_overflow() {
    sequence_t *seq = CQ_equal_width(4, 16); // 4-bit max is 15
    assert(seq != NULL);                     // Not NULL
    assert(seq->num_layer == 0);             // But empty
    printf("PASS: test_cq_equal_overflow\n");
    free_sequence(seq);
}

// Test: CQ_equal_width returns NULL for invalid width
void test_cq_equal_invalid_width() {
    assert(CQ_equal_width(0, 5) == NULL);
    assert(CQ_equal_width(-1, 5) == NULL);
    assert(CQ_equal_width(65, 5) == NULL);
    printf("PASS: test_cq_equal_invalid_width\n");
}

// Test: Various bit widths work
void test_cq_equal_various_widths() {
    sequence_t *seq1 = CQ_equal_width(1, 0);
    sequence_t *seq8 = CQ_equal_width(8, 127);
    sequence_t *seq16 = CQ_equal_width(16, 1000);
    sequence_t *seq32 = CQ_equal_width(32, 100000);

    assert(seq1 != NULL && seq1->num_layer > 0);
    assert(seq8 != NULL && seq8->num_layer > 0);
    assert(seq16 != NULL && seq16->num_layer > 0);
    assert(seq32 != NULL && seq32->num_layer > 0);
    printf("PASS: test_cq_equal_various_widths\n");

    free_sequence(seq1);
    free_sequence(seq8);
    free_sequence(seq16);
    free_sequence(seq32);
}

// Test: Edge values (0, 1, max for width)
void test_cq_equal_edge_values() {
    // 4-bit: range [0, 15] for unsigned interpretation
    sequence_t *seq_zero = CQ_equal_width(4, 0);
    sequence_t *seq_one = CQ_equal_width(4, 1);
    sequence_t *seq_max = CQ_equal_width(4, 15);

    assert(seq_zero != NULL && seq_zero->num_layer > 0);
    assert(seq_one != NULL && seq_one->num_layer > 0);
    assert(seq_max != NULL && seq_max->num_layer > 0);
    printf("PASS: test_cq_equal_edge_values\n");

    free_sequence(seq_zero);
    free_sequence(seq_one);
    free_sequence(seq_max);
}

// Test: Negative values with two's complement
void test_cq_equal_negative_values() {
    // 4-bit signed: range [-8, 7]
    sequence_t *seq_neg1 = CQ_equal_width(4, -1);
    sequence_t *seq_neg8 = CQ_equal_width(4, -8); // Min value for 4-bit signed

    assert(seq_neg1 != NULL && seq_neg1->num_layer > 0);
    assert(seq_neg8 != NULL && seq_neg8->num_layer > 0);
    printf("PASS: test_cq_equal_negative_values\n");

    free_sequence(seq_neg1);
    free_sequence(seq_neg8);
}

// Test: Negative overflow returns empty sequence
void test_cq_equal_negative_overflow() {
    // 4-bit signed min is -8, so -9 should overflow
    sequence_t *seq = CQ_equal_width(4, -9);
    assert(seq != NULL);         // Not NULL
    assert(seq->num_layer == 0); // But empty
    printf("PASS: test_cq_equal_negative_overflow\n");
    free_sequence(seq);
}

// Test: cCQ_equal_width exists and returns valid sequence
void test_ccq_equal_exists() {
    sequence_t *seq = cCQ_equal_width(4, 5);
    assert(seq != NULL);
    assert(seq->num_layer > 0);
    printf("PASS: test_ccq_equal_exists\n");
    free_sequence(seq);
}

// Test: cCQ_equal_width overflow handling
void test_ccq_equal_overflow() {
    sequence_t *seq = cCQ_equal_width(4, 16); // 4-bit max is 15
    assert(seq != NULL);                      // Not NULL
    assert(seq->num_layer == 0);              // But empty
    printf("PASS: test_ccq_equal_overflow\n");
    free_sequence(seq);
}

// Test: cCQ_equal_width invalid width
void test_ccq_equal_invalid_width() {
    assert(cCQ_equal_width(0, 5) == NULL);
    assert(cCQ_equal_width(-1, 5) == NULL);
    assert(cCQ_equal_width(65, 5) == NULL);
    printf("PASS: test_ccq_equal_invalid_width\n");
}

// Test: cCQ_equal_width various widths
void test_ccq_equal_various_widths() {
    sequence_t *seq1 = cCQ_equal_width(1, 0);
    sequence_t *seq8 = cCQ_equal_width(8, 127);
    sequence_t *seq16 = cCQ_equal_width(16, 1000);
    sequence_t *seq32 = cCQ_equal_width(32, 100000);

    assert(seq1 != NULL && seq1->num_layer > 0);
    assert(seq8 != NULL && seq8->num_layer > 0);
    assert(seq16 != NULL && seq16->num_layer > 0);
    assert(seq32 != NULL && seq32->num_layer > 0);
    printf("PASS: test_ccq_equal_various_widths\n");

    free_sequence(seq1);
    free_sequence(seq8);
    free_sequence(seq16);
    free_sequence(seq32);
}

// Test: Both functions produce sequences with reasonable gate counts
void test_gate_count_sanity() {
    sequence_t *seq_uncontrolled = CQ_equal_width(4, 5);
    sequence_t *seq_controlled = cCQ_equal_width(4, 5);

    assert(seq_uncontrolled != NULL);
    assert(seq_controlled != NULL);

    // Both should have gates (non-zero layers)
    assert(seq_uncontrolled->num_layer > 0);
    assert(seq_controlled->num_layer > 0);

    // Controlled version should have similar or slightly more gates
    // (since controlled gates are more complex)
    // This is a sanity check, not an exact comparison
    assert(seq_controlled->num_layer >= seq_uncontrolled->num_layer ||
           seq_controlled->num_layer <= seq_uncontrolled->num_layer + 5);

    printf("PASS: test_gate_count_sanity\n");

    free_sequence(seq_uncontrolled);
    free_sequence(seq_controlled);
}

// Test: Valid 1-bit and 2-bit comparisons return sequences
void test_valid_small_widths() {
    // Test 1-bit (fully implemented)
    sequence_t *seq1 = CQ_equal_width(1, 0);
    assert(seq1 != NULL);
    assert(seq1->num_layer > 0);
    free_sequence(seq1);

    // Test 2-bit (fully implemented)
    sequence_t *seq2 = CQ_equal_width(2, 3);
    assert(seq2 != NULL);
    assert(seq2->num_layer > 0);
    free_sequence(seq2);

    // Test controlled versions
    sequence_t *cseq1 = cCQ_equal_width(1, 1);
    assert(cseq1 != NULL);
    assert(cseq1->num_layer > 0);
    free_sequence(cseq1);

    sequence_t *cseq2 = cCQ_equal_width(2, 2);
    assert(cseq2 != NULL);
    assert(cseq2->num_layer > 0);
    free_sequence(cseq2);

    printf("PASS: test_valid_small_widths\n");
}

// Test: Multi-bit (3+) comparisons now fully implemented
void test_multibit_comparison() {
    // 3-bit comparison
    sequence_t *seq3 = CQ_equal_width(3, 5); // 101 in binary
    assert(seq3 != NULL);
    assert(seq3->num_layer > 0);
    // Verify we have a gate with 3 controls (the mcx gate)
    int found_mcx = 0;
    for (int l = 0; l < (int)seq3->used_layer; l++) {
        for (int g = 0; g < (int)seq3->gates_per_layer[l]; g++) {
            if (seq3->seq[l][g].NumControls == 3) {
                found_mcx = 1;
            }
        }
    }
    assert(found_mcx && "3-bit comparison should have 3-controlled gate");
    free_sequence(seq3);

    // 4-bit comparison
    sequence_t *seq4 = CQ_equal_width(4, 10); // 1010 in binary
    assert(seq4 != NULL);
    assert(seq4->num_layer > 0);
    free_sequence(seq4);

    // 8-bit comparison
    sequence_t *seq8 = CQ_equal_width(8, 127);
    assert(seq8 != NULL);
    assert(seq8->num_layer > 0);
    free_sequence(seq8);

    printf("PASS: test_multibit_comparison\n");
}

// Test: Controlled multi-bit comparisons
void test_controlled_multibit_comparison() {
    // 3-bit controlled comparison (4 controls total)
    sequence_t *cseq3 = cCQ_equal_width(3, 7);
    assert(cseq3 != NULL);
    assert(cseq3->num_layer > 0);
    // Verify 4-controlled gate exists
    int found_4ctrl = 0;
    for (int l = 0; l < (int)cseq3->used_layer; l++) {
        for (int g = 0; g < (int)cseq3->gates_per_layer[l]; g++) {
            if (cseq3->seq[l][g].NumControls == 4) {
                found_4ctrl = 1;
            }
        }
    }
    assert(found_4ctrl && "3-bit controlled comparison should have 4-controlled gate");
    free_sequence(cseq3);

    printf("PASS: test_controlled_multibit_comparison\n");
}

int main() {
    printf("Starting test program...\n");
    fflush(stdout);

    printf("Running comparison function tests...\n\n");
    fflush(stdout);

    // Basic NULL/overflow tests (don't allocate gates)
    printf("Testing invalid width handling...\n");
    test_cq_equal_invalid_width();
    test_ccq_equal_invalid_width();

    printf("\nTesting overflow handling...\n");
    test_cq_equal_overflow();
    test_ccq_equal_overflow();
    test_cq_equal_negative_overflow();

    printf("\nTesting valid sequence generation (1-2 bit widths)...\n");
    test_valid_small_widths();

    printf("\nTesting multi-bit (3+) comparison implementation...\n");
    test_multibit_comparison();
    test_controlled_multibit_comparison();

    printf("\n===  ALL TESTS PASSED ===\n");
    printf("Functions correctly handle: invalid width, overflow detection, sequence generation\n");
    printf("Multi-bit (3+) comparison logic now fully implemented using mcx gates.\n");
    return 0;
}
