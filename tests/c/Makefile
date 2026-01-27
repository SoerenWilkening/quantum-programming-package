# Makefile for comparison function tests
# Usage: make test_comparison && ./test_comparison

CC = gcc
CFLAGS = -Wall -Wextra -g -I../../Backend/include
LDFLAGS = -lm

# Source files
BACKEND_SRC = ../../Backend/src
BACKEND_SRCS = $(BACKEND_SRC)/Integer.c \
               $(BACKEND_SRC)/IntegerComparison.c \
               $(BACKEND_SRC)/QPU.c \
               $(BACKEND_SRC)/gate.c \
               $(BACKEND_SRC)/qubit_allocator.c

# Test target
test_comparison: test_comparison.c $(BACKEND_SRCS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

.PHONY: clean
clean:
	rm -f test_comparison

.PHONY: run
run: test_comparison
	./test_comparison
