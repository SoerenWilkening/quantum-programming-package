# Technology Stack

**Analysis Date:** 2026-02-22

## Languages

**Primary:**
- Python 3.11+ - Quantum language frontend, API layer, test suite (`src/quantum_language/`)
- C (C23 standard) - High-performance quantum circuit backend (`c_backend/src/`, `c_backend/include/`)
- Cython 3.x - Python/C bridge; `.pyx`/`.pxd` files compiled to `.so` extensions (`src/quantum_language/*.pyx`)

**Secondary:**
- Q# - Reference/benchmarking only; legacy comparison artifact (`circuit-gen-results/qsharp/`)
- C# (.NET 6 / Microsoft.Quantum.Sdk 0.28) - Q# host runner, reference only (`circuit-gen-results/qsharp/Program.cs`, `QuantumProject.csproj`)

## Runtime

**Environment:**
- CPython 3.13.11 (venv at `venv/`, managed via `python3 -m venv`)
- Minimum required: Python 3.11 (enforced by `pyproject.toml` `requires-python = ">=3.11"`)

**Package Manager:**
- pip (via `venv`)
- Lockfile: Not present — dependencies declared in `pyproject.toml` and `setup.py`

## Frameworks

**Core:**
- Cython 3.x (>=3.0.11,<4.0) - Compiles `.pyx` source into C extensions that bridge Python to the C backend; configured in `setup.py` via `cythonize()`
- setuptools (>=61.0) + wheel - Build backend declared in `pyproject.toml` `[build-system]`

**Testing:**
- pytest 9.0.2 - Test runner; config in `pytest.ini`; test path `tests/python/`
- pytest-timeout 2.4.0 - Test timeout enforcement
- pytest-benchmark (optional, `profiling` extra) - Performance regression tests in `tests/benchmarks/`

**Build/Dev:**
- CMake 3.28+ - Legacy C standalone build (`CMakeLists.txt`); not used for the Cython package build
- GNU Make / clang - C test compilation in `tests/c/Makefile`; Makefile at root provides convenience targets
- ruff >=0.1.0 - Python linter and formatter; configured in `pyproject.toml` `[tool.ruff]`; line length 100, target `py311`
- pre-commit >=3.0 - Enforces ruff (lint + format) and clang-format v19 on all commits (`.pre-commit-config.yaml`)
- clang-format v19.1.6 - Auto-formats all C/C++ files on commit (`.pre-commit-config.yaml`)

## Key Dependencies

**Critical:**
- `numpy>=1.24` (installed: 2.4.2) - Array ops in `compile.py`, `draw.py`; listed in `pyproject.toml` core deps
- `Pillow>=9.0` - Circuit rendering to PNG/image; used in `src/quantum_language/draw.py` (`from PIL import Image, ImageDraw, ImageFont`)
- `qiskit>=1.0` (installed: 2.3.0) - OpenQASM 3.0 circuit loading and simulation; optional `verification` extra; lazy-imported inside `grover.py` and `amplitude_estimation.py`
- `qiskit_aer 0.17.2` - `AerSimulator` backend for statevector simulation; used with `max_parallel_threads=4` limit
- `scipy 1.17.0` - `scipy.stats.beta` for IQAE confidence intervals in `src/quantum_language/amplitude_estimation.py`

**Infrastructure:**
- `openqasm3 1.0.1` - OpenQASM 3 parsing support (pulled in by qiskit)
- `antlr4-python3-runtime 4.13.2` - Grammar runtime for OpenQASM parser
- `rustworkx 0.17.1` - Qiskit graph dependency
- `psutil 7.2.2` - Process/memory utilities (qiskit_aer dependency)
- `dill 0.4.1` - Extended pickle (qiskit dependency)

**Profiling (optional extras):**
- `line-profiler>=5.0.0` - Function-level profiling
- `snakeviz>=2.2.2` - cProfile viewer
- `memray>=1.19.1` (non-Windows) - Memory profiler; `make profile-memory` target
- `py-spy>=0.4.1` (non-Windows) - Native flame graphs; `make profile-native` target
- `scalene>=2.1.3` - CPU+memory profiler

## Configuration

**Environment:**
- No `.env` files detected in project root
- Simulation limits are enforced in code: max 17 qubits, `max_parallel_threads=4` for `AerSimulator` (see `src/quantum_language/grover.py:265`, `src/quantum_language/amplitude_estimation.py:189`)
- Build mode flags via env vars: `QUANTUM_PROFILE=1` enables Cython function-level profiling; `CYTHON_DEBUG=1` re-enables bounds/wraparound checks

**Build:**
- `pyproject.toml` - PEP 517/518 build system and project metadata
- `setup.py` - Cython extension discovery and compilation; preprocesses `.pxi` include files via `build_preprocessor.py`
- `build_preprocessor.py` - Inlines `.pxi` files into `*_preprocessed.pyx` before Cython compilation (Cython 3.x `include` directive workaround)
- `CMakeLists.txt` - Legacy standalone C executable build (C23, `-O3`)
- Compiled `.so` files checked into source: `src/quantum_language/*.cpython-{311,313}-*.so` for macOS and Linux x86_64

**Compiler flags:**
- Python extensions: `-O3 -pthread` (LTO disabled; see comment in `setup.py`)
- C tests: `-Wall -Wextra -g -O2 -std=c23` with optional `-fsanitize=address` (ASan)

## Platform Requirements

**Development:**
- macOS or Linux (Pillow, memray, py-spy, scalene have non-Windows guards)
- GCC or Clang (auto-detected in root `Makefile`)
- Valgrind (optional; memory leak checking via `make memtest`)
- Python 3.11+ with pip + venv

**Production:**
- Not applicable — this is a library/framework package (`quantum_language`) installed via `pip install -e .`
- Distributed as compiled Cython extensions (`.so` files)
- Supports CPython 3.11 and 3.13 on macOS (darwin) and Linux x86_64 (pre-built `.so` binaries included)

---

*Stack analysis: 2026-02-22*
