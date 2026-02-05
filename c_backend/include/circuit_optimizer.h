/**
 * @file circuit_optimizer.h
 * @brief Post-construction circuit optimization passes.
 *
 * Provides optimization passes that can be run after circuit construction:
 * - Gate merging: combine consecutive same-type gates
 * - Inverse cancellation: remove X-X, H-H pairs
 *
 * Note: optimizer.h handles gate placement during construction.
 *       circuit_optimizer.h handles post-construction optimization.
 *
 * Dependencies: types.h
 */

#ifndef QUANTUM_CIRCUIT_OPTIMIZER_H
#define QUANTUM_CIRCUIT_OPTIMIZER_H

#include "types.h"

// Forward declaration
struct circuit_s;
typedef struct circuit_s circuit_t;

/**
 * @brief Available optimization passes.
 */
typedef enum {
    OPT_PASS_MERGE,         ///< Merge consecutive same-type gates
    OPT_PASS_CANCEL_INVERSE ///< Cancel inverse gate pairs (X-X, H-H)
} opt_pass_t;

/**
 * @brief Run all optimization passes on circuit.
 *
 * Creates optimized copy of circuit by running all available passes.
 * Original circuit is preserved.
 *
 * @param circ Circuit to optimize
 * @return New optimized circuit (caller owns and must free)
 */
circuit_t *circuit_optimize(circuit_t *circ);

/**
 * @brief Run specific optimization pass on circuit.
 *
 * Creates optimized copy of circuit by running specified pass.
 * Original circuit is preserved.
 *
 * @param circ Circuit to optimize
 * @param pass Optimization pass to run
 * @return New optimized circuit (caller owns and must free)
 */
circuit_t *circuit_optimize_pass(circuit_t *circ, opt_pass_t pass);

/**
 * @brief Check if optimization would change circuit.
 *
 * Simple heuristic: returns 1 if gates exist, 0 otherwise.
 *
 * @param circ Circuit to check
 * @return 1 if optimization would have effect, 0 otherwise
 */
int circuit_can_optimize(circuit_t *circ);

#endif // QUANTUM_CIRCUIT_OPTIMIZER_H
