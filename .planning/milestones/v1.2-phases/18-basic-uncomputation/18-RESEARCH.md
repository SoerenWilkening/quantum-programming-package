# Phase 18: Basic Uncomputation Integration - Research

**Researched:** 2026-01-28
**Domain:** Python memory management, quantum uncomputation, reference counting
**Confidence:** HIGH

## Summary

Phase 18 implements automatic uncomputation of intermediate quantum values when qbool objects go out of scope, using Python's `__del__` destructor and the existing dependency tracking infrastructure from Phase 16. The approach combines Python's reference counting with quantum circuit reversal (Phase 17) to automatically free qubits and restore quantum states.

The research confirms that Python's `__del__` method, combined with weak references from Phase 16, provides a robust foundation for automatic cleanup. The existing `reverse_circuit_range()` C function and `allocator_free()` API are already in place. The main implementation challenge is orchestrating LIFO-order cascading uncomputation while respecting Python's garbage collection semantics.

**Primary recommendation:** Implement `__del__` in the qint/qbool class that triggers uncomputation logic, using the existing dependency graph to cascade cleanup in reverse creation order, with idempotent `.uncompute()` method for explicit control.

## Standard Stack

### Core (Already in Codebase)

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python `__del__` | 3.11+ | Object finalization on garbage collection | Python's standard destructor mechanism, well-documented behavior |
| weakref module | stdlib | Weak references for dependency tracking | Already used in Phase 16, prevents circular references |
| Cython `__del__` | Current | Extension type destructor | Native support in Cython for cleanup logic |
| sys.getrefcount | stdlib | Reference count introspection (debug only) | Standard way to query object reference counts |

### Supporting (Already Implemented)

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| reverse_circuit_range() | Execution/src/execution.c | LIFO gate reversal | Phase 17 complete |
| allocator_free() | Backend/src/qubit_allocator.c | Qubit deallocation | Phase 3 complete |
| dependency_parents | quantum_language.pyx | Weak reference list | Phase 16 complete |
| _creation_order | quantum_language.pyx | LIFO ordering guarantee | Phase 16 complete |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `__del__` destructor | Context managers (`__exit__`) | Context managers are more explicit but Phase 19 will add those—this phase covers implicit cleanup |
| `__del__` destructor | weakref.finalize | finalize() is more flexible but adds complexity; `__del__` is simpler and already used for qubit deallocation |
| Reference counting | Manual tracking | Python's reference counting is automatic and proven; manual tracking error-prone |

**Installation:**
No external dependencies—all components are Python stdlib or already implemented in the codebase.

## Architecture Patterns

### Recommended Uncomputation Flow

```
qbool creation → dependency tracking (Phase 16)
                ↓
qbool goes out of scope → Python GC decrements refcount
                ↓
refcount == 0 → __del__() called
                ↓
Check if already uncomputed (idempotency flag)
                ↓
Get live parent dependencies → sort by _creation_order (descending)
                ↓
Recursively uncompute parents (LIFO order)
                ↓
Reverse this qbool's gates → reverse_circuit_range(start_layer, end_layer)
                ↓
Free this qbool's qubits → allocator_free()
                ↓
Mark as uncomputed (set flag)
```

### Pattern 1: Destructor-Triggered Uncomputation

**What:** Use Python's `__del__` method to trigger automatic uncomputation when garbage collector destroys qbool objects.

**When to use:** Implicit automatic cleanup—user writes natural code without explicit cleanup calls.

