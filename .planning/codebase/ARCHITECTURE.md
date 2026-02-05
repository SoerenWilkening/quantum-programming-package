# Architecture

**Analysis Date:** 2026-01-25

## Pattern Overview

**Overall:** Layered quantum circuit compilation architecture with hardware abstraction

**Key Characteristics:**
- Separation between backend (C) and frontend (Python/Cython)
- Gate sequence generation and circuit building layers
- Operation composition via sequence_t (gate sequences)
- Quantum state management via instruction_t (QPU state machine)
- Precompilation optimization for common operations

## Layers

**Backend (C Core):**
- Purpose: Core quantum circuit simulation and gate composition
- Location: `Backend/src/`, `Backend/include/`
- Contains: Gate primitives, integer operations, circuit management
- Depends on: Standard C library (math.h, stdlib.h)
- Used by: Python frontend (Cython binding), Execution layer

**Gate & Quantum Primitives:**
- Purpose: Define and manipulate quantum gates and basic operations
- Location: `Backend/src/gate.c`, `Backend/include/gate.h`
- Contains: Single-qubit gates (X, Y, Z, H, P, Rx, Ry, Rz), controlled gates (CX, CCX), gate utilities
- Depends on: definition.h (type definitions)
- Used by: Integer operations, Logic operations

**Integer Operations:**
- Purpose: Implement quantum integer arithmetic (addition, multiplication, comparison)
- Location: `Backend/src/Integer*.c`, `Backend/include/Integer.h`
- Contains: QINT/QBOOL allocation, ADD operations (CC_add, CQ_add, QQ_add), MUL operations, comparison
- Depends on: gate.h, QPU.h
- Used by: Logic operations, Execution layer, Python bindings

**Logic & Control Flow:**
- Purpose: Implement quantum logic operations and control flow
- Location: `Backend/src/LogicOperations.c`, `Backend/include/LogicOperations.h`
- Contains: AND, OR, XOR sequences; branch/jump operations; negation
- Depends on: Integer.h, gate.h
- Used by: Assembly operations (referenced but not fully implemented)

**Circuit Management & Allocation:**
- Purpose: Manage circuit data structures and qubit allocation
- Location: `Backend/src/circuit_allocations.c`, `Backend/src/ciruict_outputs.c`
- Contains: Circuit initialization, gate addition to layers, memory allocation
- Depends on: QPU.h, gate.h
- Used by: Execution layer

**Execution Layer:**
- Purpose: Execute sequences on circuits with qubit mapping
- Location: `Execution/src/execution.c`, `Execution/include/execution.h`
- Contains: qubit_mapping(), run_instruction(), execute()
- Depends on: QPU.h
- Used by: main.c

**Python Frontend (Cython):**
- Purpose: Python API for quantum circuit building
- Location: `python-backend/quantum_language.pyx`, `python-backend/quantum_language.pxd`
- Contains: qint/qbool classes, circuit class, array utilities
- Depends on: Backend C libraries (via Cython)
- Used by: User scripts (test.py)

## Data Flow

**Circuit Construction Flow:**

1. User creates quantum values (qint/qbool) in Python
2. Each qint/qbool allocates qubits via QINT()/QBOOL()
3. Operations on quantum values generate sequences (gate sequences)
4. Sequences added to global circuit via add_gate()
5. Circuit built as 2D array: layers[layer_index][gate_index]

**Operation Execution Flow:**

1. Operation function (e.g., QQ_add()) generates sequence_t
2. Sequence contains gate layers and gates per layer
3. run_instruction() maps logical qubits to physical qubits
4. Gates added to circuit with actual qubit indices
5. Circuit output to OpenQASM format

**Gate Composition:**

- Single-qubit gates: X, H, P, Z, Y, Rx, Ry, Rz
- Multi-qubit gates: CX (controlled-X), CCX (controlled-controlled-X)
- Gates parameterized by target and control qubits
- Gates collected into layers (gates that can execute in parallel)

**State Management:**

