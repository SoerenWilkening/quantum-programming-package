# Architecture: Automatic Uncomputation with Dependency Tracking

**Domain:** Automatic uncomputation for quantum circuit generators
**Researched:** 2026-01-28
**Confidence:** HIGH (verified with multiple academic sources and existing implementations)

## Executive Summary

Automatic uncomputation with dependency tracking requires three architectural components: (1) a dependency graph tracking which qubits/values depend on which intermediates, (2) a reverse gate generator that creates adjoint circuits for uncomputation, and (3) integration with object lifetime management to trigger uncomputation at scope exit. The architecture must decide whether tracking happens at Python level (easier integration, higher overhead) or C level (more complex, better performance). Research shows hybrid approaches work best: Python tracks high-level dependencies, C generates reverse gates.

## Current Architecture (Baseline)

### Existing 3-Layer Architecture

```
┌─────────────────────────────────────────┐
│         Python Layer (Frontend)          │
│  - qint/qbool classes                    │
│  - Operator overloading                  │
│  - Context manager (with statement)      │
│  - Object lifecycle (__init__, __del__)  │
└─────────────────┬───────────────────────┘
                  │ Cython bindings
┌─────────────────▼───────────────────────┐
│      Cython Layer (python-backend/)      │
│  - quantum_language.pyx                  │
│  - Wraps C functions                     │
│  - Converts Python→C types               │
└─────────────────┬───────────────────────┘
                  │ C function calls
┌─────────────────▼───────────────────────┐
│         C Layer (Backend/)               │
│  - gate.c: Gate primitives               │
│  - circuit.c: Circuit management         │
│  - arithmetic_ops.c, comparison_ops.c    │
│  - bitwise_ops.c                         │
│  - qubit_allocator.c: Centralized alloc  │
└──────────────────────────────────────────┘
```

**Key characteristics:**
- **Stateless C functions**: All take explicit `circuit_t*` parameter
- **Centralized qubit allocator**: Tracks ownership, reuses freed qubits
- **Python object lifecycle**: `__init__` allocates qubits, `__del__` frees them
- **Right-aligned qubit arrays**: 64-element arrays support variable width (1-64 bits)
- **Sequence-based operations**: C returns `sequence_t*` gate sequences, Python applies to circuit

### Current Flow (Without Uncomputation)

```
User writes: result = ~a & b

1. Python: intermediate = ~a
   - Calls Q_not() from bitwise_ops.c
   - Allocates new qbool for intermediate
   - Adds gates to circuit

2. Python: result = intermediate & b
   - Calls Q_and() from bitwise_ops.c
   - Allocates new qbool for result
   - Adds gates to circuit

3. Scope exit: Python __del__ called
   - intermediate.__del__() frees qubit to allocator
   - result.__del__() frees qubit to allocator
   - BUT: No uncomputation gates added!
```

**Problem:** Qubits are returned to allocator pool but remain entangled. No reverse gates are generated. Intermediate qubit states "leak" into final result.

## Recommended Architecture: Hybrid Dependency Tracking

Based on research into Silq, Unqomp, Qurts, and analysis of existing codebase, the recommended architecture uses **Python-level dependency tracking with C-level reverse gate generation**.

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                   Python Layer (Extended)                     │
│                                                                │
│  qint/qbool classes (extended):                               │
│    - dependency_list: [qbool] tracking intermediates          │
│    - add_dependency(dep: qbool)                               │
│    - uncompute() triggers cascade                             │
│                                                                │
│  DependencyManager (new):                                     │
│    - track_dependency(result, intermediate)                   │
│    - cascade_uncompute(target)                                │
│    - topological_sort(deps) for correct order                 │
│                                                                │
│  Context Manager (extended):                                  │
│    - __exit__ triggers uncomputation for scope temporaries    │
│                                                                │
└───────────────────────┬──────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│                 Cython Layer (Extended)                       │
│                                                                │
│  - Expose reverse_sequence(seq) binding                       │
│  - Expose uncompute_qubit(circuit, qubit, history)            │
│                                                                │
└───────────────────────┬──────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│                  C Layer (New Components)                     │
│                                                                │
│  reverse_gate_generator.c:                                    │
│    - reverse_sequence(sequence_t*) → sequence_t*              │
│    - reverse_gate(gate_t) → gate_t                            │
│                                                                │
│  uncomputation.c:                                             │
│    - apply_uncomputation(circuit_t*, qubit_t*, sequence_t*)   │
│                                                                │
│  Modified qubit_allocator.c:                                  │
│    - Track gate history per qubit (optional)                  │
│    - allocator_mark_computed(qubit, sequence)                 │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Lives In | Communicates With |
|-----------|---------------|----------|-------------------|
| **DependencyManager** | Track qbool→qbool dependencies, topological sort | Python (new class) | qint/qbool classes |
| **qbool.dependency_list** | Store list of intermediates this value depends on | Python (extend qbool) | DependencyManager |
| **qbool.uncompute()** | Trigger cascade uncomputation in reverse order | Python (new method) | DependencyManager, Cython bindings |
| **reverse_gate_generator** | Generate adjoint sequences (X→X, H→H, P(θ)→P(-θ), CNOT→CNOT) | C (new module) | uncomputation.c |
| **uncomputation.c** | Apply reverse sequence to circuit | C (new module) | circuit.c, reverse_gate_generator.c |
| **qubit_allocator** | (Optional) Track gate history per qubit | C (extended) | uncomputation.c |

