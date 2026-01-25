# Architecture Patterns for Quantum Programming Frameworks

**Domain:** Quantum Circuit Generation Frameworks with C Backend and Python Bindings
**Researched:** 2026-01-25
**Confidence:** MEDIUM to HIGH

## Executive Summary

Quantum programming frameworks in 2026 follow a consistent multi-layered architecture pattern that separates performance-critical circuit operations (C/C++) from user-facing APIs (Python). Modern frameworks have converged on several key architectural principles:

1. **Three-layer architecture**: Backend (low-level operations) → Binding layer (interop) → Frontend (user API)
2. **Context/handle pattern over global state**: Circuit state encapsulated in opaque handles passed explicitly
3. **Intermediate representation (IR) layer**: DAG-based circuit representation for optimization
4. **Clear component boundaries**: Gate primitives, circuit builder, optimizer, compiler/transpiler
5. **Memory management via RAII-style patterns**: Explicit init/free with owned resources

The current Quantum Assembly implementation exhibits several anti-patterns common in early-stage quantum frameworks: heavy reliance on global state, mixing of concerns between layers, and ad-hoc memory management. The recommended restructuring follows proven patterns from mature frameworks like Qiskit, QuTiP, and OpenQL.

## Current Architecture Analysis

### Existing Structure

```
Quantum Assembly (Current)
│
├── Backend (C)                           # Performance layer
│   ├── gate.c/h                         # Gate primitives (X, Y, Z, H, CX, CCX)
│   ├── QPU.c/h                          # Circuit structure + global state
│   ├── Integer.c/h                      # Quantum integer allocation
│   ├── IntegerAddition.c/h              # Arithmetic operations
│   ├── IntegerMultiplication.c/h
│   ├── IntegerComparison.c/h
│   ├── LogicOperations.c/h              # Boolean operations
│   ├── circuit_allocations.c            # Memory management
│   └── circuit_outputs.c                # OpenQASM export
│
├── python-backend (Cython)               # Binding layer
│   └── quantum_language.pyx             # Python wrapper (qint/qbool classes)
│
└── (Python layer - not visible in codebase)
```

### Current Data Flow

```
Python User Code (qint/qbool)
    ↓
Cython Bindings (quantum_language.pyx)
    ↓ [C function calls]
Integer Operations (IntegerAddition.c, etc.)
    ↓ [sequence_t generation]
Gate Sequences (gate.c)
    ↓ [add_gate calls]
Global Circuit State (QPU.c: circuit_t *circuit)
    ↓ [layer optimization + storage]
Circuit Data Structure (QPU.h: circuit_t)
    ↓ [export]
OpenQASM Output (circuit_outputs.c)
```

### Identified Anti-Patterns

**1. Global State Dependency**
- `extern circuit_t *circuit` in QPU.h (line 76)
- `extern instruction_t *QPU_state` (line 75)
- All circuit operations implicitly depend on global circuit pointer
- Makes multi-circuit workflows impossible
- Breaks thread safety

**2. Mixed Concerns in QPU.c**
- Circuit allocation, gate insertion, layer optimization, and state management all in one file
- 187 lines doing 4+ distinct jobs
- Functions like `add_gate` perform allocation, optimization, and insertion

**3. Leaky Abstractions**
- Cython layer directly manipulates C arrays (qubit_array, ancilla)
- Python layer knows about INTEGERSIZE, memory layout
- No clear API boundary between layers

**4. Ad-hoc Memory Management**
- Integer.c allocates quantum_int_t but doesn't own circuit qubits
- Circuit owns qubits, but Integer functions mutate global circuit
- Unclear ownership: who frees what?

**5. Multi-purpose Functions**
- `add_gate` does: allocation, layer calculation, collision detection, merging, optimization
- Integer operations mix circuit building with arithmetic logic

## Recommended Architecture Pattern

### Industry-Standard Three-Layer Model

