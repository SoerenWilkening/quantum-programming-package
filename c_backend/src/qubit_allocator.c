//
// Created by Claude (Anthropic) on 26.01.26.
//

#include "qubit_allocator.h"
#include "circuit.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Initial freed blocks array capacity
#define FREED_BLOCKS_INITIAL_SIZE 32

qubit_allocator_t *allocator_create(num_t initial_capacity) {
    // OWNERSHIP: Caller owns returned qubit_allocator_t*, must call allocator_destroy()
    if (initial_capacity == 0 || initial_capacity > ALLOCATOR_MAX_QUBITS) {
        return NULL;
    }

    qubit_allocator_t *alloc = malloc(sizeof(qubit_allocator_t));
    if (alloc == NULL) {
        return NULL;
    }

    // Allocate indices array
    alloc->indices = malloc(initial_capacity * sizeof(qubit_t));
    if (alloc->indices == NULL) {
        free(alloc);
        return NULL;
    }

    // Allocate freed blocks array for block-based qubit reuse
    alloc->freed_blocks = malloc(FREED_BLOCKS_INITIAL_SIZE * sizeof(qubit_block_t));
    if (alloc->freed_blocks == NULL) {
        free(alloc->indices);
        free(alloc);
        return NULL;
    }

    // Initialize basic fields
    alloc->capacity = initial_capacity;
    alloc->next_qubit = 0;
    alloc->freed_block_count = 0;
    alloc->freed_block_capacity = FREED_BLOCKS_INITIAL_SIZE;

    // Zero all statistics
    memset(&alloc->stats, 0, sizeof(allocator_stats_t));

#ifdef DEBUG
    alloc->is_ancilla_map = calloc(initial_capacity, sizeof(bool));
    if (alloc->is_ancilla_map == NULL) {
        free(alloc->freed_blocks);
        free(alloc->indices);
        free(alloc);
        return NULL;
    }
    alloc->ancilla_map_capacity = initial_capacity;
    alloc->ancilla_outstanding = 0;
#endif

#ifdef DEBUG_OWNERSHIP
    // Allocate ownership tracking arrays
    alloc->owner_tags = calloc(initial_capacity, sizeof(char *));
    if (alloc->owner_tags == NULL) {
        free(alloc->freed_blocks);
        free(alloc->indices);
        free(alloc);
        return NULL;
    }
    alloc->owner_capacity = initial_capacity;
#endif

    return alloc;
}

void allocator_destroy(qubit_allocator_t *alloc) {
    if (alloc == NULL) {
        return;
    }

#ifdef DEBUG
    if (alloc->ancilla_outstanding > 0) {
        fprintf(stderr, "ANCILLA LEAK: %u ancilla qubits not freed before destroy\n",
                alloc->ancilla_outstanding);
        for (num_t i = 0; i < alloc->next_qubit; i++) {
            if (i < alloc->ancilla_map_capacity && alloc->is_ancilla_map[i]) {
                // Check if qubit i is in the freed blocks list
                bool found_freed = false;
                for (num_t j = 0; j < alloc->freed_block_count; j++) {
                    if (i >= alloc->freed_blocks[j].start &&
                        i < alloc->freed_blocks[j].start + alloc->freed_blocks[j].count) {
                        found_freed = true;
                        break;
                    }
                }
                if (!found_freed) {
                    fprintf(stderr, "  Leaked ancilla qubit: %u\n", i);
                }
            }
        }
        assert(0 && "Ancilla leak detected");
    }
    free(alloc->is_ancilla_map);
#endif

#ifdef DEBUG_OWNERSHIP
    // Free all ownership tag strings
    if (alloc->owner_tags != NULL) {
        for (num_t i = 0; i < alloc->owner_capacity; i++) {
            if (alloc->owner_tags[i] != NULL) {
                free(alloc->owner_tags[i]);
            }
        }
        free(alloc->owner_tags);
    }
#endif

    free(alloc->freed_blocks);
    free(alloc->indices);
    free(alloc);
}