**Example (implementation pattern):**
```python
# Source: Phase 18 CONTEXT.md + Python __del__ best practices
cdef class qint:
    cdef bint _is_uncomputed  # Track state for idempotency
    cdef int _start_layer     # Layer before this qbool was created
    cdef int _end_layer       # Layer after this qbool was created

    def __del__(self):
        """Automatic uncomputation on garbage collection."""
        global _circuit

        if self._is_uncomputed or not self.allocated_qubits:
            return  # Already uncomputed or not owner of qubits

        try:
            # Cascade through dependencies first (LIFO order)
            self._cascade_uncompute()

            # Reverse this object's gates
            if self._end_layer > self._start_layer:
                reverse_circuit_range(_circuit, self._start_layer, self._end_layer)

            # Free qubits
            alloc = circuit_get_allocator(<circuit_s*>_circuit)
            if alloc != NULL:
                allocator_free(alloc, self.allocated_start, self.bits)

            self._is_uncomputed = True

        except Exception as e:
            # Phase 18 decision: __del__ failures print warning only
            import sys
            print(f"Warning: Uncomputation failed in __del__: {e}", file=sys.stderr)
```

### Pattern 2: LIFO Cascade Through Dependency Graph

**What:** Uncompute parent dependencies in reverse creation order before uncomputing the child.

**When to use:** When a qbool depends on intermediates that also need cleanup.

**Example (implementation pattern):**
```python
# Source: Phase 16 dependency tracking + quantum uncomputation LIFO
def _cascade_uncompute(self):
    """Recursively uncompute dependencies in LIFO order."""
    live_parents = self.get_live_parents()  # Already implemented in Phase 16

    # Sort by creation order (descending) for LIFO
    # Python guarantees stable sort
    live_parents.sort(key=lambda p: p._creation_order, reverse=True)

    for parent in live_parents:
        if not parent._is_uncomputed:
            # Trigger parent uncomputation
            # This may recursively cascade further
            parent.uncompute()
```

### Pattern 3: Explicit Uncomputation with Safety Checks

**What:** Provide `.uncompute()` method for explicit early uncomputation with reference count validation.

**When to use:** User wants deterministic cleanup point or needs to free qubits earlier than natural scope exit.

**Example (implementation pattern):**
```python
# Source: Phase 18 CONTEXT.md decisions
def uncompute(self):
    """Explicitly uncompute this qbool and its dependencies.

    Raises:
        RuntimeError: If other references exist (refcount > 2).
        RuntimeError: If already uncomputed (idempotent—no error).
    """
    if self._is_uncomputed:
        return  # Idempotent: calling twice is no-op

    # Check reference count (sys.getrefcount returns count + 1 for the argument)
    import sys
    refcount = sys.getrefcount(self)

    # Expected: 2 (one for the variable, one for getrefcount argument)
    # If > 2, other references exist
    if refcount > 2:
        raise RuntimeError(
            f"Cannot explicitly uncompute qbool: {refcount - 1} references still exist"
        )

    # Perform uncomputation (same logic as __del__)
    self._cascade_uncompute()

    if self._end_layer > self._start_layer:
        reverse_circuit_range(_circuit, self._start_layer, self._end_layer)

    alloc = circuit_get_allocator(<circuit_s*>_circuit)
    if alloc != NULL:
        allocator_free(alloc, self.allocated_start, self.bits)

    self._is_uncomputed = True
```

### Pattern 4: Layer Boundary Tracking

**What:** Capture circuit layer indices before and after operations to define reversal range.

**When to use:** Every qbool creation from an operation (comparisons, bitwise ops).

**Example (implementation pattern):**
```python
# Source: Phase 17 layer tracking + existing comparison operators
def __eq__(self, other):
    """Equality comparison with layer tracking for uncomputation."""
    global _circuit

    # Capture layer before operation
    start_layer = (<circuit_s*>_circuit).used_layer

    # Perform comparison (existing implementation)
    result = perform_equality_comparison(self, other)

    # Capture layer after operation
    end_layer = (<circuit_s*>_circuit).used_layer

    # Store layer range in result for future uncomputation
    result._start_layer = start_layer
    result._end_layer = end_layer

    return result
```

### Anti-Patterns to Avoid

