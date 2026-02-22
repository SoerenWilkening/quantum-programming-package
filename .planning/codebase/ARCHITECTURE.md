# Architecture

**Analysis Date:** 2026-02-22

## Pattern Overview

**Overall:** Layered Quantum Circuit Compiler with C Backend + Cython Bridge

**Key Characteristics:**
- Python user-facing API (quantum types, algorithms) built atop compiled Cython extensions
- Cython extensions (`.pyx`) act as an FFI bridge calling into a pure C gate-generation backend
- Circuit state is process-global (one active circuit at a time), managed via module-level C pointers in `_core.pyx`
- Operator overloading on `qint`/`qbool`/`qarray` drives implicit circuit construction — user writes arithmetic, gates emit automatically
- Gate capture-and-replay (`@ql.compile`) virtualizes qubit indices for reusable compiled quantum subroutines

## Layers

**User API Layer:**
- Purpose: Public Python API consumed by end users
- Location: `src/quantum_language/__init__.py`
- Contains: Re-exports from all submodules, convenience wrappers (`array()`, `draw_circuit()`, `all()`, `any()`, `parity()`)
- Depends on: Cython extension modules, pure Python modules
- Used by: User scripts, tests

**Quantum Type Layer (Cython):**
- Purpose: Quantum integer/boolean/array types with operator overloading that emit gates as side effects
- Location: `src/quantum_language/qint.pyx`, `src/quantum_language/qbool.pyx`, `src/quantum_language/qarray.pyx`, `src/quantum_language/qint_mod.pyx`
- Contains: `cdef class qint(circuit)`, `cdef class qbool(qint)`, `cdef class qarray`, `cdef class qint_mod`
- Depends on: `_core.pyx` (global circuit state, C function declarations), `c_backend` C sources
- Used by: User code, algorithm layer, `compile.py`

**Core State Module (Cython):**
- Purpose: Global circuit state keeper and C FFI declarations; single source of truth for circuit pointer
- Location: `src/quantum_language/_core.pyx`, `src/quantum_language/_core.pxd`
- Contains: `cdef circuit_t *_circuit`, control-flow globals (`_controlled`, `_control_bool`, `_list_of_controls`), `cdef class circuit`, `option()`, `extract_gate_range()`, `inject_remapped_gates()`, `reverse_instruction_range()`
- Depends on: `c_backend` C sources (linked at compile time)
- Used by: All other Cython modules via `cimport`; pure Python modules via `from ._core import`

**Gate Emission Layer (Cython):**
- Purpose: Low-level gate emission primitives (H, X, P, MCZ, etc.) called by qint operations and algorithm modules
- Location: `src/quantum_language/_gates.pyx`, `src/quantum_language/_gates.pxd`
- Contains: `emit_h()`, `emit_x()`, `emit_p()`, `emit_mcz()`, etc.
- Depends on: `_core.pyx` circuit state
- Used by: `qint.pyx`, `diffusion.py`, `oracle.py`, `grover.py`

**Algorithm Layer (Pure Python):**
- Purpose: High-level quantum algorithm implementations built atop the type layer
- Location: `src/quantum_language/compile.py`, `src/quantum_language/grover.py`, `src/quantum_language/oracle.py`, `src/quantum_language/diffusion.py`, `src/quantum_language/amplitude_estimation.py`
- Contains: `@ql.compile` decorator, `ql.grover()`, `ql.grover_oracle()`, `ql.diffusion()`, `ql.amplitude_estimate()`
- Depends on: `_core` (gate injection/extraction), `qint`/`qbool`/`qarray` types
- Used by: User code

**OpenQASM Export Layer (Cython):**
- Purpose: Serialize current circuit to OpenQASM 3.0 string for simulation
- Location: `src/quantum_language/openqasm.pyx`, `src/quantum_language/openqasm.pxd`
- Contains: `to_openqasm()` — calls `circuit_to_qasm_string()` from C backend
- Depends on: `c_backend/src/circuit_output.c`
- Used by: `grover.py`, `amplitude_estimation.py` (for Qiskit simulation)

**C Backend:**
- Purpose: High-performance quantum gate sequence generation, circuit data structures, qubit allocation, optimization, and arithmetic
- Location: `c_backend/src/`, `c_backend/include/`
- Contains: `circuit_t` struct, `gate_t`, `qubit_allocator_t`, arithmetic operations (QFT-based and Toffoli-based), hardcoded gate sequences for widths 1-16, circuit optimizer
- Depends on: Nothing (pure C, no external dependencies beyond libc)
- Used by: All Cython extensions (linked via `setup.py`)