Based on analysis of Qiskit, QuTiP, OpenQL, and XACC frameworks:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Python Frontend (User API)                    │
│  ─────────────────────────────────────────────────────  │
│  • High-level types: QuantumCircuit, QInt, QBool        │
│  • Operator overloading (__add__, __mul__, __lt__)      │
│  • Context managers (with statement for controls)       │
│  • Pythonic memory management (no manual free)          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Binding Layer (Cython/ctypes/CFFI)           │
│  ─────────────────────────────────────────────────────  │
│  • Type marshaling (Python ↔ C)                         │
│  • Lifetime management (Python GC ↔ C malloc/free)     │
│  • Exception translation (C error codes ↔ Python)      │
│  • Handle wrapping (opaque circuit_t* ↔ Python obj)    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 3: C Backend (Performance Core)                  │
│  ─────────────────────────────────────────────────────  │
│  Component A: Core Data Structures                      │
│    • circuit_t: DAG-based circuit representation        │
│    • gate_t: Gate primitives                            │
│    • qubit_allocator_t: Qubit pool management          │
│                                                          │
│  Component B: Circuit Builder                           │
│    • circuit_create(options) → circuit_t*               │
│    • circuit_add_gate(circuit_t*, gate_t*)              │
│    • circuit_free(circuit_t*)                           │
│                                                          │
│  Component C: Gate Library                              │
│    • Standard gates: X, Y, Z, H, CX, CCX                │
│    • Parameterized: Rx, Ry, Rz, P                       │
│    • Composite: QFT, arithmetic ops                     │
│                                                          │
│  Component D: Circuit Optimizer                         │
│    • Layer assignment algorithm                         │
│    • Gate merging (inverse cancellation)                │
│    • Commutation analysis (optional)                    │
│                                                          │
│  Component E: Compiler/Transpiler                       │
│    • circuit_to_qasm(circuit_t*, path)                  │
│    • Future: other backend formats                      │
│                                                          │
│  Component F: Quantum Operations Library                │
│    • Integer arithmetic (addition, multiplication)      │
│    • Comparisons (gt, lt, eq)                           │
│    • Boolean logic (AND, OR, NOT, XOR)                  │
└─────────────────────────────────────────────────────────┘
```

### Recommended Component Boundaries

| Component | Responsibility | Public API | Internal Dependencies |
|-----------|---------------|------------|----------------------|
| **Core Data Structures** | Define circuit_t, gate_t, allocation strategies | Type definitions only | None |
| **Circuit Builder** | Create/modify/destroy circuits | `circuit_create()`, `circuit_add_gate()`, `circuit_free()` | Core Data Structures |
| **Gate Library** | Gate construction helpers | `gate_x()`, `gate_cx()`, etc. | Core Data Structures |
| **Circuit Optimizer** | Layer assignment, gate merging | Internal to Circuit Builder | Core Data Structures |
| **Compiler** | Export to QASM, other formats | `circuit_to_qasm()` | Circuit Builder, Core |
| **Quantum Ops** | High-level operations (arithmetic, logic) | `qint_add()`, `qint_mul()`, etc. | Circuit Builder, Gate Library |
| **Binding Layer** | Python-C interop | Cython classes wrapping handles | All C components |
| **Python Frontend** | User-facing classes | `QuantumCircuit`, `QInt`, `QBool` | Binding Layer only |

### Data Flow in Recommended Architecture

```
User Python Code
    ↓ [creates QInt objects]
Python Frontend (qint.py)
    ↓ [calls binding methods]
Cython Binding (_quantum.pyx)
    ↓ [marshals to C types, calls C API]
┌─────────────────────────────────────────┐
│ C Backend Entry Point                   │
│   qint_add(circuit_t* ctx, ...)         │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Quantum Operations Library              │
│   • Generates gate sequence             │
│   • Uses Circuit Builder API            │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Circuit Builder                         │
│   circuit_add_gate(ctx, gate)           │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Circuit Optimizer                       │
│   • Layer assignment                    │
│   • Gate merging                        │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Circuit Data Structure (DAG)            │
│   • Stores optimized circuit            │
└─────────────────────────────────────────┘
    ↓ [when requested]
Compiler/Transpiler
    ↓
OpenQASM / Other Backend Format
```

## Key Architectural Patterns

### Pattern 1: Opaque Handle (Context Object)

**What:** Encapsulate circuit state in an opaque handle passed explicitly to all functions.

**Why:** Eliminates global state, enables multiple circuits, improves testability.

**Example:**
```c
// Bad (current): Global state
extern circuit_t *circuit;
void add_gate(gate_t *g) {
    // Uses global 'circuit'
}

// Good: Explicit context
circuit_t* circuit_create(circuit_options_t *options);
void circuit_add_gate(circuit_t *ctx, gate_t *g);
void circuit_free(circuit_t *ctx);

