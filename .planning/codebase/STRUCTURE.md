# Codebase Structure

**Analysis Date:** 2026-02-22

## Directory Layout

```
Quantum_Assembly/
├── src/                          # Python package source
│   └── quantum_language/         # Main installable package
│       ├── __init__.py           # Public API surface
│       ├── _core.pyx             # Global circuit singleton, circuit class, option()
│       ├── _core.pxd             # Cython C-level declarations for _core
│       ├── _gates.pyx            # Low-level gate emission primitives
│       ├── qint.pyx              # Quantum integer cdef class (~2800 lines)
│       ├── qint.pxd              # Cython declarations for qint
│       ├── qint_arithmetic.pxi   # Arithmetic operators included into qint.pyx
│       ├── qint_bitwise.pxi      # Bitwise operators included into qint.pyx
│       ├── qint_comparison.pxi   # Comparison operators included into qint.pyx
│       ├── qint_division.pxi     # Division included into qint.pyx
│       ├── qbool.pyx             # Quantum boolean (1-bit qint subtype)
│       ├── qbool.pxd             # Cython declarations for qbool
│       ├── qarray.pyx            # NumPy-style array of qint/qbool
│       ├── qarray.pxd            # Cython declarations for qarray
│       ├── _qarray_utils.py      # Pure-Python array helpers (shape, flatten, reduce)
│       ├── qint_mod.pyx          # Modular arithmetic subclass of qint
│       ├── qint_mod.pxd          # Cython declarations for qint_mod
│       ├── openqasm.pyx          # OpenQASM 3.0 export (calls C circuit_to_qasm_string)
│       ├── openqasm.pxd          # Cython declarations for openqasm
│       ├── compile.py            # @ql.compile capture-and-replay decorator
│       ├── oracle.py             # @ql.grover_oracle decorator
│       ├── grover.py             # End-to-end Grover search algorithm
│       ├── diffusion.py          # Grover diffusion operator
│       ├── amplitude_estimation.py  # Iterative Quantum Amplitude Estimation (IQAE)
│       ├── draw.py               # Pixel-art circuit visualization
│       ├── profiler.py           # Gate-count profiling decorator
│       ├── _core.c               # Cython-generated C (do not edit)
│       ├── _core.cpython-*.so    # Compiled extension (multiple platform variants)
│       └── quantum_language.egg-info/
├── c_backend/                    # Pure C backend (no Python dependency)
│   ├── include/                  # Public headers
│   │   ├── types.h               # Foundation types (qubit_t, gate_t, sequence_t)
│   │   ├── circuit.h             # Main API header (aggregates all others)
│   │   ├── gate.h                # Gate constructors (x, cx, ccx, h, p, QFT, etc.)
│   │   ├── qubit_allocator.h     # Centralized qubit lifecycle management
│   │   ├── optimizer.h           # Layer-assignment and gate merging
│   │   ├── circuit_output.h      # Print and OpenQASM export
│   │   ├── circuit_stats.h       # Circuit statistics (depth, gate count)
│   │   ├── circuit_optimizer.h   # Post-construction optimization passes
│   │   ├── arithmetic_ops.h      # Width-parameterized add/mul operations
│   │   ├── comparison_ops.h      # Width-parameterized equality/ordering
│   │   ├── bitwise_ops.h         # Width-parameterized NOT/XOR/AND/OR
│   │   ├── toffoli_arithmetic_ops.h   # Toffoli-based arithmetic
│   │   ├── toffoli_sequences.h   # Toffoli sequence dispatch declarations
│   │   ├── sequences.h           # QFT sequence dispatch declarations
│   │   ├── hot_path_add.h        # Hot-path QFT addition (QQ/CQ)
│   │   ├── hot_path_mul.h        # Hot-path multiplication
│   │   ├── hot_path_xor.h        # Hot-path XOR
│   │   ├── execution.h           # run_instruction() declaration
│   │   ├── module_deps.md        # Dependency graph documentation
│   │   └── [legacy wrapper headers]  # QPU.h, Integer.h, etc. (backward compat)
│   └── src/                      # C implementations
│       ├── QPU.c                 # Minimal global sequence state
│       ├── gate.c                # Gate constructors and QFT circuits
│       ├── qubit_allocator.c     # Qubit allocation with freed-block reuse
│       ├── circuit_allocations.c # Circuit lifecycle (init_circuit, free_circuit)
│       ├── optimizer.c           # add_gate() layer-assignment logic
│       ├── circuit_output.c      # print_circuit(), circuit_to_qasm_string()
│       ├── circuit_stats.c       # Gate count, depth, qubit statistics
│       ├── circuit_optimizer.c   # cancel_inverse, merge optimization passes
│       ├── execution.c           # run_instruction() — applies sequences to circuit
│       ├── Integer.c             # Integer register operations
│       ├── IntegerAddition.c     # QFT-based addition implementation
│       ├── IntegerComparison.c   # Comparison circuit generation
│       ├── IntegerMultiplication.c  # QFT-based multiplication
│       ├── LogicOperations.c     # Bitwise operation implementations
│       ├── hot_path_add.c        # Optimized QFT addition dispatch
│       ├── hot_path_add_toffoli.c  # Optimized Toffoli addition dispatch
│       ├── hot_path_mul.c        # Optimized multiplication dispatch
│       ├── hot_path_xor.c        # Optimized XOR dispatch
│       ├── ToffoliAdditionCDKM.c # CDKM ripple-carry Toffoli adder
│       ├── ToffoliAdditionCLA.c  # Brent-Kung carry-lookahead Toffoli adder
│       ├── ToffoliAdditionHelpers.c  # Shared Toffoli addition utilities
│       ├── ToffoliMultiplication.c   # Toffoli-based multiplication
│       └── sequences/            # ~107 pre-generated C gate sequence files
│           ├── add_seq_1.c … add_seq_16.c      # QFT addition, widths 1-16
│           ├── add_seq_dispatch.c
│           ├── toffoli_add_seq_1.c … _8.c      # Toffoli CDKM, widths 1-8
│           ├── toffoli_add_seq_dispatch.c
│           ├── toffoli_decomp_seq_1.c … _8.c   # MCX-decomposed sequences
│           ├── toffoli_clifft_qq_1.c … _8.c    # Clifford+T QQ sequences
│           ├── toffoli_clifft_cla_qq_2.c … _8.c  # Clifford+T CLA sequences
│           └── [more Clifford+T/CLA variants]
├── tests/                        # All test files
│   ├── conftest.py               # Root conftest: verify_circuit and clean_circuit fixtures
│   ├── python/                   # Unit/integration tests for Python API
│   │   ├── conftest.py           # Python-test-specific fixtures
│   │   ├── test_grover.py        # Grover algorithm tests
│   │   ├── test_oracle.py        # Oracle decorator tests
│   │   ├── test_amplitude_estimation.py  # IQAE tests
│   │   ├── test_qint_operations.py
│   │   ├── test_qbool_operations.py
│   │   ├── test_variable_width.py
│   │   ├── test_openqasm_export.py
│   │   └── [28 more test files]
│   ├── c/                        # C backend unit tests
│   │   ├── test_allocator_block.c
│   │   ├── test_reverse_circuit.c
│   │   ├── test_hot_path_add.c
│   │   ├── test_hot_path_mul.c
│   │   ├── test_hot_path_xor.c
│   │   ├── test_comparison.c
│   │   └── Makefile
│   ├── test_compile.py           # Compile decorator tests (~93K, comprehensive)
│   ├── test_toffoli_addition.py  # Toffoli adder verification
│   ├── test_cla_addition.py      # CLA adder verification
│   ├── test_bitwise.py
│   ├── test_compare.py
│   ├── test_add.py, test_sub.py, test_mul.py, test_div.py, test_mod.py
│   ├── test_qarray.py, test_qarray_elementwise.py, test_qarray_mutability.py
│   ├── test_draw_data.py, test_draw_render.py
│   ├── conftest.py
│   └── verify_helpers.py, verify_init.py
├── scripts/                      # Code generation and benchmarking scripts
│   ├── generate_seq_all.py       # Generate all QFT sequence .c files
│   ├── generate_seq_1_4.py
│   ├── generate_seq_5_8.py
│   ├── generate_toffoli_seq.py   # Generate Toffoli sequence .c files
│   ├── generate_toffoli_clifft_cla.py
│   ├── generate_toffoli_clifft_cq_inc.py
│   ├── generate_toffoli_decomp_seq.py
│   ├── benchmark_eval.py
│   ├── benchmark_compare.py
│   ├── benchmark_sequences.py
│   ├── verify_circuit.py         # Standalone circuit verification utility
│   └── profile_memory_61.py
├── benchmarks/                   # Benchmark run results
│   └── results/
├── circuit-gen-results/          # Circuit generation output artifacts
├── Language/                     # Legacy quantum assembly language files
│   └── Quantum_Assembly/         # .qa source files and tests
├── Programming/                  # Scratch/exploratory programs
├── build/                        # Build artifacts (generated, not committed)
├── cmake-build-debug/            # CMake debug build (generated)
├── venv/                         # Virtual environment (not committed)
├── .planning/                    # Project planning documents
│   ├── MILESTONES.md, PROJECT.md, ROADMAP.md, STATE.md
│   ├── codebase/                 # Codebase analysis documents (this directory)
│   ├── phases/                   # Per-phase implementation plans
│   ├── milestones/               # Milestone audit documents
│   └── quick/                    # Quick investigation notes
├── setup.py                      # Cython build configuration (primary build file)
├── pyproject.toml                # Project metadata and tool config (ruff, build-system)
├── CMakeLists.txt                # CMake config for C-only builds/IDE integration
├── Makefile                      # Convenience targets (test, asan-test, memtest, check)
├── pytest.ini                    # Pytest configuration
├── build_preprocessor.py         # .pyx preprocessing before Cython compilation
├── main.c                        # C-only entry point for ASAN/debug testing
├── .clang-format                 # LLVM style clang-format config for C files
├── .pre-commit-config.yaml       # Pre-commit hooks (ruff, clang-format)
└── CLAUDE.md                     # Project-specific Claude guidance
```