- Global instruction_list[MAXINSTRUCTIONS]: Sequence of operations
- QPU_state: Current instruction pointer
- Q0, Q1, Q2, Q3: Quantum register storage (quantum_int_t pointers)
- R0, R1, R2, R3: Classical register storage (int pointers)
- circuit: Global circuit_t pointer

## Key Abstractions

**gate_t (Gate Structure):**
- Purpose: Represent a single quantum gate operation
- Location: `Backend/include/gate.h` lines 17-30
- Fields: Control[2], NumControls, Gate (enum), GateValue (for parametric gates), Target
- Pattern: Used in gate_t **seq sequences, allocated per layer

**sequence_t (Gate Sequence):**
- Purpose: Represent a sequence of gate layers
- Location: `Backend/include/gate.h` lines 33-38
- Fields: gate_t **seq (2D array), num_layer, used_layer, gates_per_layer array
- Pattern: Gates organized in layers for parallel execution; returned from operation functions

**quantum_int_t (Quantum Integer):**
- Purpose: Represent a quantum integer value
- Location: `Backend/include/QPU.h` lines 46-50
- Fields: MSB (most significant bit index), q_address[INTEGERSIZE] (qubit indices)
- Pattern: Tracks qubit allocation for integer operations

**circuit_t (Circuit):**
- Purpose: Represent complete quantum circuit
- Location: `Backend/include/QPU.h` lines 22-44
- Fields: gate_t **sequence (2D), occupied_layers_of_qubit, gate_index_of_layer_and_qubits, ancilla tracking
- Pattern: Centralized circuit structure supporting efficient gate addition and optimization

**instruction_t (Instruction/Operation):**
- Purpose: Represent a queued operation with state
- Location: `Backend/include/QPU.h` lines 52-71
- Fields: name, Q0-Q3 (quantum registers), R0-R3 (classical registers), routine (function pointer)
- Pattern: Instruction list executed sequentially; state persists across calls

## Entry Points

**C Entry Point:**
- Location: `main.c`
- Triggers: Direct compilation and execution
- Responsibilities: Parse CLI args (num_qubits, run flag), initialize circuit, execute qq_or_seq(), print circuit

**Python Entry Point:**
- Location: User scripts (e.g., `test.py`)
- Triggers: Import quantum_language module
- Responsibilities: Define quantum operations in Python, build circuit via Cython bindings

**Operation Entry Points:**
- Location: `Backend/include/Integer.h`, `Backend/include/LogicOperations.h`
- Triggers: Called from Python classes or main logic
- Examples: QQ_add(), CQ_add(), qq_or_seq(), cc_equal()

## Error Handling

**Strategy:** Minimal error checking; assumes well-formed input

**Patterns:**
- NULL returns for void operations (void_seq, jmp_seq return NULL)
- Precompiled operation caching: If precompiled version exists, reuse it
- Classical (R0-R3) vs quantum (Q0-Q3) register checks: Operation functions check if registers are NULL before use

**Memory Management:**
- Manual malloc/free for sequences, gates, circuit structures
- Free circuit via free_circuit() after execution
- Ancilla qubit tracking with circuit->ancilla pointer

## Cross-Cutting Concerns

**Logging:** Printf-based debugging; circuit printing via print_circuit() and print_sequence()

**Validation:** Type checking implicit in C (gate_t fields); Python type hints in .pyx file

**Authentication:** Not applicable (single-user quantum simulator)

**Qubit Mapping:**
- Logical qubits in operations mapped to physical qubits via qubit_array in run_instruction()
- Ancilla qubits tracked separately in circuit->ancilla
- MAXQUBITS = 8000 hardcoded limit

**Optimization:**
- Precompilation: CQ_add, cCQ_add, QQ_add, cQQ_add stored in global pointers
- Gate layer organization: Supports parallel gate execution within layer
- Toffoli decomposition flag (decompose_toffoli_t) controls CCX compilation strategy

---

*Architecture analysis: 2026-01-25*