- **Raising exceptions in `__del__`:** Python documentation discourages this—use print warnings instead (Phase 18 decision).
- **Assuming immediate finalization:** `__del__` timing is non-deterministic—don't rely on it for time-critical cleanup.
- **Circular references with `__del__`:** Python won't collect cycles containing `__del__` methods—use weak references (already done in Phase 16).
- **Using sys.getrefcount() for logic:** Refcount is unreliable (varies with temporaries)—only use for debug assertions in explicit `.uncompute()`.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Weak reference management | Custom reference tracking | Python weakref module | Already used in Phase 16, handles all edge cases (dead refs, callback timing) |
| Graph traversal ordering | Custom topological sort | Sort by _creation_order field | Phase 16 guarantees parent < child creation order, simple sort suffices |
| Reference counting | Manual refcount tracking | Python's built-in refcount | Automatic, proven, integrates with GC |
| Qubit deallocation | Custom free list | allocator_free() from Phase 3 | Already handles reuse pool, thread-safety, stats |
| Gate reversal | Manual adjoint generation | reverse_circuit_range() from Phase 17 | Already handles phase gates, multi-controlled gates, LIFO iteration |

**Key insight:** Phase 16 and 17 built the infrastructure—Phase 18 just wires them together with Python's destructor mechanism.

## Common Pitfalls

### Pitfall 1: `__del__` Execution Timing

**What goes wrong:** Expecting `__del__` to run immediately when `del variable` is called, but it only runs when refcount reaches zero (may be delayed if other references exist).

**Why it happens:** Python's reference counting is automatic but not instantaneous—temporaries, debuggers, and exception handling can keep references alive.

**How to avoid:**
- Design for non-deterministic timing—don't rely on `__del__` for time-critical cleanup
- Phase 18 decision: implicit uncomputation is silent (no debug output)
- Provide explicit `.uncompute()` for deterministic cleanup points

**Warning signs:**
- Tests failing because qubits aren't freed "soon enough"
- Expecting cleanup in specific order when multiple qbools die simultaneously

### Pitfall 2: Exception Handling in Destructors

**What goes wrong:** Raising exceptions in `__del__` causes cryptic errors and can crash the interpreter during shutdown.

**Why it happens:** `__del__` can be called during garbage collection or interpreter exit when exception handling machinery is unavailable.

**How to avoid:**
- Phase 18 decision: `__del__` failures print warning only, never raise
- Use try/except around all `__del__` logic
- Reserve exceptions for explicit `.uncompute()` method only

**Warning signs:**
- Tests with cryptic "Exception ignored in __del__" messages
- Interpreter crashes during program exit

### Pitfall 3: Circular Dependencies with `__del__`

**What goes wrong:** Objects with `__del__` methods that form reference cycles become uncollectable—memory leak.

**Why it happens:** Python's cycle detector can't determine safe order to call `__del__` methods in a cycle.

**How to avoid:**
- Phase 16 already uses weak references for dependency_parents—no strong reference cycles
- Phase 16 creation order assertion prevents back-edges (parent._creation_order < self._creation_order)
- Trust the Phase 16 design—don't add strong references to parents

**Warning signs:**
- Memory usage grows over time in tests
- gc.garbage list contains qbool objects
- gc.collect() doesn't reduce object count

### Pitfall 4: Double-Free of Qubits

**What goes wrong:** Uncomputing the same qbool twice frees qubits twice, corrupting the allocator's free pool.

**Why it happens:** If user calls `.uncompute()` explicitly and then object goes out of scope, `__del__` also runs.

**How to avoid:**
- Phase 18 decision: explicit `.uncompute()` is idempotent
- Set `_is_uncomputed` flag after first uncomputation
- Check flag at start of both `.uncompute()` and `__del__`

**Warning signs:**
- allocator_free() returns -1 (double-free error)
- Qubit allocation fails mysteriously
- Freed qubit counts don't match allocated counts

### Pitfall 5: Using Qbool After Uncomputation

**What goes wrong:** User tries to use a qbool in operations after it's been explicitly uncomputed, leading to corrupted circuit or crashes.

**Why it happens:** Python doesn't prevent accessing an object after `__del__` runs (unlike C++ where the object is destroyed).