// Usage
circuit_t *my_circuit = circuit_create(NULL);
gate_t g;
gate_x(&g, 0);
circuit_add_gate(my_circuit, &g);
circuit_free(my_circuit);
```

**Benefits:**
- Multiple circuits can exist simultaneously
- Thread-safe (each thread uses own context)
- Easier testing (create/destroy contexts per test)
- Clear ownership semantics

**References:**
- [Interrupt: Practical Design Patterns: Opaque Pointers and Objects in C](https://interrupt.memfault.com/blog/opaque-pointers)
- [mbedded.ninja: Opaque Pointers](https://blog.mbedded.ninja/programming/design-patterns/opaque-pointers/)

### Pattern 2: Separation of Concerns

**What:** Each module has a single, well-defined responsibility.

**Current Problem:**
- `QPU.c` (187 lines) does allocation, optimization, insertion, and state management
- `Integer.c` mixes type creation with circuit manipulation

**Recommended Split:**

```c
// circuit_builder.c - Circuit lifecycle
circuit_t* circuit_create(circuit_options_t *opts);
void circuit_free(circuit_t *ctx);

// circuit_operations.c - Gate insertion
void circuit_add_gate(circuit_t *ctx, gate_t *g);

// circuit_optimizer.c - Optimization logic
static layer_t compute_minimum_layer(circuit_t *ctx, gate_t *g);
static bool try_merge_gates(circuit_t *ctx, gate_t *g, layer_t layer);

// circuit_allocator.c - Memory management
static void allocate_more_qubits(circuit_t *ctx, size_t needed);
static void allocate_more_layers(circuit_t *ctx, size_t needed);

// circuit_compiler.c - Export
void circuit_to_qasm(circuit_t *ctx, const char *path);
```

**Benefits:**
- Easier to understand (each file has clear purpose)
- Easier to test (unit test each component)
- Easier to maintain (changes localized)

### Pattern 3: Resource Acquisition Is Initialization (RAII-style)

**What:** Resources acquired in create functions, released in free functions. Clear ownership.

**Current Problem:**
- `quantum_int_t *QINT()` allocates struct but mutates global circuit
- Unclear who owns qubits: quantum_int_t or circuit_t?
- Memory leaks: quantum_int_t malloced but never freed in Integer.c

**Recommended:**
```c
// Clear ownership model
typedef struct {
    circuit_t *owner;      // Circuit that owns the qubits
    qubit_t *qubit_ids;    // IDs of qubits (owned by circuit)
    size_t num_qubits;
} qint_t;

// Allocate qubits from circuit's pool
qint_t* qint_create(circuit_t *ctx, size_t bits);
void qint_free(qint_t *qint);  // Returns qubits to circuit pool

// Usage
circuit_t *circ = circuit_create(NULL);
qint_t *a = qint_create(circ, 8);
qint_t *b = qint_create(circ, 8);
qint_add(circ, a, b);  // Explicit circuit context
qint_free(b);
qint_free(a);
circuit_free(circ);  // Frees all remaining qubits
```

**Benefits:**
- Clear ownership: circuit owns qubits, qint_t references them
- No leaks: all allocations paired with frees
- Explicit dependencies: qint_t requires circuit_t to exist

### Pattern 4: Intermediate Representation (DAG)

**What:** Represent circuit as Directed Acyclic Graph for optimization.

**Current Implementation:**
- Layered structure in circuit_t (good!)
- `sequence[layer][gate_index]` with optimization metadata
- Already doing layer assignment and gate merging

**Recommended Enhancement:**
Keep current layer-based structure but make DAG explicit:

```c
typedef struct gate_node {
    gate_t gate;
    size_t node_id;
    size_t *predecessors;      // Gate IDs that must execute before this
    size_t num_predecessors;
    size_t *successors;        // Gate IDs that depend on this
    size_t num_successors;
    layer_t assigned_layer;    // Computed during optimization
} gate_node_t;