### Data Flow: Automatic Uncomputation

```
User writes: result = ~a & b

Step 1: Create intermediate (~a)
┌────────────────────────────────────────┐
│ intermediate = a.__invert__()          │
│                                         │
│ 1. Allocate qubit for intermediate     │
│ 2. Generate NOT sequence from C         │
│ 3. Apply sequence to circuit            │
│ 4. Record dependency: intermediate.deps = [] │
└────────────────────────────────────────┘

Step 2: Create result (intermediate & b)
┌────────────────────────────────────────┐
│ result = intermediate.__and__(b)       │
│                                         │
│ 1. Allocate qubit for result            │
│ 2. Generate AND sequence from C          │
│ 3. Apply sequence to circuit             │
│ 4. Record dependency:                    │
│    result.deps = [intermediate]          │
│    DependencyManager.track(result, intermediate) │
└────────────────────────────────────────┘

Step 3: Scope exit triggers uncomputation
┌────────────────────────────────────────┐
│ result.__del__() called                │
│                                         │
│ 1. Check if has dependencies:           │
│    result.deps = [intermediate]         │
│                                          │
│ 2. Call result.uncompute():              │
│    a. For each dep in deps (reversed):  │
│       - Call dep.uncompute() (recursive)│
│    b. Generate reverse sequence for      │
│       operations that created result     │
│    c. Apply reverse sequence to circuit  │
│    d. Free qubit to allocator            │
│                                          │
│ 3. intermediate.uncompute():            │
│    a. intermediate.deps = [] (no deps)  │
│    b. Generate reverse NOT sequence      │
│    c. Apply to circuit                   │
│    d. Free qubit to allocator            │
└────────────────────────────────────────┘
```

## Integration Points with Existing Components

### 1. Python qbool Class (quantum_language.pyx)

**Current state (line ~2157):**
```python
cdef class qbool(qint):
    def __init__(self, value=False, ...):
        super().__init__(value, width=1, ...)

    def __del__(self):
        if self.allocated_qubits:
            alloc = circuit_get_allocator(...)
            allocator_free(alloc, self.allocated_start, self.bits)
```

**Integration point:** Extend `__del__` to call `uncompute()` before freeing:
```python
cdef class qbool(qint):
    cdef public list dependency_list  # Track intermediates

    def __init__(self, value=False, ...):
        super().__init__(value, width=1, ...)
        self.dependency_list = []

    def uncompute(self):
        """Uncompute this qbool and its dependencies."""
        # Cascade to dependencies first (reverse order)
        for dep in reversed(self.dependency_list):
            dep.uncompute()

        # Generate and apply reverse gates for self
        if self.allocated_qubits and self.creation_sequence:
            reversed_seq = reverse_sequence(self.creation_sequence)
            apply_uncomputation(_circuit, self.qubits, reversed_seq)

    def __del__(self):
        if self.allocated_qubits:
            self.uncompute()  # NEW: Uncompute before freeing
            alloc = circuit_get_allocator(...)
            allocator_free(alloc, self.allocated_start, self.bits)
```

### 2. Bitwise Operations (bitwise_ops.c)

