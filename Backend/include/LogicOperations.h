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
sequence_t *jmp_seq();
sequence_t *branch_seq();
sequence_t *cbranch_seq();

// ======================================================
// Legacy INTEGERSIZE-based operations
// Use bitwise_ops.h for variable-width operations
// ======================================================

// Legacy NOT operations
sequence_t *q_not_seq();
sequence_t *cq_not_seq();

// Legacy AND operations
sequence_t *and_seq();
sequence_t *q_and_seq();
sequence_t *cq_and_seq();
sequence_t *qq_and_seq();
sequence_t *cqq_and_seq();

// Legacy XOR operations
sequence_t *q_xor_seq();
sequence_t *cq_xor_seq();
sequence_t *qq_xor_seq();
sequence_t *cqq_xor_seq();

// Legacy OR operations
sequence_t *q_or_seq();
sequence_t *cq_or_seq();
sequence_t *qq_or_seq();
sequence_t *cqq_or_seq();

#endif // CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H
