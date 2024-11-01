#include <stdio.h>
#include <time.h>
#include "QPU.h"

hybrid_stack_t stack;

sequence_t *precompiled_QQ_add = NULL;
sequence_t *precompiled_cQQ_add = NULL;

int main(void) {

    // initialize the rest of the stack
    // prepare exerything for the execution
    stack.circuit = init_circuit();
    stack.instruction_counter = 0;
    for (int i = 0; i < 10000; ++i) {
        init_instruction(&stack.instruction_list[i]);
    }

    // ._data
    element_t *Rq = signed_quantum_integer();
    element_t *Aq = signed_quantum_integer();
    element_t *Bq = signed_quantum_integer();
    element_t *Cq = quantum_bool();
    element_t *Cc = classical_integer(12);
    element_t *Dc = classical_integer(24);

    element_t *constant_1 = classical_integer(1);
    // ._main
    clock_t t1 = clock();


    // create IDIV sequence to Divide Aq / Bq
    element_t *Y = malloc(sizeof(element_t));
    memcpy(Y, Aq, sizeof(element_t));
    for (int i = 1; i <= INTEGERSIZE; ++i) {

        SHR(Y);
        SUB(Y, Bq); // subtract Bq from Aq
        element_t *bit = bit_of_int(Rq, i - 1);
        TSTBIT(bit, Y, 0); // check if Aq is negative, stored in Cq
        IF(bit); // create control for the next instruction
        ADD(Y, Bq); // Add bq back to Aq (controlled by Cq)
        ELSE(bit);
        NOT(bit); // Invert Cq
    }
    SUB(Aq, Bq); // subtract Bq from Aq
    element_t *bit = bit_of_int(Rq, INTEGERSIZE - 1);
    TSTBIT(bit, Y, 0); // check if Aq is negative, stored in Cq
    IF(bit); // create control for the next instruction
    ADD(Y, Bq); // Add bq back to Aq (controlled by Cq)
    ELSE(bit);
    NOT(bit); // Invert Cq

    // ._execute
    for (int i = 0; i < stack.instruction_counter; ++i) {
        execute(&stack.instruction_list[i]);
    }

    printf("%f\n", (double) (clock() - t1) / CLOCKS_PER_SEC);
    return 0;
}