**Current state:** Returns `sequence_t*` for operations (Q_not, Q_and, Q_xor, Q_or)

**Integration point:** No changes needed to C functions. Python layer tracks which sequence created which qbool:

```python
def __invert__(self):  # ~self (NOT)
    result = qbool()
    seq = Q_not(self.bits)  # Get sequence from C
    run_instruction(seq, qubit_array, False, _circuit)
    result.creation_sequence = seq  # NEW: Track sequence
    result.dependency_list = []     # NEW: No deps for NOT
    return result

def __and__(self, other):  # self & other
    result = qbool()
    seq = Q_and(self.bits)  # Get sequence from C
    run_instruction(seq, qubit_array, False, _circuit)
    result.creation_sequence = seq       # NEW: Track sequence
    result.dependency_list = [self, other]  # NEW: Track deps
    return result
```

### 3. Comparison Operations (comparison_ops.c)

**Current state (line ~1426):** qint comparisons return qbool:
```python
def __eq__(self, other):
    result = qbool()
    seq = CQ_equal_width(self.bits, other)
    run_instruction(seq, ...)
    return result
```

**Integration point:** Track comparison intermediates:
```python
def __eq__(self, other):
    result = qbool()
    seq = CQ_equal_width(self.bits, other)
    run_instruction(seq, ...)
    result.creation_sequence = seq
    # For qint == qint, dependencies created during subtract-add-back
    # are already tracked. result depends on operands (no new intermediates).
    result.dependency_list = []
    return result
```

### 4. Context Manager (with statement)

**Current state (line ~546):** `__enter__` sets `_controlled = True`, `__exit__` resets.

**Integration point:** Track temporaries created within context and uncompute on exit:

```python
# Global tracking for context-local temporaries
cdef list _context_temporaries = []

def __enter__(self):
    global _controlled, _control_bool, _context_temporaries
    _controlled = True
    _control_bool = self
    _context_temporaries.append([])  # New scope
    return self

def __exit__(self, exc_type, exc, tb):
    global _controlled, _control_bool, _context_temporaries

    # Uncompute all temporaries created in this context
    temporaries = _context_temporaries.pop()
    for temp in reversed(temporaries):  # Reverse order
        temp.uncompute()

    _controlled = False
    _control_bool = None
    return False
```

### 5. Qubit Allocator (qubit_allocator.c)

**Current state:** Tracks allocation/deallocation, reuses freed qubits.

**Integration point (optional):** Track gate history per qubit for more sophisticated uncomputation:

```c
// Extension to qubit_allocator_t (optional, for Phase 2)
typedef struct {
    qubit_t *indices;
    num_t capacity;
    num_t next_qubit;
    num_t freed_count;
    qubit_t *freed_stack;
    num_t freed_capacity;
    allocator_stats_t stats;

    // NEW: Optional gate history tracking
    sequence_t **qubit_history;  // [qubit_id] -> sequence that created it
    num_t history_capacity;

#ifdef DEBUG_OWNERSHIP
    char **owner_tags;
    num_t owner_capacity;
#endif
} qubit_allocator_t;

// NEW: Mark qubit as computed with sequence
void allocator_mark_computed(qubit_allocator_t *alloc, qubit_t q, sequence_t *seq);

// NEW: Get sequence that created qubit
sequence_t* allocator_get_history(qubit_allocator_t *alloc, qubit_t q);
```

**Rationale:** Optional for Phase 1. Python-level tracking is sufficient for basic uncomputation. C-level history tracking enables more advanced optimizations (merging uncomputation sequences, detecting recomputation).

## New Components Needed

### 1. reverse_gate_generator.c (C layer)

**Purpose:** Generate adjoint (reverse) sequences for uncomputation.

