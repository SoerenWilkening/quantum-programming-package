//
// qubit_allocator.h - Centralized qubit allocation
// Dependencies: types.h
//

#ifndef QUBIT_ALLOCATOR_H
#define QUBIT_ALLOCATOR_H

#include "types.h"

// Hard-coded maximum to prevent runaway allocation
#define ALLOCATOR_MAX_QUBITS 8192

// Statistics for debugging and circuit analysis
typedef struct {
    num_t peak_allocated;      // Highest water mark
    num_t total_allocations;   // Total alloc calls
    num_t total_deallocations; // Total free calls
    num_t current_in_use;      // Currently allocated
    num_t ancilla_allocations; // Total ancilla qubits allocated (FOUND-08)
} allocator_stats_t;

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

// Lifecycle
// OWNERSHIP: Caller owns returned qubit_allocator_t*, must call allocator_destroy()
qubit_allocator_t *allocator_create(num_t initial_capacity);
void allocator_destroy(qubit_allocator_t *alloc);

// Allocation
// Returns starting qubit index, or (qubit_t)-1 on failure
// Allocates `count` contiguous qubits
// If is_ancilla is true, increments ancilla_allocations stat
qubit_t allocator_alloc(qubit_allocator_t *alloc, num_t count, bool is_ancilla);

// Deallocation
// Returns qubits to pool for potential reuse
// Returns 0 on success, -1 on double-free
int allocator_free(qubit_allocator_t *alloc, qubit_t start, num_t count);

// Statistics
allocator_stats_t allocator_get_stats(qubit_allocator_t *alloc);
void allocator_reset_stats(qubit_allocator_t *alloc);

// Accessor for Python bindings (circuit_t is opaque in Cython)
qubit_allocator_t *circuit_get_allocator(struct circuit_s *circ);

#ifdef DEBUG_OWNERSHIP
// Debug ownership tracking
void allocator_set_owner(qubit_allocator_t *alloc, qubit_t qubit, const char *tag);
const char *allocator_get_owner(qubit_allocator_t *alloc, qubit_t qubit);
#endif

#endif // QUBIT_ALLOCATOR_H