typedef struct circuit_dag {
    gate_node_t *nodes;
    size_t num_nodes;
    size_t allocated_nodes;
    // Existing layer structures for optimization
} circuit_dag_t;
```

**Benefits:**
- Makes dependencies explicit
- Enables advanced optimization (commutation analysis, reordering)
- Supports multiple compilation strategies

**Current in Industry (2026):**
- Qiskit uses DAGCircuit as primary IR
- Graph Neural Networks used for circuit optimization
- TDAG (tree-based DAG partitioning) reduces optimization time by 94.5%

**References:**
- [Circuit Transformations for Quantum Architectures](https://arxiv.org/pdf/1902.09102)
- [TDAG: Tree-based Directed Acyclic Graph Partitioning for Quantum Circuits](https://www.ornl.gov/publication/tdag-tree-based-directed-acyclic-graph-partitioning-quantum-circuits)

### Pattern 5: Layered API Design

**What:** Provide multiple API levels for different users.

```c
// Low-level API: Maximum control, verbose
circuit_t *ctx = circuit_create(NULL);
gate_t g;
gate_cx(&g, /*target=*/0, /*control=*/1);
circuit_add_gate(ctx, &g);

// Mid-level API: Circuit operations
qint_t *a = qint_create(ctx, 8);
qint_t *b = qint_create(ctx, 8);
qint_add(ctx, a, b);  // Generates gate sequence internally

// High-level API: Python
a = QInt(8)
b = QInt(8)
c = a + b  # Operator overloading, automatic circuit management
```

**Benefits:**
- Experts can use low-level for fine control
- Most users use high-level for productivity
- All layers share same backend (no duplication)

## Recommended Module Organization

### Proposed File Structure

```
Backend/
├── include/
│   ├── quantum_assembly.h          # Main public API
│   ├── circuit.h                   # Circuit types and core API
│   ├── gate.h                      # Gate types and construction
│   ├── qint.h                      # Quantum integer API
│   ├── operations.h                # Arithmetic/logic operations
│   └── internal/
│       ├── circuit_optimizer.h     # Internal optimization API
│       ├── circuit_allocator.h     # Internal memory management
│       └── dag.h                   # Internal DAG structures
│
├── src/
│   ├── core/
│   │   ├── circuit_builder.c       # Create/destroy/add gates
│   │   ├── circuit_allocator.c     # Memory management
│   │   ├── circuit_optimizer.c     # Layer assignment, merging
│   │   └── gate_primitives.c       # Gate construction
│   │
│   ├── types/
│   │   ├── qint.c                  # Quantum integer allocation
│   │   └── qubit_allocator.c       # Qubit pool management
│   │
│   ├── operations/
│   │   ├── arithmetic.c            # Add, subtract, multiply
│   │   ├── comparison.c            # GT, LT, EQ
│   │   └── logic.c                 # AND, OR, NOT, XOR
│   │
│   └── compiler/
│       ├── qasm_output.c           # OpenQASM 2.0/3.0 export
│       └── circuit_statistics.c    # Gate counts, depth, etc.
│
├── python-backend/
│   ├── _quantum_core.pyx           # Low-level Cython bindings
│   ├── circuit.py                  # QuantumCircuit Python class
│   ├── qint.py                     # QInt/QBool Python classes
│   └── setup.py
│
└── CMakeLists.txt / Makefile
```

### Dependencies Between Modules

```
┌─────────────────────────────────────────────────────────┐
│ operations/arithmetic.c, comparison.c, logic.c          │
│   Dependencies: core/circuit_builder, types/qint        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ types/qint.c                                            │
│   Dependencies: core/circuit_builder, qubit_allocator  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ core/circuit_builder.c                                  │
│   Dependencies: gate_primitives, circuit_optimizer,     │
│                 circuit_allocator                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ core/circuit_optimizer.c, circuit_allocator.c          │
│   Dependencies: circuit.h types only                    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ core/gate_primitives.c                                  │
│   Dependencies: gate.h types only                       │
└─────────────────────────────────────────────────────────┘
```

**Dependency Rules:**
- No circular dependencies
- High-level depends on low-level, never reverse
- Compiler layer depends on everything (output only)
- Python bindings depend on all C APIs

## Memory Management Strategy

### Current Problems

1. **Unclear ownership**: quantum_int_t allocated but circuit owns qubits
2. **Global state mutation**: Integer functions modify global circuit
3. **No lifecycle management**: Missing paired free() for allocations
4. **Ancilla confusion**: circuit->ancilla is a pointer into qubit_indices array

### Recommended Strategy

**Principle: Single Owner, Clear Lifetimes**

```c
// 1. Circuit owns all qubits
typedef struct circuit_t {
    // Qubit pool
    bool *qubit_allocated;   // Track which qubits are in use
    size_t total_qubits;
    size_t next_free_qubit;

    // Circuit DAG
    gate_node_t *gates;
    size_t num_gates;

    // Optimization metadata
    layer_t *gate_layers;
    // ... existing structures
} circuit_t;