**API:**
```c
/**
 * @file reverse_gate_generator.h
 * @brief Reverse gate generation for automatic uncomputation.
 */

#ifndef REVERSE_GATE_GENERATOR_H
#define REVERSE_GATE_GENERATOR_H

#include "types.h"

/**
 * @brief Reverse a single gate (generate adjoint).
 *
 * Gate reversals:
 * - X → X (self-adjoint)
 * - Y → Y (self-adjoint)
 * - Z → Z (self-adjoint)
 * - H → H (self-adjoint)
 * - CNOT → CNOT (self-adjoint)
 * - P(θ) → P(-θ)
 * - Rx(θ) → Rx(-θ)
 * - Ry(θ) → Ry(-θ)
 * - Rz(θ) → Rz(-θ)
 *
 * @param g Gate to reverse
 * @return Reversed gate (caller owns)
 */
gate_t reverse_gate(gate_t *g);

/**
 * @brief Reverse an entire sequence (generate adjoint circuit).
 *
 * Reverses gate order and applies adjoint to each gate.
 * Result: seq[n-1]† → seq[n-2]† → ... → seq[0]†
 *
 * @param seq Sequence to reverse
 * @return Reversed sequence (caller owns, must free with free_sequence)
 *
 * OWNERSHIP: Caller owns returned sequence_t*, must free
 */
sequence_t* reverse_sequence(sequence_t *seq);

/**
 * @brief Check if sequence is reversible (all gates have adjoints).
 *
 * @param seq Sequence to check
 * @return 1 if reversible, 0 otherwise
 */
int is_reversible(sequence_t *seq);

#endif // REVERSE_GATE_GENERATOR_H
```

**Implementation notes:**
- Most quantum gates are self-adjoint (X, Y, Z, H, CNOT)
- Phase gates require sign flip: P(θ) → P(-θ)
- Sequence reversal: gates applied in reverse order
- Layer structure must be rebuilt (gates reordered into new layers)

### 2. uncomputation.c (C layer)

**Purpose:** Apply uncomputation to circuit.

**API:**
```c
/**
 * @file uncomputation.h
 * @brief Apply uncomputation to quantum circuit.
 */

#ifndef UNCOMPUTATION_H
#define UNCOMPUTATION_H

#include "types.h"
#include "circuit.h"

/**
 * @brief Apply uncomputation sequence to circuit.
 *
 * Applies reversed sequence to specified qubits, effectively
 * uncomputing the original operation.
 *
 * @param circ Circuit to modify
 * @param qubits Qubit array (indices to uncompute)
 * @param reversed_seq Reversed sequence from reverse_sequence()
 * @return 0 on success, -1 on error
 */
int apply_uncomputation(circuit_t *circ, qubit_t *qubits, sequence_t *reversed_seq);

/**
 * @brief Uncompute a qbool value (Python-level helper).
 *
 * High-level function that:
 * 1. Retrieves sequence that created qbool
 * 2. Reverses the sequence
 * 3. Applies to circuit
 *
 * @param circ Circuit
 * @param qubit Qubit to uncompute
 * @param creation_seq Sequence that created this qubit's value
 * @return 0 on success, -1 on error
 */
int uncompute_qubit(circuit_t *circ, qubit_t qubit, sequence_t *creation_seq);

#endif // UNCOMPUTATION_H
```

**Implementation notes:**
- Reuses existing `add_gate()` infrastructure
- No new gate types needed
- Layering handled by circuit.c's existing logic

### 3. DependencyManager (Python layer)

**Purpose:** Centralized dependency tracking and topological sorting.

**API:**
```python
class DependencyManager:
    """Manage qbool dependency graph for automatic uncomputation.

    Tracks dependencies between qbool values and provides
    topological sorting for correct uncomputation order.
    """

    def __init__(self):
        self.dependencies = {}  # {qbool_id: [dep1, dep2, ...]}

    def track_dependency(self, result: qbool, intermediate: qbool):
        """Record that result depends on intermediate."""
        if id(result) not in self.dependencies:
            self.dependencies[id(result)] = []
        self.dependencies[id(result)].append(intermediate)

    def get_dependencies(self, qbool: qbool) -> list:
        """Get all dependencies for a qbool."""
        return self.dependencies.get(id(qbool), [])

    def cascade_uncompute(self, target: qbool):
        """Uncompute target and all dependencies in correct order.

        Uses topological sort to ensure dependencies are
        uncomputed in reverse creation order.
        """
        visited = set()

        def visit(node):
            if id(node) in visited:
                return
            visited.add(id(node))

            # Recursively visit dependencies first
            for dep in self.get_dependencies(node):
                visit(dep)

            # Uncompute this node
            node._uncompute_self()  # Internal method

        visit(target)

    def clear(self):
        """Clear all tracked dependencies."""
        self.dependencies.clear()

# Global instance
_dependency_manager = DependencyManager()
```

