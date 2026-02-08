//
// optimizer.h - Gate optimization and layer assignment
// Dependencies: types.h
//
// Handles intelligent gate placement including:
// - Layer assignment for minimal circuit depth
// - Gate merging (inverse gate cancellation)
// - Collision detection between gates
//

#ifndef QUANTUM_OPTIMIZER_H
#define QUANTUM_OPTIMIZER_H

#include "types.h"

// Forward declaration for circuit_t
struct circuit_s;
typedef struct circuit_s circuit_t;

// Add a gate to the circuit with automatic layer assignment and merging
// This is the main entry point for adding gates
void add_gate(circuit_t *circ, gate_t *g);

// Layer assignment helpers (internal, but exposed for testing)
layer_t minimum_layer(circuit_t *circ, gate_t *g, layer_t compared_layer);
layer_t smallest_layer_below_comp(circuit_t *circ, qubit_t qubit, layer_t compar);

// Gate merging (returns true if gates merged/cancelled)
int merge_gates(circuit_t *circ, gate_t *g, layer_t min_possible_layer, int gate_index);

// Get colliding gates at a layer (internal helper, caller-provided array, Phase 61)
void colliding_gates(circuit_t *circ, gate_t *g, layer_t min_possible_layer, int *gate_index,
                     gate_t **coll);

// Layer application (internal helper)
void apply_layer(circuit_t *circ, gate_t *g, layer_t min_possible_layer);
void append_gate(circuit_t *circ, gate_t *g, layer_t min_possible_layer);

#endif // QUANTUM_OPTIMIZER_H