**How to avoid:**
- Phase 18 decision: raise exception "qbool has been uncomputed and cannot be used"
- Check `_is_uncomputed` flag at start of all operations (__and__, __or__, __eq__, etc.)
- Clear error message helps users understand the problem

**Warning signs:**
- Cryptic C backend crashes after uncomputation
- Circuit contains gates on freed qubits
- Tests with "use after free" patterns

### Pitfall 6: Shared Dependency Reference Counting

**What goes wrong:** Uncomputing a qbool that shares a dependency with another live qbool causes premature cleanup of the shared parent.

**Why it happens:** Forgetting that multiple children can depend on the same parent—need to check if parent is still referenced.

**How to avoid:**
- Phase 16 weak references solve this—parent only dies when all children release it
- Use `get_live_parents()` which filters dead weak references
- Python's GC handles reference counting automatically

**Warning signs:**
- Crashes when uncomputing one of two qbools with shared dependency
- Parent qbool uncomputed while still "in use" by another child
- Test failures in chained operations (a & b, a & c)

## Code Examples

Verified patterns from existing implementation and documentation:

### Existing Destructor Pattern (Current Implementation)

```python
# Source: python-backend/quantum_language.pyx lines 606-619
def __del__(self):
    global _controlled, _control_bool, _int_counter, _smallest_allocated_qubit, ancilla
    global _num_qubits
    cdef qubit_allocator_t *alloc

    if self.allocated_qubits:
        # Return qubits to allocator
        alloc = circuit_get_allocator(<circuit_s*>_circuit)
        if alloc != NULL:
            allocator_free(alloc, self.allocated_start, self.bits)

        # Keep backward compat tracking (deprecated)
        _smallest_allocated_qubit -= self.bits
        ancilla -= self.bits
```

### Weak Reference Cleanup Pattern (Existing Phase 16)

```python
# Source: python-backend/test.py lines 149-167
def test_dependency_weak_references():
    """TRACK-03: Weak references allow garbage collection."""
    c = ql.circuit()

    a = ql.qbool(True)
    b = ql.qbool(False)
    result = a & b

    # Both parents alive
    assert len(result.get_live_parents()) == 2

    # Delete one parent
    del a
    gc.collect()

    # Now only one parent should be alive
    live = result.get_live_parents()
    assert len(live) == 1
```

### Circuit Reversal Pattern (Existing Phase 17)

```python
# Source: python-backend/quantum_language.pyx lines 2762-2772
def reverse_instruction_range(int start_layer, int end_layer):
    """Reverse gates in circuit layer range [start_layer, end_layer).

    Used for uncomputation: applies adjoint gates in LIFO order.

    Parameters
    ----------
    start_layer : int
        Starting layer index (inclusive)
    end_layer : int
        Ending layer index (exclusive)
    """
    reverse_circuit_range(_circuit, start_layer, end_layer)
```

### Layer Tracking Pattern (Existing Phase 17)