**Rationale:** Centralized manager enables:
- Cycle detection (error case: `a = b; b = a`)
- Global dependency visualization for debugging
- Weak reference tracking (avoid keeping qbools alive)

## Architecture Patterns

### Pattern 1: Dependency Tracking on Creation

**What:** Every qbool operation records its dependencies at creation time.

**When:** During operator overloading (`__invert__`, `__and__`, `__xor__`, `__or__`, comparisons).

**Implementation:**
```python
def __and__(self, other):
    result = qbool()
    # ... generate gates ...
    result.dependency_list = [self, other]  # Track dependencies
    result.creation_sequence = seq          # Track creating sequence
    return result
```

**Benefits:**
- Simple: dependency recorded when known
- No retroactive graph building
- Clear ownership: result owns its dependency list

### Pattern 2: Cascade Uncomputation on Destruction

**What:** `__del__` triggers recursive uncomputation before freeing qubits.

**When:** Scope exit, explicit `del`, or garbage collection.

**Implementation:**
```python
def __del__(self):
    if self.allocated_qubits:
        self.uncompute()  # Cascades to dependencies
        allocator_free(...)
```

**Benefits:**
- Automatic: no manual uncompute calls
- Correct ordering: recursive ensures dependencies uncomputed first
- Integrates with existing lifecycle

### Pattern 3: Sequence Reversal for Adjoint

**What:** Reverse gate sequence to generate uncomputation circuit.

**When:** During `uncompute()` call.

**Implementation:**
```c
sequence_t* reverse_sequence(sequence_t *seq) {
    sequence_t *reversed = allocate_sequence(seq->num_layer);

    // Reverse layer order
    for (int layer = 0; layer < seq->num_layer; layer++) {
        int rev_layer = seq->num_layer - 1 - layer;

        // Copy gates, applying adjoint to each
        for (int gate = 0; gate < seq->gates_per_layer[layer]; gate++) {
            reversed->seq[rev_layer][gate] = reverse_gate(&seq->seq[layer][gate]);
        }
        reversed->gates_per_layer[rev_layer] = seq->gates_per_layer[layer];
    }

    return reversed;
}
```

**Benefits:**
- Correct quantum uncomputation (adjoint circuit)
- Reuses existing gate types (no new gate primitives)
- Layer-aware: preserves parallelism

### Pattern 4: Context-Local Uncomputation

**What:** Temporaries created in `with` block are automatically uncomputed on exit.

**When:** `__exit__` of context manager.

**Implementation:**
```python
def __exit__(self, exc_type, exc, tb):
    # Uncompute all context-local temporaries
    for temp in reversed(_context_temporaries[-1]):
        temp.uncompute()
    _context_temporaries.pop()
    return False
```

**Benefits:**
- Matches user expectation: "temporary" means "cleanup on scope exit"
- Reduces qubit usage during long computations
- Integrates with existing `with` statement support

## Anti-Patterns to Avoid

### Anti-Pattern 1: C-Level Dependency Tracking

**What:** Tracking dependencies in C layer with graph data structures.

**Why bad:**
- Complex memory management (C lacks garbage collection)
- Requires exposing graph API to Python
- Duplicates Python object graph structure
- Hard to debug (no introspection)

**Instead:** Track at Python level where object references are natural and memory is managed automatically.

### Anti-Pattern 2: Immediate Uncomputation After Every Operation

**What:** Uncompute intermediates immediately after they're used.

**Why bad:**
- Breaks quantum algorithms that need intermediates
- Example: `a = x & y; b = a | z` — can't uncompute `a` until `b` done
- Forces eager evaluation, prevents optimization

**Instead:** Defer uncomputation until scope exit (lazy uncomputation).

### Anti-Pattern 3: Relying on `__del__` Timing

**What:** Assuming `__del__` called at specific time.

**Why bad:**
- CPython: `__del__` called when refcount=0, but timing varies
- PyPy/other: garbage collection is non-deterministic
- Circular references delay `__del__` indefinitely

**Instead:** Provide explicit `uncompute()` method for deterministic cleanup. Use `__del__` as fallback.

### Anti-Pattern 4: Storing Entire Circuit History

**What:** Recording every gate applied to every qubit for uncomputation.

**Why bad:**
- Memory overhead grows linearly with circuit size
- Most gates never need uncomputation (only intermediates)
- Duplicates information already in circuit structure

