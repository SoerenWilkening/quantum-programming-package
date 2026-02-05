/**
 * @file circuit.h
 * @brief Main API header for quantum circuit operations.
 *
 * This is the primary include for circuit functionality. It aggregates:
 * - types.h: Core type definitions (qubit_t, gate_t, sequence_t)
 * - gate.h: Gate creation and circuit building
 * - optimizer.h: Layer optimization
 * - circuit_output.h: Circuit printing and OpenQASM export
 * - qubit_allocator.h: Qubit lifecycle management
 * - circuit_stats.h: Circuit statistics
 * - circuit_optimizer.h: Post-construction optimization passes
 *
 * Usage:
 *   #include "circuit.h"
 *
 * Dependencies: types.h, gate.h, optimizer.h, circuit_output.h, circuit_stats.h,
 *               circuit_optimizer.h, qubit_allocator.h
 */

#ifndef QUANTUM_CIRCUIT_H
#define QUANTUM_CIRCUIT_H

// Core types
#include "types.h"

// Gate creation and manipulation
#include "gate.h"

// Qubit allocation
#include "qubit_allocator.h"

// Circuit structure constants
#define QUBIT_BLOCK 128
#define LAYER_BLOCK 128
#define GATES_PER_LAYER_BLOCK 32
#define QUBIT_INDEX_BLOCK 128
#define MAXQUBITS 8000

#define MAXINSTRUCTIONS 7

#define NUM_GATE_LAYERS 100
#define NUM_GATE_LAYER_QUBITS 50

/**
 * @brief Circuit structure - holds the quantum circuit being built.
 *
 * This structure contains all data needed to represent and manipulate a quantum circuit:
 * - Gate sequences organized by layers for parallel execution
 * - Qubit allocation and occupancy tracking
 * - Circuit statistics (depth, qubit count)
 * - Centralized qubit allocator for memory management
 */
typedef struct circuit_s {
    gate_t **sequence; // [layer][used_gates_per_layer]
    num_t used_layer;
    num_t allocated_layer;
    num_t *allocated_gates_per_layer; // [layer]
    num_t *used_gates_per_layer;      // [layer]

    int **gate_index_of_layer_and_qubits; // [layer][qubit]
    // -1 refers to the qubit being not occupied

    layer_t **occupied_layers_of_qubit;            // [qubits][index]
    num_t *allocated_occupation_indices_per_qubit; // [qubit]
    num_t *used_occupation_indices_per_qubit;      // [qubits]

    num_t allocated_qubits;
    num_t used_qubits;
    size_t used;
    decompose_toffoli_t toff_decomp;

    qubit_allocator_t *allocator; // Centralized qubit allocation

    num_t layer_floor; // Minimum layer for gate placement (set by Python before run_instruction)

    // Legacy fields (deprecated, kept for backward compatibility)
    qubit_t qubit_indices[MAXQUBITS];
    qubit_t used_qubit_indices;
    qubit_t *ancilla;
} circuit_t;

/**
 * @brief Quantum integer structure.
 *
 * Represents a quantum register with variable bit width (1-64 bits).
 * Uses right-aligned layout in q_address array.
 *
 * @note q_address uses indices [64-width] through [63] for the actual qubits.
 * @note MSB field is legacy, points to first used element (64-width) for backward compatibility.
 */
typedef struct {
    char MSB;
    unsigned char width;   // Bit width of this integer (1-64)
    qubit_t q_address[64]; // Max width for static allocation (right-aligned)
} quantum_int_t;

/**
 * @brief Initialize a new quantum circuit.
 *
 * Creates and initializes a circuit_t structure with empty gate sequences
 * and a centralized qubit allocator.
 *
 * @return Pointer to newly allocated circuit, or NULL on allocation failure.
 *
 * OWNERSHIP: Caller owns returned circuit_t*, must call free_circuit().
 */
circuit_t *init_circuit(void);

/**
 * @brief Free a quantum circuit and all associated resources.
 *
 * @param circ Circuit to free (can be NULL).
 */
void free_circuit(circuit_t *circ);

/**
 * @brief Allocate more qubits in circuit storage (internal).
 *
 * @param circ Circuit to expand.
 * @param g Gate that triggered expansion.
 */
void allocate_more_qubits(circuit_t *circ, gate_t *g);

/**
 * @brief Allocate more layers in circuit storage (internal).
 *
 * @param circ Circuit to expand.
 * @param min_possible_layer Minimum layer index required.
 */
void allocate_more_layer(circuit_t *circ, layer_t min_possible_layer);

/**
 * @brief Allocate more gate slots per layer (internal).
 *
 * @param circ Circuit to expand.
 * @param layer Layer to expand.
 * @param pos Position in layer.
 */
void allocate_more_gates_per_layer(circuit_t *circ, layer_t layer, layer_t pos);

/**
 * @brief Allocate more occupation index slots per qubit (internal).
 *
 * @param circ Circuit to expand.
 * @param loc Qubit location.
 */
void allocate_more_indices_per_qubit(circuit_t *circ, int loc);

// Import optimizer functions (add_gate is the main entry point)
#include "optimizer.h"

// Import output functions
#include "circuit_output.h"

// Import statistics functions
#include "circuit_stats.h"

// Import optimization functions
#include "circuit_optimizer.h"

#endif // QUANTUM_CIRCUIT_H
