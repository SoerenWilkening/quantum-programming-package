# Makefile for C-level unit tests
# Usage: make test_comparison && ./test_comparison
#        make test_hot_path_mul && ./test_hot_path_mul
#        make test_hot_path_add && ./test_hot_path_add
#        make test_hot_path_xor && ./test_hot_path_xor

CC = gcc
CFLAGS = -Wall -Wextra -g -I../../c_backend/include
LDFLAGS = -lm

# Source files
BACKEND_SRC = ../../c_backend/src

# Minimal sources for comparison tests
BACKEND_SRCS = $(BACKEND_SRC)/Integer.c \
               $(BACKEND_SRC)/IntegerComparison.c \
               $(BACKEND_SRC)/QPU.c \
               $(BACKEND_SRC)/gate.c \
               $(BACKEND_SRC)/qubit_allocator.c

# Full sources needed for hot_path_mul tests (includes multiplication,
# addition for QFT, execution, optimizer, circuit allocations, sequences)
SEQ_SRCS = $(wildcard $(BACKEND_SRC)/sequences/add_seq_*.c)

MUL_SRCS = $(BACKEND_SRC)/Integer.c \
           $(BACKEND_SRC)/IntegerAddition.c \
           $(BACKEND_SRC)/IntegerMultiplication.c \
           $(BACKEND_SRC)/QPU.c \
           $(BACKEND_SRC)/gate.c \
           $(BACKEND_SRC)/qubit_allocator.c \
           $(BACKEND_SRC)/execution.c \
           $(BACKEND_SRC)/optimizer.c \
           $(BACKEND_SRC)/circuit_allocations.c \
           $(BACKEND_SRC)/circuit_output.c \
           $(BACKEND_SRC)/circuit_stats.c \
           $(BACKEND_SRC)/circuit_optimizer.c \
           $(BACKEND_SRC)/hot_path_mul.c \
           $(SEQ_SRCS)

# Sources for hot_path_add tests (addition only, no multiplication)
ADD_SRCS = $(BACKEND_SRC)/Integer.c \
           $(BACKEND_SRC)/IntegerAddition.c \
           $(BACKEND_SRC)/QPU.c \
           $(BACKEND_SRC)/gate.c \
           $(BACKEND_SRC)/qubit_allocator.c \
           $(BACKEND_SRC)/execution.c \
           $(BACKEND_SRC)/optimizer.c \
           $(BACKEND_SRC)/circuit_allocations.c \
           $(BACKEND_SRC)/circuit_output.c \
           $(BACKEND_SRC)/circuit_stats.c \
           $(BACKEND_SRC)/circuit_optimizer.c \
           $(BACKEND_SRC)/hot_path_add.c \
           $(SEQ_SRCS)

# Sources for hot_path_xor tests (bitwise only, no arithmetic sequences needed)
XOR_SRCS = $(BACKEND_SRC)/Integer.c \
           $(BACKEND_SRC)/LogicOperations.c \
           $(BACKEND_SRC)/QPU.c \
           $(BACKEND_SRC)/gate.c \
           $(BACKEND_SRC)/qubit_allocator.c \
           $(BACKEND_SRC)/execution.c \
           $(BACKEND_SRC)/optimizer.c \
           $(BACKEND_SRC)/circuit_allocations.c \
           $(BACKEND_SRC)/circuit_output.c \
           $(BACKEND_SRC)/circuit_stats.c \
           $(BACKEND_SRC)/circuit_optimizer.c \
           $(BACKEND_SRC)/hot_path_xor.c

# Test targets
test_comparison: test_comparison.c $(BACKEND_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_hot_path_mul: test_hot_path_mul.c $(MUL_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_hot_path_add: test_hot_path_add.c $(ADD_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_hot_path_xor: test_hot_path_xor.c $(XOR_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

.PHONY: clean
clean:
	rm -f test_comparison test_hot_path_mul test_hot_path_add test_hot_path_xor

.PHONY: run
run: test_comparison
	./test_comparison

.PHONY: run_mul
run_mul: test_hot_path_mul
	./test_hot_path_mul
