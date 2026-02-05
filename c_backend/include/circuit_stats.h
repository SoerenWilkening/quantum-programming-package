/**
 * @file circuit_stats.h
 * @brief Circuit statistics and metrics.
 *
 * Provides functions to compute:
 * - Total gate count
 * - Circuit depth (number of layers)
 * - Qubit count
 * - Gate type breakdown (X, Y, Z, H, P, CNOT, CCX, other)
 *
 * All statistics are computed on-demand from circuit structure (no caching).
 *
 * Dependencies: types.h
 */

#ifndef QUANTUM_CIRCUIT_STATS_H
#define QUANTUM_CIRCUIT_STATS_H

#include "types.h"

// Forward declaration
struct circuit_s;
typedef struct circuit_s circuit_t;

/**
 * @brief Get total number of gates in circuit.
 *
 * @param circ Circuit to query
 * @return Total gate count, or 0 if circ is NULL
 */
size_t circuit_gate_count(circuit_t *circ);

/**
 * @brief Get circuit depth (number of layers used).
 *
 * @param circ Circuit to query
 * @return Circuit depth, or 0 if circ is NULL
 */
num_t circuit_depth(circuit_t *circ);

/**
 * @brief Get number of qubits used in circuit.
 *
 * @param circ Circuit to query
 * @return Qubit count, or 0 if circ is NULL
 */
num_t circuit_qubit_count(circuit_t *circ);

/**
 * @brief Gate type counts structure.
 *
 * Breakdown of gates by type for circuit analysis.
 */
typedef struct {
    size_t x_gates;     // X gates
    size_t y_gates;     // Y gates
    size_t z_gates;     // Z gates
    size_t h_gates;     // Hadamard gates
    size_t p_gates;     // Phase gates
    size_t cx_gates;    // Controlled-X (CNOT)
    size_t ccx_gates;   // Toffoli (CCX)
    size_t other_gates; // Other gate types
} gate_counts_t;

/**
 * @brief Get breakdown of gate types in circuit.
 *
 * Classifies gates by control count:
 * - 0 controls = X/Y/Z/H/P
 * - 1 control = CNOT (CX)
 * - 2+ controls = CCX
 *
 * @param circ Circuit to query
 * @return Gate counts structure (all zeros if circ is NULL)
 */
gate_counts_t circuit_gate_counts(circuit_t *circ);

#endif // QUANTUM_CIRCUIT_STATS_H