## Directory Purposes

**`src/quantum_language/`:**
- Purpose: The installable Python package; the entire user-facing library
- Contains: Cython `.pyx` extension modules, `.pxd` declaration files, `.pxi` include fragments, pure-Python algorithm modules
- Key files: `__init__.py` (public API), `_core.pyx` (global state), `qint.pyx` (primary type)

**`c_backend/include/`:**
- Purpose: All public headers for the C circuit backend; include only `circuit.h` for full API
- Contains: Type definitions, function declarations, dependency documentation
- Key files: `types.h` (foundation), `circuit.h` (aggregator/main include), `arithmetic_ops.h`, `module_deps.md`

**`c_backend/src/`:**
- Purpose: C implementation files for the quantum circuit backend
- Contains: Gate arithmetic, circuit lifecycle, optimizer, output, qubit allocator, Toffoli arithmetic
- Key files: `execution.c` (run_instruction), `optimizer.c` (add_gate), `circuit_allocations.c` (init/free)

**`c_backend/src/sequences/`:**
- Purpose: Pre-generated gate sequence files for specific bit widths (avoids runtime sequence construction)
- Contains: ~107 auto-generated C files; should not be edited manually
- Generated by: Scripts in `scripts/generate_*.py`

**`tests/python/`:**
- Purpose: Primary Python unit and integration tests; run with `pytest tests/python/ -v`
- Contains: Tests for all public API features, algorithm correctness, circuit generation

