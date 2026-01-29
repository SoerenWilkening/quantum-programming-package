# Makefile for Quantum Assembly Language Project
# Purpose: Provide convenient test targets with memory checking tools
# Note: This Makefile complements CMakeLists.txt (which handles the main build)

# === Variables ===
# Try to find a C compiler
CC := $(shell command -v gcc 2>/dev/null || command -v clang 2>/dev/null || command -v cc 2>/dev/null)
CFLAGS = -Wall -Wextra -g -O2 -std=c23
ASAN_FLAGS = -fsanitize=address -fno-omit-frame-pointer -g -O1
PYTHON = python3
PYTEST = $(PYTHON) -m pytest
VENV = .venv/bin/activate

# Source files
BACKEND_SRC = c_backend/src/*.c
BACKEND_INC = -Ic_backend/include
EXEC_SRC =

# Check for required tools
HAS_CC := $(shell command -v gcc 2>/dev/null || command -v clang 2>/dev/null || command -v cc 2>/dev/null)
HAS_VALGRIND := $(shell command -v valgrind 2>/dev/null)

# === Test Targets ===

.PHONY: test
test:
	@echo "Running Python characterization tests..."
	. $(VENV) && $(PYTEST) tests/python -v --tb=short

.PHONY: memtest
memtest: test
ifndef HAS_VALGRIND
	@echo "ERROR: Valgrind not found"
	@echo "Memory testing requires Valgrind to be installed."
	@echo "Install valgrind to use this target."
	@exit 1
endif
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
ifndef HAS_CC
	@echo "ERROR: No C compiler found (tried gcc, clang, cc)"
	@echo "AddressSanitizer tests require a C compiler to be installed."
	@echo "Install gcc or clang to use this target."
	@exit 1
endif
	@echo "Building C backend with AddressSanitizer..."
	@echo "Using compiler: $(CC)"
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
	@echo "  memtest    - Run tests under Valgrind (requires valgrind)"
	@echo "  asan-test  - Build and run C backend with AddressSanitizer (requires gcc/clang)"
	@echo "  check      - Run pre-commit hooks on all files"
	@echo "  clean      - Remove test artifacts"
	@echo "  help       - Show this help message"
	@echo ""
	@echo "Tool availability:"
	@echo "  C compiler: $(if $(HAS_CC),$(CC),NOT FOUND)"
	@echo "  Valgrind:   $(if $(HAS_VALGRIND),found,NOT FOUND)"
