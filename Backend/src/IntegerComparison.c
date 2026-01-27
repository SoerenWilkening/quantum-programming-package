//
// Created by Sören Wilkening on 09.11.24.
//

#include "Integer.h"
#include "QPU.h"
#include "comparison_ops.h"
#include "definition.h"
#include "gate.h"
#include <stdlib.h>

// ======================================================
// Width-Parameterized Comparison Operations (Phase 7)
// ======================================================

// Stub implementations for Phase 7
// Full C-level circuits will be implemented in Phase 8
// Phase 7 uses Python-level comparison via existing primitives

sequence_t *QQ_equal(int bits) {
    // Stub: Returns NULL, Python uses XOR pattern directly
    // Phase 8 will implement optimized C-level circuit
    (void)bits; // Suppress unused warning
    return NULL;
}

sequence_t *QQ_less_than(int bits) {
    // Stub: Returns NULL, Python uses subtraction + MSB check
    // Phase 8 will implement optimized C-level circuit
    (void)bits;
    return NULL;
}

sequence_t *CQ_equal_width(int bits, int64_t value) {
    // Stub: Returns NULL, Python converts value to qint and uses QQ pattern
    (void)bits;
    (void)value;
    return NULL;
}

sequence_t *CQ_less_than(int bits, int64_t value) {
    // Stub: Returns NULL, Python converts value to qint and uses QQ pattern
    (void)bits;
    (void)value;
    return NULL;
}

// ======================================================
// Legacy Comparison Operations (INTEGERSIZE-based)
// ======================================================

// CC_equal removed (Phase 11) - purely classical, no quantum gate generation

// CQ_equal() removed (Phase 11-04) - used QPU_state->R0 for classical value
// Use CQ_equal_width(bits, value) instead with explicit parameters

// cCQ_equal() removed (Phase 11-04) - used QPU_state->R0 for classical value
// Use controlled version of CQ_equal_width() when available
