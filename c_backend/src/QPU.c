//
// QPU.c - Backward compatibility module
//
// Global instruction state removed (Phase 11).
// Gate operations moved to optimizer.c (Phase 4).
// Circuit allocation is in circuit_allocations.c.
// Sequence generation functions now take explicit parameters.
//
// This file is kept for backward compatibility only.
// New code should use circuit.h API directly.
//

#include "QPU.h"

// Global state removed (Phase 11) - all functions now use explicit parameters
// instruction_list[], QPU_state, and instruction_counter were removed
// because sequence generation functions no longer depend on global state.