**Instead:** Only track creation sequences for qbools that might need uncomputation (intermediates). Main results don't need history.

### Anti-Pattern 5: Global State for Dependencies

**What:** Single global dependency graph for all circuits.

**Why bad:**
- Multiple circuits can't coexist
- Thread-unsafe
- No isolation between computations

**Instead:** Dependency tracking tied to circuit instance (already global per module, but could be circuit-local in future).

## Scalability Considerations

| Concern | At 10 qbools | At 100 qbools | At 1000 qbools |
|---------|--------------|---------------|----------------|
| **Dependency tracking** | Python list (~10 refs) | Python list (~100 refs) | Consider weak references to avoid keeping all alive |
| **Sequence storage** | Keep all sequences | Keep all sequences | Consider lazy loading or discarding sequences for long-lived qbools |
| **Uncomputation cost** | O(gates) per qbool | O(gates) per qbool | Optimize: batch uncomputation, merge sequences |
| **Memory overhead** | Negligible | ~KB per qbool | Switch to C-level tracking or sparse representation |

### Optimization Strategies

**Phase 1 (MVP):** Python-level tracking, immediate sequence reversal
- Simple, correct, sufficient for <100 qbools
- No C API changes
- Easy to debug

**Phase 2 (Optimization):** Lazy sequence reversal, weak references
- Generate reverse sequence only when needed
- Use `weakref.ref` to avoid keeping dependencies alive unnecessarily
- Python-only changes

**Phase 3 (Advanced):** C-level sequence merging
- Merge multiple uncomputation sequences into single optimized sequence
- Requires C API for sequence manipulation
- Significant gate count reduction for complex expressions

## Qubit-Saving Mode (Future Extension)

**Goal:** Minimize peak qubit usage by uncomputing intermediates eagerly.

**Architecture:**
```python
# User enables qubit-saving mode
ql.option("qubit_saving", True)

# Now intermediates are uncomputed immediately after use
result = ~a & b  # Intermediate (~a) uncomputed right after AND
```

**Implementation:**
- Track "last use" of each qbool
- Uncompute immediately after last use, not at scope exit
- Requires dataflow analysis to determine last use
- Trade-off: More gates (less optimization opportunity) for fewer qubits

**Integration point:** Extend `DependencyManager` with reference counting:
```python
class DependencyManager:
    def record_use(self, qbool):
        self.use_count[id(qbool)] += 1

    def record_last_use(self, qbool):
        if _qubit_saving_enabled:
            qbool.uncompute()  # Immediate uncomputation
```

## Build Order (Suggested Phasing)

### Phase 1: Core Uncomputation (Python-level tracking)

**Components:**
1. `reverse_gate_generator.c` + `.h`
2. `uncomputation.c` + `.h`
3. Cython bindings for reverse_sequence, apply_uncomputation
4. Extend qbool with `dependency_list`, `creation_sequence`, `uncompute()`
5. Modify `__del__` to call `uncompute()`

**Integration points:**
- Extend qbool class in quantum_language.pyx
- Add two new C modules (reverse_gate_generator, uncomputation)
- Update Cython bindings

**Test coverage:**
- Unit test: reverse_sequence for each gate type
- Unit test: apply_uncomputation adds correct gates
- Integration test: `a = ~b; del a` uncomputes NOT
- Integration test: `result = a & b & c; del result` uncomputes in correct order

**Success criteria:**
- Intermediate qubits correctly uncomputed
- Circuit gates include adjoint sequences
- No memory leaks (valgrind clean)

### Phase 2: Dependency Tracking (DependencyManager)

**Components:**
1. `DependencyManager` Python class
2. Integrate into operator overloading
3. Update comparison operations to track dependencies

**Integration points:**
- Modify `__and__`, `__or__`, `__xor__`, `__invert__` in qbool
- Modify `__eq__`, `__lt__`, `__gt__`, etc. in qint

**Test coverage:**
- Test: Dependencies tracked for bitwise ops
- Test: Dependencies tracked for comparisons
- Test: Cascade uncomputation for nested expressions
- Test: No duplicate uncomputation (if intermediate used twice)

**Success criteria:**
- Complex expressions uncompute all intermediates
- Topological sort handles arbitrary dependency graphs
- No crashes on circular references (error raised)

### Phase 3: Context Manager Integration