// 2. QInt borrows qubits from circuit
typedef struct qint_t {
    circuit_t *circuit;      // Borrowed reference (not owned)
    qubit_t *qubit_ids;      // Array of qubit IDs (owned by qint_t)
    size_t num_qubits;
} qint_t;

// 3. Explicit allocation/deallocation
circuit_t* circuit_create(circuit_options_t *opts) {
    circuit_t *ctx = malloc(sizeof(circuit_t));
    ctx->qubit_allocated = calloc(INITIAL_QUBITS, sizeof(bool));
    ctx->total_qubits = INITIAL_QUBITS;
    ctx->next_free_qubit = 0;
    // ... initialize other fields
    return ctx;
}

qint_t* qint_create(circuit_t *ctx, size_t bits) {
    qint_t *qi = malloc(sizeof(qint_t));
    qi->circuit = ctx;  // Borrowed
    qi->qubit_ids = malloc(bits * sizeof(qubit_t));
    qi->num_qubits = bits;

    // Allocate qubits from circuit's pool
    for (size_t i = 0; i < bits; i++) {
        qi->qubit_ids[i] = allocate_qubit(ctx);
    }
    return qi;
}

void qint_free(qint_t *qi) {
    // Return qubits to circuit pool
    for (size_t i = 0; i < qi->num_qubits; i++) {
        deallocate_qubit(qi->circuit, qi->qubit_ids[i]);
    }
    free(qi->qubit_ids);
    free(qi);
}

void circuit_free(circuit_t *ctx) {
    free(ctx->qubit_allocated);
    // Free gates, layers, etc.
    free(ctx);
}
```

**Lifetime Rules:**
1. Circuit must outlive all qint_t that reference it
2. qint_free() must be called before circuit_free()
3. Python binding layer enforces this via reference counting

### Ancilla Management

**Current:** `circuit->ancilla` is a pointer into `qubit_indices` array (confusing)

**Recommended:**
```c
typedef struct qubit_allocator_t {
    bool *allocated;       // Which qubits are in use
    size_t total;
    size_t ancilla_base;   // First ancilla qubit ID
    size_t next_ancilla;   // Next available ancilla
} qubit_allocator_t;

// Explicit ancilla allocation
qubit_t allocate_ancilla(circuit_t *ctx) {
    return ctx->allocator.next_ancilla++;
}

void deallocate_ancilla(circuit_t *ctx, qubit_t qubit_id) {
    // Mark as free, potentially reuse
}
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: God Object (QPU.c)

**What goes wrong:** Single file/module doing too many things (circuit state, allocation, optimization, insertion).

**Why it happens:** Incremental feature addition without refactoring.

**Consequences:**
- Hard to test individual components
- Changes have unexpected side effects
- Code becomes unmaintainable

**Prevention:**
- One file, one responsibility
- Extract cohesive modules early
- Review file size (>500 lines = refactor candidate)

**Detection:**
- File does >3 unrelated things
- Many includes from same file
- Difficult to describe file purpose in one sentence

### Anti-Pattern 2: Global State

**What goes wrong:** `extern circuit_t *circuit` makes testing impossible, breaks multi-circuit use cases.

**Why it happens:** Convenience during prototyping.

**Consequences:**
- Can't have multiple circuits
- Tests interfere with each other
- Thread-unsafe
- Hidden dependencies

**Prevention:** Use opaque handle pattern from day one.

**Detection:**
- `extern` variables in headers
- Functions with no parameters that access state
- Unit tests that must run in specific order

### Anti-Pattern 3: Leaky Abstractions

**What goes wrong:** Python layer knows about INTEGERSIZE, C memory layout.

**Why it happens:** Direct Cython access to C internals.

**Consequences:**
- Changes to C layout break Python
- Can't change implementation without breaking users
- Tight coupling between layers

**Prevention:**
- Define clear API boundary
- Python layer calls C functions, doesn't access C structs directly
- Use opaque types at API boundary

