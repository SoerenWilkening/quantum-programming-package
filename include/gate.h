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
    X, R, H, Rx, Ry, Rz, P, Z, M
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
#define MAXGATESPERLAYER 500

typedef struct {
    gate_t **seq;
    num_t num_layer;
    num_t used_layer;
    num_t *gates_per_layer;
} sequence_t;

void print_sequence(sequence_t *seq);

sequence_t *QFT(sequence_t *seq);

sequence_t *QFT_inverse(sequence_t *seq);

void p(gate_t *g, qubit_t target, double value);
void cp(gate_t *g, qubit_t target, qubit_t control, double value);

void x(gate_t *g, qubit_t target);
void cx(gate_t *g, qubit_t target, qubit_t control);
void ccx(gate_t *g, qubit_t target, qubit_t control1, qubit_t control2);

sequence_t *cx_gate();

#endif //CQ_BACKEND_IMPROVED_GATE_H
