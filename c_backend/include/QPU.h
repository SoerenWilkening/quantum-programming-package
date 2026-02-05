//
// QPU.h - Backward compatibility header
//
// This header is kept for backward compatibility with existing code.
// It simply includes circuit.h which provides the full API.
//
// Global state (instruction_t, QPU_state, R0-R3 registers) was removed
// in Phase 11. All functions now use explicit parameters instead.
//

#ifndef CQ_BACKEND_IMPROVED_QPU_H
#define CQ_BACKEND_IMPROVED_QPU_H

#include "circuit.h"

// Legacy global state removed (Phase 11):
// - instruction_t type (Q0-Q3, R0-R3 registers)
// - instruction_list[] array
// - QPU_state pointer
// - instruction_counter
//
// All sequence generation functions now take explicit parameters.
// See arithmetic_ops.h, bitwise_ops.h, comparison_ops.h for new APIs.

#endif // CQ_BACKEND_IMPROVED_QPU_H