**Detection:**
- Python code with `cdef` accessing C struct fields
- Constants duplicated across layers
- Direct pointer arithmetic in binding layer

### Anti-Pattern 4: Mixed In-place and Out-of-place Operations

**What goes wrong:** `qint.__add__` creates new qint, `qint.__iadd__` modifies in-place, but both generate gates on circuit.

**Why it happens:** Python semantics don't map cleanly to quantum operations.

**Consequences:**
- User confusion about when circuit is modified
- Unintended gate generation
- Hard to optimize

**Prevention:**
- Be explicit: all operations generate gates
- Document clearly whether operations are in-place
- Consider separate methods for circuit-modifying vs. non-modifying

**Example:**
```python
# Clear semantics
a = QInt(8, value=5)
b = QInt(8, value=3)

# Creates new QInt, generates gates
c = a + b

# In-place add, generates gates, modifies 'a'
a += b

# Both generate gates! User must understand this.
```

## Phased Restructuring Strategy

### Phase 1: Eliminate Global State (Foundation)

**Goal:** Replace global `circuit` with explicit context parameter.

**Changes:**
```c
// Before
extern circuit_t *circuit;
void add_gate(gate_t *g);

// After
circuit_t* circuit_create(circuit_options_t *opts);
void circuit_add_gate(circuit_t *ctx, gate_t *g);
void circuit_free(circuit_t *ctx);
```

**Dependencies:** All C backend functions

**Testing:** Update all unit tests to create/destroy contexts

**Impact:** Breaking change at C API level (Cython must update)

**Priority:** CRITICAL (enables all other improvements)

### Phase 2: Separate Circuit Builder from Optimizer

**Goal:** Extract optimization logic from QPU.c

**New Files:**
- `circuit_optimizer.c/h` (layer assignment, gate merging)
- `circuit_operations.c/h` (add_gate, now simpler)

**Dependencies:** Phase 1 complete

**Testing:** Optimization tests separate from builder tests

**Impact:** Internal refactoring (no API changes)

**Priority:** HIGH (improves maintainability)

### Phase 3: Introduce Qubit Allocator

**Goal:** Centralize qubit lifecycle management

**New Files:**
- `qubit_allocator.c/h`

**Changes:**
- `qint_create` calls `allocate_qubits(ctx, n)`
- `qint_free` calls `deallocate_qubits(ctx, ids, n)`
- Circuit owns allocator, qint_t borrows qubits

**Dependencies:** Phase 1 complete

**Testing:** Allocator unit tests (allocation, deallocation, reuse)

**Impact:** Moderate (changes qint API)

**Priority:** HIGH (fixes memory management)

### Phase 4: Refactor Operation Libraries

**Goal:** Separate arithmetic/logic operations from Integer.c

**New Files:**
- `operations/arithmetic.c`
- `operations/comparison.c`
- `operations/logic.c`

**Changes:**
- Move `QQ_add`, `CQ_add`, etc. to arithmetic.c
- All functions take explicit `circuit_t *ctx` parameter
- Integer.c becomes type definitions only

**Dependencies:** Phase 1, 3 complete

**Testing:** Operation tests independent of type system

**Impact:** Internal refactoring

**Priority:** MEDIUM (improves organization)

### Phase 5: Update Python Bindings

**Goal:** Adapt Cython layer to new C API

**Changes:**
```python
# Before
cdef circuit_t *_circuit  # Global

# After
cdef class QuantumCircuit:
    cdef circuit_t *_ctx

    def __init__(self):
        self._ctx = circuit_create(NULL)

    def __dealloc__(self):
        circuit_free(self._ctx)

cdef class QInt:
    cdef qint_t *_qint
    cdef QuantumCircuit _circuit  # Keep circuit alive

    def __init__(self, circuit, bits=8):
        self._circuit = circuit
        self._qint = qint_create(circuit._ctx, bits)

    def __dealloc__(self):
        qint_free(self._qint)
```

**Dependencies:** Phases 1-4 complete

**Testing:** Python integration tests

**Impact:** Breaking change at Python level

**Priority:** CRITICAL (user-facing API)

### Phase 6: Introduce Explicit DAG (Optional)

**Goal:** Make circuit dependencies explicit for advanced optimization

**New Files:**
- `internal/dag.c/h`

**Changes:**
- Add predecessor/successor tracking to gates
- Enable commutation analysis
- Support advanced rewriting passes