**Components:**
1. Extend `__enter__` to push context scope
2. Extend `__exit__` to uncompute context temporaries
3. Track temporaries created within `with` block

**Integration points:**
- Modify qint/qbool `__enter__` and `__exit__`
- Add global `_context_temporaries` stack

**Test coverage:**
- Test: `with flag: temp = a & b` — temp uncomputed on exit
- Test: Nested `with` blocks uncompute correctly
- Test: Exception in `with` block still uncomputes

**Success criteria:**
- Temporaries in `with` blocks auto-uncomputed
- Scope exit triggers uncomputation before control qbool freed
- No interference with existing controlled gate functionality

### Phase 4: Optional Qubit History (C-level)

**Components:**
1. Extend `qubit_allocator_t` with history tracking
2. `allocator_mark_computed`, `allocator_get_history` functions
3. Python bindings for history access

**Integration points:**
- Modify qubit_allocator.c
- Add Cython bindings

**Test coverage:**
- Test: History recorded on allocation
- Test: History retrieved correctly
- Test: History cleared on deallocation

**Success criteria:**
- Optional feature (disabled by default)
- Enables future optimizations (sequence merging, recomputation detection)
- No performance impact when disabled

## Dependency Flow Diagram

```
User Code:
    cross_win = ~(count_cross_wins < 1)

Step 1: count_cross_wins < 1 creates intermediate temp1
    temp1 = count_cross_wins.__lt__(1)
    temp1.deps = []
    temp1.creation_seq = CQ_less_than(bits, 1)

Step 2: ~temp1 creates cross_win
    cross_win = temp1.__invert__()
    cross_win.deps = [temp1]
    cross_win.creation_seq = Q_not(1)

Scope exit: cross_win.__del__()
    1. cross_win.uncompute()
       a. For dep in reversed([temp1]):
          - temp1.uncompute()
            i. temp1.deps = [] (no further deps)
            ii. rev_seq = reverse_sequence(temp1.creation_seq)
            iii. apply_uncomputation(circuit, temp1.qubits, rev_seq)
       b. rev_seq = reverse_sequence(cross_win.creation_seq)
       c. apply_uncomputation(circuit, cross_win.qubits, rev_seq)
    2. allocator_free(cross_win.qubits)
```

## References and Confidence Assessment

### HIGH Confidence Sources

