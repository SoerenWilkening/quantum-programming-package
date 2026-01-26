# Module Dependency Graph

This document describes the module organization of the Quantum Assembly C backend.

## Module Overview

| Module | Purpose | Lines (Header/Source) |
|--------|---------|----------------------|
| types.h | Core types (qubit_t, gate_t, sequence_t) | 84 / - |
| gate.h / gate.c | Gate creation and manipulation | 43 / 442 |
| qubit_allocator.h / qubit_allocator.c | Qubit lifecycle management | 71 / 252 |
| optimizer.h / optimizer.c | Layer assignment and gate merging | 38 / 208 |
| circuit_output.h / circuit_output.c | Visualization and QASM export | 27 / 224 |
| circuit.h / circuit_allocations.c | Main public API and circuit lifecycle | 90 / 360 |

## Dependency Graph

```
                    types.h
                       |
           +-----------+-----------+
           |           |           |
        gate.h   qubit_allocator.h |
           |           |           |
           +-----------+-----------+
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

## Legacy Headers

- `QPU.h` - Now a thin wrapper (43 lines) that includes circuit.h
- `definition.h` - Now a thin wrapper that includes types.h

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
