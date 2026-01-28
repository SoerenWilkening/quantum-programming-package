# Technology Stack: Automatic Uncomputation with Dependency Tracking

**Project:** Quantum Assembly Language - Automatic Uncomputation Milestone
**Researched:** 2026-01-28
**Confidence:** HIGH

## Executive Summary

Automatic uncomputation requires dependency tracking to determine when intermediate qbool/qint results can be safely uncomputed. The existing three-layer stateless architecture (C backend → Cython → Python frontend) constrains where tracking can occur. Research indicates **Python-level dependency tracking with C-level circuit generation** is the optimal pattern, avoiding the complexity of C-level object graphs while maintaining the performance-critical circuit generation in C.

## Recommended Patterns

### Core Pattern: Python-Level Dependency Graph

| Component | Technology | Purpose | Why |
|-----------|-----------|---------|-----|
| Dependency Storage | Python list/dict | Track parent→children relationships | Native Python collections; no external dependency; O(1) lookups |
| Lifetime Management | `weakref.finalize` | Trigger uncomputation on GC | Reliable cleanup without `__del__` pitfalls (PEP 442) |
| Reference Tracking | `weakref.ref` | Track dependencies without preventing GC | Prevents circular reference issues; allows natural GC |
| Uncomputation Trigger | Python callback | Invoke C circuit generation | Clean separation of tracking (Python) and generation (C) |

**Why Python-level tracking:**
- Existing architecture is stateless at C level (no object lifecycle)
- Python already manages qint/qbool object lifetimes
- Dependency graph mutations are infrequent (creation-time only)
- Avoids retrofitting object lifecycle into C backend

**Why NOT C-level tracking:**
- C backend is stateless by design (circuit_t is just gate storage)
- Would require adding object lifecycle management to C
- Python already has robust GC and weak reference support
- Cython bindings would need complex memory ownership logic

### Alternative Pattern: C-Level Dependency Tracking (NOT RECOMMENDED)

| Component | Technology | Purpose | Why NOT |
|-----------|-----------|---------|---------|
| Dependency Storage | C linked list | Track parent→child pointers | Complex memory management; no native weak references |
| Lifetime Management | Manual ref counting | Track object lifetimes | Error-prone; duplicates Python's GC; no weak reference support |
| Uncomputation | C function | Generate inverse gates | Already possible; tracking is the hard part |

**Rejection rationale:**
- C has no weak reference equivalent (would need manual ref counting)
- Existing architecture is stateless at C level
- Duplicates Python's GC machinery
- Increases Cython binding complexity (ownership transfer)

## Dependency Tracking Approach

### Data Structure: Dependency Graph

```python
# Python-level tracking in qint/qbool base class or circuit singleton
class DependencyTracker:
    def __init__(self):
        # Map: dependent object -> list of parent dependencies
        self._dependencies = {}  # dict[int(id(obj)), list[weakref.ref]]

        # Map: object -> finalization callback
        self._finalizers = {}  # dict[int(id(obj)), weakref.finalize]
```

**Storage rationale:**
- `dict` provides O(1) lookup by object ID
- `weakref.ref` allows parent garbage collection without blocking
- `weakref.finalize` provides reliable cleanup trigger (PEP 442)

**Why NOT NetworkX:**
- Dependency graphs are simple (parent→child edges only)
- No need for graph algorithms (topological sort, cycle detection)
- Avoid external dependency for simple use case
- Native Python dict/list sufficient

### Lifetime Pattern: weakref.finalize (Not __del__)

```python
# Pattern: Register finalization callback at creation time
class qbool(qint):
    def __init__(self, ...):
        super().__init__(...)

        # Register uncomputation callback
        if has_dependencies:
            finalizer = weakref.finalize(
                self,
                self._uncompute_callback,
                self.qubits,  # Pass data, not self reference
                self.dependencies
            )
            tracker.register_finalizer(id(self), finalizer)
```

**Why `weakref.finalize` over `__del__`:**
- **Reliability:** `__del__` not guaranteed to be called (circular refs, interpreter exit)
- **Order:** `weakref.finalize` respects dependency order
- **PEP 442:** Modern Python (3.4+) finalization is safer but `weakref.finalize` still preferred
- **Testing:** Finalizers can be triggered manually for tests

