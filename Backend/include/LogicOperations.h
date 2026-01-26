//
// Created by Sören Wilkening on 05.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H
#define CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H

#include "Integer.h"
#include "QPU.h"
#include "definition.h"
#include "gate.h"

sequence_t *void_seq();
sequence_t *jmp_seq();

sequence_t *q_not_seq();
sequence_t *cq_not_seq();

// Width-parameterized NOT operations (Phase 6)
sequence_t *Q_not(int bits);
sequence_t *cQ_not(int bits);

sequence_t *and_seq();
sequence_t *q_and_seq();
sequence_t *cq_and_seq();
sequence_t *qq_and_seq();
sequence_t *cqq_and_seq();

sequence_t *branch_seq();
sequence_t *cbranch_seq();

sequence_t *q_xor_seq();
sequence_t *cq_xor_seq();
sequence_t *qq_xor_seq();
sequence_t *cqq_xor_seq();

sequence_t *q_or_seq();
sequence_t *cq_or_seq();
sequence_t *qq_or_seq();
sequence_t *cqq_or_seq();

#endif // CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H
