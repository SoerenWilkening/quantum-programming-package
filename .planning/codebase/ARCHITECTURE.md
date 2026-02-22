# Architecture

**Analysis Date:** 2026-02-22

## Pattern Overview

**Overall:** Layered quantum compiler with Cython FFI bridge

**Key Characteristics:**
- Python user-facing API compiled to native extensions via Cython (.pyx files)
- C backend handles all circuit data structures and quantum gate arithmetic
- Global circuit singleton owned by `_core.pyx`; all quantum types inherit from `circuit`
- Gate sequences are pre-compiled and cached per bit-width; Python dispatches to C via `run_instruction`
- Verification pipeline exports OpenQASM 3.0 from C then simulates via Qiskit Aer

## Layers

**User API Layer:**
- Purpose: High-level quantum programming constructs exposed to end users
- Location: `src/quantum_language/__init__.py`
- Contains: `qint`, `qbool`, `qint_mod`, `qarray`, `circuit`, `compile`, `grover`, `amplitude_estimate`, `to_openqasm`, `draw_circuit`, `option`, `profile`
- Depends on: Cython extension layer
- Used by: End-user scripts, test files, `src/demo.py`

**Cython Extension Layer:**
- Purpose: Compiled Python/C bridge; implements quantum types as `cdef class` objects
- Location: `src/quantum_language/*.pyx`, `src/quantum_language/*.pxi`
- Contains:
  - `_core.pyx` — Global circuit singleton, `circuit` base class, `option()`, module-level state accessors
  - `qint.pyx` — Quantum integer (`cdef class qint(circuit)`), arithmetic/bitwise/comparison via included `.pxi` files
  - `qbool.pyx` — Single-bit quantum boolean
  - `qarray.pyx` — NumPy-style array of qint/qbool elements
  - `qint_mod.pyx` — Modular arithmetic subclass of qint
  - `openqasm.pyx` — Calls C `circuit_to_qasm_string()` and returns Python string
  - `_gates.pyx` — Low-level gate emission primitives (`emit_x`, `emit_h`, `emit_mcz`, etc.)
- Depends on: C backend (linked at build time), `_core.pyx` global state
- Used by: User API layer

**Algorithm Layer:**
- Purpose: Quantum algorithms built on top of the Cython types
- Location: `src/quantum_language/` (pure Python)
- Contains:
  - `compile.py` — `@ql.compile` capture-and-replay decorator with gate-level optimization
  - `oracle.py` — `@ql.grover_oracle` decorator (compute-phase-uncompute enforcement)
  - `grover.py` — End-to-end Grover search (oracle + diffusion + Qiskit simulation)
  - `diffusion.py` — Grover diffusion operator (X-MCZ-X pattern)
  - `amplitude_estimation.py` — Iterative Quantum Amplitude Estimation (IQAE)
  - `draw.py` — Pixel-art circuit visualization (requires Pillow)
  - `profiler.py` — Gate-count and depth profiling decorator
- Depends on: Cython extension layer, Qiskit (for simulation in `grover.py`, `amplitude_estimation.py`)
- Used by: User API layer, test files

**C Backend Layer:**
- Purpose: Efficient circuit data structures, gate arithmetic sequences, and optimization
- Location: `c_backend/src/`, `c_backend/include/`
- Contains: Circuit lifecycle, qubit allocator, QFT/Toffoli gate sequences, layer optimizer, OpenQASM exporter, Clifford+T decomposer
- Depends on: Nothing (pure C, no external libraries beyond libc)
- Used by: Cython extension layer (linked as compiled object files via `setup.py`)

**Hardcoded Sequence Layer:**
- Purpose: Pre-generated C gate sequences for specific bit widths (1-16); avoids runtime sequence construction overhead
- Location: `c_backend/src/sequences/`
- Contains: ~107 C files (QFT add, Toffoli CDKM, Toffoli CLA, Clifford+T variants), each encoding a fully unrolled gate sequence for one bit width
- Depends on: `types.h`, C backend headers
- Used by: Dispatch functions in `c_backend/src/` (e.g., `add_seq_dispatch.c`, `toffoli_add_seq_dispatch.c`)

## Data Flow

**Quantum Operation (e.g., `a + b`):**

1. User calls `a + b` on two `qint` objects in Python
2. `qint.__add__` (in `qint.pyx`) checks arithmetic mode (`ARITH_QFT` or `ARITH_TOFFOLI`) and controlled context
3. Calls the appropriate C function: `QQ_add(bits)` (QFT) or Toffoli equivalent; these return a cached `sequence_t*`
4. `run_instruction(sequence, qubit_array, invert, circuit)` in `execution.c` maps logical qubit indices to physical and adds all gates to the circuit via `add_gate()`
5. `add_gate()` in `optimizer.c` assigns each gate to the earliest available layer using occupancy tracking, merging commuting rotation gates where possible
6. The gate is stored in `circuit_t.sequence[layer][]`

**Circuit Export and Simulation:**

1. User calls `ql.to_openqasm()`
2. `openqasm.pyx` retrieves the global `circuit_t*` pointer from `_core.pyx` and passes it to `circuit_to_qasm_string()` in `circuit_output.c`
3. C function writes QASM 3.0 string (heap-allocated); Cython decodes and frees it
4. Test fixtures in `tests/conftest.py` load the QASM into Qiskit via `qiskit.qasm3.loads()`, simulate with `AerSimulator(method="statevector")`, and extract measurement counts

