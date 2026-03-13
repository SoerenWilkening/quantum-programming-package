# Makefile for C-level unit tests
# Usage: make test_comparison && ./test_comparison
#        make test_hot_path_mul && ./test_hot_path_mul
#        make test_reverse_circuit && ./test_reverse_circuit
#        make test_allocator_block && ./test_allocator_block
#        make test_tracking_only && ./test_tracking_only

CC = gcc
CFLAGS = -Wall -Wextra -g -I../../c_backend/include
LDFLAGS = -lm

# Source files
BACKEND_SRC = ../../c_backend/src

# Sources for comparison tests (gate.c now requires optimizer.c for add_gate
# due to Clifford+T decomposition added in Phase 74)
BACKEND_SRCS = $(BACKEND_SRC)/Integer.c \
               $(BACKEND_SRC)/IntegerComparison.c \
               $(BACKEND_SRC)/gate.c \
               $(BACKEND_SRC)/qubit_allocator.c \
               $(BACKEND_SRC)/optimizer.c \
               $(BACKEND_SRC)/circuit_allocations.c \
               $(BACKEND_SRC)/circuit_output.c \
               $(BACKEND_SRC)/circuit_stats.c \
               $(BACKEND_SRC)/circuit_optimizer.c \
               $(BACKEND_SRC)/execution.c

# Full sources needed for hot_path_mul tests (includes multiplication,
# addition for QFT, execution, optimizer, circuit allocations, sequences)
SEQ_SRCS = $(wildcard $(BACKEND_SRC)/sequences/add_seq_*.c)
TOFFOLI_SEQ_SRCS = $(wildcard $(BACKEND_SRC)/sequences/toffoli_*.c)

MUL_SRCS = $(BACKEND_SRC)/Integer.c \
           $(BACKEND_SRC)/IntegerAddition.c \
           $(BACKEND_SRC)/IntegerMultiplication.c \
           $(BACKEND_SRC)/ToffoliMultiplication.c \
           $(BACKEND_SRC)/ToffoliAdditionCDKM.c \
           $(BACKEND_SRC)/ToffoliAdditionCLA.c \
           $(BACKEND_SRC)/ToffoliAdditionHelpers.c \
           $(BACKEND_SRC)/gate.c \
           $(BACKEND_SRC)/qubit_allocator.c \
           $(BACKEND_SRC)/execution.c \
           $(BACKEND_SRC)/optimizer.c \
           $(BACKEND_SRC)/circuit_allocations.c \
           $(BACKEND_SRC)/circuit_output.c \
           $(BACKEND_SRC)/circuit_stats.c \
           $(BACKEND_SRC)/circuit_optimizer.c \
           $(BACKEND_SRC)/hot_path_mul.c \
           $(SEQ_SRCS) \
           $(TOFFOLI_SEQ_SRCS)


# Sources for allocator block tests (minimal -- allocator only)
ALLOC_SRCS = $(BACKEND_SRC)/qubit_allocator.c

# Sources for reverse_circuit tests (circuit + execution, no arithmetic)
REVERSE_SRCS = $(BACKEND_SRC)/execution.c \
               $(BACKEND_SRC)/optimizer.c \
               $(BACKEND_SRC)/gate.c \
               $(BACKEND_SRC)/qubit_allocator.c \
               $(BACKEND_SRC)/circuit_allocations.c \
               $(BACKEND_SRC)/circuit_output.c \
               $(BACKEND_SRC)/circuit_stats.c \
               $(BACKEND_SRC)/circuit_optimizer.c

# Sources for tracking_only tests (circuit + execution, no arithmetic)
TRACKING_SRCS = $(BACKEND_SRC)/execution.c \
                $(BACKEND_SRC)/optimizer.c \
                $(BACKEND_SRC)/gate.c \
                $(BACKEND_SRC)/qubit_allocator.c \
                $(BACKEND_SRC)/circuit_allocations.c \
                $(BACKEND_SRC)/circuit_output.c \
                $(BACKEND_SRC)/circuit_stats.c \
                $(BACKEND_SRC)/circuit_optimizer.c

# Test targets
test_comparison: test_comparison.c $(BACKEND_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_hot_path_mul: test_hot_path_mul.c $(MUL_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)


test_reverse_circuit: test_reverse_circuit.c $(REVERSE_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_tracking_only: test_tracking_only.c $(TRACKING_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_allocator_block: test_allocator_block.c $(ALLOC_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_allocator_block_debug: test_allocator_block.c $(ALLOC_SRCS)
	$(CC) $(CFLAGS) -DDEBUG -o $@ $^ $(LDFLAGS)

.PHONY: clean
clean:
	rm -f test_comparison test_hot_path_mul test_reverse_circuit test_tracking_only test_allocator_block test_allocator_block_debug

.PHONY: run
run: test_comparison
	./test_comparison

.PHONY: run_mul
run_mul: test_hot_path_mul
	./test_hot_path_mul

.PHONY: run_reverse
run_reverse: test_reverse_circuit
	./test_reverse_circuit

.PHONY: run_alloc
run_alloc: test_allocator_block
	./test_allocator_block

.PHONY: run_alloc_debug
run_alloc_debug: test_allocator_block_debug
	./test_allocator_block_debug
