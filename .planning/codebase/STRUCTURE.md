# Codebase Structure

**Analysis Date:** 2026-02-22

## Directory Layout

```
Quantum_Assembly/               # Project root
├── src/                        # Python package source (install root)
│   └── quantum_language/       # Main package
│       ├── __init__.py         # Public API re-exports
│       ├── _core.pyx/.pxd      # Global circuit state + C FFI declarations
│       ├── _gates.pyx/.pxd     # Low-level gate emission primitives
│       ├── qint.pyx/.pxd       # Quantum integer type (core)
│       ├── qint_arithmetic.pxi # Arithmetic ops included by qint.pyx
│       ├── qint_bitwise.pxi    # Bitwise ops included by qint.pyx
│       ├── qint_comparison.pxi # Comparison ops included by qint.pyx
│       ├── qint_division.pxi   # Division ops included by qint.pyx
│       ├── qint_preprocessed.pyx  # Build artifact (inlined .pxi)
│       ├── qbool.pyx/.pxd      # Quantum boolean (1-bit qint subclass)
│       ├── qarray.pyx/.pxd     # Quantum array type
│       ├── _qarray_utils.py    # Pure Python qarray utilities
│       ├── qint_mod.pyx/.pxd   # Modular integer type
│       ├── openqasm.pyx/.pxd   # OpenQASM 3.0 export
│       ├── compile.py          # @ql.compile decorator (capture-replay)
│       ├── grover.py           # Grover search algorithm
│       ├── oracle.py           # @ql.grover_oracle decorator
│       ├── diffusion.py        # Grover diffusion operator
│       ├── amplitude_estimation.py  # IQAE algorithm
│       ├── draw.py             # Circuit visualization (PIL)
│       ├── profiler.py         # cProfile context manager wrapper
│       └── state/              # State subpackage
│           ├── __init__.py
│           └── __init__.pxd
├── c_backend/                  # C quantum circuit backend
│   ├── include/                # Public headers
│   │   ├── types.h             # Core types (gate_t, circuit_t, etc.)
│   │   ├── circuit.h           # Main circuit API (aggregates all headers)
│   │   ├── gate.h              # Gate creation and add_gate()
│   │   ├── qubit_allocator.h   # Qubit lifecycle management
│   │   ├── circuit_stats.h     # Statistics queries
│   │   ├── circuit_output.h    # Print and OpenQASM export
│   │   ├── circuit_optimizer.h # Post-construction optimization passes
│   │   ├── optimizer.h         # Layer optimization (add_gate routing)
│   │   ├── arithmetic_ops.h    # QFT arithmetic dispatch
│   │   ├── toffoli_arithmetic_ops.h  # Toffoli arithmetic dispatch
│   │   ├── comparison_ops.h    # Comparison operations
│   │   ├── bitwise_ops.h       # Bitwise operations
│   │   ├── hot_path_add.h      # Hardcoded QFT addition dispatch
│   │   ├── hot_path_mul.h      # Hardcoded multiplication dispatch
│   │   ├── hot_path_xor.h      # Hardcoded XOR dispatch
│   │   ├── sequences.h         # Hardcoded gate sequences header
│   │   ├── toffoli_sequences.h # Toffoli hardcoded sequences header
│   │   ├── toffoli_addition_internal.h  # Internal Toffoli adder helpers
│   │   ├── QPU.h               # QPU-level operations
│   │   ├── Integer.h           # Integer register operations
│   │   ├── IntegerComparison.h # Integer comparison C API
│   │   ├── LogicOperations.h   # Logic gate operations
│   │   ├── execution.h         # run_instruction() and related
│   │   └── definition.h        # Backward compat alias for types.h
│   └── src/                    # C implementation files
│       ├── QPU.c               # QPU top-level operations
│       ├── Integer.c           # Integer register management
│       ├── IntegerAddition.c   # QFT-based addition
│       ├── IntegerComparison.c # Comparison circuits
│       ├── IntegerMultiplication.c  # QFT-based multiplication
│       ├── LogicOperations.c   # AND/OR/XOR circuits
│       ├── ToffoliAdditionCDKM.c    # CDKM ripple-carry adder
│       ├── ToffoliAdditionCLA.c     # Brent-Kung CLA adder
│       ├── ToffoliAdditionHelpers.c # Shared Toffoli helpers
│       ├── ToffoliMultiplication.c  # Toffoli-based multiplication
│       ├── circuit_allocations.c    # circuit_t memory management
│       ├── circuit_optimizer.c      # Post-construction optimization (cancel_inverse, merge)
│       ├── circuit_output.c    # Print and OpenQASM 3.0 export
│       ├── circuit_stats.c     # Gate count, depth, qubit count queries
│       ├── execution.c         # run_instruction() dispatcher
│       ├── gate.c              # Gate struct creation and add_gate()
│       ├── hot_path_add.c      # QFT addition hot path (width-dispatched)
│       ├── hot_path_add_toffoli.c   # Toffoli addition hot path
│       ├── hot_path_mul.c      # Multiplication hot path
│       ├── hot_path_xor.c      # XOR hot path
│       ├── optimizer.c         # Layer scheduling optimizer
│       ├── qubit_allocator.c   # Block-based qubit pool
│       └── sequences/          # Hardcoded per-width gate sequences
│           ├── add_seq_1.c ... add_seq_16.c      # QFT add sequences (widths 1-16)
│           ├── add_seq_dispatch.c                # Dispatch for QFT adds
│           ├── toffoli_add_seq_1.c ... _8.c      # Toffoli add sequences
│           ├── toffoli_decomp_seq_1.c ... _8.c   # MCX-decomposed Toffoli sequences
│           ├── toffoli_cq_inc_seq_1.c ... _8.c   # Classical-quantum increment sequences
│           ├── toffoli_clifft_qq_1.c ... _8.c    # Clifford+T CDKM QQ sequences
│           ├── toffoli_clifft_cqq_1.c ... _8.c   # Clifford+T CDKM CQQ sequences
│           ├── toffoli_clifft_cq_inc_1.c ... _8.c
│           ├── toffoli_clifft_ccq_inc_1.c ... _8.c
│           ├── toffoli_clifft_cdkm_dispatch.c
│           ├── toffoli_clifft_cla_qq_2.c ... _8.c  # Clifford+T BK-CLA sequences
│           ├── toffoli_clifft_cla_cqq_2.c ... _8.c
│           ├── toffoli_clifft_cla_cq_inc_2.c ... _8.c
│           ├── toffoli_clifft_cla_ccq_inc_2.c ... _8.c
│           └── toffoli_clifft_cla_dispatch.c
├── tests/                      # Test suite
│   ├── python/                 # Python integration tests (pytest)
│   │   ├── conftest.py
│   │   └── test_*.py           # ~30 test files (one per feature/phase)
│   ├── c/                      # C unit tests (Makefile-based)
│   │   ├── Makefile
│   │   ├── test_allocator_block.c
│   │   ├── test_comparison.c
│   │   ├── test_hot_path_add.c
│   │   ├── test_hot_path_mul.c
│   │   ├── test_hot_path_xor.c
│   │   └── test_reverse_circuit.c
│   ├── bugfix/                 # Regression tests for specific bug fixes
│   ├── benchmarks/             # Performance benchmarks (pytest-benchmark)
│   └── quick/                  # Ad-hoc quick-check scripts
├── scripts/                    # Utility scripts
├── benchmarks/                 # Benchmark results and tooling
│   └── results/
├── circuit-gen-results/        # Competitor comparison data
│   ├── qiskit/                 # Qiskit comparison circuits
│   ├── cirq/                   # Cirq comparison circuits
│   └── ...                     # Other frameworks (pytket, pennylane, etc.)
├── .planning/                  # GSD planning documents
│   ├── codebase/               # This document and sibling analysis docs
│   ├── milestones/             # Per-milestone phase plans (v1.0 through v4.0)
│   └── phases/                 # Loose phase plans
├── setup.py                    # Cython build configuration
├── pyproject.toml              # Build system, dependencies, ruff config
├── build_preprocessor.py       # .pxi include inliner (build-time tool)
├── pytest.ini                  # Test configuration
├── CMakeLists.txt              # Legacy CMake config (historical, not used for Python build)
├── Makefile                    # Convenience targets
├── Dockerfile                  # Container definition
└── main.c                      # Legacy C entry point (historical)
```

