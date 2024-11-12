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

    // ._main
    element_t *state = unsigned_quantum_integer();
    element_t *mod = unsigned_quantum_integer();
    element_t *constant_0 = classical_integer(0);
    element_t *constant_5 = classical_integer(5);
    element_t *phase = classical_integer(-1);
    element_t *bool1 = quantum_bool();

    BRANCH(state, 0);
    BRANCH(state, 1);
    BRANCH(state, 2);
    BRANCH(state, 3);

    // function oracle
    IMOD(mod, state, constant_5);
    EQ(bool1, mod, constant_0);
    PMUL(bool1, phase);
    INV();
    EQ(bool1, mod, constant_0);
    INV();
    IMOD(mod, state, constant_5);

    BRANCH(state, 0);
    BRANCH(state, 1);
    BRANCH(state, 2);
    BRANCH(state, 3);

    // phase oracle for 0 state
    EQ(bool1, state, constant_0);
    PMUL(bool1, phase);
    INV();
    EQ(bool1, state, constant_0);

    BRANCH(state, 0);
    BRANCH(state, 1);
    BRANCH(state, 2);
    BRANCH(state, 3);

    // second grover iteration
    IMOD(mod, state, constant_5);
    EQ(bool1, mod, constant_0);
    PMUL(bool1, phase);
    INV();
    EQ(bool1, mod, constant_0);
    INV();
    IMOD(mod, state, constant_5);

    BRANCH(state, 0);
    BRANCH(state, 1);
    BRANCH(state, 2);
    BRANCH(state, 3);

    // phase oracle for 0 state
    EQ(bool1, state, constant_0);
    PMUL(bool1, phase);
    INV();
    EQ(bool1, state, constant_0);

    BRANCH(state, 0);
    BRANCH(state, 1);
    BRANCH(state, 2);
    BRANCH(state, 3);
//
//     Include measurement

    // ._execute
    clock_t t1 = clock();
    for (int i = 0; i < stack.instruction_counter; ++i) {
        execute(&stack.instruction_list[i]);
    }
    print_circuit(stack.circuit);

    printf("%f\n", (double) (clock() - t1) / CLOCKS_PER_SEC);
    return 0;
}