**`tests/c/`:**
- Purpose: C backend unit tests; compiled and run independently via `tests/c/Makefile`
- Contains: Tests for qubit allocator, hot paths, reverse circuit

**`scripts/`:**
- Purpose: Code generation and benchmarking (not part of library runtime)
- Contains: Scripts that write `.c` files into `c_backend/src/sequences/`, benchmark harnesses

**`.planning/`:**
- Purpose: Project planning, phase tracking, milestone documentation
- Generated: No — committed planning documents
- Key file: `STATE.md` (current project state)

## Key File Locations

**Entry Points:**
- `src/quantum_language/__init__.py`: Library public API surface; start here for feature discovery
- `src/demo.py`: Demo script illustrating API usage patterns
- `main.c`: C-only ASAN/debug test entry point

**Configuration:**
- `setup.py`: Build configuration — lists all C sources, Cython modules, compiler flags
- `pyproject.toml`: Project metadata, `ruff` lint/format config, optional dependencies
- `pytest.ini`: Test discovery configuration
- `.clang-format`: LLVM style C formatting config
- `.pre-commit-config.yaml`: Pre-commit hooks (ruff for Python, clang-format for C)

**Core Logic:**
- `src/quantum_language/_core.pyx`: Global circuit state, `circuit` class, `option()`, all state accessors
- `src/quantum_language/qint.pyx`: Quantum integer with all operator implementations
- `c_backend/src/execution.c`: `run_instruction()` — the bridge between sequence dispatch and circuit building
- `c_backend/src/optimizer.c`: `add_gate()` — gate placement with layer-assignment logic
- `c_backend/include/circuit.h`: Main C API header; aggregates all other C headers

**Algorithm Files:**
- `src/quantum_language/compile.py`: `@ql.compile` capture-replay decorator
- `src/quantum_language/grover.py`: End-to-end Grover search
- `src/quantum_language/oracle.py`: `@ql.grover_oracle` decorator
- `src/quantum_language/amplitude_estimation.py`: IQAE algorithm

**Testing:**
- `tests/conftest.py`: Root fixture `verify_circuit` — full pipeline: ql API → QASM → Qiskit sim → assert
- `tests/python/conftest.py`: Python-unit-test fixtures
- `tests/c/Makefile`: C backend test build and run

