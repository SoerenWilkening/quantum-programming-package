//
// LogicOperations.h - Logic and control flow operations
// Dependencies: bitwise_ops.h, Integer.h, QPU.h, gate.h
//
// This header provides:
// - Width-parameterized bitwise ops (via bitwise_ops.h)
// - Legacy qbool operations (fixed INTEGERSIZE)
// - Control flow sequences (branch, void, jmp)
//

#ifndef CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H
#define CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H

#include "Integer.h"
#include "QPU.h"
#include "bitwise_ops.h"
#include "definition.h"
#include "gate.h"

// ======================================================
// Control flow operations
// ======================================================
sequence_t *void_seq();
// jmp_seq removed (Phase 11) - manipulated QPU_state pointer for control flow that's no longer used
sequence_t *branch_seq();
sequence_t *cbranch_seq();

// ======================================================
// Legacy INTEGERSIZE-based operations
// Use bitwise_ops.h for variable-width operations
// ======================================================

// Legacy NOT operations
// not_seq removed (Phase 11) - purely classical, no quantum gate generation
sequence_t *q_not_seq();
sequence_t *cq_not_seq();

// Legacy AND operations (DEPRECATED - use Q_and/CQ_and from bitwise_ops.h instead)
// and_seq removed (Phase 11) - purely classical, no quantum gate generation
sequence_t *q_and_seq(int bits, int classical_value);
sequence_t *cq_and_seq(int bits, int classical_value);
sequence_t *qq_and_seq();
sequence_t *cqq_and_seq(int bits);

// Legacy XOR operations (DEPRECATED - use Q_xor/cQ_xor from bitwise_ops.h instead)
// xor_seq removed (Phase 11) - purely classical, no quantum gate generation
sequence_t *q_xor_seq(int bits, int classical_value);
sequence_t *cq_xor_seq(int bits, int classical_value);
sequence_t *qq_xor_seq(int bits);
sequence_t *cqq_xor_seq(int bits);

// Legacy OR operations (DEPRECATED - use Q_or/CQ_or from bitwise_ops.h instead)
// or_seq removed (Phase 11) - purely classical, no quantum gate generation
sequence_t *q_or_seq(int bits, int classical_value);
sequence_t *cq_or_seq(int bits, int classical_value);
sequence_t *qq_or_seq();
sequence_t *cqq_or_seq(int bits);

#endif // CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H