**Silq (ETH Zurich, PLDI 2020):**
- [Silq: A High-Level Quantum Language with Safe Uncomputation](https://dl.acm.org/doi/10.1145/3385412.3386007)
- Type system ensures uncomputation safety
- Automatic uncomputation based on classical evaluation patterns
- Demonstrates feasibility of compiler-driven uncomputation

**Unqomp (ETH Zurich, PLDI 2021):**
- [Unqomp: Synthesizing Uncomputation in Quantum Circuits](https://github.com/eth-sri/Unqomp)
- Integrates with Qiskit via Python extension
- Uses dependency graph in `dependencygraph.py`
- Demonstrates Python-level tracking with C-level (Qiskit) integration

**Qurts (2024, ACM POPL 2025):**
- [Qurts: Automatic Quantum Uncomputation by Affine Types with Lifetime](https://arxiv.org/abs/2411.10835)
- Uses Rust's lifetime tracking for scope-based uncomputation
- Affine types during lifetime, linear types outside
- Demonstrates type-system-driven automatic uncomputation

**TUSQ (2025):**
- [Noisy Quantum Simulation Using Tracking, Uncomputation and Sampling](https://arxiv.org/abs/2508.04880)
- Tree-based execution with dependency tracking
- Uncomputation for rollback-recovery
- 52.5× speedup over Qiskit via uncomputation

### MEDIUM Confidence Sources

**Modular Synthesis (OOPSLA 2024):**
- [Modular Synthesis of Efficient Quantum Uncomputation](https://arxiv.org/pdf/2406.14227)
- Intermediate representation for expressive quantum programs
- Modular algorithms for synthesizing adjoints
- Demonstrates IR-based approach

**Scalable Memory Recycling (March 2025):**
- [Scalable Memory Recycling for Large Quantum Programs](https://arxiv.org/pdf/2503.00822)
- Control flow graph for quantum code
- Scheduling uncomputation operations
- Qubit reuse via dependency analysis

**DAG-based Intermediate Representations:**
- [Quantum Circuit Optimization Review](https://arxiv.org/pdf/2408.08941)
- DAG structure for gate dependencies
- Standard approach in Qiskit, TKET
- Well-understood for dependency tracking

### Python Lifetime Management

**Python Reference Counting:**
- [Managing Python Object Lifecycles (2025)](https://www.oreateai.com/blog/managing-python-object-lifecycles-an-indepth-analysis-of-the-del-destructor-method-and-garbage-collection-mechanism/fe335ac233f71becd8d2e930c3c32419)
- [Python 3.14 Data Model](https://docs.python.org/3/reference/datamodel.html)
- `__del__` called when refcount=0
- Circular references require garbage collector

**Weak References:**
- [Python Weak References in 2025](https://medium.com/pythoneers/python-weak-references-in-2025-a-simpler-way-to-work-with-the-garbage-collector-26517aebde2e)
- `weakref.ref` for non-owning references
- `weakref.finalize` for cleanup callbacks
- Avoids circular reference issues

## Summary: Architecture Confidence

| Area | Confidence | Reasoning |
|------|------------|-----------|
| **Python-level tracking** | HIGH | Proven by Unqomp, natural Python idiom, matches existing codebase patterns |
| **C-level reverse gate generation** | HIGH | Standard quantum computing technique (adjoint circuits), well-understood |
| **Dependency graph approach** | HIGH | Used by Silq, Unqomp, TUSQ, standard compiler technique |
| **Integration with existing code** | HIGH | Analyzed actual codebase, identified specific integration points |
| **`__del__` for uncomputation trigger** | MEDIUM | Works in CPython, but timing non-deterministic; explicit `uncompute()` safer |
| **Context manager integration** | HIGH | Natural Python idiom, matches existing `with` statement support |
| **Qubit-saving mode** | MEDIUM | Research prototype in literature, requires dataflow analysis |

## Open Questions for Phase-Specific Research

1. **Sequence caching:** Should reversed sequences be cached (memoized) or regenerated each time?
   - Pro cache: Faster uncomputation for repeated patterns
   - Con cache: Memory overhead
   - Research in Phase 1 during performance testing

2. **Weak vs strong references:** Should `dependency_list` use `weakref.ref` or strong references?
   - Strong: Simpler, ensures intermediates not GC'd prematurely
   - Weak: Allows earlier cleanup, more complex
   - Research in Phase 2 during large circuit testing

3. **C-level history tracking:** Is per-qubit history worth the complexity?
   - Enables advanced optimizations (sequence merging)
   - Adds memory overhead and API complexity
   - Research in Phase 4 after basic uncomputation working

4. **Optimization passes:** Should uncomputation sequences go through optimizer?
   - Pro: Gate count reduction, inverse cancellation
   - Con: Correctness concerns (optimizer must preserve semantics)
   - Research in Phase 3 after optimizer integration

---

**Sources:**

Academic Research:
- [Silq: A High-Level Quantum Language with Safe Uncomputation](https://dl.acm.org/doi/10.1145/3385412.3386007)
- [Unqomp: Automated Uncomputation for Quantum Programs](https://github.com/eth-sri/Unqomp)
- [Qurts: Automatic Quantum Uncomputation by Affine Types with Lifetime](https://arxiv.org/abs/2411.10835)
- [TUSQ: Noisy Quantum Simulation Using Tracking, Uncomputation and Sampling](https://arxiv.org/abs/2508.04880)
- [Modular Synthesis of Efficient Quantum Uncomputation](https://arxiv.org/pdf/2406.14227)
- [Scalable Memory Recycling for Large Quantum Programs](https://arxiv.org/pdf/2503.00822)
- [Quantum Circuit Optimization Review](https://arxiv.org/pdf/2408.08941)

Python Resources:
- [Managing Python Object Lifecycles](https://www.oreateai.com/blog/managing-python-object-lifecycles-an-indepth-analysis-of-the-del-destructor-method-and-garbage-collection-mechanism/fe335ac233f71becd8d2e930c3c32419)
- [Python 3.14 Data Model](https://docs.python.org/3/reference/datamodel.html)
- [Python Weak References in 2025](https://medium.com/pythoneers/python-weak-references-in-2025-a-simpler-way-to-work-with-the-garbage-collector-26517aebde2e)
