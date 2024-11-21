#include <stdio.h>
#include <time.h>
#include "AssemblyComparison.h"
#include "AssemblyReader.h"
#include "execution.h"

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
    stack.GPR1[0].type = UNINITIALIZED;
    stack.GPR2[0].type = UNINITIALIZED;
    stack.GPR3[0].type = UNINITIALIZED;
    stack.GPC[0].type = UNINITIALIZED;
    stack.circuit = init_circuit();
    stack.instruction_counter = 0;
    for (int i = 0; i < 10000; ++i) init_instruction(&stack.instruction_list[i]);

    AsmbFromFile();

    // ._execute
    clock_t t1 = clock();
    instruction_t *instruction_pointer = stack.instruction_list;
    for (int i = 0; i < stack.instruction_counter; ++i) {
        execute(instruction_pointer);
        instruction_pointer++;
    }
    print_circuit(stack.circuit);

    printf("%f\n", (double) (clock() - t1) / CLOCKS_PER_SEC);
    return 0;
}
