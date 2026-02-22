# Technology Stack

**Analysis Date:** 2026-02-22

## Languages

**Primary:**
- C (C23 standard) - Core quantum circuit backend: gate generation, qubit allocation, arithmetic sequences, circuit optimization. Located in `c_backend/src/` and `c_backend/include/`. Compiled flags: `-O3 -pthread`.
- Python 3.13 - Public API layer, algorithm implementations (Grover, IQAE, diffusion), test suite, and build tooling. Located in `src/quantum_language/`.
- Cython >= 3.0.11, < 4.0 - Bridge between Python API and C backend. All `.pyx` files in `src/quantum_language/` compile to C extension modules (`.so`). Compiled with `language_level="3"`, `embedsignature=True`.

**Secondary:**
- C# / Q# (reference only) - Microsoft Q# reference implementation in `circuit-gen-results/qsharp/`. Targets .NET 6.0 with `Microsoft.Quantum.Sdk 0.28`. Not part of active build.
- JavaScript/Node.js - Only in `Dockerfile` to install `get-shit-done-cc` tooling. Not part of the quantum framework.

## Runtime

**Environment:**
- Python 3.13.11 (venv at `venv/`, using `/usr/local/opt/python@3.13/bin/python3.13`)
- Minimum supported: Python 3.11 (enforced in `pyproject.toml` via `requires-python = ">=3.11"`)

**Package Manager:**
- pip (standard Python); virtual environment at `venv/`
- No lockfile present — `pyproject.toml` uses version ranges (e.g., `numpy>=1.24`, `qiskit>=1.0`)

## Frameworks

**Core:**
- setuptools >= 61.0 - Package build backend, declared in `pyproject.toml` `[build-system]`
- Cython >= 3.0.11, < 4.0 - Auto-discovers all `src/quantum_language/**/*.pyx` files; handles `.pxi` include inlining via `build_preprocessor.py`

**Testing:**
- pytest 9.0.2 - Test runner; configured in `pytest.ini` with `testpaths = tests/python`, `--strict-markers`, `--tb=short`
- pytest-timeout 2.4.0 - Per-test timeouts
- pytest-benchmark (optional profiling extra) - Performance benchmarking under `tests/benchmarks/`

**Build/Dev:**
- GNU Make + `Makefile` - Convenience targets: `test`, `memtest` (Valgrind), `asan-test` (AddressSanitizer), `check` (pre-commit), profiling targets
- CMake 3.28+ + `CMakeLists.txt` - Legacy standalone C executable build (`CQ_backend_improved`); not used for Python package
- clang-format v19.1.6 (via pre-commit) - C/C++ code formatting; config in `.clang-format` (LLVM style, `IndentWidth: 4`, `ColumnLimit: 100`)
- Ruff 0.9.0 (via pre-commit) - Python linting (E, F, W, I, B, C4, UP rules) and formatting (double quotes, spaces); `line-length = 100`, `target-version = "py311"`
- pre-commit - Hook config in `.pre-commit-config.yaml`: ruff linter+formatter (Python), clang-format (C/C++)

**Profiling (optional `[profiling]` extra):**
- line-profiler >= 5.0.0
- snakeviz >= 2.2.2
- memray >= 1.19.1 (Linux/macOS only)
- py-spy >= 0.4.1 (Linux/macOS only)
- scalene >= 2.1.3 (Linux/macOS only)

## Key Dependencies

**Critical (always required at runtime):**
- numpy 2.4.2 - Qubit index arrays (`np.zeros(64, dtype=np.uint32)`), used in `src/quantum_language/compile.py`, `src/quantum_language/draw.py`, `src/quantum_language/_core.pyx`
- Pillow >= 9.0 - Circuit visualization renderer (`src/quantum_language/draw.py`); uses `PIL.Image`, `PIL.ImageDraw`, `PIL.ImageFont`. Declared as `install_requires` in `setup.py`.

**Verification (optional `[verification]` extra):**
- qiskit 2.3.0 - OpenQASM 3.0 parsing (`qiskit.qasm3.loads`) and circuit transpilation. Imported lazily in `src/quantum_language/grover.py` and `src/quantum_language/amplitude_estimation.py`.
- qiskit-aer 0.17.2 - `AerSimulator` for circuit simulation. Always invoked with `max_parallel_threads=4` per project memory constraint. Used in `tests/conftest.py`, `src/quantum_language/grover.py`, `src/quantum_language/amplitude_estimation.py`.
- qiskit_qasm3_import 0.6.0 - OpenQASM 3.0 loader (transitively required by `qiskit.qasm3`).
- scipy 1.17.0 - `scipy.stats.beta.ppf` for Clopper-Pearson confidence intervals in IQAE algorithm (`src/quantum_language/amplitude_estimation.py`).

**Installed in venv (transitive):**
- rustworkx 0.17.1 (Qiskit graph library)
- openqasm3 1.0.1 (OpenQASM 3 parser)
- antlr4-python3-runtime 4.13.2 (parser runtime)
- psutil 7.2.2

**Build-time only:**
- Cython >= 3.0.11, < 4.0 - Not needed at runtime
- `build_preprocessor.py` (project-local script) - Inlines `.pxi` include files into `*_preprocessed.pyx` before Cython compilation

## Configuration

**Environment:**
- `QUANTUM_PROFILE=1` - Enables Cython function-level profiling (`profile=True`, `linetrace=True`, `-DCYTHON_TRACE=1`) in `setup.py`
- `CYTHON_DEBUG=1` - Enables safety checks in Cython build (`boundscheck`, `wraparound`, `initializedcheck`) in `setup.py`
- No `.env` file or runtime secrets detected

**Build:**
- `pyproject.toml` - Build system declaration, project metadata, dependency lists, Ruff config
- `setup.py` - Cython extension discovery and compilation; handles preprocessed `.pyx` files, all shared C sources from `c_backend/`, compiler flags (`-O3 -pthread`)
- `CMakeLists.txt` - Legacy CMake build for standalone C binary (not used for Python package)
- `Makefile` - Developer convenience targets for test, profiling, and memory analysis
- `.clang-format` - C formatting rules
- `.pre-commit-config.yaml` - Pre-commit hook declarations
- `pytest.ini` - pytest settings: `testpaths = tests/python`, `pythonpath = src`, strict markers

## Platform Requirements

**Development:**
- C compiler: gcc or clang (auto-detected by Makefile)
- Valgrind (optional, for `make memtest`)
- py-spy (optional, for `make profile-native`)
- memray (optional, for `make profile-memory`; Linux/macOS only)

**Production:**
- Library/framework only; no server deployment
- Precompiled `.so` artifacts committed for CPython 3.11 and 3.13 on darwin (macOS) and x86_64-linux-gnu: e.g., `src/quantum_language/_core.cpython-313-darwin.so`, `src/quantum_language/_core.cpython-313-x86_64-linux-gnu.so`
- Install via `pip install -e .` from project root

---

*Stack analysis: 2026-02-22*