qubit_t allocator_alloc(qubit_allocator_t *alloc, num_t count, bool is_ancilla) {
    if (alloc == NULL || count == 0) {
        return (qubit_t)-1;
    }

    qubit_t start_qubit;

    // Try to reuse freed blocks (first-fit search for any count >= 1)
    bool reused = false;
    for (num_t i = 0; i < alloc->freed_block_count; i++) {
        if (alloc->freed_blocks[i].count >= count) {
            start_qubit = alloc->freed_blocks[i].start;

            if (alloc->freed_blocks[i].count == count) {
                // Exact fit: remove block from array
                alloc->freed_block_count--;
                if (i < alloc->freed_block_count) {
                    memmove(&alloc->freed_blocks[i], &alloc->freed_blocks[i + 1],
                            (alloc->freed_block_count - i) * sizeof(qubit_block_t));
                }
            } else {
                // Partial fit: shrink block (take from the front)
                alloc->freed_blocks[i].start += count;
                alloc->freed_blocks[i].count -= count;
            }

            reused = true;
            break;
        }
    }

    if (!reused) {
        // No freed block fits -- allocate fresh from next_qubit
        // Check if we need to expand capacity
        if (alloc->next_qubit + count > alloc->capacity) {
            // Double capacity, but don't exceed max
            num_t new_capacity = alloc->capacity * 2;
            if (new_capacity > ALLOCATOR_MAX_QUBITS) {
                new_capacity = ALLOCATOR_MAX_QUBITS;
            }

            // Would still exceed max?
            if (alloc->next_qubit + count > new_capacity) {
                return (qubit_t)-1;
            }

            // Reallocate indices array
            qubit_t *new_indices = realloc(alloc->indices, new_capacity * sizeof(qubit_t));
            if (new_indices == NULL) {
                return (qubit_t)-1;
            }
            alloc->indices = new_indices;
            alloc->capacity = new_capacity;

#ifdef DEBUG_OWNERSHIP
            // Reallocate ownership tracking
            char **new_owner_tags = realloc(alloc->owner_tags, new_capacity * sizeof(char *));
            if (new_owner_tags == NULL) {
                return (qubit_t)-1;
            }
            // Zero new entries
            for (num_t i = alloc->owner_capacity; i < new_capacity; i++) {
                new_owner_tags[i] = NULL;
            }
            alloc->owner_tags = new_owner_tags;
            alloc->owner_capacity = new_capacity;
#endif
        }

        // Allocate from next_qubit
        start_qubit = alloc->next_qubit;
        alloc->next_qubit += count;
    }

    // Update statistics
    alloc->stats.total_allocations++;
    alloc->stats.current_in_use += count;
    if (alloc->stats.current_in_use > alloc->stats.peak_allocated) {
        alloc->stats.peak_allocated = alloc->stats.current_in_use;
    }

    // Track ancilla allocations and debug map
    if (is_ancilla) {
        alloc->stats.ancilla_allocations += count;

#ifdef DEBUG
        {
            // Expand ancilla map if needed
            if (start_qubit + count > alloc->ancilla_map_capacity) {
                num_t new_cap = alloc->ancilla_map_capacity;
                while (new_cap < start_qubit + count) {
                    new_cap *= 2;
                }
                if (new_cap > ALLOCATOR_MAX_QUBITS)
                    new_cap = ALLOCATOR_MAX_QUBITS;
                bool *new_map = realloc(alloc->is_ancilla_map, new_cap * sizeof(bool));
                if (new_map != NULL) {
                    memset(new_map + alloc->ancilla_map_capacity, 0,
                           (new_cap - alloc->ancilla_map_capacity) * sizeof(bool));
                    alloc->is_ancilla_map = new_map;
                    alloc->ancilla_map_capacity = new_cap;
                }
            }
            // Mark qubits as ancilla
            for (num_t i = 0; i < count; i++) {
                if (start_qubit + i < alloc->ancilla_map_capacity) {
                    alloc->is_ancilla_map[start_qubit + i] = true;
                }
            }
            alloc->ancilla_outstanding += count;
        }
#endif
    }

    return start_qubit;
}

