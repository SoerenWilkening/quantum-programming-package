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

sequence_t *and_sequence();

sequence_t *branch();

#endif //CQ_BACKEND_IMPROVED_LOGICOPERATIONS_H
