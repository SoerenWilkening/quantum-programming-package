//
// add_seq_1_4.c - Hardcoded QQ_add and cQQ_add sequences for 1-4 bit widths
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
// QQ_ADD WIDTH 1 (3 layers)
// Qubit layout: [0] = target, [1] = control
// ============================================================================

static const gate_t QQ_ADD_1_L0[] = {{.Gate = H,
                                      .Target = 0,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_1_L1[] = {{.Gate = P,
                                      .Target = 0,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_1_L2[] = {{.Gate = H,
                                      .Target = 0,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t *QQ_ADD_1_LAYERS[] = {QQ_ADD_1_L0, QQ_ADD_1_L1, QQ_ADD_1_L2};
static const num_t QQ_ADD_1_GPL[] = {1, 1, 1};

static const sequence_t HARDCODED_QQ_ADD_1 = {.seq = (gate_t **)QQ_ADD_1_LAYERS,
                                              .num_layer = 3,
                                              .used_layer = 3,
                                              .gates_per_layer = (num_t *)QQ_ADD_1_GPL};

// ============================================================================
// QQ_ADD WIDTH 2 (8 layers)
// Qubit layout: [0,1] = target, [2,3] = control
// ============================================================================

static const gate_t QQ_ADD_2_L0[] = {{.Gate = H,
                                      .Target = 1,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_2_L1[] = {{.Gate = P,
                                      .Target = 1,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_2_L2[] = {{.Gate = H,
                                      .Target = 0,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_2_L3[] = {{.Gate = P,
                                      .Target = 0,
                                      .NumControls = 1,
                                      .Control = {2},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_2_L4[] = {{.Gate = P,
                                      .Target = 1,
                                      .NumControls = 1,
                                      .Control = {2},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_2_L5[] = {{.Gate = P,
                                      .Target = 1,
                                      .NumControls = 1,
                                      .Control = {3},
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

static const gate_t QQ_ADD_2_L6[] = {{.Gate = P,
                                      .Target = 1,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = -SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_2_L7[] = {{.Gate = H,
                                      .Target = 1,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t *QQ_ADD_2_LAYERS[] = {QQ_ADD_2_L0, QQ_ADD_2_L1, QQ_ADD_2_L2, QQ_ADD_2_L3,
                                          QQ_ADD_2_L4, QQ_ADD_2_L5, QQ_ADD_2_L6, QQ_ADD_2_L7};
static const num_t QQ_ADD_2_GPL[] = {1, 1, 1, 1, 1, 2, 1, 1};

static const sequence_t HARDCODED_QQ_ADD_2 = {.seq = (gate_t **)QQ_ADD_2_LAYERS,
                                              .num_layer = 8,
                                              .used_layer = 8,
                                              .gates_per_layer = (num_t *)QQ_ADD_2_GPL};

// ============================================================================
// QQ_ADD WIDTH 3 (14 layers)
// Qubit layout: [0,2] = target, [3,5] = control
// ============================================================================

static const gate_t QQ_ADD_3_L0[] = {{.Gate = H,
                                      .Target = 2,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_3_L1[] = {{.Gate = P,
                                      .Target = 2,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_3_L2[] = {{.Gate = P,
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

static const gate_t QQ_ADD_3_L3[] = {{.Gate = P,
                                      .Target = 1,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_3_L4[] = {{.Gate = H,
                                      .Target = 0,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_3_L5[] = {{.Gate = P,
                                      .Target = 0,
                                      .NumControls = 1,
                                      .Control = {3},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_3_L6[] = {{.Gate = P,
                                      .Target = 1,
                                      .NumControls = 1,
                                      .Control = {3},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_3_L7[] = {{.Gate = P,
                                      .Target = 2,
                                      .NumControls = 1,
                                      .Control = {3},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0},
                                     {.Gate = P,
                                      .Target = 1,
                                      .NumControls = 1,
                                      .Control = {4},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_3_L8[] = {{.Gate = P,
                                      .Target = 2,
                                      .NumControls = 1,
                                      .Control = {4},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_3_L9[] = {{.Gate = P,
                                      .Target = 2,
                                      .NumControls = 1,
                                      .Control = {5},
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

static const gate_t QQ_ADD_3_L10[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_3_L11[] = {{.Gate = H,
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

static const gate_t QQ_ADD_3_L12[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_3_L13[] = {{.Gate = H,
                                       .Target = 2,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t *QQ_ADD_3_LAYERS[] = {
    QQ_ADD_3_L0, QQ_ADD_3_L1, QQ_ADD_3_L2, QQ_ADD_3_L3,  QQ_ADD_3_L4,  QQ_ADD_3_L5,  QQ_ADD_3_L6,
    QQ_ADD_3_L7, QQ_ADD_3_L8, QQ_ADD_3_L9, QQ_ADD_3_L10, QQ_ADD_3_L11, QQ_ADD_3_L12, QQ_ADD_3_L13};
static const num_t QQ_ADD_3_GPL[] = {1, 1, 2, 1, 1, 1, 1, 2, 1, 2, 1, 2, 1, 1};

static const sequence_t HARDCODED_QQ_ADD_3 = {.seq = (gate_t **)QQ_ADD_3_LAYERS,
                                              .num_layer = 14,
                                              .used_layer = 14,
                                              .gates_per_layer = (num_t *)QQ_ADD_3_GPL};

// ============================================================================
// QQ_ADD WIDTH 4 (23 layers)
// Qubit layout: [0,3] = target, [4,7] = control
// ============================================================================

static const gate_t QQ_ADD_4_L0[] = {{.Gate = H,
                                      .Target = 3,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L1[] = {{.Gate = P,
                                      .Target = 3,
                                      .NumControls = 1,
                                      .Control = {2},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L2[] = {{.Gate = P,
                                      .Target = 3,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 4,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L3[] = {{.Gate = P,
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

static const gate_t QQ_ADD_4_L4[] = {{.Gate = P,
                                      .Target = 2,
                                      .NumControls = 1,
                                      .Control = {1},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L5[] = {{.Gate = P,
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

static const gate_t QQ_ADD_4_L6[] = {{.Gate = P,
                                      .Target = 1,
                                      .NumControls = 1,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L7[] = {{.Gate = H,
                                      .Target = 0,
                                      .NumControls = 0,
                                      .Control = {0},
                                      .large_control = NULL,
                                      .GateValue = 0,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L8[] = {{.Gate = P,
                                      .Target = 0,
                                      .NumControls = 1,
                                      .Control = {4},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L9[] = {{.Gate = P,
                                      .Target = 1,
                                      .NumControls = 1,
                                      .Control = {4},
                                      .large_control = NULL,
                                      .GateValue = SEQ_PI / 2,
                                      .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L10[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L11[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 8,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L12[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L13[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0},
                                      {.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L14[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L15[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {7},
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

static const gate_t QQ_ADD_4_L16[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L17[] = {{.Gate = H,
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

static const gate_t QQ_ADD_4_L18[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L19[] = {{.Gate = H,
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

static const gate_t QQ_ADD_4_L20[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L21[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t QQ_ADD_4_L22[] = {{.Gate = H,
                                       .Target = 3,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t *QQ_ADD_4_LAYERS[] = {
    QQ_ADD_4_L0,  QQ_ADD_4_L1,  QQ_ADD_4_L2,  QQ_ADD_4_L3,  QQ_ADD_4_L4,  QQ_ADD_4_L5,
    QQ_ADD_4_L6,  QQ_ADD_4_L7,  QQ_ADD_4_L8,  QQ_ADD_4_L9,  QQ_ADD_4_L10, QQ_ADD_4_L11,
    QQ_ADD_4_L12, QQ_ADD_4_L13, QQ_ADD_4_L14, QQ_ADD_4_L15, QQ_ADD_4_L16, QQ_ADD_4_L17,
    QQ_ADD_4_L18, QQ_ADD_4_L19, QQ_ADD_4_L20, QQ_ADD_4_L21, QQ_ADD_4_L22};
static const num_t QQ_ADD_4_GPL[] = {1, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 2,
                                     1, 2, 1, 2, 1, 2, 1, 2, 1, 1, 1};

static const sequence_t HARDCODED_QQ_ADD_4 = {.seq = (gate_t **)QQ_ADD_4_LAYERS,
                                              .num_layer = 23,
                                              .used_layer = 23,
                                              .gates_per_layer = (num_t *)QQ_ADD_4_GPL};

// ============================================================================
// QQ_ADD DISPATCH HELPER FOR 1-4
// ============================================================================

const sequence_t *get_hardcoded_QQ_add_1_4(int bits) {
    switch (bits) {
    case 1:
        return &HARDCODED_QQ_ADD_1;
    case 2:
        return &HARDCODED_QQ_ADD_2;
    case 3:
        return &HARDCODED_QQ_ADD_3;
    case 4:
        return &HARDCODED_QQ_ADD_4;
    default:
        return NULL;
    }
}

// ============================================================================
// cQQ_ADD WIDTH 1 (7 layers)
// Qubit layout: [0] = target, [1] = b, [2] = control
// ============================================================================

static const gate_t cQQ_ADD_1_L0[] = {{.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_1_L1[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_1_L2[] = {{.Gate = X,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = 1,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_1_L3[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_1_L4[] = {{.Gate = X,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = 1,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_1_L5[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_1_L6[] = {{.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t *cQQ_ADD_1_LAYERS[] = {cQQ_ADD_1_L0, cQQ_ADD_1_L1, cQQ_ADD_1_L2, cQQ_ADD_1_L3,
                                           cQQ_ADD_1_L4, cQQ_ADD_1_L5, cQQ_ADD_1_L6};
static const num_t cQQ_ADD_1_GPL[] = {1, 1, 1, 1, 1, 1, 1};

static const sequence_t HARDCODED_cQQ_ADD_1 = {.seq = (gate_t **)cQQ_ADD_1_LAYERS,
                                               .num_layer = 7,
                                               .used_layer = 7,
                                               .gates_per_layer = (num_t *)cQQ_ADD_1_GPL};

// ============================================================================
// cQQ_ADD WIDTH 2 (15 layers)
// Qubit layout: [0,1] = target, [2,3] = b, [4] = control
// ============================================================================

static const gate_t cQQ_ADD_2_L0[] = {{.Gate = H,
                                       .Target = 1,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L1[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L2[] = {{.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L3[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L4[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = 3 * SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L5[] = {{.Gate = X,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = 1,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L6[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L7[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {3},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L8[] = {{.Gate = X,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = 1,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L9[] = {{.Gate = X,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {4},
                                       .large_control = NULL,
                                       .GateValue = 1,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L10[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L11[] = {{.Gate = X,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {4},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L12[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {2},
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

static const gate_t cQQ_ADD_2_L13[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_2_L14[] = {{.Gate = H,
                                        .Target = 1,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t *cQQ_ADD_2_LAYERS[] = {
    cQQ_ADD_2_L0,  cQQ_ADD_2_L1,  cQQ_ADD_2_L2,  cQQ_ADD_2_L3,  cQQ_ADD_2_L4,
    cQQ_ADD_2_L5,  cQQ_ADD_2_L6,  cQQ_ADD_2_L7,  cQQ_ADD_2_L8,  cQQ_ADD_2_L9,
    cQQ_ADD_2_L10, cQQ_ADD_2_L11, cQQ_ADD_2_L12, cQQ_ADD_2_L13, cQQ_ADD_2_L14};
static const num_t cQQ_ADD_2_GPL[] = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 2, 1, 1};

static const sequence_t HARDCODED_cQQ_ADD_2 = {.seq = (gate_t **)cQQ_ADD_2_LAYERS,
                                               .num_layer = 15,
                                               .used_layer = 15,
                                               .gates_per_layer = (num_t *)cQQ_ADD_2_GPL};

// ============================================================================
// cQQ_ADD WIDTH 3 (26 layers)
// Qubit layout: [0,2] = target, [3,5] = b, [6] = control
// ============================================================================

static const gate_t cQQ_ADD_3_L0[] = {{.Gate = H,
                                       .Target = 2,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L1[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L2[] = {{.Gate = P,
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

static const gate_t cQQ_ADD_3_L3[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L4[] = {{.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L5[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L6[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = 3 * SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L7[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = 7 * SEQ_PI / 8,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L8[] = {{.Gate = X,
                                       .Target = 5,
                                       .NumControls = 1,
                                       .Control = {6},
                                       .large_control = NULL,
                                       .GateValue = 1,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L9[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {5},
                                       .large_control = NULL,
                                       .GateValue = -SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L10[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L11[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L12[] = {{.Gate = X,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L13[] = {{.Gate = X,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L14[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {4},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L15[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {4},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L16[] = {{.Gate = X,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L17[] = {{.Gate = X,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L18[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {3},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L19[] = {{.Gate = X,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L20[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {4},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {4},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L21[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {3},
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

static const gate_t cQQ_ADD_3_L22[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L23[] = {{.Gate = H,
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

static const gate_t cQQ_ADD_3_L24[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_3_L25[] = {{.Gate = H,
                                        .Target = 2,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t *cQQ_ADD_3_LAYERS[] = {
    cQQ_ADD_3_L0,  cQQ_ADD_3_L1,  cQQ_ADD_3_L2,  cQQ_ADD_3_L3,  cQQ_ADD_3_L4,  cQQ_ADD_3_L5,
    cQQ_ADD_3_L6,  cQQ_ADD_3_L7,  cQQ_ADD_3_L8,  cQQ_ADD_3_L9,  cQQ_ADD_3_L10, cQQ_ADD_3_L11,
    cQQ_ADD_3_L12, cQQ_ADD_3_L13, cQQ_ADD_3_L14, cQQ_ADD_3_L15, cQQ_ADD_3_L16, cQQ_ADD_3_L17,
    cQQ_ADD_3_L18, cQQ_ADD_3_L19, cQQ_ADD_3_L20, cQQ_ADD_3_L21, cQQ_ADD_3_L22, cQQ_ADD_3_L23,
    cQQ_ADD_3_L24, cQQ_ADD_3_L25};
static const num_t cQQ_ADD_3_GPL[] = {1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                      1, 1, 1, 1, 1, 1, 4, 2, 2, 1, 2, 1, 1};

static const sequence_t HARDCODED_cQQ_ADD_3 = {.seq = (gate_t **)cQQ_ADD_3_LAYERS,
                                               .num_layer = 26,
                                               .used_layer = 26,
                                               .gates_per_layer = (num_t *)cQQ_ADD_3_GPL};

// ============================================================================
// cQQ_ADD WIDTH 4 (40 layers)
// Qubit layout: [0,3] = target, [4,7] = b, [8] = control
// ============================================================================

static const gate_t cQQ_ADD_4_L0[] = {{.Gate = H,
                                       .Target = 3,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L1[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {2},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L2[] = {{.Gate = P,
                                       .Target = 3,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L3[] = {{.Gate = P,
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

static const gate_t cQQ_ADD_4_L4[] = {{.Gate = P,
                                       .Target = 2,
                                       .NumControls = 1,
                                       .Control = {1},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L5[] = {{.Gate = P,
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

static const gate_t cQQ_ADD_4_L6[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L7[] = {{.Gate = H,
                                       .Target = 0,
                                       .NumControls = 0,
                                       .Control = {0},
                                       .large_control = NULL,
                                       .GateValue = 0,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L8[] = {{.Gate = P,
                                       .Target = 0,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = SEQ_PI / 2,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L9[] = {{.Gate = P,
                                       .Target = 1,
                                       .NumControls = 1,
                                       .Control = {8},
                                       .large_control = NULL,
                                       .GateValue = 3 * SEQ_PI / 4,
                                       .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L10[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = 7 * SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L11[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = 15 * SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L12[] = {{.Gate = X,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L13[] = {{.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L14[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L15[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L16[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L17[] = {{.Gate = X,
                                        .Target = 7,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L18[] = {{.Gate = X,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L19[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L20[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L21[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L22[] = {{.Gate = X,
                                        .Target = 6,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L23[] = {{.Gate = X,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L24[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L25[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L26[] = {{.Gate = X,
                                        .Target = 5,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L27[] = {{.Gate = X,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L28[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {4},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L29[] = {{.Gate = X,
                                        .Target = 4,
                                        .NumControls = 1,
                                        .Control = {8},
                                        .large_control = NULL,
                                        .GateValue = 1,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 0,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {7},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 16,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L30[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {6},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 8,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L31[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 2,
                                        .NumBasisGates = 0},
                                       {.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {5},
                                        .large_control = NULL,
                                        .GateValue = SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L32[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {4},
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

static const gate_t cQQ_ADD_4_L33[] = {{.Gate = P,
                                        .Target = 1,
                                        .NumControls = 1,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L34[] = {{.Gate = H,
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

static const gate_t cQQ_ADD_4_L35[] = {{.Gate = P,
                                        .Target = 2,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L36[] = {{.Gate = H,
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

static const gate_t cQQ_ADD_4_L37[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {1},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 4,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L38[] = {{.Gate = P,
                                        .Target = 3,
                                        .NumControls = 1,
                                        .Control = {2},
                                        .large_control = NULL,
                                        .GateValue = -SEQ_PI / 2,
                                        .NumBasisGates = 0}};

static const gate_t cQQ_ADD_4_L39[] = {{.Gate = H,
                                        .Target = 3,
                                        .NumControls = 0,
                                        .Control = {0},
                                        .large_control = NULL,
                                        .GateValue = 0,
                                        .NumBasisGates = 0}};

static const gate_t *cQQ_ADD_4_LAYERS[] = {
    cQQ_ADD_4_L0,  cQQ_ADD_4_L1,  cQQ_ADD_4_L2,  cQQ_ADD_4_L3,  cQQ_ADD_4_L4,  cQQ_ADD_4_L5,
    cQQ_ADD_4_L6,  cQQ_ADD_4_L7,  cQQ_ADD_4_L8,  cQQ_ADD_4_L9,  cQQ_ADD_4_L10, cQQ_ADD_4_L11,
    cQQ_ADD_4_L12, cQQ_ADD_4_L13, cQQ_ADD_4_L14, cQQ_ADD_4_L15, cQQ_ADD_4_L16, cQQ_ADD_4_L17,
    cQQ_ADD_4_L18, cQQ_ADD_4_L19, cQQ_ADD_4_L20, cQQ_ADD_4_L21, cQQ_ADD_4_L22, cQQ_ADD_4_L23,
    cQQ_ADD_4_L24, cQQ_ADD_4_L25, cQQ_ADD_4_L26, cQQ_ADD_4_L27, cQQ_ADD_4_L28, cQQ_ADD_4_L29,
    cQQ_ADD_4_L30, cQQ_ADD_4_L31, cQQ_ADD_4_L32, cQQ_ADD_4_L33, cQQ_ADD_4_L34, cQQ_ADD_4_L35,
    cQQ_ADD_4_L36, cQQ_ADD_4_L37, cQQ_ADD_4_L38, cQQ_ADD_4_L39};
static const num_t cQQ_ADD_4_GPL[] = {1, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                                      1, 1, 1, 1, 1, 1, 1, 1, 1, 5, 3, 2, 2, 1, 2, 1, 2, 1, 1, 1};

static const sequence_t HARDCODED_cQQ_ADD_4 = {.seq = (gate_t **)cQQ_ADD_4_LAYERS,
                                               .num_layer = 40,
                                               .used_layer = 40,
                                               .gates_per_layer = (num_t *)cQQ_ADD_4_GPL};

// ============================================================================
// cQQ_ADD DISPATCH HELPER FOR 1-4
// ============================================================================

const sequence_t *get_hardcoded_cQQ_add_1_4(int bits) {
    switch (bits) {
    case 1:
        return &HARDCODED_cQQ_ADD_1;
    case 2:
        return &HARDCODED_cQQ_ADD_2;
    case 3:
        return &HARDCODED_cQQ_ADD_3;
    case 4:
        return &HARDCODED_cQQ_ADD_4;
    default:
        return NULL;
    }
}