```python
# Source: python-backend/quantum_language.pyx lines 2750-2760
def get_current_layer():
    """Get current circuit layer index (used for uncomputation tracking).

    Returns
    -------
    int
        Current layer index from circuit.used_layer
    """
    return (<circuit_s*>_circuit).used_layer
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual qubit cleanup | Automatic via `__del__` | Phase 18 (now) | Users don't manually free qubits—natural Python scoping |
| No dependency tracking | Weak reference graph | Phase 16 (v1.2) | Enables cascading uncomputation without cycles |
| Manual gate reversal | LIFO reverse_circuit_range() | Phase 17 (v1.2) | Automatic adjoint generation for all gate types |
| Static qubit allocation | Freed qubit reuse pool | Phase 3 (v1.1) | Enables qubit recycling after uncomputation |
| Global QPU_state | Stateless C backend | Phase 11 (v1.1) | Clean architecture for Python-level uncomputation |

**Recent research (2024-2025):**
- [Modular Synthesis of Efficient Quantum Uncomputation](https://dl.acm.org/doi/pdf/10.1145/3689785) (Oct 2024): First modular automatic uncomputation approach
- [Scalable Memory Recycling for Large Quantum Programs](https://ar5iv.labs.arxiv.org/html/2503.00822) (Mar 2025): Topological sort of control flow graph for qubit reuse optimization

**Deprecated/outdated:**
- Manual `__del__` for qubit deallocation only: Phase 18 extends this to full uncomputation (gates + qubits)
- Context managers for all cleanup: Python 3.4+ allows `__del__` and context managers to coexist—use both (Phase 19 adds context managers)

## Open Questions

Things that couldn't be fully resolved:

1. **Multiple qbools dying in same GC cycle**
   - What we know: Python's GC may finalize multiple objects in single collection pass
   - What's unclear: Guaranteed ordering of `__del__` calls when multiple qbools have same refcount
   - Recommendation: Trust weak reference cleanup—if parent is still alive (refcount > 0), don't uncompute it. LIFO ordering within a single object's cascade is sufficient.

2. **Performance impact of sys.getrefcount() checks**
   - What we know: sys.getrefcount() adds overhead (creates temporary reference)
   - What's unclear: Whether to use it in explicit `.uncompute()` or trust user
   - Recommendation: Use it with clear documentation that refcount > 2 means "other references exist". Mark as LOW confidence—may remove in future if problematic.

3. **Interaction with Python debuggers**
   - What we know: Debuggers keep references to local variables, delaying `__del__`
   - What's unclear: Whether to document this as expected behavior or add debug mode
   - Recommendation: Document as expected—implicit uncomputation is best-effort, explicit `.uncompute()` for determinism

## Sources

### Primary (HIGH confidence)

- [Python 3.14 Data Model Documentation](https://docs.python.org/3/reference/datamodel.html) - `__del__` method specification and best practices
- [Python weakref module documentation](https://docs.python.org/3/library/weakref.html) - Weak reference API and garbage collection interaction
- [Cython Special Methods documentation](https://cython.readthedocs.io/en/latest/src/userguide/special_methods.html) - `__del__` vs `__dealloc__` in Cython
- Existing codebase: quantum_language.pyx (Phase 16 dependency tracking, existing `__del__` for qubits)
- Existing codebase: execution.c (Phase 17 reverse_circuit_range implementation)
- Existing codebase: qubit_allocator.c (Phase 3 allocator_free implementation)

### Secondary (MEDIUM confidence)

- [Safely Using Destructors in Python](https://eli.thegreenplace.net/2009/06/12/safely-using-destructors-in-python) - Best practices for `__del__` (verified with official docs)
- [Quantum Computing Uncomputation](https://grokipedia.com/page/uncomputation) - LIFO reverse order pattern (verified with research papers)
- [A Guide to Python's Weak References](https://medium.com/data-science/a-guide-to-pythons-weak-references-using-weakref-module-d3381b01db99) - Weak reference patterns
- [Garbage Collection in Python](https://rushter.com/blog/python-garbage-collector/) - Reference counting mechanics

### Tertiary (LOW confidence - research papers, recent)

- [Modular Synthesis of Efficient Quantum Uncomputation](https://dl.acm.org/doi/pdf/10.1145/3689785) (ACM 2024) - Recent research on automatic uncomputation
- [Scalable Memory Recycling for Large Quantum Programs](https://ar5iv.labs.arxiv.org/html/2503.00822) (2025) - Topological sort for qubit reuse

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components are Python stdlib or already implemented in codebase
- Architecture: HIGH - Pattern is well-established in Python (destructor + weak refs), proven by Phase 16 implementation
- Pitfalls: HIGH - Based on official Python documentation warnings + existing codebase experience

**Research date:** 2026-01-28
**Valid until:** 90 days (Python stdlib stable, codebase architecture stable)

**Phase 18 specific notes:**
- CONTEXT.md provides clear implementation decisions—no ambiguity
- Phase 16 and 17 infrastructure is complete and tested
- Main work is orchestration layer, not new concepts
- All required C functions already exist (reverse_circuit_range, allocator_free)
- Python patterns are well-documented and proven
