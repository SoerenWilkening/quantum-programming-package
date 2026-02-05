/**
 * @file qubit_allocator.h
 * @brief Centralized qubit allocation and lifecycle management.
 *
 * Provides centralized qubit allocation with:
 * - Contiguous qubit allocation
 * - Freed qubit reuse for memory efficiency
 * - Usage statistics for debugging and circuit analysis
 * - Optional DEBUG_OWNERSHIP tracking
 *
 * Dependencies: types.h
 */

#ifndef QUBIT_ALLOCATOR_H
#define QUBIT_ALLOCATOR_H

#include "types.h"

// Hard-coded maximum to prevent runaway allocation
#define ALLOCATOR_MAX_QUBITS 8192

/**
 * @brief Statistics for debugging and circuit analysis.
 *
 * Tracks qubit allocation patterns and usage for debugging and optimization.
 */
typedef struct {
    num_t peak_allocated;      // Highest water mark
    num_t total_allocations;   // Total alloc calls
    num_t total_deallocations; // Total free calls
    num_t current_in_use;      // Currently allocated
    num_t ancilla_allocations; // Total ancilla qubits allocated (FOUND-08)
} allocator_stats_t;

/**
 * @brief Centralized qubit allocator structure.
 *
 * Manages qubit allocation with reuse capability for freed qubits.
 * Prevents runaway allocation with hard-coded ALLOCATOR_MAX_QUBITS limit.
 */
typedef struct {
    qubit_t *indices;        // Array of qubit indices
    num_t capacity;          // Current array capacity
    num_t next_qubit;        // Next qubit index to allocate
    num_t freed_count;       // Number of qubits returned to pool
    qubit_t *freed_stack;    // Stack of freed qubit indices (for reuse)
    num_t freed_capacity;    // Capacity of freed stack
    allocator_stats_t stats; // Usage statistics

#ifdef DEBUG_OWNERSHIP
    // Debug-only: track which entity owns each qubit
    char **owner_tags; // [qubit] -> "qint_3" or "ancilla_5"
    num_t owner_capacity;
#endif
} qubit_allocator_t;

// Forward declaration for circuit_t (avoid circular dependency)
struct circuit_s;

/**
 * @brief Create a new qubit allocator.
 *
 * @param initial_capacity Initial capacity for qubit storage
 * @return Pointer to newly allocated allocator, or NULL on failure
 *
 * OWNERSHIP: Caller owns returned qubit_allocator_t*, must call allocator_destroy()
 */
qubit_allocator_t *allocator_create(num_t initial_capacity);

/**
 * @brief Destroy a qubit allocator and free all resources.
 *
 * @param alloc Allocator to destroy (can be NULL)
 */
void allocator_destroy(qubit_allocator_t *alloc);

/**
 * @brief Allocate contiguous qubits.
 *
 * Allocates `count` contiguous qubits. Reuses freed qubits when possible.
 * If is_ancilla is true, increments ancilla_allocations stat.
 *
 * @param alloc Allocator to use
 * @param count Number of contiguous qubits to allocate
 * @param is_ancilla True if allocating ancilla qubits
 * @return Starting qubit index, or (qubit_t)-1 on failure
 */
qubit_t allocator_alloc(qubit_allocator_t *alloc, num_t count, bool is_ancilla);

/**
 * @brief Return qubits to pool for potential reuse.
 *
 * @param alloc Allocator to use
 * @param start Starting qubit index
 * @param count Number of qubits to free
 * @return 0 on success, -1 on double-free
 */
int allocator_free(qubit_allocator_t *alloc, qubit_t start, num_t count);

/**
 * @brief Get allocation statistics.
 *
 * @param alloc Allocator to query
 * @return Allocation statistics structure
 */
allocator_stats_t allocator_get_stats(qubit_allocator_t *alloc);

/**
 * @brief Reset allocation statistics to zero.
 *
 * @param alloc Allocator to reset
 */
void allocator_reset_stats(qubit_allocator_t *alloc);

/**
 * @brief Get allocator from circuit (accessor for Python bindings).
 *
 * circuit_t is opaque in Cython, so this accessor is needed.
 *
 * @param circ Circuit to query
 * @return Pointer to circuit's allocator
 */
qubit_allocator_t *circuit_get_allocator(struct circuit_s *circ);

#ifdef DEBUG_OWNERSHIP
// Debug ownership tracking
void allocator_set_owner(qubit_allocator_t *alloc, qubit_t qubit, const char *tag);
const char *allocator_get_owner(qubit_allocator_t *alloc, qubit_t qubit);
#endif

#endif // QUBIT_ALLOCATOR_H
