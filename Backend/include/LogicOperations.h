//
// Created by Sören Wilkening on 05.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H
#define CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H

#include "definition.h"
#include "gate.h"
#include "QPU.h"
#include "Integer.h"

sequence_t *void_seq();

sequence_t *not_seq();
sequence_t *ctrl_not_seq();

sequence_t *and_seq();
sequence_t *q_and_seq();
sequence_t *qq_and_seq();
sequence_t *cq_and_seq();
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

#endif //CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H