int allocator_free(qubit_allocator_t *alloc, qubit_t start, num_t count) {
    if (alloc == NULL || count == 0) {
        return -1;
    }

    // Basic validation: check if indices are in valid range
    if (start >= alloc->next_qubit || start + count > alloc->next_qubit) {
        // Potential double-free or invalid indices
        return -1;
    }

    // Update statistics
    alloc->stats.total_deallocations++;
    alloc->stats.current_in_use -= count;

#ifdef DEBUG
    // Decrement ancilla outstanding for any ancilla qubits being freed
    for (num_t i = 0; i < count; i++) {
        qubit_t q = start + i;
        if (q < alloc->ancilla_map_capacity && alloc->is_ancilla_map[q]) {
            alloc->ancilla_outstanding--;
            alloc->is_ancilla_map[q] = false; // Clear the flag
        }
    }
#endif

    // Expand freed_blocks array if needed
    if (alloc->freed_block_count >= alloc->freed_block_capacity) {
        num_t new_capacity = alloc->freed_block_capacity * 2;
        qubit_block_t *new_blocks =
            realloc(alloc->freed_blocks, new_capacity * sizeof(qubit_block_t));
        if (new_blocks == NULL) {
            // Can't expand, but freeing still succeeded conceptually
            return 0;
        }
        alloc->freed_blocks = new_blocks;
        alloc->freed_block_capacity = new_capacity;
    }

    // Find insertion point to maintain sort by start index
    num_t insert_pos = 0;
    while (insert_pos < alloc->freed_block_count && alloc->freed_blocks[insert_pos].start < start) {
        insert_pos++;
    }

    // Make room for the new block by shifting elements right
    if (insert_pos < alloc->freed_block_count) {
        memmove(&alloc->freed_blocks[insert_pos + 1], &alloc->freed_blocks[insert_pos],
                (alloc->freed_block_count - insert_pos) * sizeof(qubit_block_t));
    }

    // Insert the new block
    alloc->freed_blocks[insert_pos].start = start;
    alloc->freed_blocks[insert_pos].count = count;
    alloc->freed_block_count++;

    // Coalesce with next block (if adjacent)
    if (insert_pos + 1 < alloc->freed_block_count) {
        qubit_block_t *cur = &alloc->freed_blocks[insert_pos];
        qubit_block_t *next = &alloc->freed_blocks[insert_pos + 1];
        if (cur->start + cur->count == next->start) {
            // Merge next into current
            cur->count += next->count;
            // Remove next block
            alloc->freed_block_count--;
            if (insert_pos + 1 < alloc->freed_block_count) {
                memmove(&alloc->freed_blocks[insert_pos + 1], &alloc->freed_blocks[insert_pos + 2],
                        (alloc->freed_block_count - insert_pos - 1) * sizeof(qubit_block_t));
            }
        }
    }

    // Coalesce with previous block (if adjacent)
    if (insert_pos > 0) {
        qubit_block_t *prev = &alloc->freed_blocks[insert_pos - 1];
        qubit_block_t *cur = &alloc->freed_blocks[insert_pos];
        if (prev->start + prev->count == cur->start) {
            // Merge current into previous
            prev->count += cur->count;
            // Remove current block
            alloc->freed_block_count--;
            if (insert_pos < alloc->freed_block_count) {
                memmove(&alloc->freed_blocks[insert_pos], &alloc->freed_blocks[insert_pos + 1],
                        (alloc->freed_block_count - insert_pos) * sizeof(qubit_block_t));
            }
        }
    }

#ifdef DEBUG_OWNERSHIP
    // Clear ownership tags
    for (num_t i = 0; i < count; i++) {
        qubit_t q = start + i;
        if (q < alloc->owner_capacity && alloc->owner_tags[q] != NULL) {
            free(alloc->owner_tags[q]);
            alloc->owner_tags[q] = NULL;
        }
    }
#endif

    return 0;
}

allocator_stats_t allocator_get_stats(qubit_allocator_t *alloc) {
    allocator_stats_t empty_stats = {0};
    if (alloc == NULL) {
        return empty_stats;
    }
    return alloc->stats;
}

void allocator_reset_stats(qubit_allocator_t *alloc) {
    if (alloc == NULL) {
        return;
    }
    memset(&alloc->stats, 0, sizeof(allocator_stats_t));
}

bool allocator_is_allocated(qubit_allocator_t *alloc, qubit_t qubit) {
    if (alloc == NULL) {
        return false;
    }

    // Qubit must have been allocated at some point
    if (qubit >= alloc->next_qubit) {
        return false;
    }

    // Check if qubit is in any freed block
    for (num_t i = 0; i < alloc->freed_block_count; i++) {
        qubit_t block_start = alloc->freed_blocks[i].start;
        num_t block_count = alloc->freed_blocks[i].count;
        if (qubit >= block_start && qubit < block_start + block_count) {
            return false; // Qubit is in a freed block
        }
    }

    return true; // Qubit is allocated and not freed
}

qubit_allocator_t *circuit_get_allocator(struct circuit_s *circ) {
    if (circ == NULL) {
        return NULL;
    }
    // Access allocator field via cast to circuit_t
    circuit_t *circuit = (circuit_t *)circ;
    return circuit->allocator;
}

#ifdef DEBUG_OWNERSHIP
void allocator_set_owner(qubit_allocator_t *alloc, qubit_t qubit, const char *tag) {
    if (alloc == NULL || qubit >= alloc->owner_capacity || tag == NULL) {
        return;
    }

    // Free existing tag if present
    if (alloc->owner_tags[qubit] != NULL) {
        free(alloc->owner_tags[qubit]);
    }

    // Allocate and copy new tag
    alloc->owner_tags[qubit] = malloc(strlen(tag) + 1);
    if (alloc->owner_tags[qubit] != NULL) {
        strcpy(alloc->owner_tags[qubit], tag);
    }
}

const char *allocator_get_owner(qubit_allocator_t *alloc, qubit_t qubit) {
    if (alloc == NULL || qubit >= alloc->owner_capacity) {
        return NULL;
    }
    return alloc->owner_tags[qubit];
}
#endif
