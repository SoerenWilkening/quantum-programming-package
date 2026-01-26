//
// Created by Sören Wilkening on 26.10.24.
//
#include "QPU.h"
#include "qubit_allocator.h"
#include <stdint.h>

quantum_int_t *QBOOL(circuit_t *circ) {
    // OWNERSHIP: Caller owns returned quantum_int_t*, must call free_element() when done
    // Qubits are borrowed from circuit's allocator
    if (circ == NULL || circ->allocator == NULL) {
        return NULL;
    }
    quantum_int_t *integer = malloc(sizeof(quantum_int_t));
    if (integer == NULL) {
        return NULL;
    }

    // Allocate 1 qubit through circuit's allocator (is_ancilla=true for QBOOL)
    qubit_t start = allocator_alloc(circ->allocator, 1, true);
    if (start == (qubit_t)-1) {
        free(integer);
        return NULL; // Allocation failed (hit limit)
    }

    integer->MSB = INTEGERSIZE - 1;
    integer->q_address[INTEGERSIZE - 1] = start;

#ifdef DEBUG_OWNERSHIP
    // Track ownership for debugging
    static int qbool_counter = 0;
    char tag[32];
    snprintf(tag, sizeof(tag), "qbool_%d", ++qbool_counter);
    allocator_set_owner(circ->allocator, start, tag);
#endif

    // Keep backward compat tracking (remove in later phase)
    // IMPORTANT: Match existing pattern - increment both by 1 for QBOOL
    circ->ancilla += 1;
    circ->used_qubit_indices += 1;

    return integer;
}

quantum_int_t *QINT(circuit_t *circ) {
    // OWNERSHIP: Caller owns returned quantum_int_t*, must call free_element() when done
    // Qubits are borrowed from circuit's allocator
    if (circ == NULL || circ->allocator == NULL) {
        return NULL;
    }
    quantum_int_t *integer = malloc(sizeof(quantum_int_t));
    if (integer == NULL) {
        return NULL;
    }

    // Allocate INTEGERSIZE qubits through circuit's allocator (is_ancilla=true for QINT ancillas)
    qubit_t start = allocator_alloc(circ->allocator, INTEGERSIZE, true);
    if (start == (qubit_t)-1) {
        free(integer);
        return NULL; // Allocation failed (hit limit)
    }

    integer->MSB = 0;
    for (int i = 0; i < INTEGERSIZE; ++i) {
        integer->q_address[i] = start + i;
    }

#ifdef DEBUG_OWNERSHIP
    static int qint_counter = 0;
    char tag[32];
    snprintf(tag, sizeof(tag), "qint_%d", ++qint_counter);
    for (int i = 0; i < INTEGERSIZE; ++i) {
        allocator_set_owner(circ->allocator, start + i, tag);
    }
#endif

    // Keep backward compat tracking (remove in later phase)
    // IMPORTANT: Match existing pattern - ancilla += INTEGERSIZE, used_qubit_indices increments per
    // loop
    circ->ancilla += INTEGERSIZE;
    // Note: existing code does used_qubit_indices++ inside the loop (INTEGERSIZE times)
    // We replicate that effect here:
    circ->used_qubit_indices += INTEGERSIZE;

    return integer;
}

quantum_int_t *INT(int64_t intg) {
    quantum_int_t *integer = malloc(sizeof(quantum_int_t));
    if (integer == NULL) {
        return NULL;
    }
    //    integer->c_address = malloc(sizeof(int64_t));
    //    *integer->c_address = intg;
    return integer;
}
quantum_int_t *BOOL(bool intg) {
    quantum_int_t *integer = malloc(sizeof(quantum_int_t));
    if (integer == NULL) {
        return NULL;
    }
    //    integer->c_address = malloc(sizeof(int64_t));
    //    *integer->c_address = intg;
    return integer;
}
quantum_int_t *bit_of_int(quantum_int_t *el1, int bit) {
    quantum_int_t *b = malloc(sizeof(quantum_int_t));
    if (b == NULL) {
        return NULL;
    }
    b->MSB = INTEGERSIZE - 1;
    b->q_address[INTEGERSIZE - 1] = el1->q_address[bit];
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

    // Determine width based on MSB (QBOOL has MSB=INTEGERSIZE-1, QINT has MSB=0)
    int width = (el1->MSB == INTEGERSIZE - 1) ? 1 : INTEGERSIZE;
    qubit_t start = el1->q_address[el1->MSB];

    // Return qubits to allocator
    if (circ->allocator != NULL) {
        allocator_free(circ->allocator, start, width);
    }

    // Keep backward compat tracking (remove in later phase)
    // IMPORTANT: The EXISTING code decrements both by 1 regardless of width!
    // This appears to be a bug in the original code, but we maintain it for now
    // to avoid behavioral changes during this migration.
    // TODO(Phase 3): Fix this when removing backward compat tracking
    circ->ancilla--;
    circ->used_qubit_indices--;

    free(el1);
}

sequence_t *setting_seq() {
    int *bin = two_complement(*QPU_state->R0, INTEGERSIZE);
    if (bin == NULL) {
        return NULL;
    }
    sequence_t *seq;
    seq = malloc(sizeof(sequence_t));
    if (seq == NULL) {
        free(bin);
        return NULL;
    }
    seq->used_layer = 1;
    seq->num_layer = 1;
    seq->gates_per_layer = calloc(1, sizeof(num_t));
    if (seq->gates_per_layer == NULL) {
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq = calloc(1, sizeof(gate_t *));
    if (seq->seq == NULL) {
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    seq->seq[0] = calloc(INTEGERSIZE, sizeof(gate_t));
    if (seq->seq[0] == NULL) {
        free(seq->seq);
        free(seq->gates_per_layer);
        free(bin);
        free(seq);
        return NULL;
    }
    seq->gates_per_layer[0] = 0;
    for (int i = QPU_state->Q0->MSB; i < INTEGERSIZE; ++i) {
        if (bin[i])
            x(&seq->seq[0][seq->gates_per_layer[0]++], i);
    }

    free(bin);
    return seq;
}