**Sources:**
- [Python weakref documentation](https://docs.python.org/3/library/weakref.html) - Official Python 3.14.2 docs (Jan 26, 2026)
- [PEP 442 – Safe object finalization](https://peps.python.org/pep-0442/) - Python Enhancement Proposal
- [Python Weak References in 2025](https://medium.com/pythoneers/python-weak-references-in-2025-a-simpler-way-to-work-with-the-garbage-collector-26517aebde2e) - Medium article (2025)

### Uncomputation Modes

#### Mode 1: Deferred Uncomputation (Default)

**Pattern:** Keep intermediates until final result is uncomputed

```python
# Track dependencies at creation
result = a < b  # Creates intermediate qbools
# Intermediates remain allocated

# When result is GC'd, trigger cascade uncomputation:
# 1. Uncompute result
# 2. Check if any intermediate now has no remaining dependents
# 3. Uncompute those intermediates
# 4. Recursively uncompute freed dependencies
```

**Implementation strategy:**
- Reference counting: track how many dependents each intermediate has
- Cascade trigger: when dependent drops to zero, uncompute and propagate
- Requires: `weakref.ref` for tracking without preventing GC

**Why this mode:**
- Enables clean circuit reversal (inverse gates in reverse order)
- Natural Python pattern (object lifetime = resource lifetime)
- Matches quantum algorithm patterns (uncompute after use)

#### Mode 2: Immediate Uncomputation (Qubit-Saving)

**Pattern:** Uncompute intermediates as soon as final result computed

```python
# Compute final result
result = a < b  # Creates and uses intermediates

# Immediately after final gate, insert uncomputation gates
# for all intermediate qbools
# (if no other references exist)
```

**Implementation strategy:**
- Eager finalization: call `finalizer()` manually after operation
- Check reference count: only uncompute if refcount == 1 (only result holds it)
- Mode flag: user sets mode at circuit or operation level

**Tradeoff:**
- **Pro:** Reduces peak qubit usage (up to 80% in some cases per literature)
- **Con:** Cannot reverse circuit (intermediate states destroyed)
- **Con:** Increased gate count (uncomputation immediately, not batched)

**Sources:**
- [Qubit-Reuse Compilation with Mid-Circuit Measurement](https://link.aps.org/doi/10.1103/PhysRevX.13.041057) - Physical Review X (2023)
- [Integrated Qubit Reuse and Circuit Cutting](https://arxiv.org/html/2312.10298v1) - arXiv (2023)
- [Scalable Memory Recycling for Large Quantum Programs](https://ar5iv.labs.arxiv.org/html/2503.00822) - arXiv (2025)

## Integration with Existing Architecture

### Current Architecture (v1.1)

```
Python Frontend (quantum_language.pyx)
  - qint/qbool classes with __init__, __del__, operators
  - Operations call C functions via Cython
  ↓
Cython Bindings
  - Type conversion (Python → C types)
  - Function wrapping (Python API → C API)
  ↓
C Backend (Backend/src/)
  - Gate generation (CQ_equal_width, Q_and, etc.)
  - Circuit building (add_gate, layers, optimization)
  - Qubit allocation (qubit_allocator_t)
```

### Modified Architecture (Automatic Uncomputation)

```
Python Frontend (quantum_language.pyx)
  - qint/qbool classes
  - NEW: DependencyTracker singleton
  - NEW: weakref.finalize registration in operations
  - Operations call C functions (unchanged)
  ↓
Dependency Tracking (Python-level)
  - Track parent→child relationships at creation
  - Register finalization callbacks
  - On GC: trigger uncomputation cascade
  ↓
Uncomputation Trigger (Python callback)
  - Identify inverse operation sequence
  - Call C backend to generate inverse gates
  ↓
Cython Bindings (minimal changes)
  - Expose C uncomputation functions (if new ones needed)
  ↓
C Backend (Backend/src/)
  - NEW: Inverse gate sequences (already possible via invert flag)
  - Circuit building (unchanged)
  - Qubit allocation (unchanged)
```

**Key integration points:**

1. **qint/qbool operators** (`__eq__`, `__lt__`, `__and__`, etc.)
   - After creating result qbool, register dependencies
   - Record operation type for inverse lookup

2. **weakref.finalize callback**
   - Receives qubit indices and operation type
   - Calls C backend to append inverse gates

3. **qubit_allocator_t** (existing)
   - Already handles qubit freeing via `allocator_free`
   - Uncomputation happens before freeing (circuit generation first, then free)

### Changes Required by Layer

**Python Layer (quantum_language.pyx):**
- Add `DependencyTracker` class (new, ~100 lines)
- Modify comparison operators (`__eq__`, `__lt__`, etc.) to register dependencies (~5 lines per operator)
- Add `_register_dependency` method to qbool/qint (~20 lines)
- Add `_uncompute_callback` static method (~30 lines)

**Cython Layer:**
- Expose C inverse operation functions (if not already exposed)
- No ownership changes needed (Python still owns qint/qbool lifecycle)

**C Layer:**
- Verify inverse operation support (via `invert` flag in `run_instruction`)
- Add any missing inverse operation generators (if needed)
- No dependency tracking code needed

**Estimated LOC:**
- Python: ~200 lines new code
- Cython: ~20 lines exposing functions
- C: 0-50 lines (only if inverse operations missing)

## Technology Choices: NOT to Add

### Rejected: External Graph Libraries

**Option:** NetworkX, graphlib
**Rejection rationale:**
- Dependency graphs are trivial (parent→child edges only)
- No complex graph algorithms needed
- Native Python dict/list sufficient
- Avoid external dependency

**Exception:** If future phases need topological sort or cycle detection, `graphlib` (stdlib since Python 3.9) is appropriate.

**Sources:**
- [NetworkX for Dependency Graphs](https://towardsdatascience.com/network-graphs-for-dependency-resolution-5327cffe650f/) - Medium (2020, still relevant)
- [Building a Dependency Graph](https://www.python.org/success-stories/building-a-dependency-graph-of-our-python-codebase/) - Python.org success stories

### Rejected: C-Level Object System

**Option:** Implement reference counting and weak references in C
**Rejection rationale:**
- Duplicates Python's GC
- Existing architecture is stateless at C level
- High complexity for marginal gain
- Python already provides robust weak references

### Rejected: Context Managers for Uncomputation

**Option:** Use `with` statement to define uncomputation scope
**Rejection rationale:**
- Awkward API: `with temp_bool: result = a < b` is unnatural
- User must explicitly scope every intermediate
- Defeats purpose of "automatic" uncomputation
- Better for explicit resource management (e.g., `with circuit_mode(qubit_saving):`)

**Valid use:** Mode switching (deferred vs immediate)
```python
with circuit_mode(qubit_saving=True):
    result = compute_complex_expression()
# All intermediates uncomputed immediately within this block
```

**Sources:**
- [Python Context Managers](https://docs.python.org/3/library/contextlib.html) - Official Python docs
- [Understanding Python Context Managers](https://realpython.com/python-with-statement/) - Real Python (2025)

## Anti-Patterns to Avoid

### Anti-Pattern 1: Using __del__ for Uncomputation

**What goes wrong:**
- `__del__` not called for circular references
- Order of `__del__` calls undefined (dependencies may uncompute before parents)
- `__del__` not called on interpreter exit
- Testing difficult (cannot trigger manually)

**Prevention:**
- Use `weakref.finalize` exclusively
- Document why `__del__` is insufficient

### Anti-Pattern 2: Strong References in Dependency Graph

**What goes wrong:**
- Storing `parent_obj` directly prevents GC
- Circular references (parent→child→parent) cause memory leaks
- Defeats automatic lifetime management

**Prevention:**
- Store `weakref.ref(parent_obj)` instead
- Document weak reference requirement

### Anti-Pattern 3: C-Level Dependency Tracking

**What goes wrong:**
- Duplicates Python's GC
- No native weak reference support in C
- Manual ref counting error-prone
- Breaks stateless architecture

**Prevention:**
- Keep dependency tracking in Python layer
- C layer remains stateless (circuit generation only)

### Anti-Pattern 4: Global Mutable State

**What goes wrong:**
- Multiple circuits interfere with each other
- Testing difficult (state persists between tests)
- Thread-safety issues

**Prevention:**
- Make `DependencyTracker` per-circuit or use weak references to circuit
- Document that tracker is circuit-scoped

## Comparison: Python vs C Tracking

| Aspect | Python-Level | C-Level | Winner |
|--------|--------------|---------|--------|
| **Weak references** | Native (`weakref.ref`) | Manual ref counting | Python |
| **GC integration** | Automatic (PEP 442) | Must implement | Python |
| **Architecture fit** | Natural (qint/qbool are Python objects) | Requires C object system | Python |
| **Implementation effort** | ~200 LOC | ~800 LOC + ref counting | Python |
| **Testing** | Easy (trigger finalizers) | Complex (memory leak testing) | Python |
| **Performance** | Dependency registration: O(1), Uncomputation trigger: O(dependencies) | Same | Tie |
| **Maintenance** | Standard Python patterns | Custom memory management | Python |

**Verdict:** Python-level tracking is superior for this architecture.

## Research Sources

### Quantum Uncomputation Research (2024-2026)

- [Qurts: Automatic Quantum Uncomputation by Affine Types with Lifetime](https://arxiv.org/abs/2411.10835) - arXiv (2024)
- [Modular Synthesis of Efficient Quantum Uncomputation](https://dl.acm.org/doi/pdf/10.1145/3689785) - ACM (2024)
- [Unqomp: Synthesizing Uncomputation in Quantum Circuits](https://files.sri.inf.ethz.ch/website/papers/pldi21-unqomp.pdf) - PLDI (2021, still relevant)
- [Rise of conditionally clean ancillae](https://quantum-journal.org/papers/q-2025-05-21-1752/pdf/) - Quantum Journal (2025)

### Python Patterns

- [weakref — Weak references](https://docs.python.org/3/library/weakref.html) - Python 3.14.2 docs (Jan 26, 2026)
- [PEP 442 – Safe object finalization](https://peps.python.org/pep-0442/) - Python Enhancement Proposal
- [Python Context Managers](https://docs.python.org/3/library/contextlib.html) - Official Python docs
- [Python Weak References in 2025](https://medium.com/pythoneers/python-weak-references-in-2025-a-simpler-way-to-work-with-the-garbage-collector-26517aebde2e) - Medium (2025)

### Qubit Reuse Research

- [Qubit-Reuse Compilation with Mid-Circuit Measurement and Reset](https://link.aps.org/doi/10.1103/PhysRevX.13.041057) - Physical Review X (2023)
- [Integrated Qubit Reuse and Circuit Cutting](https://arxiv.org/html/2312.10298v1) - arXiv (2023)
- [Scalable Memory Recycling for Large Quantum Programs](https://ar5iv.labs.arxiv.org/html/2503.00822) - arXiv (2025)

### Dependency Graph Patterns

- [NetworkX for Dependency Graphs](https://towardsdatascience.com/network-graphs-for-dependency-resolution-5327cffe650f/) - Medium (2020)
- [Building a Dependency Graph](https://www.python.org/success-stories/building-a-dependency-graph-of-our-python-codebase/) - Python.org

## Confidence Assessment

| Area | Confidence | Rationale |
|------|-----------|-----------|
| Python patterns | HIGH | Official Python docs (3.14.2, 2026-01-26), PEP 442, multiple educational sources |
| Quantum uncomputation | MEDIUM-HIGH | Recent research (2024-2026), but academic not production-tested |
| Architecture fit | HIGH | Direct codebase analysis confirms stateless C layer, Python object lifecycle |
| Implementation effort | HIGH | Clear pattern with well-defined integration points |

## Open Questions

1. **Inverse operation availability:** Does every C operation support `invert` flag? Need to audit C backend.
   - **Resolution:** Code audit in implementation phase

2. **Partial uncomputation:** What if only some intermediates should be kept?
   - **Resolution:** User can take explicit reference: `keep_me = intermediate` prevents GC

3. **Qubit-saving mode implementation:** Should it be per-circuit, per-operation, or dynamic?
   - **Resolution:** Start with per-circuit flag, add per-operation in later phase

4. **Cross-circuit dependencies:** What if qbool from circuit A used in circuit B?
   - **Resolution:** Document as unsupported (single circuit at a time in v1.2)
