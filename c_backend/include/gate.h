//
// gate.h - Gate creation and manipulation functions
// Dependencies: types.h
//

#ifndef CQ_BACKEND_IMPROVED_GATE_H
#define CQ_BACKEND_IMPROVED_GATE_H

#define _USE_MATH_DEFINES
#include <math.h>

// Ensure M_PI is defined on all platforms
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#include "types.h"

void print_dash(int k);
void print_empty(int k);
void print_sequence(sequence_t *seq);
void print_gate(gate_t *g);

sequence_t *QFT(sequence_t *seq, int num_qubits);
sequence_t *QFT_inverse(sequence_t *seq, int num_qubits);

void p(gate_t *g, qubit_t target, double value);
void h(gate_t *g, qubit_t target);

void cp(gate_t *g, qubit_t target, qubit_t control, double value);

void z(gate_t *g, qubit_t target);
void cz(gate_t *g, qubit_t target, qubit_t control);

void y(gate_t *g, qubit_t target);
void cy(gate_t *g, qubit_t target, qubit_t control);

void x(gate_t *g, qubit_t target);
void cx(gate_t *g, qubit_t target, qubit_t control);
void ccx(gate_t *g, qubit_t target, qubit_t control1, qubit_t control2);
void mcx(gate_t *g, qubit_t target, qubit_t *controls, num_t num_controls);

void t_gate(gate_t *g, qubit_t target);
void tdg_gate(gate_t *g, qubit_t target);

// Forward declaration for circuit_t (full definition in circuit.h)
struct circuit_s;
typedef struct circuit_s circuit_t;

/**
 * @brief Emit CCX decomposed into Clifford+T basis gates into a circuit.
 *
 * Standard exact decomposition: 2H + 4T + 3Tdg + 6CX = 15 gates, 7 T/Tdg.
 * Source: Nielsen & Chuang Fig. 4.9, Shende & Markov arXiv:0803.2316.
 *
 * @param circ   Active circuit (gates emitted via add_gate)
 * @param target Target qubit
 * @param ctrl1  First control qubit
 * @param ctrl2  Second control qubit
 */
void emit_ccx_clifford_t(circuit_t *circ, qubit_t target, qubit_t ctrl1, qubit_t ctrl2);

/**
 * @brief Emit CCX decomposed into Clifford+T basis gates into a sequence.
 *
 * Same 15-gate decomposition as emit_ccx_clifford_t, but emitted into
 * sequential layers of a sequence_t. Each gate occupies one layer.
 * Caller must ensure sequence has at least 15 layers available from *layer.
 *
 * @param seq    Sequence to emit gates into
 * @param layer  Pointer to current layer index (incremented by 15)
 * @param target Target qubit
 * @param ctrl1  First control qubit
 * @param ctrl2  Second control qubit
 */
void emit_ccx_clifford_t_seq(sequence_t *seq, int *layer, qubit_t target, qubit_t ctrl1,
                             qubit_t ctrl2);

sequence_t *cx_gate();
sequence_t *ccx_gate();

bool gates_are_inverse(gate_t *G1, gate_t *G2);
bool gates_commute(gate_t *g1, gate_t *g2);

qubit_t max_qubit(gate_t *g);
qubit_t min_qubit(gate_t *g);

#endif // CQ_BACKEND_IMPROVED_GATE_H