**Visualization Layer (Pure Python):**
- Purpose: Render quantum circuits as pixel-art images
- Location: `src/quantum_language/draw.py`
- Contains: `render()` (overview mode), `render_detail()` (label mode), `draw_circuit()` (auto-zoom)
- Depends on: PIL/Pillow, NumPy, `_core.circuit.draw_data()`
- Used by: User code (optional; Pillow is an optional dependency)

## Data Flow

**Circuit Construction (Typical User Operation):**

1. User calls `ql.circuit()` — allocates a new `circuit_t` in C, resets all global state in `_core.pyx`
2. User creates `qint(5, width=8)` — allocates 8 qubits via `qubit_allocator_t`, emits X gates for bit initialization into `circuit_t.sequence[][]`
3. User writes `result = a + b` — `qint.__add__` dispatches to `QQ_add()` or `hot_path_add_qq()` (C function), which calls `add_gate()` for each gate
4. Gates accumulate in `circuit_t.sequence[layer][gate_idx]` organized as a layered DAG (layers that can execute in parallel)
5. User calls `ql.to_openqasm()` → `circuit_to_qasm_string()` in C serializes to OpenQASM 3.0 string

**Grover Search Flow:**

1. User calls `ql.grover(predicate, width=N)`
2. `grover.py` synthesizes oracle from predicate via `_predicate_to_oracle()` (traces predicate on dummy qints)
3. Creates fresh `circuit()`, allocates search registers, applies Hadamard layer (`branch(0.5)`)
4. For each iteration: applies oracle gates, `_apply_hadamard_layer()`, `diffusion()`, `_apply_hadamard_layer()`
5. Calls `to_openqasm()` → exports circuit to QASM string
6. Passes QASM string to Qiskit `AerSimulator` (max 4 threads), single-shot measurement
7. Parses bitstring → returns `(value, iterations)` tuple

**Compile Decorator (Capture-Replay):**

1. First call: `@ql.compile` captures gate layer range via `extract_gate_range()`, virtualizes qubit indices into `CompiledBlock`, optimizes gate list (cancels inverses, merges rotations)
2. Also derives controlled variant of the block by adding 1 control qubit to every gate
3. Cache key: `(classical_args, widths_tuple, control_count, qubit_saving_mode)`
4. Subsequent calls: `inject_remapped_gates()` replays virtual gate sequence with fresh physical qubit mapping — no Python re-execution

**Uncomputation (Qubit-Saving Mode):**

1. When `ql.option('qubit_saving', True)`, compiled functions auto-uncompute ancilla qubits after each call
2. Temp ancillas are identified (not in return or input qubit sets), their adjoint gates are injected, qubits returned to allocator pool via `allocator_free()`

**State Management:**
- Module-level `cdef circuit_t *_circuit` in `_core.pyx` is the live circuit pointer
- All Python-level flags (`_controlled`, `_control_bool`, `_list_of_controls`, `_qubit_saving_mode`) are module globals in `_core.pyx` accessed via accessor functions by other modules
- New `ql.circuit()` resets all state and clears compile caches via registered hooks
- `contextvars.ContextVar` used for scope depth tracking (dependency cycle prevention)

## Key Abstractions

**`circuit_t` (C struct):**
- Purpose: Core circuit data structure — layered gate array + qubit allocator + occupancy tracking + mode flags
- File: `c_backend/include/circuit.h`
- Pattern: Pointer owned by `_core.pyx` module; crosses Python/C boundary as `unsigned long long` cast, never as value

**`gate_t` (C struct):**
- Purpose: Single quantum gate with target qubit, up to 2 inline control qubits (or heap `large_control` for MCX), gate type enum, and rotation angle
- File: `c_backend/include/types.h`
- Pattern: Allocated per-gate in `circuit_t.sequence[layer]` array

**`qint` (Cython cdef class):**
- Purpose: Quantum integer with operator overloading; inherits from `circuit` to access global state accessors
- File: `src/quantum_language/qint.pyx`
- Pattern: `qint.__add__` calls C arithmetic function, returns new `qint` wrapping result qubits; `qint.__enter__`/`__exit__` set `_controlled = True` for controlled-context blocks

