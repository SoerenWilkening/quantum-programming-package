//
// Created by Sören Wilkening on 26.10.24.
//
#include "QPU.h"
#include "qubit_allocator.h"
#include <stdint.h>

quantum_int_t *QINT(circuit_t *circ, int width) {
    // OWNERSHIP: Caller owns returned quantum_int_t*, must call free_element() when done
    // Qubits are borrowed from circuit's allocator
    if (circ == NULL || circ->allocator == NULL) {
        return NULL;
    }

    // Validate width: must be 1-64 bits
    if (width < 1 || width > 64) {
        return NULL;
    }

    quantum_int_t *integer = malloc(sizeof(quantum_int_t));
    if (integer == NULL) {
        return NULL;
    }

    // Allocate 'width' qubits through circuit's allocator (is_ancilla=true)
    qubit_t start = allocator_alloc(circ->allocator, width, true);
    if (start == (qubit_t)-1) {
        free(integer);
        return NULL; // Allocation failed (hit limit)
    }

    // Store width explicitly in struct
    integer->width = (unsigned char)width;

    // Right-align in q_address array: indices [64-width] through [63]
    integer->MSB = 64 - width; // Points to first used element
    for (int i = 0; i < width; ++i) {
        integer->q_address[64 - width + i] = start + i;
    }

#ifdef DEBUG_OWNERSHIP
    static int qint_counter = 0;
    char tag[32];
    snprintf(tag, sizeof(tag), "qint_%d_w%d", ++qint_counter, width);
    for (int i = 0; i < width; ++i) {
        allocator_set_owner(circ->allocator, start + i, tag);
    }
#endif

    // Keep backward compat tracking (remove in later phase)
    circ->ancilla += width;
    circ->used_qubit_indices += width;

    return integer;
}

quantum_int_t *QBOOL(circuit_t *circ) {
    // QBOOL is simply a 1-bit quantum integer
    return QINT(circ, 1);
}

quantum_int_t *INT(int64_t intg) {
    // Classical integer (no qubits allocated)
    (void)intg; // Unused for now (classical value handling TBD)
    quantum_int_t *integer = malloc(sizeof(quantum_int_t));
    if (integer == NULL) {
        return NULL;
    }
    integer->width = 64; // Classical integers default to 64-bit
    integer->MSB = 0;    // For consistency with 64-bit layout
    return integer;
}

quantum_int_t *BOOL(bool intg) {
    // Classical boolean (no qubits allocated)
    (void)intg; // Unused for now (classical value handling TBD)
    quantum_int_t *integer = malloc(sizeof(quantum_int_t));
    if (integer == NULL) {
        return NULL;
    }
    integer->width = 1; // Classical bools are 1-bit
    integer->MSB = 63;  // Last element in right-aligned array
    return integer;
}

quantum_int_t *bit_of_int(quantum_int_t *el1, int bit) {
    // Create a 1-bit reference to a specific bit of an integer
    // bit: bit index within the original integer (0 = LSB)
    if (el1 == NULL) {
        return NULL;
    }
    quantum_int_t *b = malloc(sizeof(quantum_int_t));
    if (b == NULL) {
        return NULL;
    }
    b->width = 1;
    b->MSB = 63; // Last element in right-aligned array (for 1-bit)
    // Access the bit from the source integer's right-aligned array
    // Source bit 0 is at index [64 - el1->width], source bit (width-1) is at [63]
    b->q_address[63] = el1->q_address[64 - el1->width + bit];
    return b;
}

// Function to compute n-bit two's complement bit representation of x
int *two_complement(int64_t x, int n) {
    // Print the n-bit two's complement bit representation
    uint64_t mask = 1ULL << (n - 1); // Start from the highest bit
    int *bin = calloc(n, sizeof(int));
    if (bin == NULL) {
        return NULL;
    }

    for (int i = 0; i < n; ++i) {
        // Check each bit using mask and print '1' or '0'
        bin[i] = (x & mask) ? 1 : 0;
        mask >>= 1; // Shift the mask right
    }
    return bin;
}

void free_element(circuit_t *circ, quantum_int_t *el1) {
    // OWNERSHIP: Frees the quantum_int_t, returns qubits to circuit's allocator
    if (circ == NULL || el1 == NULL) {
        return;
    }

    // Read width from struct (stored explicitly since Phase 5)
    int width = el1->width;
    // Calculate start from the first used element in right-aligned array
    qubit_t start = el1->q_address[64 - width];

    // Return qubits to allocator
    if (circ->allocator != NULL) {
        allocator_free(circ->allocator, start, width);
    }

    // Keep backward compat tracking (remove in later phase)
    // IMPORTANT: The EXISTING code decrements both by 1 regardless of width!
    // This appears to be a bug in the original code, but we maintain it for now
    // to avoid behavioral changes during this migration.
    // TODO(Phase 5 follow-up): Fix this when removing backward compat tracking
    circ->ancilla--;
    circ->used_qubit_indices--;

    free(el1);
}

// TODO(Phase 4): setting_seq() removed during global state cleanup
// This function used QPU_state global which was eliminated in 04-02
// Function was not called from Python bindings (verified via grep)
// If needed in future, should be refactored to accept circuit_t* parameter
