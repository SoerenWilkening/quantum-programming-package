/**
 * @file test_allocator_block.c
 * @brief Unit tests for block-based qubit allocator (Phase 65, Plan 02).
 *
 * Tests block allocation, reuse, splitting, coalescing (forward, reverse,
 * three-way), mixed single/block operations, and oversized requests.
 */

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

#include "qubit_allocator.h"

/* ------------------------------------------------------------------ */
/* Test 1: Single-qubit alloc/free backward compatibility             */
/* ------------------------------------------------------------------ */
static void test_single_qubit_alloc_free(void) {
    printf("test_single_qubit_alloc_free... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    qubit_t q1 = allocator_alloc(alloc, 1, false);
    assert(q1 != (qubit_t)-1);

    int rc = allocator_free(alloc, q1, 1);
    assert(rc == 0);

    qubit_t q2 = allocator_alloc(alloc, 1, false);
    assert(q2 == q1 && "Second single-qubit alloc should reuse first index");

    allocator_destroy(alloc);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 2: Block alloc returns contiguous fresh qubits                */
/* ------------------------------------------------------------------ */
static void test_block_alloc_contiguous(void) {
    printf("test_block_alloc_contiguous... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    qubit_t s1 = allocator_alloc(alloc, 4, false);
    assert(s1 != (qubit_t)-1);

    qubit_t s2 = allocator_alloc(alloc, 4, false);
    assert(s2 != (qubit_t)-1);
    assert(s2 == s1 + 4 && "Second block should be contiguous with first");

    allocator_destroy(alloc);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 3: Block reuse after free                                     */
/* ------------------------------------------------------------------ */
static void test_block_reuse_after_free(void) {
    printf("test_block_reuse_after_free... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    qubit_t s1 = allocator_alloc(alloc, 4, false);
    assert(s1 != (qubit_t)-1);

    int rc = allocator_free(alloc, s1, 4);
    assert(rc == 0);

    qubit_t s2 = allocator_alloc(alloc, 4, false);
    assert(s2 == s1 && "Freed block of 4 should be reused");

    allocator_destroy(alloc);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 4: Fresh allocation when no freed block fits                  */
/* ------------------------------------------------------------------ */
static void test_block_alloc_fresh_when_no_fit(void) {
    printf("test_block_alloc_fresh_when_no_fit... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    /* Allocate block of 3 (indices 0-2), then free it */
    qubit_t s1 = allocator_alloc(alloc, 3, false);
    assert(s1 == 0);
    int rc = allocator_free(alloc, s1, 3);
    assert(rc == 0);

    /* Request block of 5 -- freed block is only 3, so allocate fresh */
    qubit_t s2 = allocator_alloc(alloc, 5, false);
    assert(s2 == 3 && "Should allocate fresh since freed block (3) is too small for 5");

    allocator_destroy(alloc);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 5: Block splitting on partial reuse                           */
/* ------------------------------------------------------------------ */
static void test_block_split_on_partial_reuse(void) {
    printf("test_block_split_on_partial_reuse... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    /* Allocate 6 (indices 0-5), free all */
    qubit_t s1 = allocator_alloc(alloc, 6, false);
    assert(s1 == 0);
    int rc = allocator_free(alloc, s1, 6);
    assert(rc == 0);

    /* Request 2 -- should take from front of freed block */
    qubit_t s2 = allocator_alloc(alloc, 2, false);
    assert(s2 == 0 && "Should reuse start of freed block");

    /* Request 4 -- should take remainder */
    qubit_t s3 = allocator_alloc(alloc, 4, false);
    assert(s3 == 2 && "Should reuse remainder of split block");

    allocator_destroy(alloc);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 6: Coalesce adjacent blocks (forward order free)              */
/* ------------------------------------------------------------------ */
static void test_coalesce_adjacent_blocks(void) {
    printf("test_coalesce_adjacent_blocks... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    /* Allocate three consecutive blocks of 2: [0,1], [2,3], [4,5] */
    qubit_t a = allocator_alloc(alloc, 2, false);
    qubit_t b = allocator_alloc(alloc, 2, false);
    qubit_t c = allocator_alloc(alloc, 2, false);
    assert(a == 0 && b == 2 && c == 4);

    /* Free [0,1] then [2,3] -- should coalesce into [0,3] */
    allocator_free(alloc, a, 2);
    allocator_free(alloc, b, 2);

    /* Request block of 4 -- should be satisfied by coalesced block [0,3] */
    qubit_t s = allocator_alloc(alloc, 4, false);
    assert(s == 0 && "Coalesced block [0,3] should satisfy request for 4");

    allocator_destroy(alloc);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 7: Coalesce adjacent blocks (reverse order free)              */
/* ------------------------------------------------------------------ */
static void test_coalesce_reverse_order(void) {
    printf("test_coalesce_reverse_order... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    /* Allocate three consecutive blocks of 2: [0,1], [2,3], [4,5] */
    qubit_t a = allocator_alloc(alloc, 2, false);
    qubit_t b = allocator_alloc(alloc, 2, false);
    qubit_t c = allocator_alloc(alloc, 2, false);
    assert(a == 0 && b == 2 && c == 4);

    /* Free [2,3] then [0,1] -- should coalesce into [0,3] */
    allocator_free(alloc, b, 2);
    allocator_free(alloc, a, 2);

    /* Request block of 4 -- should be satisfied by coalesced block [0,3] */
    qubit_t s = allocator_alloc(alloc, 4, false);
    assert(s == 0 && "Coalesced block [0,3] should satisfy request for 4 (reverse free)");

    allocator_destroy(alloc);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 8: Three-way coalescing                                       */
/* ------------------------------------------------------------------ */
static void test_coalesce_three_way(void) {
    printf("test_coalesce_three_way... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    /* Allocate three blocks of 2: [0,1], [2,3], [4,5] */
    qubit_t a = allocator_alloc(alloc, 2, false);
    qubit_t b = allocator_alloc(alloc, 2, false);
    qubit_t c = allocator_alloc(alloc, 2, false);
    assert(a == 0 && b == 2 && c == 4);

    /* Free [0,1], then [4,5], then [2,3] */
    allocator_free(alloc, a, 2);
    allocator_free(alloc, c, 2);
    allocator_free(alloc, b, 2);

    /* After freeing [2,3], all three should coalesce into [0,5] */
    qubit_t s = allocator_alloc(alloc, 6, false);
    assert(s == 0 && "Three-way coalesced block [0,5] should satisfy request for 6");

    allocator_destroy(alloc);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 9: Mixed single-qubit and block operations                    */
/* ------------------------------------------------------------------ */
static void test_mixed_single_and_block(void) {
    printf("test_mixed_single_and_block... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    /* Allocate: 1 qubit (idx 0), block of 3 (idx 1-3), 1 qubit (idx 4) */
    qubit_t q1 = allocator_alloc(alloc, 1, false);
    qubit_t blk = allocator_alloc(alloc, 3, false);
    qubit_t q2 = allocator_alloc(alloc, 1, false);
    assert(q1 == 0 && blk == 1 && q2 == 4);

    /* Free the block of 3 (indices 1-3) */
    allocator_free(alloc, blk, 3);

    /* Allocate 1 qubit -- should come from freed block (index 1) */
    qubit_t q3 = allocator_alloc(alloc, 1, false);
    assert(q3 == 1 && "Single qubit should reuse from freed block");

    /* Allocate block of 2 -- should come from remainder (indices 2-3) */
    qubit_t blk2 = allocator_alloc(alloc, 2, false);
    assert(blk2 == 2 && "Block of 2 should reuse remainder of freed block");

    allocator_destroy(alloc);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Test 10: No reuse for oversized request                            */
/* ------------------------------------------------------------------ */
static void test_no_reuse_for_oversized_request(void) {
    printf("test_no_reuse_for_oversized_request... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    /* Allocate and free several small blocks */
    qubit_t a = allocator_alloc(alloc, 2, false); /* 0-1 */
    qubit_t b = allocator_alloc(alloc, 3, false); /* 2-4 */
    qubit_t c = allocator_alloc(alloc, 2, false); /* 5-6 */
    assert(a == 0 && b == 2 && c == 5);

    allocator_free(alloc, a, 2);
    allocator_free(alloc, b, 3);
    allocator_free(alloc, c, 2);
    /* Free list should have coalesced block [0,6] = 7 qubits */

    /* Request block of 10 -- even coalesced block (7) is too small */
    qubit_t s = allocator_alloc(alloc, 10, false);
    assert(s >= 7 && "Oversized request should allocate fresh (start >= 7)");

    allocator_destroy(alloc);
    printf("PASS\n");
}

/* ------------------------------------------------------------------ */
/* Main                                                               */
/* ------------------------------------------------------------------ */
int main(void) {
    printf("=== block allocator unit tests ===\n\n");

    test_single_qubit_alloc_free();
    test_block_alloc_contiguous();
    test_block_reuse_after_free();
    test_block_alloc_fresh_when_no_fit();
    test_block_split_on_partial_reuse();
    test_coalesce_adjacent_blocks();
    test_coalesce_reverse_order();
    test_coalesce_three_way();
    test_mixed_single_and_block();
    test_no_reuse_for_oversized_request();

    printf("\n=== ALL 10 TESTS PASSED ===\n");
    return 0;
}