## Directory Purposes

**`src/quantum_language/`:**
- Purpose: The installable Python package. All user-facing code lives here.
- Contains: Cython `.pyx` sources, `.pxd` declaration files, pure Python modules, compiled `.so`/`.cpython-*.so` shared libraries (build artifacts committed for dev convenience)
- Key files: `__init__.py` (public API), `_core.pyx` (state + circuit class), `qint.pyx` (core quantum type)

**`c_backend/`:**
- Purpose: Pure C library implementing all quantum gate math. Never imported directly by Python — always linked into Cython extensions at build time.
- Contains: Headers in `include/`, implementation in `src/`, precomputed hardcoded gate sequences in `src/sequences/`
- Key files: `include/circuit.h` (main API header), `include/types.h` (all type definitions), `src/qubit_allocator.c` (memory management)

**`c_backend/src/sequences/`:**
- Purpose: Hardcoded gate sequences for specific qubit widths (1-16 for QFT additions, 1-8 for Toffoli). Avoids runtime computation by precomputing and storing optimal sequences.
- Generated: Manually authored / generated during optimization phases
- Contains: ~100 `.c` files, one per (algorithm, width) combination

**`tests/python/`:**
- Purpose: Primary test suite. Each file covers a feature area or milestone phase.
- Key files: `conftest.py` (shared fixtures), `test_grover.py`, `test_amplitude_estimation.py`, `test_qint_operations.py`