**`CompiledBlock` (Python class):**
- Purpose: Cached virtualized gate sequence from `@ql.compile`
- File: `src/quantum_language/compile.py`
- Pattern: Virtual qubit indices (params first, then ancillas), stored in `OrderedDict` cache keyed by `(classical_args, widths, control_count, qubit_saving)`

**`qubit_allocator_t` (C struct):**
- Purpose: Block-based qubit pool with freed-qubit reuse (first-fit, sorted free list with coalescing)
- File: `c_backend/include/qubit_allocator.h`
- Pattern: Embedded in `circuit_t`, hard limit of 8192 qubits; tracks peak allocation and ancilla counts

**`GroverOracle` (Python class):**
- Purpose: Wraps a compiled quantum function with oracle semantics (compute-phase-uncompute validation)
- File: `src/quantum_language/oracle.py`
- Pattern: Layers on top of `@ql.compile`, validates oracle pattern (ORCL-02/03/04), caches keyed by source hash + arithmetic mode

## Entry Points

**User Circuit Entry:**
- Location: `src/quantum_language/_core.pyx` — `circuit.__init__()`
- Triggers: `ql.circuit()` call from user code
- Responsibilities: Allocates `circuit_t` via `init_circuit()`, resets all Python globals, clears all compile caches via registered hooks, resets ancilla array

**Package Import:**
- Location: `src/quantum_language/__init__.py`
- Triggers: `import quantum_language as ql`
- Responsibilities: Re-exports all types and functions; a `circuit()` is auto-created at module import (final line of `_core.pyx`: `circuit()`)

**Build Entry:**
- Location: `setup.py`
- Triggers: `pip install -e .` or `python setup.py build_ext --inplace`
- Responsibilities: Runs `build_preprocessor.py` to inline `.pxi` files, then `cythonize()` all `.pyx` files, compiles each as a shared extension with all C backend sources linked in

**Test Entry:**
- Location: `tests/python/` (pytest), `tests/c/Makefile` (C unit tests)
- Triggers: `pytest tests/python/ -v`
- Responsibilities: Integration and unit tests; verification tests use Qiskit simulation

## Error Handling

**Strategy:** Raise Python exceptions at the Cython boundary; C functions return NULL or sentinel values.

**Patterns:**
- C `init_circuit()` returns NULL on allocation failure → Cython checks and raises `MemoryError`
- C `circuit_to_qasm_string()` returns NULL on failure → Cython raises `RuntimeError`
- `_circuit_initialized` guard checked at start of every function requiring an active circuit; raises `RuntimeError("Circuit not initialized")`
- Qubit allocator hard limit 8192 → `allocator_alloc()` returns `(qubit_t)-1`; callers propagate error
- `@ql.compile` capture depth > 16 → raises `RecursionError`
- Double-free of ancilla qubits → `allocator_free()` returns `-1` (double-free check in debug mode)

## Cross-Cutting Concerns

**Logging:** None — no logging framework. Debug output via `print(..., file=sys.stderr)` in `compile.py` when `debug=True` flag passed to `@ql.compile`.

**Validation:** Input validation at Python API boundary (e.g., width 1-64 for qint, bool values for `option()`). C layer assumes valid inputs.

**Arithmetic Modes:** `circuit_t.arithmetic_mode` flag (`ARITH_QFT` or `ARITH_TOFFOLI`) routes arithmetic to different C implementations. `ARITH_TOFFOLI` uses only CCX/CX/X gates (fault-tolerant compatible). Controlled via `ql.option('fault_tolerant', True)`.

**Adder Selection:** `circuit_t.cla_override` and `circuit_t.qubit_saving` flags select CDKM Ripple-Carry Adder vs Brent-Kung CLA vs Kogge-Stone CLA for Toffoli additions. Controlled via `ql.option('cla', ...)` and `ql.option('qubit_saving', ...)`.

**Controlled Context:** Python-level `_controlled` boolean in `_core.pyx` gates whether each emitted gate wraps with a control qubit. `with qbool_var:` sets `_controlled = True` and `_control_bool = qbool_var` for the block duration.

**Toffoli Decomposition:** `circuit_t.toffoli_decompose` flag decomposes CCX to Clifford+T gates (T, Tdg, H, CX) for fault-tolerant circuit analysis. Controlled via `ql.option('toffoli_decompose', True)`.

---

*Architecture analysis: 2026-02-22*
