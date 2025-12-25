//
// Created by Sören Wilkening on 05.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_GATE_H
#define CQ_BACKEND_IMPROVED_GATE_H

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "definition.h"

typedef enum {
    X, Y, Z, R, H, Rx, Ry, Rz, P, M
} Standardgate_t;

typedef struct {
    qubit_t Control[MAXCONTROLS];
    qubit_t *large_control;
    num_t NumControls;
    Standardgate_t Gate;
    double GateValue;
    qubit_t Target;
    num_t NumBasisGates;
    // store range of multiqubit gates
} gate_t;

#define MAXLAYERINSEQUENCE 10000
#define MAXGATESPERLAYER INTEGERSIZE

typedef struct {
    gate_t **seq;
    num_t num_layer;
    num_t used_layer;
    num_t *gates_per_layer;
} sequence_t;

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

sequence_t *cx_gate();
sequence_t *ccx_gate();

bool gates_are_inverse(gate_t *G1, gate_t *G2);
bool gates_commute(gate_t *g1, gate_t *g2);

qubit_t max_qubit(gate_t *g);
qubit_t min_qubit(gate_t *g);

#endif //CQ_BACKEND_IMPROVED_GATE_H
