#include <stdio.h>
#include <time.h>
#include "include/AssemblyOperations.h"

hybrid_stack_t stack;

sequence_t *precompiled_QQ_add = NULL;
sequence_t *precompiled_cQQ_add = NULL;
sequence_t *precompiled_CQ_add = NULL;
sequence_t *precompiled_cCQ_add = NULL;

sequence_t *precompiled_cQQ_mul = NULL;
sequence_t *precompiled_QQ_mul = NULL;

int main(void) {

    // initialize the rest of the stack
    // prepare exerything for the execution
    stack.circuit = init_circuit();
    stack.instruction_counter = 0;
    for (int i = 0; i < 10000; ++i) {
        init_instruction(&stack.instruction_list[i]);
    }

    // ._data
    element_t *Aq = signed_quantum_integer();
    element_t *Bq = signed_quantum_integer();
    element_t *Rq = signed_quantum_integer();
    element_t *Cq = quantum_bool();
    element_t *Dq = quantum_bool();
    element_t *Eq = quantum_bool();
    element_t *Cc = classical_integer(12);
    element_t *Dc = classical_integer(24);

    // ._main
    clock_t t1 = clock();
    GE(Cq, Aq, Cc);
//    AND(Aq, Dc, Bq);
//    IF(Cq);
//    IDIV(Aq, Bq, Rq);
//    IMUL(Aq, Rq, Bq);

    // ._execute
    for (int i = 0; i < stack.instruction_counter; ++i) {
        execute(&stack.instruction_list[i]);
    }

    printf("%f\n", (double) (clock() - t1) / CLOCKS_PER_SEC);
    return 0;
}
