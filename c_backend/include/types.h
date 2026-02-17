//
// types.h - Core types for Quantum Assembly
// Dependencies: None (this is the foundation module)
// All other modules include this header.
//

#ifndef QUANTUM_TYPES_H
#define QUANTUM_TYPES_H

#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ======================================================
// Size Constants
// ======================================================
#define INTEGERSIZE 8

#define QBITSIZE 1
#define QBYTESIZE 8
#define QHWORDSIZE 16
#define QWORDSIZE 32
#define QDWORDSIZE 64

// ======================================================
// Control and Decomposition Constants
// ======================================================
#define MAXCONTROLS 2

#define INVERTED 1
#define NOTINVERTED 0

#define DECOMPOSETOFFOLI 1
#define DONTDECOMPOSETOFFOLI 0

// ======================================================
// Memory and Type Constants
// ======================================================
#define POINTER 1
#define VALUE 0

#define Qu 0
#define Cl 1

// ======================================================
// Sequence and Layer Constants
// ======================================================
#define MAXLAYERINSEQUENCE 10000
#define MAXGATESPERLAYER INTEGERSIZE

// ======================================================
// Type Definitions
// ======================================================
typedef char decompose_toffoli_t;
typedef unsigned int qubit_t;
typedef size_t layer_t;
typedef unsigned int num_t;

// ======================================================
// Gate Types
// ======================================================
typedef enum { X, Y, Z, R, H, Rx, Ry, Rz, P, M, T_GATE, TDG_GATE } Standardgate_t;

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

typedef struct {
    gate_t **seq;
    num_t num_layer;
    num_t used_layer;
    num_t *gates_per_layer;
} sequence_t;

// ======================================================
// Arithmetic Mode (Phase 66: Toffoli arithmetic support)
// ======================================================
typedef enum { ARITH_QFT = 0, ARITH_TOFFOLI = 1 } arithmetic_mode_t;

#endif // QUANTUM_TYPES_H
