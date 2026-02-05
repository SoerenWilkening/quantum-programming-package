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

sequence_t *cx_gate();
sequence_t *ccx_gate();

bool gates_are_inverse(gate_t *G1, gate_t *G2);
bool gates_commute(gate_t *g1, gate_t *g2);

qubit_t max_qubit(gate_t *g);
qubit_t min_qubit(gate_t *g);

#endif // CQ_BACKEND_IMPROVED_GATE_H
