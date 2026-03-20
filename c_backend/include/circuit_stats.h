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
size_t circuit_gate_count(const circuit_t *circ);

/**
 * @brief Get circuit depth (number of layers used).
 *
 * @param circ Circuit to query
 * @return Circuit depth, or 0 if circ is NULL
 */
num_t circuit_depth(const circuit_t *circ);

/**
 * @brief Get number of qubits used in circuit.
 *
 * @param circ Circuit to query
 * @return Qubit count, or 0 if circ is NULL
 */
num_t circuit_qubit_count(const circuit_t *circ);

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
    size_t ccx_gates;   // Toffoli (CCX, exactly 2 controls)
    size_t t_gates;     // T gates (actual T_GATE count)
    size_t tdg_gates;   // Tdg gates (actual TDG_GATE count)
    size_t other_gates; // Other gate types
    size_t t_count;     // Total T-cost: t_gates + tdg_gates when decomposed, or 7 * ccx_gates as
                        // estimate when not
} gate_counts_t;

/**
 * @brief Get breakdown of gate types in circuit.
 *
 * Classifies gates by control count:
 * - 0 controls = X/Y/Z/H/P
 * - 1 control = CNOT (CX)
 * - 2 controls = CCX (Toffoli)
 * - 3+ controls = MCX (multi-controlled X)
 *
 * @param circ Circuit to query
 * @return Gate counts structure (all zeros if circ is NULL)
 */
gate_counts_t circuit_gate_counts(const circuit_t *circ);

/**
 * @brief Get breakdown of gate types in a range of circuit layers.
 *
 * Like circuit_gate_counts but only considers layers in [start_layer, end_layer).
 * Useful for computing delta gate counts after an operation.
 *
 * @param circ Circuit to query
 * @param start_layer First layer (inclusive)
 * @param end_layer Last layer (exclusive)
 * @return Gate counts structure (all zeros if circ is NULL or range is empty)
 */
gate_counts_t circuit_gate_counts_range(const circuit_t *circ, num_t start_layer, num_t end_layer);

#endif // QUANTUM_CIRCUIT_STATS_H
