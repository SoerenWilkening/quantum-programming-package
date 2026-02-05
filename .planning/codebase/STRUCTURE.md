# Codebase Structure

**Analysis Date:** 2026-01-25

## Directory Layout

```
Quantum_Assembly/
├── Backend/                    # Quantum circuit core engine (C)
│   ├── include/               # Header files (6 files)
│   │   ├── definition.h       # Type definitions, constants
│   │   ├── gate.h             # Gate primitives and sequences
│   │   ├── QPU.h              # Circuit and instruction structures
│   │   ├── Integer.h          # Integer arithmetic operations
│   │   ├── IntegerComparison.h # Comparison operations
│   │   └── LogicOperations.h  # Logic gates and control flow
│   └── src/                   # Implementation (9 files)
│       ├── gate.c             # Gate primitives implementation
│       ├── Integer.c          # Quantum integer allocation
│       ├── IntegerAddition.c  # Addition sequences (CC, CQ, QQ variants)
│       ├── IntegerMultiplication.c # Multiplication sequences
│       ├── IntegerComparison.c # Comparison operations
│       ├── LogicOperations.c  # AND, OR, XOR, NOT sequences
│       ├── QPU.c              # Circuit core (not found; referenced)
│       ├── circuit_allocations.c # Circuit memory management
│       └── ciruict_outputs.c  # Circuit output/printing
├── Execution/                 # Circuit execution and compilation
│   ├── include/
│   │   └── execution.h        # Execution API
│   └── src/
│       ├── execution.c        # Qubit mapping, gate execution
│       └── run_circuit.py     # Python execution wrapper (unused)
├── python-backend/            # Python/Cython bindings
│   ├── quantum_language.pyx   # Cython source (C+Python)
│   ├── quantum_language.pxd   # Cython type declarations
│   ├── quantum_language.c     # Generated C from Cython
│   ├── quantum_language.cpython-311-darwin.so # Compiled module
│   ├── setup.py               # Cython build configuration
│   └── test.py                # Example usage (Tic-Tac-Toe game)
├── main.c                     # C entry point
├── CMakeLists.txt             # CMake build configuration
├── assembly.pqsm              # Assembly code example (unused)
├── circuit.qasm               # QASM output example (unused)
├── README.md                  # Project overview
├── .planning/                 # Planning documents (generated)
│   └── codebase/
└── build/                     # CMake build output (ignored)
```

## Directory Purposes

**Backend:**
- Purpose: Core quantum circuit compilation and optimization engine
- Contains: C source files implementing gate primitives, integer operations, logic operations, circuit management
- Key files: gate.h, Integer.h, QPU.h

**Backend/include:**
- Purpose: Public headers for quantum operations
- Contains: Type definitions, function declarations for all quantum operations
- Key files:
  - `definition.h`: INTEGERSIZE=8, gate types, qubit type definitions
  - `gate.h`: gate_t, sequence_t structures; gate functions (h, x, cx, ccx, p)
  - `QPU.h`: circuit_t, quantum_int_t, instruction_t structures; circuit API
  - `Integer.h`: Integer operations (QINT, QBOOL, QQ_add, CQ_add, etc.)
  - `IntegerComparison.h`: Comparison operations
  - `LogicOperations.h`: Logic gate sequences (AND, OR, XOR, NOT)

**Backend/src:**
- Purpose: Implementation of quantum operations
- Contains: Gate implementations, operation sequences, circuit management
- Key files:
  - `gate.c`: Single and multi-qubit gate implementations
  - `Integer.c`: Quantum integer allocation and manipulation
  - `IntegerAddition.c`: Addition gate sequences with Fourier transforms
  - `LogicOperations.c`: Logic operation gate sequences
  - `circuit_allocations.c`: Circuit initialization and memory management
  - `ciruict_outputs.c`: Circuit printing and visualization

**Execution:**
- Purpose: Execute compiled sequences on circuits
- Contains: Qubit mapping, sequence application
- Key files:
  - `execution.h`: qubit_mapping(), run_instruction() declarations
  - `execution.c`: Maps logical to physical qubits; applies gates with inversion support

**python-backend:**
- Purpose: Python API for circuit building via Cython
- Contains: High-level quantum language interface
- Key files:
  - `quantum_language.pyx`: qint, qbool, circuit classes; operation overloading
  - `setup.py`: Cython build configuration; links to Backend C files
  - `test.py`: Example usage (Tic-Tac-Toe game demonstrating operations)

**Root:**
- `main.c`: Standalone C executable entry point; demonstrates QQ_add on 64 qubits
- `CMakeLists.txt`: Builds C executable with all Backend and Execution sources (note: Assembly files referenced but missing)
- `README.md`: Project overview and build instructions

## Key File Locations

**Entry Points:**
- `main.c`: C standalone entry point
- `python-backend/quantum_language.pyx`: Python module entry (Cython compiled)
- `python-backend/test.py`: Example Python usage

**Configuration:**
- `CMakeLists.txt`: C build configuration (C23 standard, -O3 optimization)
- `python-backend/setup.py`: Python/Cython build configuration
- `Backend/include/definition.h`: Core constants (INTEGERSIZE=8, MAXCONTROLS=2, MAXQUBITS=8000)

**Core Logic - Gate Primitives:**
- `Backend/include/gate.h`: Gate structure definitions; single-qubit gates (h, x, y, z, p, rx, ry, rz)
- `Backend/src/gate.c`: Gate implementation; circuit visualization

