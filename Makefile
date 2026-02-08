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
HAS_PYSPY := $(shell command -v py-spy 2>/dev/null)
HAS_MEMRAY := $(shell command -v memray 2>/dev/null)

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
	rm -f profile.svg memray.bin memory.html

# === Profiling Targets ===

.PHONY: profile-cython
profile-cython:
	@echo "Generating Cython annotation HTML..."
	@mkdir -p build/cython-annotate
	@echo "Processing files without include directives..."
	@for f in src/quantum_language/_core.pyx src/quantum_language/openqasm.pyx src/quantum_language/qarray.pyx src/quantum_language/qbool.pyx src/quantum_language/qint_mod.pyx; do \
		if [ -f "$$f" ]; then \
			echo "  Annotating $$f"; \
			cython -a -3 "$$f" -o build/cython-annotate/$$(basename $${f%.pyx}.c) 2>/dev/null || true; \
		fi; \
	done
	@echo "Processing preprocessed files..."
	@for f in src/quantum_language/*_preprocessed.pyx; do \
		if [ -f "$$f" ]; then \
			echo "  Annotating $$f"; \
			cython -a -3 "$$f" -o build/cython-annotate/$$(basename $${f%.pyx}.c) 2>/dev/null || true; \
		fi; \
	done
	@echo ""
	@ls -la build/cython-annotate/*.html 2>/dev/null || echo "No HTML files generated"
	@echo ""
	@echo "Annotation files generated in build/cython-annotate/"
	@echo "Open the .html files in a browser to see Python/C interaction points"
	@echo "(Yellow lines = Python C-API calls = potential optimization targets)"

.PHONY: profile-native
profile-native:
ifndef HAS_PYSPY
	@echo "ERROR: py-spy not found"
	@echo "Install with: pip install py-spy"
	@exit 1
endif
	@echo "Running py-spy with native frame support..."
	@echo "This requires elevated privileges on some systems."
	. $(VENV) && PYTHONPATH=src py-spy record --native -o profile.svg -- $(PYTHON) -c "\
		import quantum_language as ql; \
		c = ql.circuit(); \
		a = ql.qint(12345, width=16); \
		b = ql.qint(6789, width=16); \
		for _ in range(100): r = a + b"
	@echo "Flame graph saved to profile.svg"

.PHONY: profile-memory
profile-memory:
ifndef HAS_MEMRAY
	@echo "ERROR: memray not found (Linux/macOS only)"
	@echo "Install with: pip install memray"
	@exit 1
endif
	@echo "Running memray memory profiler..."
	. $(VENV) && PYTHONPATH=src memray run --native -o memray.bin -- $(PYTHON) -c "\
		import quantum_language as ql; \
		c = ql.circuit(); \
		for _ in range(100): \
			a = ql.qint(12345, width=16); \
			b = ql.qint(6789, width=16); \
			r = a + b"
	. $(VENV) && memray flamegraph memray.bin -o memory.html
	@echo "Memory flame graph saved to memory.html"

.PHONY: profile-cprofile
profile-cprofile:
	@echo "Running cProfile on quantum operations..."
	@. $(VENV) && PYTHONPATH=src $(PYTHON) -c "import cProfile, pstats, io; pr = cProfile.Profile(); pr.enable(); import quantum_language as ql; c = ql.circuit(); a = ql.qint(12345, width=16); b = ql.qint(6789, width=16); [a + b for _ in range(100)]; pr.disable(); s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats('cumulative').print_stats(30); print(s.getvalue())"

.PHONY: benchmark
benchmark:
	@echo "Running benchmark tests..."
	. $(VENV) && $(PYTEST) tests/benchmarks/ -v --benchmark-only

.PHONY: benchmark-compare
benchmark-compare:
	@echo "Running benchmarks with comparison to baseline..."
	. $(VENV) && $(PYTEST) tests/benchmarks/ -v --benchmark-only --benchmark-autosave
	@echo "Results saved. Compare with: pytest tests/benchmarks/ --benchmark-compare"

.PHONY: build-profile
build-profile:
	@echo "Building with Cython profiling enabled..."
	@echo "This enables function-level profiling in cProfile output."
	. $(VENV) && QUANTUM_PROFILE=1 $(PYTHON) setup.py build_ext --inplace
	@echo "Profiling build complete. Cython functions now visible in cProfile."

.PHONY: verify-optimization
verify-optimization:
	@echo "Verifying Cython optimizations..."
	@echo "1. Rebuilding package..."
	. $(VENV) && $(PYTHON) setup.py build_ext --inplace -q
	@echo "2. Regenerating annotations..."
	$(MAKE) profile-cython
	@echo "3. Running verification tests..."
	. $(VENV) && $(PYTEST) tests/python/test_cython_optimization.py -v
	@echo "4. Running benchmarks..."
	. $(VENV) && $(PYTEST) tests/benchmarks/ -v --benchmark-only
	@echo ""
	@echo "Optimization verification complete!"

# === Help ===

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  test             - Run pytest characterization tests"
	@echo "  memtest          - Run tests under Valgrind (requires valgrind)"
	@echo "  asan-test        - Build and run C backend with AddressSanitizer"
	@echo "  check            - Run pre-commit hooks on all files"
	@echo "  clean            - Remove test artifacts"
	@echo ""
	@echo "Profiling targets:"
	@echo "  profile-cython      - Generate Cython annotation HTML (run after optimizations)"
	@echo "  profile-native      - Run py-spy with native frames (requires py-spy)"
	@echo "  profile-memory      - Run memray memory profiler (requires memray)"
	@echo "  profile-cprofile    - Run cProfile on quantum operations"
	@echo "  benchmark           - Run pytest-benchmark tests"
	@echo "  benchmark-compare   - Run benchmarks and save for comparison"
	@echo "  build-profile       - Build with Cython profiling enabled"
	@echo "  verify-optimization - Full optimization verification (rebuild, annotate, test, benchmark)"
	@echo ""
	@echo "Tool availability:"
	@echo "  C compiler: $(if $(HAS_CC),$(CC),NOT FOUND)"
	@echo "  Valgrind:   $(if $(HAS_VALGRIND),found,NOT FOUND)"
	@echo "  py-spy:     $(if $(HAS_PYSPY),found,NOT FOUND)"
	@echo "  memray:     $(if $(HAS_MEMRAY),found,NOT FOUND)"
