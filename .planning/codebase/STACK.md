# Technology Stack

**Analysis Date:** 2026-01-25

## Languages

**Primary:**
- C (C23 standard) - Core quantum circuit backend and QPU operations in `Backend/` and `Execution/`
- Python (3.11+) - High-level interface and test scripts, frontend bindings
- Cython - Bridge between Python and C for quantum language operations in `python-backend/quantum_language.pyx`

**Secondary:**
- C# - QSharp integration found in `circuit-gen-results/qsharp/`
- QASM - Quantum assembly language files (`circuit.qasm`, `assembly.pqsm`)

## Runtime

**Environment:**
- GCC/Clang C compiler (CMake configured, C23 standard)
- Python 3.11+ runtime
- CPython with Cython compilation support

**Package Manager:**
- Python: pip (with `.venv/` virtual environment)
- C/C++: CMake 3.28+ for build system

## Frameworks

**Core:**
- CMake 3.28+ - Build system for C backend in `CMakeLists.txt`
- Cython 3.2.4 - Python-C integration for `quantum_language` module in `python-backend/setup.py`

**Quantum Computing:**
- Qiskit 0.43.2 - Quantum circuit parsing and execution framework in `Execution/src/run_circuit.py`
- Qiskit Aer 0.12.1 - Quantum circuit simulator backend
- Qiskit QASM3 Import 0.5.1 - OpenQASM 3 file parsing

**Testing:**
- pytest (installed in .venv) - Python test framework

**Build/Dev:**
- setuptools - Python package building for Cython extensions
- Cython 3.2.4 - Compiling `.pyx` files to C

## Key Dependencies

**Critical:**
- numpy 1.23.5 - Array operations for quantum state management in `python-backend/quantum_language.pyx`
- Qiskit (0.43.2) - OpenQASM parsing and circuit execution for testing/validation in `Execution/src/run_circuit.py`
- Qiskit Terra 0.24.1 - Core quantum circuits API
- Qiskit Aer 0.12.1 - High-performance quantum simulator

**Infrastructure:**
- Qiskit IBMQ Provider 0.20.2 - Cloud quantum computer access capability (optional)

## Configuration

**Environment:**
- C Backend: Configurable via CMake flags
  - `CMAKE_C_STANDARD` set to 23
  - Optimization flags: `-O3` (level 3 optimization)
  - Compile flags: `-flto` (link-time optimization), `-pthread` (threading)
- Python: Uses `.venv/` for isolation
- Default integer size: `INTEGERSIZE = 8` in `Backend/include/definition.h`

**Build:**
- `CMakeLists.txt` - Primary C backend build configuration
- `python-backend/setup.py` - Cython extension build configuration
- Compiler flags for performance: `-O3 -flto -pthread`

## Platform Requirements

**Development:**
- CMake 3.28+
- C compiler (GCC or Clang) with C23 support
- Python 3.11+
- Cython 3.2.4+
- Standard Unix/Linux development tools

**Production:**
- Compiled C shared library (`.so` file)
- Python 3.11+ runtime
- Quantum simulator backend (Aer or custom)
- Optional: Cloud access to quantum hardware (via Qiskit IBMQ)

## Docker

**Container:**
- Dockerfile exists but incomplete: requires Node.js, npm, and get-shit-done-cc package
- Status: Not production-ready

## Build Output

**C Backend:**
- Executable: `CQ_backend_improved` (from main.c)
- Compiles: Core QPU, gates, integer operations, logic operations, execution engine

**Python Backend:**
- Compiled extension: `quantum_language.cpython-311-darwin.so` (macOS example)
- Dynamically linked against C backend source files at build time

---

*Stack analysis: 2026-01-25*
