//
// QPU.c - Global instruction state for sequence generation
//
// Gate optimization moved to optimizer.c (Phase 4)
// Circuit allocation is in circuit_allocations.c
//
// This file now contains only the global instruction state needed by
// sequence generation functions (CQ_add, CC_mul, etc. in IntegerAddition.c, etc.)
//

#include "QPU.h"

// Global instruction state for sequence generation
// Used by IntegerAddition.c, IntegerMultiplication.c, IntegerComparison.c, LogicOperations.c
// TODO(Phase 5+): Refactor sequence generation to accept parameters instead of using globals
instruction_t instruction_list[MAXINSTRUCTIONS];
instruction_t *QPU_state = &instruction_list[0];
int instruction_counter = 0;
