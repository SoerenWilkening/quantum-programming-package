//
// circuit_optimizer.h - Post-construction circuit optimization
// Dependencies: types.h
//
// Provides optimization passes that can be run after circuit construction:
// - Gate merging: combine consecutive same-type gates
// - Inverse cancellation: remove X-X, H-H pairs
//
// Note: optimizer.h handles gate placement during construction.
//       circuit_optimizer.h handles post-construction optimization.
//

#ifndef QUANTUM_CIRCUIT_OPTIMIZER_H
#define QUANTUM_CIRCUIT_OPTIMIZER_H

#include "types.h"

// Forward declaration
struct circuit_s;
typedef struct circuit_s circuit_t;

// Available optimization passes
typedef enum {
    OPT_PASS_MERGE,         // Merge consecutive same-type gates
    OPT_PASS_CANCEL_INVERSE // Cancel inverse gate pairs (X-X, H-H)
} opt_pass_t;

// Run all optimization passes
// Returns new optimized circuit (caller owns and must free)
// Original circuit is preserved
circuit_t *circuit_optimize(circuit_t *circ);

// Run specific optimization pass
// Returns new optimized circuit (caller owns and must free)
// Original circuit is preserved
circuit_t *circuit_optimize_pass(circuit_t *circ, opt_pass_t pass);

// Check if optimization would change circuit
// Returns 1 if optimization would have effect, 0 otherwise
int circuit_can_optimize(circuit_t *circ);

#endif // QUANTUM_CIRCUIT_OPTIMIZER_H
