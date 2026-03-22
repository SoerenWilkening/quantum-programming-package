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
HAS_LCOV := $(shell command -v lcov 2>/dev/null)

# === Test Targets ===

.PHONY: test
test:
	@echo "Running Python characterization tests..."
	. $(VENV) && $(PYTEST) tests/python -v --tb=short

.PHONY: test-docker
test-docker:
	@echo "Running tests with process isolation (for memory-limited environments)..."
	. $(VENV) && MALLOC_TRIM_THRESHOLD_=0 $(PYTEST) tests/python -v --tb=short --forked -m "not slow"

.PHONY: test-memray
test-memray:
	@echo "Running tests with memray memory limits (512 MB per test)..."
	. $(VENV) && $(PYTEST) tests/python -v --tb=short --memray

# === Coverage ===

.PHONY: coverage
coverage:
	@echo "=== Coverage Pipeline ==="
	@mkdir -p reports/coverage
	@echo "1. Building with coverage instrumentation..."
	. $(VENV) && QUANTUM_COVERAGE=1 $(PYTHON) setup.py build_ext --inplace --force
	@echo "2. Running tests with coverage..."
ifdef HAS_LCOV
	. $(VENV) && $(PYTEST) tests/python -v --cov=quantum_language --cov-report=json:reports/coverage/coverage.json --cov-report=lcov:reports/coverage/python.lcov --cov-report=html:reports/coverage/html
	@echo "3. Capturing C coverage with lcov..."
	lcov --capture --directory . --output-file reports/coverage/c.lcov --no-external
	@echo "4. Merging Python and C coverage..."
	lcov -a reports/coverage/python.lcov -a reports/coverage/c.lcov -o reports/coverage/combined.lcov
	@echo "5. Generating unified HTML report..."
	genhtml reports/coverage/combined.lcov --output-directory reports/coverage/html
else
	@echo "WARNING: lcov not found -- C coverage will not be included."
	@echo "         Install lcov for unified Python+C coverage reports."
	. $(VENV) && $(PYTEST) tests/python -v --cov=quantum_language --cov-report=json:reports/coverage/coverage.json --cov-report=html:reports/coverage/html
endif
	@echo ""
	@echo "Coverage report: reports/coverage/html/index.html"

.PHONY: coverage-clean
coverage-clean:
	rm -rf reports/
	find . -name '*.gcda' -delete 2>/dev/null || true
	find . -name '*.gcno' -delete 2>/dev/null || true

# === Code Generation ===

.PHONY: generate-sequences
generate-sequences:
	@echo "Regenerating all hardcoded sequence C files..."
	@echo "1/5: QFT addition sequences (widths 1-16)..."
	$(PYTHON) scripts/generate_seq_all.py
	@echo "2/5: Toffoli CDKM sequences (widths 1-8)..."
	$(PYTHON) scripts/generate_toffoli_seq.py
	@echo "3/5: Toffoli MCX-decomposed sequences (widths 1-8)..."
	$(PYTHON) scripts/generate_toffoli_decomp_seq.py
	@echo "4/5: Clifford+T CQ/CCQ increment sequences (widths 1-8)..."
	$(PYTHON) scripts/generate_toffoli_clifft_cq_inc.py
	@echo "5/5: Clifford+T BK CLA sequences (widths 2-8)..."
	$(PYTHON) scripts/generate_toffoli_clifft_cla.py
	@echo "All sequences regenerated successfully."

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

# === Static Analysis ===

HAS_CPPCHECK := $(shell command -v cppcheck 2>/dev/null)
HAS_CLANG_TIDY := $(shell command -v clang-tidy 2>/dev/null)

.PHONY: cppcheck
cppcheck:
ifndef HAS_CPPCHECK
	@echo "ERROR: cppcheck not found"
	@echo "Install with: sudo apt-get install cppcheck"
	@exit 1
endif
	@echo "Running cppcheck static analysis on C backend..."
	cppcheck --enable=all --inconclusive \
		--suppressions-list=c_backend/suppressions.txt \
		--suppress=missingIncludeSystem \
		-I c_backend/include \
		--std=c11 \
		--error-exitcode=1 \
		c_backend/src/ c_backend/include/
	@echo "cppcheck: PASSED (zero findings)"

.PHONY: clang-tidy
clang-tidy:
ifndef HAS_CLANG_TIDY
	@echo "ERROR: clang-tidy not found"
	@echo "Install with: sudo apt-get install clang-tidy"
	@exit 1
endif
	@echo "Running clang-tidy on C backend..."
	clang-tidy \
		--config-file=c_backend/.clang-tidy \
		c_backend/src/*.c \
		-- -I c_backend/include -std=c11
	@echo "clang-tidy: complete"

.PHONY: static-analysis
static-analysis: cppcheck clang-tidy
	@echo "All static analysis checks complete."

# === Cleanup ===

.PHONY: clean
clean:
	rm -rf build/test_runner_asan
	rm -f valgrind-output.log
	rm -f profile.svg memray.bin memory.html
	rm -rf reports/
	find . -name '*.gcda' -delete 2>/dev/null || true
	find . -name '*.gcno' -delete 2>/dev/null || true

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
	@echo "  test-docker      - Run tests with process isolation (for memory-limited containers)"
	@echo "  memtest          - Run tests under Valgrind (requires valgrind)"
	@echo "  asan-test        - Build and run C backend with AddressSanitizer"
	@echo "  check            - Run pre-commit hooks on all files"
	@echo "  cppcheck         - Run cppcheck static analysis on C backend"
	@echo "  clang-tidy       - Run clang-tidy on C backend"
	@echo "  static-analysis  - Run all static analysis (cppcheck + clang-tidy)"
	@echo "  clean            - Remove test artifacts"
	@echo ""
	@echo "Coverage targets:"
	@echo "  coverage         - Build with instrumentation, run tests with coverage, generate HTML report"
	@echo "  coverage-clean   - Remove coverage reports and gcov artifacts"
	@echo ""
	@echo "Code generation targets:"
	@echo "  generate-sequences - Regenerate all hardcoded sequence C files (QFT, Toffoli, Clifford+T)"
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
	@echo "  lcov:       $(if $(HAS_LCOV),found,NOT FOUND (C coverage unavailable))"
	@echo "  cppcheck:   $(if $(HAS_CPPCHECK),found,NOT FOUND)"
	@echo "  clang-tidy: $(if $(HAS_CLANG_TIDY),found,NOT FOUND)"