**Dependencies:** All previous phases

**Testing:** DAG construction tests, optimization tests

**Impact:** Internal enhancement

**Priority:** LOW (future optimization)

## Suggested Phase Ordering for Roadmap

**Recommended Order:**

1. **Phase 1** (Eliminate Global State) - Foundation
   - Rationale: Unblocks all other improvements, critical for testing
   - Risk: High (touches everything)
   - Time: 2-3 weeks

2. **Phase 3** (Qubit Allocator) - Memory Management
   - Rationale: Fixes memory safety issues early
   - Risk: Medium (changes type creation)
   - Time: 1-2 weeks

3. **Phase 2** (Separate Optimizer) - Code Organization
   - Rationale: Improves maintainability without changing APIs
   - Risk: Low (internal refactoring)
   - Time: 1 week

4. **Phase 4** (Refactor Operations) - Module Structure
   - Rationale: Logical separation, easier testing
   - Risk: Low (internal refactoring)
   - Time: 1 week

5. **Phase 5** (Update Python Bindings) - User API
   - Rationale: Expose improvements to users
   - Risk: High (user-facing changes)
   - Time: 2 weeks

6. **Phase 6** (Explicit DAG) - Advanced Features
   - Rationale: Enables future optimizations
   - Risk: Low (additive change)
   - Time: 2-3 weeks (can be deferred)

**Critical Path:** Phases 1 → 3 → 5 (core restructuring)

**Parallel Opportunities:** Phases 2 and 4 can happen in parallel after Phase 1

## Scalability Considerations

| Concern | At 10 qubits | At 100 qubits | At 1000+ qubits |
|---------|--------------|---------------|-----------------|
| **Circuit Storage** | Current layer-based structure adequate | Same, memory ~O(gates) | May need sparse representation |
| **Layer Assignment** | O(gates × qubits) acceptable | Same algorithm works | Consider incremental/cached approach |
| **Gate Merging** | Full scan OK | Same | May need indexing (qubit → gates map) |
| **Memory Allocation** | Block allocation (QUBIT_BLOCK=128) works | Same | May need arena allocator |
| **QASM Export** | Linear scan fine | Same | Same (I/O-bound) |
| **Python Overhead** | Negligible | Noticeable for tight loops | Consider batching operations |

**Current Implementation:** Already uses good scaling patterns (block allocation, layer-based optimization)

**Future Enhancements (if needed):**
- Sparse DAG representation for large circuits
- Incremental optimization (reoptimize only changed subgraphs)
- Arena allocator for batch allocation/deallocation
- Parallel layer assignment (independent qubits)

## Sources

- [Extending Python for Quantum-classical Computing via Quantum Just-in-time Compilation](https://dl.acm.org/doi/10.1145/3544496)
- [QuTiP Development Roadmap](https://qutip.readthedocs.io/en/latest/development/roadmap.html)
- [Qiskit Backends: what they are and how to work with them](https://medium.com/qiskit/qiskit-backends-what-they-are-and-how-to-work-with-them-fb66b3bd0463)
- [Review of intermediate representations for quantum computing](https://link.springer.com/article/10.1007/s11227-024-06892-2)
- [HUGR: A Quantum-Classical Intermediate Representation](https://arxiv.org/pdf/2510.11420)
- [Interrupt: Practical Design Patterns: Opaque Pointers and Objects in C](https://interrupt.memfault.com/blog/opaque-pointers)
- [mbedded.ninja: Opaque Pointers](https://blog.mbedded.ninja/programming/design-patterns/opaque-pointers/)
- [The Encapsulate Context Pattern](https://accu.org/journals/overload/12/63/kelly_246/)
- [Circuit Transformations for Quantum Architectures](https://arxiv.org/pdf/1902.09102)
- [Quantum Circuit Synthesis and Compilation Optimization: Overview and Prospects](https://arxiv.org/html/2407.00736v1)
- [TDAG: Tree-based Directed Acyclic Graph Partitioning for Quantum Circuits](https://www.ornl.gov/publication/tdag-tree-based-directed-acyclic-graph-partitioning-quantum-circuits)
- [A Model-Driven Framework for Composition-Based Quantum Circuit Design](https://dl.acm.org/doi/10.1145/3688856)
- [Introduction to Qiskit patterns](https://docs.quantum.ibm.com/guides/intro-to-patterns)
