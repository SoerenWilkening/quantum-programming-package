# Module Dependency Graph

This document describes the module organization of the Quantum Assembly C backend.

## Module Overview

| Module | Purpose | Lines (Header/Source) |
|--------|---------|----------------------|
| types.h | Core types (qubit_t, gate_t, sequence_t) | 84 / - |
| gate.h / gate.c | Gate creation and manipulation | 43 / 442 |
| qubit_allocator.h / qubit_allocator.c | Qubit lifecycle management | 71 / 252 |
| arithmetic_ops.h | Addition, subtraction, multiplication operations | 158 / - |
| comparison_ops.h | Equality and ordering comparisons | 74 / - |
| bitwise_ops.h | Width-parameterized bitwise operations | 106 / - |
| optimizer.h / optimizer.c | Layer assignment and gate merging | 38 / 208 |
| circuit_output.h / circuit_output.c | Visualization and QASM export | 27 / 224 |
| circuit.h / circuit_allocations.c | Main public API and circuit lifecycle | 90 / 360 |

## Dependency Graph

```
                       types.h
                          |
              +-----------+-----------+
              |           |           |
           gate.h  qubit_allocator.h  |
              |           |           |
              +-----------+-----------+
                          |
     +--------------------+--------------------+
     |                    |                    |
   arithmetic_ops.h  comparison_ops.h  bitwise_ops.h
     |                    |                    |
     +--------------------+--------------------+
                          |
                     optimizer.h
                          |
                    circuit_output.h
                          |
                      circuit.h  <-- Main API (include this)
```

## Include Order

For users of the library:
```c
#include "circuit.h"  // Includes everything needed
```

For internal modules, include only what's needed:
```c
// Example: optimizer.c
#include "optimizer.h"
#include "circuit.h"      // For circuit_t definition
#include "gate.h"         // For gate functions
```

## Operation Modules

### arithmetic_ops.h (158 lines)
Width-parameterized arithmetic operations.

**Dependencies:** types.h, stdint.h

- Addition: QQ_add(bits), CQ_add(bits, value), cQQ_add(bits), cCQ_add(bits, value)
- Multiplication: QQ_mul(bits), CQ_mul(bits, value), cQQ_mul(bits), cCQ_mul(bits, value)
- Legacy operations: CC_add(), CC_mul()
- Precompiled caches: precompiled_*_add_width[65], precompiled_*_mul_width[65]

**Note:** Subtraction implemented at Python level using addition with two's complement.

### comparison_ops.h (74 lines)
Width-parameterized comparison operations.

**Dependencies:** types.h, stdint.h

- Equality: QQ_equal(bits), CQ_equal_width(bits, value)
- Less-than: QQ_less_than(bits), CQ_less_than(bits, value)
- Legacy operations: CC_equal(), CQ_equal(), cCQ_equal()
- Derived comparisons (>, <=, >=) implemented at Python level

### bitwise_ops.h (106 lines)
Width-parameterized bitwise operations.

**Dependencies:** types.h, stdint.h

- NOT: Q_not(bits), cQ_not(bits)
- XOR: Q_xor(bits), cQ_xor(bits)
- AND: Q_and(bits), CQ_and(bits, value)
- OR: Q_or(bits), CQ_or(bits, value)

Circuit depth characteristics:
- Q_not, Q_xor, Q_and: O(1) - parallel gates
- cQ_not, cQ_xor: O(bits) - sequential gates
- Q_or: O(3) - 3-layer implementation

## Legacy Headers

- `QPU.h` - Now a thin wrapper (43 lines) that includes circuit.h
- `definition.h` - Now a thin wrapper that includes types.h
- `Integer.h` - Now includes arithmetic_ops.h (kept for backward compatibility)
- `IntegerComparison.h` - Now includes comparison_ops.h (backward compat wrapper)
- `LogicOperations.h` - Now includes bitwise_ops.h (backward compat wrapper)

These are kept for backward compatibility with existing code.

## Module Responsibilities

### types.h (84 lines)
Foundation module with zero dependencies.

- Fundamental types: qubit_t, layer_t, num_t
- Gate enum: Standardgate_t
- Structures: gate_t, sequence_t
- Constants: INTEGERSIZE, MAXCONTROLS

### gate.h / gate.c (43 / 442 lines)
Gate creation and manipulation functions.

**Dependencies:** types.h

