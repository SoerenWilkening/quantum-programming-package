# Makefile for C-level unit tests
# Usage: make test_comparison && ./test_comparison
#        make test_reverse_circuit && ./test_reverse_circuit
#        make test_allocator_block && ./test_allocator_block
#        make test_tracking_only && ./test_tracking_only
#        make test_sequence_gate_count && ./test_sequence_gate_count

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

# Sources for sequence_gate_count tests (circuit + execution + ToffoliAdditionHelpers)
SEQ_COUNT_SRCS = $(BACKEND_SRC)/execution.c \
                 $(BACKEND_SRC)/optimizer.c \
                 $(BACKEND_SRC)/gate.c \
                 $(BACKEND_SRC)/qubit_allocator.c \
                 $(BACKEND_SRC)/circuit_allocations.c \
                 $(BACKEND_SRC)/circuit_output.c \
                 $(BACKEND_SRC)/circuit_stats.c \
                 $(BACKEND_SRC)/circuit_optimizer.c \
                 $(BACKEND_SRC)/ToffoliAdditionHelpers.c

# Test targets
test_comparison: test_comparison.c $(BACKEND_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)


test_reverse_circuit: test_reverse_circuit.c $(REVERSE_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_tracking_only: test_tracking_only.c $(TRACKING_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_sequence_gate_count: test_sequence_gate_count.c $(SEQ_COUNT_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_allocator_block: test_allocator_block.c $(ALLOC_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_allocator_block_debug: test_allocator_block.c $(ALLOC_SRCS)
	$(CC) $(CFLAGS) -DDEBUG -o $@ $^ $(LDFLAGS)

.PHONY: clean
clean:
	rm -f test_comparison test_reverse_circuit test_tracking_only test_sequence_gate_count test_allocator_block test_allocator_block_debug

.PHONY: run
run: test_comparison
	./test_comparison

.PHONY: run_reverse
run_reverse: test_reverse_circuit
	./test_reverse_circuit

.PHONY: run_alloc
run_alloc: test_allocator_block
	./test_allocator_block

.PHONY: run_alloc_debug
run_alloc_debug: test_allocator_block_debug
	./test_allocator_block_debug