**Core Logic - Integer Arithmetic:**
- `Backend/include/Integer.h`: Operation signatures for addition/multiplication
- `Backend/src/Integer.c`: Quantum integer and boolean allocation (QINT, QBOOL)
- `Backend/src/IntegerAddition.c`: QFT-based addition (CC_add, CQ_add, QQ_add, cQQ_add)
- `Backend/src/IntegerMultiplication.c`: Multiplication implementations

**Core Logic - Logic Operations:**
- `Backend/src/LogicOperations.c`: AND, OR, XOR, NOT gate sequences

**Circuit Management:**
- `Backend/include/QPU.h`: Circuit structures (circuit_t, instruction_t, quantum_int_t)
- `Backend/src/circuit_allocations.c`: Circuit initialization and allocation
- `Backend/src/ciruict_outputs.c`: Circuit output (printing, QASM export)

**Execution:**
- `Execution/include/execution.h`: Execution API
- `Execution/src/execution.c`: run_instruction(), qubit_mapping()

## Naming Conventions

**Files:**
- C source: `snake_case.c` (e.g., `IntegerAddition.c`, `circuit_allocations.c`)
- C headers: `PascalCase.h` (e.g., `Integer.h`, `QPU.h`, `LogicOperations.h`)
- Python/Cython: `snake_case.pyx`, `snake_case.pxd` (e.g., `quantum_language.pyx`)
- Test files: `test.py` (single main test file)

**Functions - C Backend:**
- Operation generators: `CQ_add()`, `QQ_mul()`, `qq_or_seq()` - lowercase with underscores, describe operand types
- Gate primitives: `h()`, `x()`, `cx()`, `ccx()`, `p()` - single letter or standard gate name
- Utilities: `QINT()`, `QBOOL()` - UPPERCASE for allocation functions
- Helpers: `two_complement()`, `print_sequence()`, `free_element()` - snake_case

**Functions - Python/Cython:**
- Classes: `qint`, `qbool`, `circuit` - lowercase
- Methods: `__init__()`, `__dealloc__()`, `add_qubits()` - snake_case
- Module functions: `array()` - lowercase

**Types:**
- Structures: `gate_t`, `sequence_t`, `quantum_int_t`, `circuit_t`, `instruction_t` - PascalCase with _t suffix
- Enums: `Standardgate_t` - PascalCase with _t suffix
- Basic types: `qubit_t`, `layer_t`, `num_t` - snake_case with _t suffix (unsigned int aliases)

**Constants:**
- Defines: `INTEGERSIZE`, `MAXQUBITS`, `MAXINSTRUCTIONS`, `MAXCONTROLS` - UPPERCASE with underscores
- Enum values: `X`, `Y`, `Z`, `H`, `P`, `M`, `Rx`, `Ry`, `Rz` - UPPERCASE or Mixed

**Variables - Global:**
- QPU state: `QPU_state`, `instruction_list`, `circuit`, `instruction_counter` - lowercase with underscores

## Where to Add New Code

**New Quantum Operation (e.g., floating-point addition):**
- Header: Add function declaration to `Backend/include/Integer.h` or new header
- Implementation: Create `Backend/src/FloatingPointAddition.c`
- Integration: Update `CMakeLists.txt` to include new source file
- Precompilation: Add global sequence pointer in header if caching needed

**New Gate Type:**
- Definition: Add to Standardgate_t enum in `Backend/include/gate.h`
- Implementation: Add gate function in `Backend/src/gate.c`
- Usage: Call from sequence generators (e.g., IntegerAddition.c)

**New Control Flow Operation:**
- Implementation: Add `*_seq()` function to `Backend/src/LogicOperations.c`
- Declaration: Add to `Backend/include/LogicOperations.h`
- Registration: Map to instruction_t routine pointer in main.c

**New Python Wrapper:**
- Implementation: Add class/method to `python-backend/quantum_language.pyx`
- Type hints: Add corresponding declarations in `quantum_language.pxd`
- Binding: Use Cython's `cdef extern` to call Backend C functions

**New Integration with External Framework:**
- Output: Extend `Backend/src/ciruict_outputs.c` to export to new format (e.g., Cirq, Qiskit)
- Header: Add export function to `Backend/include/QPU.h`

## Special Directories

**circuit-gen-results/:**
- Purpose: Results from running circuit on multiple quantum frameworks
- Generated: Yes (at runtime)
- Committed: Yes (contains example outputs for qiskit, cirq, qsharp, etc.)
- Contents: Test harnesses for different quantum simulation frameworks (not part of core engine)

**cmake-build-debug/, build/:**
- Purpose: CMake build output directories
- Generated: Yes
- Committed: No (ignored by .gitignore)
- Contents: Compiled executables and object files

**python-backend/build/:**
- Purpose: Python/Cython build output
- Generated: Yes (by setup.py)
- Committed: No (contains .so binaries and temporary files)
- Contents: Compiled Cython extension, build artifacts

**.planning/codebase/:**
- Purpose: Architecture and structure documentation
- Generated: Yes (by GSD mapper)
- Committed: Yes
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

## Module Dependencies

**Backend → C Standard Library:**
- math.h (pow, M_PI)
- stdlib.h (malloc, calloc, free)
- string.h (memcpy, memset)
- stdio.h (printf)

**Python-backend → Backend:**
- Cython compilation includes Backend/include/ and links Backend/src/ files
- setup.py explicitly lists Backend source files

**Execution → Backend:**
- execution.c includes QPU.h, gate.h
- Uses circuit_t, sequence_t, gate_t structures

**main.c → Backend + Execution:**
- Includes from Backend/include/ and Execution/include/
- Calls initialization, sequence generation, execution, printing

**Python test.py → python-backend:**
- Imports quantum_language module (compiled Cython)
- Uses qint, qbool, array classes

---

*Structure analysis: 2026-01-25*