- Gate constructors: x(), cx(), ccx(), h(), p(), z(), etc.
- QFT circuits: QFT(), QFT_inverse()
- Gate analysis: gates_are_inverse(), gates_commute()
- Sequence printing: print_sequence(), print_gate()

### qubit_allocator.h / qubit_allocator.c (71 / 252 lines)
Centralized qubit allocation with reuse and statistics.

**Dependencies:** types.h

- Qubit allocation: allocator_create(), allocator_alloc()
- Qubit deallocation: allocator_free(), allocator_destroy()
- Statistics: allocator_get_stats(), allocator_reset_stats()
- Debug ownership tracking (optional): allocator_set_owner()

### optimizer.h / optimizer.c (38 / 208 lines)
Intelligent gate placement and circuit optimization.

**Dependencies:** types.h, (forward declares circuit_t)

- Gate adding: add_gate() - main entry point
- Layer assignment: minimum_layer(), smallest_layer_below_comp()
- Gate merging: merge_gates(), colliding_gates()
- Layer application: apply_layer(), append_gate()

### circuit_output.h / circuit_output.c (27 / 224 lines)
Circuit visualization and export functionality.

**Dependencies:** types.h, (forward declares circuit_t)

- Text visualization: print_circuit()
- QASM export: circuit_to_opanqasm()

### arithmetic_ops.h (158 lines)
Width-parameterized arithmetic operations.

**Dependencies:** types.h, stdint.h

- Addition functions: QQ_add, CQ_add, cQQ_add, cCQ_add (all with bits parameter)
- Multiplication functions: QQ_mul, CQ_mul, cQQ_mul, cCQ_mul (all with bits parameter)
- Legacy operations: CC_add(), CC_mul() (INTEGERSIZE only)
- Width caches: precompiled_*_add_width[65], precompiled_*_mul_width[65]

### comparison_ops.h (74 lines)
Width-parameterized comparison operations.

**Dependencies:** types.h, stdint.h

- Equality functions: QQ_equal(bits), CQ_equal_width(bits, value)
- Less-than functions: QQ_less_than(bits), CQ_less_than(bits, value)
- Legacy operations: CC_equal(), CQ_equal(), cCQ_equal()
- XOR-based equality: O(n) gates
- Ancilla-based less-than: preserves input operands

### bitwise_ops.h (106 lines)
Width-parameterized bitwise operations.

**Dependencies:** types.h, stdint.h

- NOT operations: Q_not(bits), cQ_not(bits)
- XOR operations: Q_xor(bits), cQ_xor(bits)
- AND operations: Q_and(bits), CQ_and(bits, value)
- OR operations: Q_or(bits), CQ_or(bits, value)
- Circuit depth: O(1) for parallel ops, O(bits) for sequential, O(3) for OR

### circuit.h / circuit_allocations.c (90 / 360 lines)
Main public API header and circuit lifecycle implementation.

**Dependencies:** types.h, gate.h, qubit_allocator.h, optimizer.h, circuit_output.h

- Circuit structure definition: circuit_t
- Circuit lifecycle: init_circuit(), free_circuit()
- Memory management: allocate_more_*() functions
- Aggregates all other headers for convenience

## Design Principles

1. **Single Source of Truth**: types.h defines all shared types
2. **Minimal Coupling**: Each module depends only on what it needs
3. **Forward Declarations**: optimizer.h and circuit_output.h use forward declarations to avoid circular dependencies
4. **Clear Hierarchy**: Dependency graph is acyclic and well-documented
5. **Backward Compatibility**: Legacy headers (QPU.h, definition.h) maintained as thin wrappers

## Historical Context

Before Phase 4 (module separation), this codebase had:
- QPU.c as a "god object" (201 lines of mixed responsibilities)
- No clear module boundaries
- Global state mixed with circuit logic
- Difficult to test individual components

After Phase 4:
- QPU.c reduced to 18 lines (just globals for sequence generation)
- Clear module boundaries with documented dependencies
- Easier to test, maintain, and extend
- New code uses circuit.h, legacy code still works via QPU.h

After Phase 9 (operation header organization):
- Operations organized by category (arithmetic, comparison, bitwise)
- Dedicated module headers: arithmetic_ops.h, comparison_ops.h, bitwise_ops.h
- Legacy headers converted to backward compatibility wrappers
- Clear separation between width-parameterized (1-64 bits) and legacy (INTEGERSIZE) operations
- Migration path: new code uses *_ops.h headers, old code continues to work
