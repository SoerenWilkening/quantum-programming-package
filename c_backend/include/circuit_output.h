//
// circuit_output.h - Circuit visualization and export
// Dependencies: types.h
//
// Provides functions for:
// - Text-based circuit visualization
// - OpenQASM 3.0 export
//

#ifndef QUANTUM_CIRCUIT_OUTPUT_H
#define QUANTUM_CIRCUIT_OUTPUT_H

#include "types.h"

// Forward declaration
struct circuit_s;
typedef struct circuit_s circuit_t;

// Print circuit to stdout in text format
// Shows gate count, layer count, qubit count, and ASCII diagram
void print_circuit(circuit_t *circ);

// Enhanced circuit visualization with horizontal layout
// Shows:
// - Qubit indices on left
// - Layer numbers on top
// - Compact gate symbols (H, X, Z, P, etc.)
// - Control connections with vertical lines (| and @)
// - Time flows left-to-right
void circuit_visualize(circuit_t *circ);

// Export circuit to OpenQASM 3.0 format
// Creates file at: {path}/circuit.qasm
void circuit_to_opanqasm(circuit_t *circ, char *path);

// Export circuit to OpenQASM 3.0 string (heap-allocated)
// Returns malloc'd string buffer containing valid OpenQASM 3.0
// Caller must free() the returned pointer
// Returns NULL on error (NULL circuit, malloc failure)
char *circuit_to_qasm_string(circuit_t *circ);

// Export circuit to OpenQASM 3.0 file (fixed version)
// Returns 0 on success, -1 on error
int circuit_to_openqasm(circuit_t *circ, const char *path);

// ======================================================
// Draw Data Extraction (Phase 45)
// ======================================================

// Structured gate data for rendering (parallel arrays)
typedef struct {
    unsigned int num_layers;
    unsigned int num_qubits; // Dense count after compaction
    unsigned int num_gates;
    unsigned int *gate_layer;    // Layer index per gate
    unsigned int *gate_target;   // Target qubit (compacted index)
    unsigned int *gate_type;     // Standardgate_t as unsigned int
    double *gate_angle;          // GateValue (P, Rx, Ry, Rz)
    unsigned int *gate_num_ctrl; // Control count per gate
    unsigned int *ctrl_qubits;   // All control qubits concatenated (compacted)
    unsigned int *ctrl_offsets;  // Offset into ctrl_qubits for each gate
    unsigned int *qubit_map;     // qubit_map[dense] = original sparse index
} draw_data_t;

// Extract structured gate data from circuit for rendering
// Returns heap-allocated draw_data_t, caller must call free_draw_data()
// Returns NULL if circ is NULL or on allocation failure
draw_data_t *circuit_to_draw_data(circuit_t *circ);

// Free draw_data_t and all its arrays (safe with NULL)
void free_draw_data(draw_data_t *data);

#endif // QUANTUM_CIRCUIT_OUTPUT_H
