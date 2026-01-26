# Makefile for Quantum Assembly Language Project
# Purpose: Provide convenient test targets with memory checking tools
# Note: This Makefile complements CMakeLists.txt (which handles the main build)

# === Variables ===
CC = gcc
CFLAGS = -Wall -Wextra -g -O2 -std=c23
ASAN_FLAGS = -fsanitize=address -fno-omit-frame-pointer -g -O1
PYTHON = python3
PYTEST = $(PYTHON) -m pytest
VENV = .venv/bin/activate

# Source files
BACKEND_SRC = Backend/src/*.c
BACKEND_INC = -IBackend/include -IExecution/include
EXEC_SRC = Execution/src/*.c

# === Test Targets ===

.PHONY: test
test:
	@echo "Running Python characterization tests..."
	. $(VENV) && $(PYTEST) tests/python -v --tb=short

.PHONY: memtest
memtest: test
	@echo "Running Python tests under Valgrind..."
	@echo "Note: Use PYTHONMALLOC=malloc to avoid false positives"
	. $(VENV) && PYTHONMALLOC=malloc valgrind \
		--leak-check=full \
		--show-leak-kinds=definite,indirect \
		--error-exitcode=1 \
		--suppressions=/dev/null \
		$(PYTHON) -m pytest tests/python -v --tb=short 2>&1 | tee valgrind-output.log
	@echo "Valgrind output saved to valgrind-output.log"

.PHONY: asan-test
asan-test:
	@echo "Building C backend with AddressSanitizer..."
	@mkdir -p build
	$(CC) $(CFLAGS) $(ASAN_FLAGS) $(BACKEND_INC) \
		$(BACKEND_SRC) $(EXEC_SRC) main.c \
		-o build/test_runner_asan -lm
	@echo "Running ASan-instrumented binary..."
	./build/test_runner_asan 16 1

# === Code Quality ===

.PHONY: check
check:
	@echo "Running pre-commit checks..."
	. $(VENV) && pre-commit run --all-files

# === Cleanup ===

.PHONY: clean
clean:
	rm -rf build/test_runner_asan
	rm -f valgrind-output.log

# === Help ===

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  test       - Run pytest characterization tests"
	@echo "  memtest    - Run tests under Valgrind (slow, comprehensive)"
	@echo "  asan-test  - Build and run C backend with AddressSanitizer (fast)"
	@echo "  check      - Run pre-commit hooks on all files"
	@echo "  clean      - Remove test artifacts"
	@echo "  help       - Show this help message"
