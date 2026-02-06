//
// add_seq_5_8.c - Hardcoded QQ_add and cQQ_add sequences for 5-8 bit widths
//
// This file contains statically-defined gate sequences that match the
// dynamically-generated sequences from QQ_add() and cQQ_add() in IntegerAddition.c
//

#include "sequences.h"

// SEQ_PI as compile-time constant for static initializers
// (math.h M_PI is not a constant expression in standard C)
#ifndef SEQ_PI
#define SEQ_PI 3.14159265358979323846
#endif

// ============================================================================
// QQ_ADD WIDTH 5 (35 layers)
// Qubit layout: [0,4] = target, [5,9] = control
// ============================================================================

static const gate_t QQ_ADD_5_L0[] = {{.Gate = H,
                                      .Target = 4,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L1[] = {{.Gate = P,
                                      .Target = 4,
                                      .NumControls = 1,
                                      .Control = {3},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L2[] = {{.Gate = P,
                                      .Target = 4,
                                      .NumControls = 1,
                                      .Control = {2},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L3[] = {{.Gate = P,
                                      .Target = 4,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 8,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L4[] = {{.Gate = P,
                                      .Target = 4,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 16,
                                      .NumBasisGates = 0},
                                     {.Gate = H,
                                      .Target = 3,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L5[] = {{.Gate = P,
                                      .Target = 3,
                                      .NumControls = 1,
                                      .Control = {2},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L6[] = {{.Gate = P,
                                      .Target = 3,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L7[] = {{.Gate = P,
                                      .Target = 3,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 8,
                                      .NumBasisGates = 0},
                                     {.Gate = H,
                                      .Target = 2,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L8[] = {{.Gate = P,
                                      .Target = 2,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L9[] = {{.Gate = P,
                                      .Target = 2,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0},
                                     {.Gate = H,
                                      .Target = 1,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L10[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L11[] = {{.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L12[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L13[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L14[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L15[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L16[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L17[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L18[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L19[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L20[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L21[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L22[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L23[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L24[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L25[] = {{.Gate = H,
                                       .Target = 1,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L26[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L27[] = {{.Gate = H,
                                       .Target = 2,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L28[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L29[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L30[] = {{.Gate = H,
                                       .Target = 3,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L31[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L32[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L33[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_5_L34[] = {{.Gate = H,
                                       .Target = 4,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t *QQ_ADD_5_LAYERS[] = {
    QQ_ADD_5_L0,  QQ_ADD_5_L1,  QQ_ADD_5_L2,  QQ_ADD_5_L3,  QQ_ADD_5_L4,  QQ_ADD_5_L5,
    QQ_ADD_5_L6,  QQ_ADD_5_L7,  QQ_ADD_5_L8,  QQ_ADD_5_L9,  QQ_ADD_5_L10, QQ_ADD_5_L11,
    QQ_ADD_5_L12, QQ_ADD_5_L13, QQ_ADD_5_L14, QQ_ADD_5_L15, QQ_ADD_5_L16, QQ_ADD_5_L17,
    QQ_ADD_5_L18, QQ_ADD_5_L19, QQ_ADD_5_L20, QQ_ADD_5_L21, QQ_ADD_5_L22, QQ_ADD_5_L23,
    QQ_ADD_5_L24, QQ_ADD_5_L25, QQ_ADD_5_L26, QQ_ADD_5_L27, QQ_ADD_5_L28, QQ_ADD_5_L29,
    QQ_ADD_5_L30, QQ_ADD_5_L31, QQ_ADD_5_L32, QQ_ADD_5_L33, QQ_ADD_5_L34};
static const num_t QQ_ADD_5_GPL[] = {1, 1, 1, 1, 2, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 2, 1,
                                     1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 1, 2, 1, 1, 1, 1};

static const sequence_t HARDCODED_QQ_ADD_5 = {.seq = (gate_t **)QQ_ADD_5_LAYERS,
                                              .num_layer = 35,
                                              .used_layer = 35,
                                              .gates_per_layer = (num_t *)QQ_ADD_5_GPL};

// ============================================================================
// QQ_ADD WIDTH 6 (50 layers)
// Qubit layout: [0,5] = target, [6,11] = control
// ============================================================================

static const gate_t QQ_ADD_6_L0[] = {{.Gate = H,
                                      .Target = 5,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L1[] = {{.Gate = P,
                                      .Target = 5,
                                      .NumControls = 1,
                                      .Control = {4},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L2[] = {{.Gate = P,
                                      .Target = 5,
                                      .NumControls = 1,
                                      .Control = {3},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L3[] = {{.Gate = P,
                                      .Target = 5,
                                      .NumControls = 1,
                                      .Control = {2},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 8,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L4[] = {{.Gate = P,
                                      .Target = 5,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 16,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L5[] = {{.Gate = P,
                                      .Target = 5,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 32,
                                      .NumBasisGates = 0},
                                     {.Gate = H,
                                      .Target = 4,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L6[] = {{.Gate = P,
                                      .Target = 4,
                                      .NumControls = 1,
                                      .Control = {3},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L7[] = {{.Gate = P,
                                      .Target = 4,
                                      .NumControls = 1,
                                      .Control = {2},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L8[] = {{.Gate = P,
                                      .Target = 4,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 8,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L9[] = {{.Gate = P,
                                      .Target = 4,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 16,
                                      .NumBasisGates = 0},
                                     {.Gate = H,
                                      .Target = 3,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L10[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L11[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L12[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 2,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L13[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L14[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 1,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L15[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L16[] = {{.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L17[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L18[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L19[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L20[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L21[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L22[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L23[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L24[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L25[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L26[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L27[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L28[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L29[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L30[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L31[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L32[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L33[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {11},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L34[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L35[] = {{.Gate = H,
                                       .Target = 1,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L36[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L37[] = {{.Gate = H,
                                       .Target = 2,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L38[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L39[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L40[] = {{.Gate = H,
                                       .Target = 3,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L41[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L42[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L43[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L44[] = {{.Gate = H,
                                       .Target = 4,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L45[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L46[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L47[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L48[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_6_L49[] = {{.Gate = H,
                                       .Target = 5,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t *QQ_ADD_6_LAYERS[] = {
    QQ_ADD_6_L0,  QQ_ADD_6_L1,  QQ_ADD_6_L2,  QQ_ADD_6_L3,  QQ_ADD_6_L4,  QQ_ADD_6_L5,
    QQ_ADD_6_L6,  QQ_ADD_6_L7,  QQ_ADD_6_L8,  QQ_ADD_6_L9,  QQ_ADD_6_L10, QQ_ADD_6_L11,
    QQ_ADD_6_L12, QQ_ADD_6_L13, QQ_ADD_6_L14, QQ_ADD_6_L15, QQ_ADD_6_L16, QQ_ADD_6_L17,
    QQ_ADD_6_L18, QQ_ADD_6_L19, QQ_ADD_6_L20, QQ_ADD_6_L21, QQ_ADD_6_L22, QQ_ADD_6_L23,
    QQ_ADD_6_L24, QQ_ADD_6_L25, QQ_ADD_6_L26, QQ_ADD_6_L27, QQ_ADD_6_L28, QQ_ADD_6_L29,
    QQ_ADD_6_L30, QQ_ADD_6_L31, QQ_ADD_6_L32, QQ_ADD_6_L33, QQ_ADD_6_L34, QQ_ADD_6_L35,
    QQ_ADD_6_L36, QQ_ADD_6_L37, QQ_ADD_6_L38, QQ_ADD_6_L39, QQ_ADD_6_L40, QQ_ADD_6_L41,
    QQ_ADD_6_L42, QQ_ADD_6_L43, QQ_ADD_6_L44, QQ_ADD_6_L45, QQ_ADD_6_L46, QQ_ADD_6_L47,
    QQ_ADD_6_L48, QQ_ADD_6_L49};
static const num_t QQ_ADD_6_GPL[] = {1, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1, 2, 1, 1,
                                     1, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1, 2, 1, 2,
                                     1, 2, 1, 2, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1};

static const sequence_t HARDCODED_QQ_ADD_6 = {.seq = (gate_t **)QQ_ADD_6_LAYERS,
                                              .num_layer = 50,
                                              .used_layer = 50,
                                              .gates_per_layer = (num_t *)QQ_ADD_6_GPL};

// ============================================================================
// QQ_ADD WIDTH 7 (68 layers)
// Qubit layout: [0,6] = target, [7,13] = control
// ============================================================================

static const gate_t QQ_ADD_7_L0[] = {{.Gate = H,
                                      .Target = 6,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L1[] = {{.Gate = P,
                                      .Target = 6,
                                      .NumControls = 1,
                                      .Control = {5},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L2[] = {{.Gate = P,
                                      .Target = 6,
                                      .NumControls = 1,
                                      .Control = {4},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L3[] = {{.Gate = P,
                                      .Target = 6,
                                      .NumControls = 1,
                                      .Control = {3},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 8,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L4[] = {{.Gate = P,
                                      .Target = 6,
                                      .NumControls = 1,
                                      .Control = {2},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 16,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L5[] = {{.Gate = P,
                                      .Target = 6,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 32,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L6[] = {{.Gate = P,
                                      .Target = 6,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 64,
                                      .NumBasisGates = 0},
                                     {.Gate = H,
                                      .Target = 5,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L7[] = {{.Gate = P,
                                      .Target = 5,
                                      .NumControls = 1,
                                      .Control = {4},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L8[] = {{.Gate = P,
                                      .Target = 5,
                                      .NumControls = 1,
                                      .Control = {3},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L9[] = {{.Gate = P,
                                      .Target = 5,
                                      .NumControls = 1,
                                      .Control = {2},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 8,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L10[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L11[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 4,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L12[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L13[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L14[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L15[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 3,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L16[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L17[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L18[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 2,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L19[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L20[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 1,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L21[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L22[] = {{.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L23[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L24[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L25[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L26[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L27[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L28[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L29[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {7},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 64,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L30[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L31[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L32[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L33[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L34[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L35[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L36[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L37[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L38[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L39[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L40[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L41[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {11},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L42[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {11},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L43[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {11},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {12},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L44[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {12},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L45[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {13},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L46[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L47[] = {{.Gate = H,
                                       .Target = 1,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L48[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L49[] = {{.Gate = H,
                                       .Target = 2,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L50[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L51[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L52[] = {{.Gate = H,
                                       .Target = 3,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L53[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L54[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L55[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L56[] = {{.Gate = H,
                                       .Target = 4,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L57[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L58[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L59[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L60[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L61[] = {{.Gate = H,
                                       .Target = 5,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 64,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L62[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L63[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L64[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L65[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L66[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_7_L67[] = {{.Gate = H,
                                       .Target = 6,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t *QQ_ADD_7_LAYERS[] = {
    QQ_ADD_7_L0,  QQ_ADD_7_L1,  QQ_ADD_7_L2,  QQ_ADD_7_L3,  QQ_ADD_7_L4,  QQ_ADD_7_L5,
    QQ_ADD_7_L6,  QQ_ADD_7_L7,  QQ_ADD_7_L8,  QQ_ADD_7_L9,  QQ_ADD_7_L10, QQ_ADD_7_L11,
    QQ_ADD_7_L12, QQ_ADD_7_L13, QQ_ADD_7_L14, QQ_ADD_7_L15, QQ_ADD_7_L16, QQ_ADD_7_L17,
    QQ_ADD_7_L18, QQ_ADD_7_L19, QQ_ADD_7_L20, QQ_ADD_7_L21, QQ_ADD_7_L22, QQ_ADD_7_L23,
    QQ_ADD_7_L24, QQ_ADD_7_L25, QQ_ADD_7_L26, QQ_ADD_7_L27, QQ_ADD_7_L28, QQ_ADD_7_L29,
    QQ_ADD_7_L30, QQ_ADD_7_L31, QQ_ADD_7_L32, QQ_ADD_7_L33, QQ_ADD_7_L34, QQ_ADD_7_L35,
    QQ_ADD_7_L36, QQ_ADD_7_L37, QQ_ADD_7_L38, QQ_ADD_7_L39, QQ_ADD_7_L40, QQ_ADD_7_L41,
    QQ_ADD_7_L42, QQ_ADD_7_L43, QQ_ADD_7_L44, QQ_ADD_7_L45, QQ_ADD_7_L46, QQ_ADD_7_L47,
    QQ_ADD_7_L48, QQ_ADD_7_L49, QQ_ADD_7_L50, QQ_ADD_7_L51, QQ_ADD_7_L52, QQ_ADD_7_L53,
    QQ_ADD_7_L54, QQ_ADD_7_L55, QQ_ADD_7_L56, QQ_ADD_7_L57, QQ_ADD_7_L58, QQ_ADD_7_L59,
    QQ_ADD_7_L60, QQ_ADD_7_L61, QQ_ADD_7_L62, QQ_ADD_7_L63, QQ_ADD_7_L64, QQ_ADD_7_L65,
    QQ_ADD_7_L66, QQ_ADD_7_L67};
static const num_t QQ_ADD_7_GPL[] = {1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1,
                                     1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1,
                                     2, 1, 1, 1, 2, 1, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1,
                                     1, 2, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1};

static const sequence_t HARDCODED_QQ_ADD_7 = {.seq = (gate_t **)QQ_ADD_7_LAYERS,
                                              .num_layer = 68,
                                              .used_layer = 68,
                                              .gates_per_layer = (num_t *)QQ_ADD_7_GPL};

// ============================================================================
// QQ_ADD WIDTH 8 (89 layers)
// Qubit layout: [0,7] = target, [8,15] = control
// ============================================================================

static const gate_t QQ_ADD_8_L0[] = {{.Gate = H,
                                      .Target = 7,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L1[] = {{.Gate = P,
                                      .Target = 7,
                                      .NumControls = 1,
                                      .Control = {6},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L2[] = {{.Gate = P,
                                      .Target = 7,
                                      .NumControls = 1,
                                      .Control = {5},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L3[] = {{.Gate = P,
                                      .Target = 7,
                                      .NumControls = 1,
                                      .Control = {4},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 8,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L4[] = {{.Gate = P,
                                      .Target = 7,
                                      .NumControls = 1,
                                      .Control = {3},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 16,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L5[] = {{.Gate = P,
                                      .Target = 7,
                                      .NumControls = 1,
                                      .Control = {2},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 32,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L6[] = {{.Gate = P,
                                      .Target = 7,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 64,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L7[] = {{.Gate = P,
                                      .Target = 7,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 128,
                                      .NumBasisGates = 0},
                                     {.Gate = H,
                                      .Target = 6,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L8[] = {{.Gate = P,
                                      .Target = 6,
                                      .NumControls = 1,
                                      .Control = {5},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L9[] = {{.Gate = P,
                                      .Target = 6,
                                      .NumControls = 1,
                                      .Control = {4},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L10[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L11[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L12[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L13[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 64,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 5,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L14[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L15[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L16[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L17[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L18[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 4,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L19[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L20[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L21[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L22[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 3,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L23[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L24[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L25[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 2,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L26[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L27[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 1,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L28[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L29[] = {{.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L30[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L31[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L32[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L33[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L34[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L35[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L36[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 64,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L37[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 128,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L38[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L39[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L40[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L41[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L42[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L43[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {9},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 64,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L44[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L45[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L46[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L47[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L48[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {10},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {11},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L49[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {11},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L50[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {11},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L51[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {11},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L52[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {11},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {12},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L53[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {12},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L54[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {12},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L55[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {12},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {13},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L56[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {13},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L57[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {13},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {14},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L58[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {14},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L59[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {15},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L60[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L61[] = {{.Gate = H,
                                       .Target = 1,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L62[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L63[] = {{.Gate = H,
                                       .Target = 2,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L64[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L65[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L66[] = {{.Gate = H,
                                       .Target = 3,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L67[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L68[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L69[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L70[] = {{.Gate = H,
                                       .Target = 4,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L71[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L72[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L73[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L74[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L75[] = {{.Gate = H,
                                       .Target = 5,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 64,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L76[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L77[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L78[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L79[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L80[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L81[] = {{.Gate = H,
                                       .Target = 6,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 128,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L82[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 64,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L83[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L84[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L85[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L86[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L87[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_8_L88[] = {{.Gate = H,
                                       .Target = 7,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t *QQ_ADD_8_LAYERS[] = {
    QQ_ADD_8_L0,  QQ_ADD_8_L1,  QQ_ADD_8_L2,  QQ_ADD_8_L3,  QQ_ADD_8_L4,  QQ_ADD_8_L5,
    QQ_ADD_8_L6,  QQ_ADD_8_L7,  QQ_ADD_8_L8,  QQ_ADD_8_L9,  QQ_ADD_8_L10, QQ_ADD_8_L11,
    QQ_ADD_8_L12, QQ_ADD_8_L13, QQ_ADD_8_L14, QQ_ADD_8_L15, QQ_ADD_8_L16, QQ_ADD_8_L17,
    QQ_ADD_8_L18, QQ_ADD_8_L19, QQ_ADD_8_L20, QQ_ADD_8_L21, QQ_ADD_8_L22, QQ_ADD_8_L23,
    QQ_ADD_8_L24, QQ_ADD_8_L25, QQ_ADD_8_L26, QQ_ADD_8_L27, QQ_ADD_8_L28, QQ_ADD_8_L29,
    QQ_ADD_8_L30, QQ_ADD_8_L31, QQ_ADD_8_L32, QQ_ADD_8_L33, QQ_ADD_8_L34, QQ_ADD_8_L35,
    QQ_ADD_8_L36, QQ_ADD_8_L37, QQ_ADD_8_L38, QQ_ADD_8_L39, QQ_ADD_8_L40, QQ_ADD_8_L41,
    QQ_ADD_8_L42, QQ_ADD_8_L43, QQ_ADD_8_L44, QQ_ADD_8_L45, QQ_ADD_8_L46, QQ_ADD_8_L47,
    QQ_ADD_8_L48, QQ_ADD_8_L49, QQ_ADD_8_L50, QQ_ADD_8_L51, QQ_ADD_8_L52, QQ_ADD_8_L53,
    QQ_ADD_8_L54, QQ_ADD_8_L55, QQ_ADD_8_L56, QQ_ADD_8_L57, QQ_ADD_8_L58, QQ_ADD_8_L59,
    QQ_ADD_8_L60, QQ_ADD_8_L61, QQ_ADD_8_L62, QQ_ADD_8_L63, QQ_ADD_8_L64, QQ_ADD_8_L65,
    QQ_ADD_8_L66, QQ_ADD_8_L67, QQ_ADD_8_L68, QQ_ADD_8_L69, QQ_ADD_8_L70, QQ_ADD_8_L71,
    QQ_ADD_8_L72, QQ_ADD_8_L73, QQ_ADD_8_L74, QQ_ADD_8_L75, QQ_ADD_8_L76, QQ_ADD_8_L77,
    QQ_ADD_8_L78, QQ_ADD_8_L79, QQ_ADD_8_L80, QQ_ADD_8_L81, QQ_ADD_8_L82, QQ_ADD_8_L83,
    QQ_ADD_8_L84, QQ_ADD_8_L85, QQ_ADD_8_L86, QQ_ADD_8_L87, QQ_ADD_8_L88};
static const num_t QQ_ADD_8_GPL[] = {
    1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1, 2, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1, 2, 1, 2,
    1, 2, 1, 2, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1};

static const sequence_t HARDCODED_QQ_ADD_8 = {.seq = (gate_t **)QQ_ADD_8_LAYERS,
                                              .num_layer = 89,
                                              .used_layer = 89,
                                              .gates_per_layer = (num_t *)QQ_ADD_8_GPL};

// ============================================================================
// QQ_ADD DISPATCH HELPER FOR 5-8
// ============================================================================

const sequence_t *get_hardcoded_QQ_add_5_8(int bits) {
    switch (bits) {
    case 5:
        return &HARDCODED_QQ_ADD_5;
    case 6:
        return &HARDCODED_QQ_ADD_6;
    case 7:
        return &HARDCODED_QQ_ADD_7;
    case 8:
        return &HARDCODED_QQ_ADD_8;
    default:
        return NULL;
    }
}

// ============================================================================
// cQQ_ADD WIDTH 5 (57 layers)
// Qubit layout: [0,4] = target, [5,9] = b, [10] = control
// ============================================================================

static const gate_t cQQ_ADD_5_L0[] = {{.Gate = H,
                                       .Target = 4,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L1[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L2[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L3[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L4[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 3,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L5[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L6[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L7[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 2,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L8[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L9[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 1,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L10[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L11[] = {{.Gate = H,
                                        .Target = 0,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L12[] = {{.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L13[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 3 * SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L14[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 7 * SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L15[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 15 * SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L16[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 31 * SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L17[] = {{.Gate = X,
                                        .Target = 9,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L18[] = {{.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L19[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L20[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L21[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L22[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L23[] = {{.Gate = X,
                                        .Target = 9,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L24[] = {{.Gate = X,
                                        .Target = 8,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L25[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L26[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L27[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L28[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L29[] = {{.Gate = X,
                                        .Target = 8,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L30[] = {{.Gate = X,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L31[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L32[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L33[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L34[] = {{.Gate = X,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L35[] = {{.Gate = X,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L36[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L37[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L38[] = {{.Gate = X,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L39[] = {{.Gate = X,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L40[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L41[] = {{.Gate = X,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L42[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L43[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L44[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L45[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 0,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L46[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L47[] = {{.Gate = H,
                                        .Target = 1,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L48[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L49[] = {{.Gate = H,
                                        .Target = 2,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L50[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L51[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L52[] = {{.Gate = H,
                                        .Target = 3,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L53[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L54[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L55[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_5_L56[] = {{.Gate = H,
                                        .Target = 4,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t *cQQ_ADD_5_LAYERS[] = {
    cQQ_ADD_5_L0,  cQQ_ADD_5_L1,  cQQ_ADD_5_L2,  cQQ_ADD_5_L3,  cQQ_ADD_5_L4,  cQQ_ADD_5_L5,
    cQQ_ADD_5_L6,  cQQ_ADD_5_L7,  cQQ_ADD_5_L8,  cQQ_ADD_5_L9,  cQQ_ADD_5_L10, cQQ_ADD_5_L11,
    cQQ_ADD_5_L12, cQQ_ADD_5_L13, cQQ_ADD_5_L14, cQQ_ADD_5_L15, cQQ_ADD_5_L16, cQQ_ADD_5_L17,
    cQQ_ADD_5_L18, cQQ_ADD_5_L19, cQQ_ADD_5_L20, cQQ_ADD_5_L21, cQQ_ADD_5_L22, cQQ_ADD_5_L23,
    cQQ_ADD_5_L24, cQQ_ADD_5_L25, cQQ_ADD_5_L26, cQQ_ADD_5_L27, cQQ_ADD_5_L28, cQQ_ADD_5_L29,
    cQQ_ADD_5_L30, cQQ_ADD_5_L31, cQQ_ADD_5_L32, cQQ_ADD_5_L33, cQQ_ADD_5_L34, cQQ_ADD_5_L35,
    cQQ_ADD_5_L36, cQQ_ADD_5_L37, cQQ_ADD_5_L38, cQQ_ADD_5_L39, cQQ_ADD_5_L40, cQQ_ADD_5_L41,
    cQQ_ADD_5_L42, cQQ_ADD_5_L43, cQQ_ADD_5_L44, cQQ_ADD_5_L45, cQQ_ADD_5_L46, cQQ_ADD_5_L47,
    cQQ_ADD_5_L48, cQQ_ADD_5_L49, cQQ_ADD_5_L50, cQQ_ADD_5_L51, cQQ_ADD_5_L52, cQQ_ADD_5_L53,
    cQQ_ADD_5_L54, cQQ_ADD_5_L55, cQQ_ADD_5_L56};
static const num_t cQQ_ADD_5_GPL[] = {1, 1, 1, 1, 2, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                      1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                      1, 1, 1, 6, 4, 3, 2, 2, 1, 2, 1, 2, 1, 1, 2, 1, 1, 1, 1};

static const sequence_t HARDCODED_cQQ_ADD_5 = {.seq = (gate_t **)cQQ_ADD_5_LAYERS,
                                               .num_layer = 57,
                                               .used_layer = 57,
                                               .gates_per_layer = (num_t *)cQQ_ADD_5_GPL};

// ============================================================================
// cQQ_ADD WIDTH 6 (77 layers)
// Qubit layout: [0,5] = target, [6,11] = b, [12] = control
// ============================================================================

static const gate_t cQQ_ADD_6_L0[] = {{.Gate = H,
                                       .Target = 5,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L1[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L2[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L3[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L4[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L5[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 4,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L6[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L7[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L8[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L9[] = {{.Gate = P,
                                       .Target = 4,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 3,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L10[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L11[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L12[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 2,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L13[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L14[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 1,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L15[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L16[] = {{.Gate = H,
                                        .Target = 0,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L17[] = {{.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L18[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 3 * SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L19[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 7 * SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L20[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 15 * SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L21[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 31 * SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L22[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 63 * SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L23[] = {{.Gate = X,
                                        .Target = 11,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L24[] = {{.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L25[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L26[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L27[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L28[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L29[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L30[] = {{.Gate = X,
                                        .Target = 11,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L31[] = {{.Gate = X,
                                        .Target = 10,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L32[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L33[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L34[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L35[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L36[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L37[] = {{.Gate = X,
                                        .Target = 10,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L38[] = {{.Gate = X,
                                        .Target = 9,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L39[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L40[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L41[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L42[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L43[] = {{.Gate = X,
                                        .Target = 9,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L44[] = {{.Gate = X,
                                        .Target = 8,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L45[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L46[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L47[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L48[] = {{.Gate = X,
                                        .Target = 8,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L49[] = {{.Gate = X,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L50[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L51[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L52[] = {{.Gate = X,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L53[] = {{.Gate = X,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L54[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L55[] = {{.Gate = X,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L56[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L57[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L58[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L59[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L60[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 0,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L61[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L62[] = {{.Gate = H,
                                        .Target = 1,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L63[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L64[] = {{.Gate = H,
                                        .Target = 2,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L65[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L66[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L67[] = {{.Gate = H,
                                        .Target = 3,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L68[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L69[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L70[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L71[] = {{.Gate = H,
                                        .Target = 4,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L72[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L73[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L74[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L75[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {4},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_6_L76[] = {{.Gate = H,
                                        .Target = 5,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t *cQQ_ADD_6_LAYERS[] = {
    cQQ_ADD_6_L0,  cQQ_ADD_6_L1,  cQQ_ADD_6_L2,  cQQ_ADD_6_L3,  cQQ_ADD_6_L4,  cQQ_ADD_6_L5,
    cQQ_ADD_6_L6,  cQQ_ADD_6_L7,  cQQ_ADD_6_L8,  cQQ_ADD_6_L9,  cQQ_ADD_6_L10, cQQ_ADD_6_L11,
    cQQ_ADD_6_L12, cQQ_ADD_6_L13, cQQ_ADD_6_L14, cQQ_ADD_6_L15, cQQ_ADD_6_L16, cQQ_ADD_6_L17,
    cQQ_ADD_6_L18, cQQ_ADD_6_L19, cQQ_ADD_6_L20, cQQ_ADD_6_L21, cQQ_ADD_6_L22, cQQ_ADD_6_L23,
    cQQ_ADD_6_L24, cQQ_ADD_6_L25, cQQ_ADD_6_L26, cQQ_ADD_6_L27, cQQ_ADD_6_L28, cQQ_ADD_6_L29,
    cQQ_ADD_6_L30, cQQ_ADD_6_L31, cQQ_ADD_6_L32, cQQ_ADD_6_L33, cQQ_ADD_6_L34, cQQ_ADD_6_L35,
    cQQ_ADD_6_L36, cQQ_ADD_6_L37, cQQ_ADD_6_L38, cQQ_ADD_6_L39, cQQ_ADD_6_L40, cQQ_ADD_6_L41,
    cQQ_ADD_6_L42, cQQ_ADD_6_L43, cQQ_ADD_6_L44, cQQ_ADD_6_L45, cQQ_ADD_6_L46, cQQ_ADD_6_L47,
    cQQ_ADD_6_L48, cQQ_ADD_6_L49, cQQ_ADD_6_L50, cQQ_ADD_6_L51, cQQ_ADD_6_L52, cQQ_ADD_6_L53,
    cQQ_ADD_6_L54, cQQ_ADD_6_L55, cQQ_ADD_6_L56, cQQ_ADD_6_L57, cQQ_ADD_6_L58, cQQ_ADD_6_L59,
    cQQ_ADD_6_L60, cQQ_ADD_6_L61, cQQ_ADD_6_L62, cQQ_ADD_6_L63, cQQ_ADD_6_L64, cQQ_ADD_6_L65,
    cQQ_ADD_6_L66, cQQ_ADD_6_L67, cQQ_ADD_6_L68, cQQ_ADD_6_L69, cQQ_ADD_6_L70, cQQ_ADD_6_L71,
    cQQ_ADD_6_L72, cQQ_ADD_6_L73, cQQ_ADD_6_L74, cQQ_ADD_6_L75, cQQ_ADD_6_L76};
static const num_t cQQ_ADD_6_GPL[] = {1, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1,
                                      1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                      1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 7, 5, 4, 3, 2,
                                      2, 1, 2, 1, 2, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1};

static const sequence_t HARDCODED_cQQ_ADD_6 = {.seq = (gate_t **)cQQ_ADD_6_LAYERS,
                                               .num_layer = 77,
                                               .used_layer = 77,
                                               .gates_per_layer = (num_t *)cQQ_ADD_6_GPL};

// ============================================================================
// cQQ_ADD WIDTH 7 (100 layers)
// Qubit layout: [0,6] = target, [7,13] = b, [14] = control
// ============================================================================

static const gate_t cQQ_ADD_7_L0[] = {{.Gate = H,
                                       .Target = 6,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L1[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L2[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L3[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L4[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L5[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L6[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 64,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 5,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L7[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L8[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L9[] = {{.Gate = P,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L10[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L11[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 4,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L12[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L13[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L14[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L15[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 3,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L16[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L17[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L18[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 2,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L19[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L20[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 1,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L21[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L22[] = {{.Gate = H,
                                        .Target = 0,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L23[] = {{.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L24[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 3 * SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L25[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 7 * SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L26[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 15 * SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L27[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 31 * SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L28[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 63 * SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L29[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 127 * SEQ_PI / 128,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L30[] = {{.Gate = X,
                                        .Target = 13,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L31[] = {{.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L32[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L33[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L34[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L35[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L36[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L37[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 128,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L38[] = {{.Gate = X,
                                        .Target = 13,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L39[] = {{.Gate = X,
                                        .Target = 12,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L40[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L41[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L42[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L43[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L44[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L45[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L46[] = {{.Gate = X,
                                        .Target = 12,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L47[] = {{.Gate = X,
                                        .Target = 11,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L48[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L49[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L50[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L51[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L52[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L53[] = {{.Gate = X,
                                        .Target = 11,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L54[] = {{.Gate = X,
                                        .Target = 10,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L55[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L56[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L57[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L58[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L59[] = {{.Gate = X,
                                        .Target = 10,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L60[] = {{.Gate = X,
                                        .Target = 9,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L61[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L62[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L63[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L64[] = {{.Gate = X,
                                        .Target = 9,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L65[] = {{.Gate = X,
                                        .Target = 8,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L66[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L67[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L68[] = {{.Gate = X,
                                        .Target = 8,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L69[] = {{.Gate = X,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L70[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L71[] = {{.Gate = X,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 64,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 128,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L72[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L73[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L74[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L75[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L76[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L77[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 0,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L78[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L79[] = {{.Gate = H,
                                        .Target = 1,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L80[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L81[] = {{.Gate = H,
                                        .Target = 2,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L82[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L83[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L84[] = {{.Gate = H,
                                        .Target = 3,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L85[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L86[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L87[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L88[] = {{.Gate = H,
                                        .Target = 4,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L89[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L90[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L91[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L92[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {4},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L93[] = {{.Gate = H,
                                        .Target = 5,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L94[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L95[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L96[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L97[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {4},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L98[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_7_L99[] = {{.Gate = H,
                                        .Target = 6,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t *cQQ_ADD_7_LAYERS[] = {
    cQQ_ADD_7_L0,  cQQ_ADD_7_L1,  cQQ_ADD_7_L2,  cQQ_ADD_7_L3,  cQQ_ADD_7_L4,  cQQ_ADD_7_L5,
    cQQ_ADD_7_L6,  cQQ_ADD_7_L7,  cQQ_ADD_7_L8,  cQQ_ADD_7_L9,  cQQ_ADD_7_L10, cQQ_ADD_7_L11,
    cQQ_ADD_7_L12, cQQ_ADD_7_L13, cQQ_ADD_7_L14, cQQ_ADD_7_L15, cQQ_ADD_7_L16, cQQ_ADD_7_L17,
    cQQ_ADD_7_L18, cQQ_ADD_7_L19, cQQ_ADD_7_L20, cQQ_ADD_7_L21, cQQ_ADD_7_L22, cQQ_ADD_7_L23,
    cQQ_ADD_7_L24, cQQ_ADD_7_L25, cQQ_ADD_7_L26, cQQ_ADD_7_L27, cQQ_ADD_7_L28, cQQ_ADD_7_L29,
    cQQ_ADD_7_L30, cQQ_ADD_7_L31, cQQ_ADD_7_L32, cQQ_ADD_7_L33, cQQ_ADD_7_L34, cQQ_ADD_7_L35,
    cQQ_ADD_7_L36, cQQ_ADD_7_L37, cQQ_ADD_7_L38, cQQ_ADD_7_L39, cQQ_ADD_7_L40, cQQ_ADD_7_L41,
    cQQ_ADD_7_L42, cQQ_ADD_7_L43, cQQ_ADD_7_L44, cQQ_ADD_7_L45, cQQ_ADD_7_L46, cQQ_ADD_7_L47,
    cQQ_ADD_7_L48, cQQ_ADD_7_L49, cQQ_ADD_7_L50, cQQ_ADD_7_L51, cQQ_ADD_7_L52, cQQ_ADD_7_L53,
    cQQ_ADD_7_L54, cQQ_ADD_7_L55, cQQ_ADD_7_L56, cQQ_ADD_7_L57, cQQ_ADD_7_L58, cQQ_ADD_7_L59,
    cQQ_ADD_7_L60, cQQ_ADD_7_L61, cQQ_ADD_7_L62, cQQ_ADD_7_L63, cQQ_ADD_7_L64, cQQ_ADD_7_L65,
    cQQ_ADD_7_L66, cQQ_ADD_7_L67, cQQ_ADD_7_L68, cQQ_ADD_7_L69, cQQ_ADD_7_L70, cQQ_ADD_7_L71,
    cQQ_ADD_7_L72, cQQ_ADD_7_L73, cQQ_ADD_7_L74, cQQ_ADD_7_L75, cQQ_ADD_7_L76, cQQ_ADD_7_L77,
    cQQ_ADD_7_L78, cQQ_ADD_7_L79, cQQ_ADD_7_L80, cQQ_ADD_7_L81, cQQ_ADD_7_L82, cQQ_ADD_7_L83,
    cQQ_ADD_7_L84, cQQ_ADD_7_L85, cQQ_ADD_7_L86, cQQ_ADD_7_L87, cQQ_ADD_7_L88, cQQ_ADD_7_L89,
    cQQ_ADD_7_L90, cQQ_ADD_7_L91, cQQ_ADD_7_L92, cQQ_ADD_7_L93, cQQ_ADD_7_L94, cQQ_ADD_7_L95,
    cQQ_ADD_7_L96, cQQ_ADD_7_L97, cQQ_ADD_7_L98, cQQ_ADD_7_L99};
static const num_t cQQ_ADD_7_GPL[] = {1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1,
                                      2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                      1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                      1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 8, 6, 5, 4, 3, 2, 2, 1, 2,
                                      1, 2, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1};

static const sequence_t HARDCODED_cQQ_ADD_7 = {.seq = (gate_t **)cQQ_ADD_7_LAYERS,
                                               .num_layer = 100,
                                               .used_layer = 100,
                                               .gates_per_layer = (num_t *)cQQ_ADD_7_GPL};

// ============================================================================
// cQQ_ADD WIDTH 8 (126 layers)
// Qubit layout: [0,7] = target, [8,15] = b, [16] = control
// ============================================================================

static const gate_t cQQ_ADD_8_L0[] = {{.Gate = H,
                                       .Target = 7,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L1[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L2[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L3[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L4[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 16,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L5[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 32,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L6[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 64,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L7[] = {{.Gate = P,
                                       .Target = 7,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 128,
                                       .NumBasisGates = 0},
                                      {.Gate = H,
                                       .Target = 6,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L8[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L9[] = {{.Gate = P,
                                       .Target = 6,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L10[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L11[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L12[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L13[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 64,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 5,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L14[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {4},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L15[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L16[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L17[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L18[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 4,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L19[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L20[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L21[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L22[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 3,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L23[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L24[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L25[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 2,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L26[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L27[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 1,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L28[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L29[] = {{.Gate = H,
                                        .Target = 0,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L30[] = {{.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L31[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 3 * SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L32[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 7 * SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L33[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 15 * SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L34[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 31 * SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L35[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 63 * SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L36[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 127 * SEQ_PI / 128,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L37[] = {{.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 255 * SEQ_PI / 256,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L38[] = {{.Gate = X,
                                        .Target = 15,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L39[] = {{.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L40[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L41[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L42[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L43[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L44[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L45[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 128,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L46[] = {{.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 256,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L47[] = {{.Gate = X,
                                        .Target = 15,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L48[] = {{.Gate = X,
                                        .Target = 14,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L49[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L50[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L51[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L52[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L53[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L54[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L55[] = {{.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 128,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L56[] = {{.Gate = X,
                                        .Target = 14,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L57[] = {{.Gate = X,
                                        .Target = 13,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L58[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L59[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L60[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L61[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L62[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L63[] = {{.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L64[] = {{.Gate = X,
                                        .Target = 13,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L65[] = {{.Gate = X,
                                        .Target = 12,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L66[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L67[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L68[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L69[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L70[] = {{.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L71[] = {{.Gate = X,
                                        .Target = 12,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L72[] = {{.Gate = X,
                                        .Target = 11,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L73[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L74[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L75[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L76[] = {{.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L77[] = {{.Gate = X,
                                        .Target = 11,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L78[] = {{.Gate = X,
                                        .Target = 10,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L79[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L80[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L81[] = {{.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L82[] = {{.Gate = X,
                                        .Target = 10,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L83[] = {{.Gate = X,
                                        .Target = 9,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L84[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L85[] = {{.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L86[] = {{.Gate = X,
                                        .Target = 9,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L87[] = {{.Gate = X,
                                        .Target = 8,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L88[] = {{.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L89[] = {{.Gate = X,
                                        .Target = 8,
                                        .NumControls = 1,
                                        .Control = {16},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 64,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 128,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {15},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 256,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L90[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 64,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {14},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 128,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L91[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {13},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 64,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L92[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {12},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 32,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L93[] = {{.Gate = P,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {11},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L94[] = {{.Gate = P,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {10},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L95[] = {{.Gate = P,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {9},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L96[] = {{.Gate = P,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = H,
                                        .Target = 0,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L97[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L98[] = {{.Gate = H,
                                        .Target = 1,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L99[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L100[] = {{.Gate = H,
                                         .Target = 2,
                                         .NumControls = 0,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = 0,
                                         .NumBasisGates = 0},
                                        {.Gate = P,
                                         .Target = 3,
                                         .NumControls = 1,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 8,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L101[] = {{.Gate = P,
                                         .Target = 3,
                                         .NumControls = 1,
                                         .Control = {1},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 4,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L102[] = {{.Gate = P,
                                         .Target = 3,
                                         .NumControls = 1,
                                         .Control = {2},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 2,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L103[] = {{.Gate = H,
                                         .Target = 3,
                                         .NumControls = 0,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = 0,
                                         .NumBasisGates = 0},
                                        {.Gate = P,
                                         .Target = 4,
                                         .NumControls = 1,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 16,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L104[] = {{.Gate = P,
                                         .Target = 4,
                                         .NumControls = 1,
                                         .Control = {1},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 8,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L105[] = {{.Gate = P,
                                         .Target = 4,
                                         .NumControls = 1,
                                         .Control = {2},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 4,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L106[] = {{.Gate = P,
                                         .Target = 4,
                                         .NumControls = 1,
                                         .Control = {3},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 2,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L107[] = {{.Gate = H,
                                         .Target = 4,
                                         .NumControls = 0,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = 0,
                                         .NumBasisGates = 0},
                                        {.Gate = P,
                                         .Target = 5,
                                         .NumControls = 1,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 32,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L108[] = {{.Gate = P,
                                         .Target = 5,
                                         .NumControls = 1,
                                         .Control = {1},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 16,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L109[] = {{.Gate = P,
                                         .Target = 5,
                                         .NumControls = 1,
                                         .Control = {2},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 8,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L110[] = {{.Gate = P,
                                         .Target = 5,
                                         .NumControls = 1,
                                         .Control = {3},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 4,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L111[] = {{.Gate = P,
                                         .Target = 5,
                                         .NumControls = 1,
                                         .Control = {4},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 2,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L112[] = {{.Gate = H,
                                         .Target = 5,
                                         .NumControls = 0,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = 0,
                                         .NumBasisGates = 0},
                                        {.Gate = P,
                                         .Target = 6,
                                         .NumControls = 1,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 64,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L113[] = {{.Gate = P,
                                         .Target = 6,
                                         .NumControls = 1,
                                         .Control = {1},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 32,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L114[] = {{.Gate = P,
                                         .Target = 6,
                                         .NumControls = 1,
                                         .Control = {2},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 16,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L115[] = {{.Gate = P,
                                         .Target = 6,
                                         .NumControls = 1,
                                         .Control = {3},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 8,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L116[] = {{.Gate = P,
                                         .Target = 6,
                                         .NumControls = 1,
                                         .Control = {4},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 4,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L117[] = {{.Gate = P,
                                         .Target = 6,
                                         .NumControls = 1,
                                         .Control = {5},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 2,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L118[] = {{.Gate = H,
                                         .Target = 6,
                                         .NumControls = 0,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = 0,
                                         .NumBasisGates = 0},
                                        {.Gate = P,
                                         .Target = 7,
                                         .NumControls = 1,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 128,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L119[] = {{.Gate = P,
                                         .Target = 7,
                                         .NumControls = 1,
                                         .Control = {1},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 64,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L120[] = {{.Gate = P,
                                         .Target = 7,
                                         .NumControls = 1,
                                         .Control = {2},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 32,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L121[] = {{.Gate = P,
                                         .Target = 7,
                                         .NumControls = 1,
                                         .Control = {3},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 16,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L122[] = {{.Gate = P,
                                         .Target = 7,
                                         .NumControls = 1,
                                         .Control = {4},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 8,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L123[] = {{.Gate = P,
                                         .Target = 7,
                                         .NumControls = 1,
                                         .Control = {5},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 4,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L124[] = {{.Gate = P,
                                         .Target = 7,
                                         .NumControls = 1,
                                         .Control = {6},
                                         .large_control = NULL,
                                         .GateValue = -SEQ_PI / 2,
                                         .NumBasisGates = 0}};

static const gate_t cQQ_ADD_8_L125[] = {{.Gate = H,
                                         .Target = 7,
                                         .NumControls = 0,
                                         .Control = {0},
                                         .large_control = NULL,
                                         .GateValue = 0,
                                         .NumBasisGates = 0}};

static const gate_t *cQQ_ADD_8_LAYERS[] = {
    cQQ_ADD_8_L0,   cQQ_ADD_8_L1,   cQQ_ADD_8_L2,   cQQ_ADD_8_L3,   cQQ_ADD_8_L4,   cQQ_ADD_8_L5,
    cQQ_ADD_8_L6,   cQQ_ADD_8_L7,   cQQ_ADD_8_L8,   cQQ_ADD_8_L9,   cQQ_ADD_8_L10,  cQQ_ADD_8_L11,
    cQQ_ADD_8_L12,  cQQ_ADD_8_L13,  cQQ_ADD_8_L14,  cQQ_ADD_8_L15,  cQQ_ADD_8_L16,  cQQ_ADD_8_L17,
    cQQ_ADD_8_L18,  cQQ_ADD_8_L19,  cQQ_ADD_8_L20,  cQQ_ADD_8_L21,  cQQ_ADD_8_L22,  cQQ_ADD_8_L23,
    cQQ_ADD_8_L24,  cQQ_ADD_8_L25,  cQQ_ADD_8_L26,  cQQ_ADD_8_L27,  cQQ_ADD_8_L28,  cQQ_ADD_8_L29,
    cQQ_ADD_8_L30,  cQQ_ADD_8_L31,  cQQ_ADD_8_L32,  cQQ_ADD_8_L33,  cQQ_ADD_8_L34,  cQQ_ADD_8_L35,
    cQQ_ADD_8_L36,  cQQ_ADD_8_L37,  cQQ_ADD_8_L38,  cQQ_ADD_8_L39,  cQQ_ADD_8_L40,  cQQ_ADD_8_L41,
    cQQ_ADD_8_L42,  cQQ_ADD_8_L43,  cQQ_ADD_8_L44,  cQQ_ADD_8_L45,  cQQ_ADD_8_L46,  cQQ_ADD_8_L47,
    cQQ_ADD_8_L48,  cQQ_ADD_8_L49,  cQQ_ADD_8_L50,  cQQ_ADD_8_L51,  cQQ_ADD_8_L52,  cQQ_ADD_8_L53,
    cQQ_ADD_8_L54,  cQQ_ADD_8_L55,  cQQ_ADD_8_L56,  cQQ_ADD_8_L57,  cQQ_ADD_8_L58,  cQQ_ADD_8_L59,
    cQQ_ADD_8_L60,  cQQ_ADD_8_L61,  cQQ_ADD_8_L62,  cQQ_ADD_8_L63,  cQQ_ADD_8_L64,  cQQ_ADD_8_L65,
    cQQ_ADD_8_L66,  cQQ_ADD_8_L67,  cQQ_ADD_8_L68,  cQQ_ADD_8_L69,  cQQ_ADD_8_L70,  cQQ_ADD_8_L71,
    cQQ_ADD_8_L72,  cQQ_ADD_8_L73,  cQQ_ADD_8_L74,  cQQ_ADD_8_L75,  cQQ_ADD_8_L76,  cQQ_ADD_8_L77,
    cQQ_ADD_8_L78,  cQQ_ADD_8_L79,  cQQ_ADD_8_L80,  cQQ_ADD_8_L81,  cQQ_ADD_8_L82,  cQQ_ADD_8_L83,
    cQQ_ADD_8_L84,  cQQ_ADD_8_L85,  cQQ_ADD_8_L86,  cQQ_ADD_8_L87,  cQQ_ADD_8_L88,  cQQ_ADD_8_L89,
    cQQ_ADD_8_L90,  cQQ_ADD_8_L91,  cQQ_ADD_8_L92,  cQQ_ADD_8_L93,  cQQ_ADD_8_L94,  cQQ_ADD_8_L95,
    cQQ_ADD_8_L96,  cQQ_ADD_8_L97,  cQQ_ADD_8_L98,  cQQ_ADD_8_L99,  cQQ_ADD_8_L100, cQQ_ADD_8_L101,
    cQQ_ADD_8_L102, cQQ_ADD_8_L103, cQQ_ADD_8_L104, cQQ_ADD_8_L105, cQQ_ADD_8_L106, cQQ_ADD_8_L107,
    cQQ_ADD_8_L108, cQQ_ADD_8_L109, cQQ_ADD_8_L110, cQQ_ADD_8_L111, cQQ_ADD_8_L112, cQQ_ADD_8_L113,
    cQQ_ADD_8_L114, cQQ_ADD_8_L115, cQQ_ADD_8_L116, cQQ_ADD_8_L117, cQQ_ADD_8_L118, cQQ_ADD_8_L119,
    cQQ_ADD_8_L120, cQQ_ADD_8_L121, cQQ_ADD_8_L122, cQQ_ADD_8_L123, cQQ_ADD_8_L124, cQQ_ADD_8_L125};
static const num_t cQQ_ADD_8_GPL[] = {
    1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1, 2, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 9, 7, 6, 5, 4, 3, 2,
    2, 1, 2, 1, 2, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1};

static const sequence_t HARDCODED_cQQ_ADD_8 = {.seq = (gate_t **)cQQ_ADD_8_LAYERS,
                                               .num_layer = 126,
                                               .used_layer = 126,
                                               .gates_per_layer = (num_t *)cQQ_ADD_8_GPL};

// ============================================================================
// cQQ_ADD DISPATCH HELPER FOR 5-8
// ============================================================================

const sequence_t *get_hardcoded_cQQ_add_5_8(int bits) {
    switch (bits) {
    case 5:
        return &HARDCODED_cQQ_ADD_5;
    case 6:
        return &HARDCODED_cQQ_ADD_6;
    case 7:
        return &HARDCODED_cQQ_ADD_7;
    case 8:
        return &HARDCODED_cQQ_ADD_8;
    default:
        return NULL;
    }
}

// ============================================================================
// UNIFIED PUBLIC DISPATCH FUNCTIONS (covers all 1-8)
// ============================================================================

const sequence_t *get_hardcoded_QQ_add(int bits) {
    if (bits >= 1 && bits <= 4) {
        return get_hardcoded_QQ_add_1_4(bits);
    } else if (bits >= 5 && bits <= 8) {
        return get_hardcoded_QQ_add_5_8(bits);
    }
    return NULL; // > 8 or < 1: caller must use dynamic generation
}

const sequence_t *get_hardcoded_cQQ_add(int bits) {
    if (bits >= 1 && bits <= 4) {
        return get_hardcoded_cQQ_add_1_4(bits);
    } else if (bits >= 5 && bits <= 8) {
        return get_hardcoded_cQQ_add_5_8(bits);
    }
    return NULL;
}