**`tests/c/`:**
- Purpose: C-level unit tests for allocator, hot paths, and circuit operations. Compiled independently via `Makefile`.
- Key files: `test_allocator_block.c`, `test_hot_path_add.c`

**`.planning/milestones/`:**
- Purpose: Phase-by-phase implementation plans from v1.0 through v4.0. Not code — planning documents only.
- Generated: No (committed planning artifacts)

**`build/`:**
- Purpose: setuptools build artifacts (compiled `.c` and `.so` files per Python version/platform)
- Generated: Yes
- Committed: No (in `.gitignore`)

**`circuit-gen-results/`:**
- Purpose: Benchmark circuits from competing frameworks (Qiskit, Cirq, pytket, etc.) used for gate count comparison
- Contains: Per-framework subdirectories with circuit files and notes

## Key File Locations

**Entry Points:**
- `src/quantum_language/__init__.py`: Public API — imports everything a user needs
- `src/quantum_language/_core.pyx`: Circuit class, global state, C FFI bridge

**Configuration:**
- `setup.py`: Cython build config, all C source lists, include paths, compiler flags
- `pyproject.toml`: Project metadata, dependencies, ruff linter config
- `pytest.ini`: Test runner configuration
- `build_preprocessor.py`: Build-time .pxi inliner

**Core Logic:**
- `src/quantum_language/qint.pyx`: Quantum integer — arithmetic, bitwise, comparison, context manager
- `src/quantum_language/compile.py`: Capture-replay decorator (`CompiledBlock`, `CompiledFunc`)
- `src/quantum_language/grover.py`: Grover search end-to-end (BBHT + exact)
- `src/quantum_language/oracle.py`: Oracle decorator and predicate synthesis
- `c_backend/src/hot_path_add.c`: QFT addition (width-dispatched to hardcoded sequences)
- `c_backend/src/ToffoliAdditionCDKM.c`: CDKM adder implementation
- `c_backend/src/qubit_allocator.c`: Qubit pool management

**Testing:**
- `tests/python/test_qint_operations.py`: Core qint operations
- `tests/python/test_grover.py`: Grover search integration tests
- `tests/python/test_amplitude_estimation.py`: IQAE tests
- `tests/python/conftest.py`: Shared pytest fixtures

## Naming Conventions

