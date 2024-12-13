//
// Created by Sören Wilkening on 05.11.24.
//

#ifndef CQ_BACKEND_IMPROVED_INTEGER_H
#define CQ_BACKEND_IMPROVED_INTEGER_H

#include <math.h>
#include "definition.h"
#include "gate.h"
#include "QPU.h"

int *two_complement(int64_t x, int n);

quantum_int_t *QBOOL();
quantum_int_t *QINT();
quantum_int_t *INT(int64_t intg);
quantum_int_t *BOOL(bool intg);
quantum_int_t *bit_of_int(quantum_int_t *el1, int bit);
sequence_t *setting_seq();
void free_element(quantum_int_t *el1);

// implementation of Integer operations gate sequences
sequence_t *CC_mul();
sequence_t *CQ_mul();
sequence_t *QQ_mul();
sequence_t *cCQ_mul();
sequence_t *cQQ_mul();

sequence_t *CC_add();
sequence_t *CQ_add();
sequence_t *QQ_add();
sequence_t *cCQ_add();
sequence_t *cQQ_add();

sequence_t *P_add();

extern sequence_t *precompiled_QQ_add;
extern sequence_t *precompiled_cQQ_add;
extern sequence_t *precompiled_CQ_add;
extern sequence_t *precompiled_cCQ_add;

extern sequence_t *precompiled_QQ_mul;
extern sequence_t *precompiled_cQQ_mul;

#endif //CQ_BACKEND_IMPROVED_INTEGER_H