## Naming Conventions

**Files:**
- Cython extension modules: `snake_case.pyx` (e.g., `qint_mod.pyx`, `_gates.pyx`)
- Cython declaration files: same name with `.pxd` extension
- Cython inline includes: `snake_case.pxi` (e.g., `qint_arithmetic.pxi`)
- Private/internal modules: prefixed with `_` (e.g., `_core.pyx`, `_gates.pyx`, `_qarray_utils.py`)
- C source files: `PascalCase.c` for high-level operations (e.g., `IntegerAddition.c`, `ToffoliAdditionCDKM.c`), `snake_case.c` for infrastructure (e.g., `circuit_allocations.c`, `qubit_allocator.c`)
- Generated sequence files: `{operation}_seq_{width}.c` (e.g., `add_seq_4.c`, `toffoli_clifft_cla_qq_6.c`)
- Test files: `test_{area}.py` (e.g., `test_grover.py`, `test_toffoli_addition.py`)

**Directories:**
- Python package: `snake_case` (`quantum_language`)
- C backend: flat `c_backend/` with `include/` and `src/` split

**C Types and Functions:**
- Types: `snake_case_t` suffix (e.g., `circuit_t`, `gate_t`, `qubit_allocator_t`)
- Functions: `snake_case` (e.g., `init_circuit`, `add_gate`, `run_instruction`)
- Operation functions: `{OPERAND_TYPES}_{operation}(bits, ...)` (e.g., `CQ_add`, `QQ_mul`, `cQQ_add`)
  - Prefix `C` = classical operand, `Q` = quantum operand, leading `c` = controlled

**Python/Cython:**
- Public API functions: `snake_case` (e.g., `to_openqasm`, `grover_oracle`)
- Internal state accessors in `_core.pyx`: `_get_{name}()` / `_set_{name}()` pattern
- Quantum types: lowercase class names (`qint`, `qbool`, `qarray`, `qint_mod`)
- Type annotations used in public algorithm signatures

## Where to Add New Code

**New Quantum Type:**
- Implementation: `src/quantum_language/{typename}.pyx` + `.pxd`
- Export: add to `src/quantum_language/__init__.py` imports and `__all__`
- Build: add `.pyx` module entry in `setup.py` `ext_modules` list
- Tests: `tests/python/test_{typename}_operations.py`

**New Quantum Algorithm (pure Python):**
- Implementation: `src/quantum_language/{algorithm_name}.py`
- Export: add to `src/quantum_language/__init__.py`
- Tests: `tests/python/test_{algorithm_name}.py`
- Uses `verify_circuit` fixture from `tests/conftest.py` for end-to-end validation

**New C Operation (arithmetic/bitwise):**
- Header: `c_backend/include/arithmetic_ops.h` or appropriate ops header
- Implementation: `c_backend/src/Integer{OperationType}.c` or new `{name}.c`
- Add source to `c_backend_sources` list in `setup.py`
- Declare in Cython: add `extern` declaration in `src/quantum_language/_core.pxd`
- Expose to Python via `_core.pyx` or the relevant `.pyx` type file

**New Pre-generated Sequences:**
- Write generator script in `scripts/generate_{name}.py`
- Output target: `c_backend/src/sequences/{name}_{width}.c`
- Add dispatch file: `c_backend/src/sequences/{name}_dispatch.c`
- Register all files in `setup.py` `c_sources` list

**New Test File:**
- Python verification test: `tests/test_{area}.py` (uses `verify_circuit` fixture, runs Qiskit)
- Python unit test: `tests/python/test_{area}.py` (uses `clean_circuit` fixture, no simulation)
- C backend test: `tests/c/test_{area}.c` + add to `tests/c/Makefile`

**New Script (benchmarking/generation):**
- Location: `scripts/{purpose}.py`
- Not part of library; not included in package install

## Special Directories

**`build/`:**
- Purpose: Cython-generated C files and compiled `.so` extension objects (build artifacts)
- Generated: Yes
- Committed: No (in `.gitignore`)

**`c_backend/src/sequences/`:**
- Purpose: Pre-generated hardcoded gate sequences; performance-critical, not human-maintained
- Generated: Yes, by `scripts/generate_*.py`
- Committed: Yes (generated output is committed for reproducible builds)

**`cmake-build-debug/`:**
- Purpose: CMake IDE integration build directory (CLion/VS Code)
- Generated: Yes
- Committed: No

**`venv/`:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No

**`.planning/`:**
- Purpose: Project management documents, phase plans, milestone audits
- Generated: No (hand-authored)
- Committed: Yes

---

*Structure analysis: 2026-02-22*