**Files:**
- Cython extension modules: `_name.pyx` (private/internal) or `name.pyx` (public type)
- Cython declaration files: same stem as `.pyx`, extension `.pxd`
- Cython include fragments: `qint_<feature>.pxi` (included into `qint.pyx`)
- Build artifacts: `name.c` (generated from `.pyx`), `name.cpython-NNN-<platform>.so`
- C source files: `PascalCase.c` for operations (e.g., `IntegerAddition.c`), `snake_case.c` for infrastructure (e.g., `qubit_allocator.c`)
- C header files: match source stem with `.h` extension
- Test files: `test_<feature>.py` (Python), `test_<feature>.c` (C)
- Sequence files: `<algorithm>_seq_<width>.c` or `toffoli_clifft_<variant>_<width>.c`

**Directories:**
- Package code: `src/<package_name>/` (PEP 517 src layout)
- Test categories: `tests/<type>/` (python, c, bugfix, benchmarks, quick)

**Functions/Types:**
- Public Python API: `snake_case` functions, `lowercase` class names (`qint`, `qbool`, `qarray`)
- C functions: `snake_case` (e.g., `allocator_alloc()`, `circuit_gate_count()`)
- C types: `snake_case_t` suffix (e.g., `circuit_t`, `gate_t`, `qubit_allocator_t`)
- C enums: `UPPER_CASE` variants (e.g., `ARITH_QFT`, `ARITH_TOFFOLI`)
- C macros: `UPPER_CASE` (e.g., `MAXQUBITS`, `ALLOCATOR_MAX_QUBITS`)
- Internal Python helpers: `_leading_underscore` (e.g., `_get_circuit()`, `_build_virtual_mapping()`)

## Where to Add New Code

**New Quantum Operation (e.g., new arithmetic operation on qint):**
- Primary code: `src/quantum_language/qint.pyx` (add method to `cdef class qint`) or a new `.pxi` file included by qint.pyx
- C implementation: `c_backend/src/NewOperation.c` + `c_backend/include/new_operation.h`
- Register C source in `setup.py` `c_sources` list
- Tests: `tests/python/test_<feature>.py`

**New Pure Python Algorithm (e.g., new quantum search variant):**
- Implementation: `src/quantum_language/new_algorithm.py`
- Export: Add import to `src/quantum_language/__init__.py` and to `__all__`
- Tests: `tests/python/test_new_algorithm.py`

**New Hardcoded Gate Sequence (e.g., for a new width):**
- Implementation: `c_backend/src/sequences/algorithm_seq_N.c`
- Register in dispatch file: `c_backend/src/sequences/algorithm_dispatch.c`
- Register in `setup.py` `c_sources` list

**New Cython Extension Module:**
- Create: `src/quantum_language/module_name.pyx` + `src/quantum_language/module_name.pxd`
- `setup.py` auto-discovers all `.pyx` files in `src/quantum_language/` — no manual registration needed
- Export from: `src/quantum_language/__init__.py`

**New C Infrastructure (allocator, optimizer, etc.):**
- Header: `c_backend/include/new_module.h`
- Source: `c_backend/src/new_module.c`
- Register in `setup.py` `c_sources` list
- Include in `c_backend/include/circuit.h` if part of the main circuit API

**Utilities and Helpers:**
- Pure Python helpers for a Cython module: `src/quantum_language/_module_utils.py`
- Build-time utilities: project root (alongside `build_preprocessor.py`)

## Special Directories

**`build/`:**
- Purpose: setuptools intermediate objects and final `.so` files per Python version/platform
- Generated: Yes
- Committed: No

**`venv/`:**
- Purpose: Local virtualenv for development dependencies
- Generated: Yes
- Committed: No

**`cmake-build-debug/`:**
- Purpose: Historical CMake build artifacts from early development; no longer part of active build system
- Generated: Yes (historical)
- Committed: Partially (directory structure committed but build artifacts excluded)

**`.planning/`:**
- Purpose: GSD project management — milestone plans, phase documents, codebase analysis docs
- Generated: No
- Committed: Yes

**`circuit-gen-results/`:**
- Purpose: Benchmark/comparison data against other quantum frameworks
- Generated: Partially (results gathered manually)
- Committed: Yes

---

*Structure analysis: 2026-02-22*
