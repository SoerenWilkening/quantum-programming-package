//
// QPU.h - Backward compatibility header
// New code should include circuit.h directly
//
// This header is kept for backward compatibility with existing code.
// It simply includes circuit.h which provides the full API.
//

#ifndef CQ_BACKEND_IMPROVED_QPU_H
#define CQ_BACKEND_IMPROVED_QPU_H

#include "circuit.h"

// Instruction type for sequence generation (not part of circuit API)
typedef struct instruction_t {
    char *name;

    // quantum storing registers
    quantum_int_t *Q0;
    quantum_int_t *Q1;
    quantum_int_t *Q2;
    quantum_int_t *Q3;

    // classical storing registers
    int *R0;
    int *R1;
    int *R2;
    int *R3;

    sequence_t *(*routine)();

    bool invert;
    struct instruction_t *next_instruction; // used for jumps
} instruction_t;

// Global instruction state (used by sequence generation functions in IntegerAddition, etc.)
// TODO(Phase 5+): These are needed for CQ_add/CC_mul style functions that generate sequences
// from classical inputs. Not related to circuit gate adding (which moved to optimizer.c)
extern instruction_t instruction_list[MAXINSTRUCTIONS];
extern int instruction_counter;
extern instruction_t *QPU_state;

#endif // CQ_BACKEND_IMPROVED_QPU_H