**Grover Search (`ql.grover()`):**

1. `grover.py` accepts a predicate function or decorated oracle
2. Optionally wraps predicate in `@grover_oracle` (from `oracle.py`)
3. Calls `ql.circuit()` to reset global state, applies Hadamard layer via `emit_h`
4. Iteratively applies oracle + `diffusion()` for `ceil(pi/4 * sqrt(N/M))` rounds
5. Exports QASM, simulates via Qiskit, parses measured bitstring, verifies classically

**State Management:**
- Single global `circuit_t*` owned by `_core.pyx` as a C-level module variable
- Python-level state (qubit counter, control context, scope stack) stored as module globals in `_core.pyx` with explicit getter/setter functions used by all other Cython modules
- `ql.circuit()` resets all global state and frees the old circuit

## Key Abstractions

**`circuit_t` (C struct):**
- Purpose: The central quantum circuit data structure
- Location: `c_backend/include/circuit.h`
- Contains: `gate_t**` sequence organized by layer, qubit occupancy matrix, `qubit_allocator_t*`, arithmetic mode flag, layer floor for gate placement
- Pattern: Allocated via `init_circuit()`, freed via `free_circuit()`. Python holds pointer as `unsigned long long`

**`sequence_t` (C struct):**
- Purpose: A pre-compiled gate sequence for one operation at one bit width
- Location: `c_backend/include/types.h`
- Pattern: Returned by functions like `CQ_add(bits, value)`, `QQ_mul(bits)`. Results are cached by width — DO NOT FREE the returned pointer. Applied to physical qubits via `run_instruction()`

**`qint` (Cython cdef class):**
- Purpose: Quantum integer; primary user-facing type; inherits from `circuit` to participate in context manager protocol
- Location: `src/quantum_language/qint.pyx`
- Pattern: Allocates contiguous qubits on construction via `allocator_alloc()`. Arithmetic operators call C backend functions, then `run_instruction()`. Destructor may inject uncomputation gates

**`@ql.compile` decorator:**
- Purpose: Capture gate sequences on first call, replay with qubit remapping on subsequent calls
- Location: `src/quantum_language/compile.py`
- Pattern: Uses `extract_gate_range()` and `inject_remapped_gates()` (C-level functions exposed via `_core.pyx`). Supports `inverse=True` variant and `key=` function for cache invalidation

**`qubit_allocator_t` (C struct):**
- Purpose: Centralized qubit lifecycle manager with freed-qubit reuse
- Location: `c_backend/include/qubit_allocator.h`, `c_backend/src/qubit_allocator.c`
- Pattern: Block-based free-list with adjacent-block coalescing. Prevents runaway allocation at `ALLOCATOR_MAX_QUBITS = 8192`

## Entry Points

**Library Import:**
- Location: `src/quantum_language/__init__.py`
- Triggers: Python `import quantum_language as ql`
- Responsibilities: Re-exports all public API symbols from Cython extensions and pure-Python modules

**Circuit Reset:**
- Location: `src/quantum_language/_core.pyx`, `circuit.__init__()`
- Triggers: `ql.circuit()` call
- Responsibilities: Frees old `circuit_t*`, calls `init_circuit()`, resets all Python globals, clears `@ql.compile` caches

**Build Entry Point:**
- Location: `setup.py`
- Triggers: `python setup.py build_ext --inplace`
- Responsibilities: Runs `build_preprocessor.py` to preprocess `.pyx` files, then Cythonizes all `.pyx` modules, compiling them with all C backend sources as linked object files with `-O3 -pthread`

**Standalone C Entry Point (legacy/testing):**
- Location: `main.c`
- Triggers: Direct compilation with gcc/clang
- Responsibilities: Runs raw C backend tests without Python layer (used with ASAN targets in `Makefile`)

## Error Handling

**Strategy:** Exceptions propagate from C to Cython to Python via return-value checks and explicit `RuntimeError`/`ValueError` raises

**Patterns:**
- C functions returning `NULL` pointers trigger `RuntimeError` in the Cython layer (e.g., `openqasm.pyx` checks `c_str == NULL`)
- `ql.option()` raises `ValueError` for unknown keys or wrong value types
- `@ql.compile` raises `ValueError` if trying to invert a measurement gate
- `ql.grover()` raises `ValueError` for invalid oracle types and warns if solution not found classically
- Test verification pipeline (`tests/conftest.py`) includes QASM text in exception messages for debugging

## Cross-Cutting Concerns

**Logging:** No structured logging; `print()` used in debug paths and some C `printf()` in circuit visualization (`circuit_output.c`)

**Validation:** Gate-level: `add_gate()` enforces qubit occupancy constraints and layer assignment. Python-level: `option()`, `qint.__init__()`, and oracle decorators perform argument validation.

**Authentication:** Not applicable (local library, no network layer)

**Controlled Context:** Cross-cutting pattern: when user code runs inside `with qbool_variable:`, the `_controlled` and `_control_bool` globals in `_core.pyx` are set. All gate emission functions in `_gates.pyx` check these to emit controlled variants (CX instead of X, etc.)

**Arithmetic Mode:** `ql.option('fault_tolerant', True/False)` and `ql.option('cla', True/False)` toggle between QFT-based rotations and Toffoli-based (CDKM ripple-carry or Brent-Kung CLA) arithmetic globally, stored in `circuit_t.arithmetic_mode` and `circuit_t.cla_override`

---

*Architecture analysis: 2026-02-22*
