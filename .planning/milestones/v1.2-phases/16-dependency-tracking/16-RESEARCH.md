# Phase 16: Dependency Tracking Infrastructure - Research

**Researched:** 2026-01-28
**Domain:** Python-level dependency tracking for quantum intermediate values
**Confidence:** HIGH

## Summary

Phase 16 builds the infrastructure to track parent→child dependencies when qbool operations create intermediate results. This enables downstream phases (17-20) to know what to uncompute and in what order. Research shows that **Python-level dependency tracking with weak references** is the optimal pattern for this codebase's stateless C backend architecture.

The standard approach uses Python's `weakref` module for lifecycle management, native dict/list structures for dependency storage, and explicit registration during qbool/qint operations. This avoids retrofitting object lifecycle into the stateless C backend while maintaining clean separation between tracking (Python) and circuit generation (C).

**Primary recommendation:** Implement dependency tracking as Python-level attributes on qbool/qint with weak reference storage, triggered by multi-operand operations (`&`, `|`, `^`, comparisons).

## Standard Stack

The established libraries/tools for dependency tracking in Python:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| weakref | Python 3.11+ stdlib | Weak reference tracking and finalization | Native garbage collection integration; prevents circular references; PEP 442 safe finalization |
| dict/list | Python stdlib | Dependency graph storage | O(1) lookups; no external dependency; sufficient for parent→child edges |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| graphlib.TopologicalSorter | Python 3.9+ stdlib | Topological ordering | Phase 19+ cascade uncomputation (NOT Phase 16) |
| contextvars | Python 3.7+ stdlib | Scope/layer tracking | Phase 19 `with` block scope tracking |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| weakref.ref | Strong references | Strong refs prevent GC, cause memory leaks with circular deps |
| dict storage | NetworkX graph | NetworkX overkill for simple parent→child edges; adds external dependency |
| weakref.finalize | \_\_del\_\_ method | \_\_del\_\_ unreliable with circular refs, order undefined, not called on exit |

**Installation:**
```bash
# No installation needed - all stdlib modules
# Minimum Python version: 3.11 (already required by project)
```

## Architecture Patterns

### Recommended Project Structure
```
python-backend/
├── quantum_language.pyx        # Extended with dependency tracking
│   ├── qint class             # Add dependency_parents attribute
│   ├── qbool class            # Inherits tracking from qint
│   └── Operators              # Register dependencies in &, |, ^, ==, <, etc.
└── (no new files needed)
```

### Pattern 1: Weak Reference Storage
**What:** Store parent dependencies as weak references to avoid preventing garbage collection

**When to use:** All dependency edges (parent→child relationships)

**Example:**
```python
# Source: Python weakref documentation (https://docs.python.org/3/library/weakref.html)
import weakref

class qbool(qint):
    def __init__(self, ...):
        super().__init__(...)
        # Store list of weak references to parent qbools
        self.dependency_parents = []  # list[weakref.ref[qbool]]

    def add_dependency(self, parent: qbool):
        """Register parent as dependency (weak reference)."""
        # Store weakref to parent, not parent itself
        weak_parent = weakref.ref(parent)
        self.dependency_parents.append(weak_parent)
```

**Why weak references:**
- Parent can be garbage collected independently
- Prevents circular reference memory leaks
- Aligns with Python's GC-based resource management
- No manual reference counting needed

### Pattern 2: Dependency Registration in Operators
**What:** Multi-operand operations automatically register dependencies when creating results

**When to use:** Binary operations that create new qbool/qint (AND, OR, XOR, comparisons)

**Example:**
```python
# Source: Existing quantum_language.pyx operator patterns
def __and__(self, other):
    """Bitwise AND: self & other - creates result with dependencies"""
    # ... existing gate generation code ...
    result = qint(width=result_bits)  # Allocate result

    # NEW: Register dependencies
    result.add_dependency(self)   # Result depends on self
    result.add_dependency(other)  # Result depends on other
    result.operation_type = 'AND'  # For Phase 18 inverse lookup

    # ... existing gate application ...
    return result
```

**Operations that register:**
- `qbool & qbool` (AND)
- `qbool | qbool` (OR)
- `qbool ^ qbool` (XOR)
- `qint == qint` (equality comparison)
- `qint < qint` (less-than)
- `qint > qint` (greater-than)
- Arithmetic temporaries (e.g., overflow qubits from addition)

**Operations that do NOT register:**
- `~qbool` (NOT) - single operand, no dependency needed
- `qint + int` (classical operands don't need tracking)
- Variable assignment (no new qbool created)

### Pattern 3: Scope Stack for Layer Awareness
**What:** Track which dependencies were created in which `with` block context

**When to use:** Phase 19 integration (not Phase 16 itself, but prepare structure)

**Example:**
```python
# Source: Python contextvars module patterns
import contextvars

# Global context variable tracking current scope depth
current_scope = contextvars.ContextVar('current_scope', default=0)

class qbool(qint):
    def __init__(self, ...):
        super().__init__(...)
        self.dependency_parents = []
        self.creation_scope = current_scope.get()  # Capture scope depth
        self.control_qubits = []  # Which qubits controlled this creation
```

**Scope tracking:**
- `creation_scope`: Integer depth (0 = top level, 1 = first `with`, etc.)
- `control_qubits`: List of qubit indices that were active controls when created
- Used in Phase 19 to determine uncomputation order (later scopes before earlier)

### Pattern 4: Bidirectional vs Unidirectional Tracking
**What:** Store child→parent edges only, or both child→parent and parent→child?

**Decision (from CONTEXT.md):** Claude's discretion - evaluate tradeoffs

**Option A: Child→Parent Only (Simpler)**
```python
class qbool(qint):
    def __init__(self):
        self.dependency_parents = []  # list[weakref.ref[qbool]]

# Cascade uncomputation: walk parents, check if they have other children
def can_uncompute(qbool):
    # Must check ALL qbools to see if any reference this as parent
    # O(N) where N = total qbools
    return not any(me in other.dependency_parents for other in all_qbools)
```

**Pros:** Simple, no memory overhead for parent→child storage
**Cons:** O(N) cascade check, must iterate all qbools

**Option B: Bidirectional (Phase 20 Eager Mode)**
```python
class qbool(qint):
    def __init__(self):
        self.dependency_parents = []   # list[weakref.ref[qbool]]
        self.dependency_children = []  # list[weakref.ref[qbool]]

# Cascade uncomputation: direct child lookup
def can_uncompute(qbool):
    # O(1) check: count children with alive weakrefs
    return sum(1 for c in self.dependency_children if c() is not None) == 0
```

**Pros:** O(1) cascade check, enables Phase 20 eager uncomputation
**Cons:** 2x memory for edges, must maintain consistency (add/remove both directions)

**Recommendation for Phase 16:** Start with child→parent only (simpler), refactor to bidirectional in Phase 20 if needed.

### Anti-Patterns to Avoid

- **Strong references in dependency graph:** Storing `self.parents = [parent1, parent2]` prevents garbage collection. Always use `weakref.ref(parent)`.
- **Using \_\_del\_\_ for lifecycle:** Not called for circular references, order undefined. Use `weakref.finalize` in Phase 18.
- **Global mutable state:** Avoid `global_dependency_map = {}` - ties lifecycle to module import. Store on instances or circuit object.
- **Circular dependencies:** Never allow `a` depends on `b` AND `b` depends on `a`. Creation order prevents this naturally.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Weak references | Manual ref counting in Python | `weakref.ref` | Python GC integration, handles circular refs, thread-safe |
| Topological sort | Custom DFS graph traversal | `graphlib.TopologicalSorter` (Phase 19+) | Stdlib since 3.9, handles cycles, tested |
| Finalization | Custom \_\_del\_\_ + cleanup queue | `weakref.finalize` (Phase 18) | PEP 442 guarantees, respects dep order, testable |
| Scope tracking | Manual stack in global variable | `contextvars.ContextVar` | Thread-safe, async-aware, proper scoping |

**Key insight:** Python's stdlib provides robust primitives for lifecycle management. Custom implementations reintroduce bugs that PEP 442 (finalization) and PEP 567 (contextvars) solved.

## Common Pitfalls

### Pitfall 1: Strong References Prevent Garbage Collection
**What goes wrong:** Storing `self.parents = [parent1, parent2]` creates strong references that prevent Python GC from collecting parents when they go out of scope.

**Why it happens:** Natural Python pattern is strong references. Weak references are counterintuitive.

**How to avoid:**
```python
# WRONG: Strong reference
self.parents = [parent1, parent2]  # Prevents GC

# RIGHT: Weak reference
import weakref
self.parents = [weakref.ref(parent1), weakref.ref(parent2)]

# Access with check
for parent_ref in self.parents:
    parent = parent_ref()  # Returns None if collected
    if parent is not None:
        # Use parent
```

**Warning signs:**
- Memory usage grows over time
- `del` statements don't free memory
- Objects remain alive after scope exit

### Pitfall 2: Forgetting to Check Weakref Liveness
**What goes wrong:** Calling `parent_ref()` returns `None` if parent was garbage collected, leading to `AttributeError` when accessing attributes.

**Why it happens:** Weak references look like normal references but can become `None` at any time.

**How to avoid:**
```python
# WRONG: Assumes parent is alive
for parent_ref in self.dependency_parents:
    parent = parent_ref()
    parent.some_method()  # CRASH if parent was collected

# RIGHT: Check for None
for parent_ref in self.dependency_parents:
    parent = parent_ref()
    if parent is not None:  # Guard against collected parent
        parent.some_method()
```

**Warning signs:**
- Intermittent `AttributeError: 'NoneType' has no attribute`
- Errors that only occur after garbage collection runs

### Pitfall 3: Circular Dependencies
**What goes wrong:** If `a` depends on `b` AND `b` depends on `a`, neither can be uncomputed first, causing deadlock.

**Why it happens:** Bidirectional operations or user code that creates cycles.

**How to avoid:**
- **Creation order guarantees acyclicity:** If dependencies only flow from older objects to newer (creation timestamp), cycles are impossible
- **Document invariant:** "Dependencies only point to objects created before this one"
- **Assert in add_dependency:** Check that parent's creation timestamp < self's timestamp

```python
class qbool(qint):
    _creation_counter = 0  # Global counter

    def __init__(self):
        qbool._creation_counter += 1
        self._creation_order = qbool._creation_counter
        self.dependency_parents = []

    def add_dependency(self, parent):
        # Assert no cycles: parent must be older
        assert parent._creation_order < self._creation_order, \
            "Cycle detected: dependency must be older than dependent"
        self.dependency_parents.append(weakref.ref(parent))
```

**Warning signs:**
- Uncomputation hangs or loops forever
- Memory leak where nothing can be freed

### Pitfall 4: Global State vs Instance State
**What goes wrong:** Storing dependencies in global dict ties lifecycle to module import, breaks testing, causes cross-circuit interference.

**Why it happens:** Singleton pattern seems convenient for "one circuit at a time" assumption.

**How to avoid:**
```python
# WRONG: Global state
global_dependency_map = {}  # Persists across tests

def add_dependency(result, parent):
    global_dependency_map[id(result)] = parent  # Leaks memory

# RIGHT: Instance state
class qbool(qint):
    def __init__(self):
        self.dependency_parents = []  # Per-instance storage

# OR: Circuit-scoped (if managing multiple circuits)
class Circuit:
    def __init__(self):
        self.dependency_tracker = DependencyTracker()
```

**Warning signs:**
- Test failures that depend on test execution order
- Memory leaks across test runs
- Unexpected behavior with multiple circuits

## Code Examples

Verified patterns from official sources and codebase analysis:

### Dependency Registration in AND Operation
```python
# Source: quantum_language.pyx __and__ method (extended)
def __and__(self, other):
    """Bitwise AND: self & other

    Result tracks both operands as dependencies for future uncomputation.
    """
    global _controlled, _control_bool, qubit_array
    cdef sequence_t *seq
    cdef unsigned int[:] arr
    cdef int result_bits

    # Determine result width
    if type(other) == int:
        classical_width = other.bit_length() if other > 0 else 1
        result_bits = max(self.bits, classical_width)
    elif type(other) == qint or type(other) == qbool:
        result_bits = max(self.bits, (<qint>other).bits)
    else:
        raise TypeError("Operand must be qint or int")

    # Allocate result (ancilla qubits)
    result = qint(width=result_bits)

    # NEW: Register dependencies
    import weakref
    if not hasattr(result, 'dependency_parents'):
        result.dependency_parents = []
    result.dependency_parents.append(weakref.ref(self))
    if type(other) != int:  # Don't track classical operands
        result.dependency_parents.append(weakref.ref(other))
    result.operation_type = 'AND'  # For Phase 18 inverse gate lookup

    # ... existing gate generation code ...
    # Build qubit array: [output:N], [self:N], [other:N]
    self_offset = 64 - self.bits
    result_offset = 64 - result_bits

    qubit_array[:result_bits] = result.qubits[result_offset:64]
    qubit_array[result_bits:result_bits + self.bits] = self.qubits[self_offset:64]

    if type(other) == int:
        seq = CQ_and(result_bits, other)
    else:
        other_offset = 64 - (<qint>other).bits
        qubit_array[2*result_bits:2*result_bits + (<qint>other).bits] = \
            (<qint>other).qubits[other_offset:64]
        seq = Q_and(result_bits)

    arr = qubit_array
    run_instruction(seq, &arr[0], False, _circuit)

    return result
```

### Comparison Result Tracking
```python
# Source: quantum_language.pyx __lt__ method (extended)
def __lt__(self, other):
    """Less-than comparison: self < other

    Result qbool tracks both compared qints as dependencies.
    """
    # Self-comparison optimization
    if self is other:
        return qbool(False)  # x < x is always false

    # Handle qint operand
    if type(other) == qint:
        # In-place subtraction on self
        self -= other
        # Check MSB (sign bit) - if 1, result is negative (self < other)
        msb = self[64 - self.bits]
        result = qbool()
        result ^= msb  # Copy MSB to result

        # NEW: Track dependency on compared qints
        import weakref
        result.dependency_parents = [
            weakref.ref(self),
            weakref.ref(other)
        ]
        result.operation_type = 'LESS_THAN'

        # Restore operand
        self += other
        return result

    # ... handle int operand ...
```

### Safe Weakref Access Pattern
```python
# Source: Python weakref documentation
def get_live_parents(qbool_obj):
    """Get list of parent dependencies that are still alive.

    Filters out parents that have been garbage collected.
    """
    live_parents = []
    for parent_ref in qbool_obj.dependency_parents:
        parent = parent_ref()  # Dereference weakref
        if parent is not None:  # Check if still alive
            live_parents.append(parent)
    return live_parents

# Usage in cascade uncomputation (Phase 19)
def can_uncompute(qbool_obj):
    """Check if qbool can be safely uncomputed.

    Returns True if all children using this qbool have been cleaned up.
    """
    # For Phase 16: just check if dependencies exist
    return len(get_live_parents(qbool_obj)) > 0
```

### Scope Depth Tracking
```python
# Source: Python contextvars module patterns
import contextvars

# Global context variable for scope depth
current_scope_depth = contextvars.ContextVar('scope_depth', default=0)

class qbool(qint):
    def __init__(self, value=False, ...):
        super().__init__(value, width=1, ...)
        self.dependency_parents = []

        # Capture scope at creation time
        self.creation_scope = current_scope_depth.get()

        # Capture active control qubits (from _control_bool global)
        global _control_bool
        if _control_bool is not None:
            self.control_context = [_control_bool.qubits[63]]
        else:
            self.control_context = []

# Context manager increments scope depth
def __enter__(self):
    """Enter controlled context - increment scope depth."""
    global _controlled, _control_bool

    # Existing control logic
    if not _controlled:
        _control_bool = self
    else:
        _list_of_controls.append(_control_bool)
        _control_bool &= self
    _controlled = True

    # NEW: Increment scope depth
    token = current_scope_depth.set(current_scope_depth.get() + 1)
    self._scope_token = token  # Store for __exit__

    return self

def __exit__(self, exc_type, exc, tb):
    """Exit controlled context - restore scope depth."""
    global _controlled, _control_bool

    # NEW: Restore scope depth
    current_scope_depth.reset(self._scope_token)

    # Existing control logic
    _controlled = False
    _control_bool = None
    return False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual uncomputation (user writes inverse) | Automatic via dependency tracking | 2020 (Silq/Unqomp papers) | 46% code reduction, prevents errors |
| \_\_del\_\_ for cleanup | weakref.finalize | Python 3.4 (PEP 442) | Reliable cleanup, no circular ref issues |
| Global ref counting | Weak references + GC | Python 2.2 (weakref added) | Automatic lifecycle, no manual counting |
| Single-use qubits | Qubit reuse via uncomputation | 2023 (PRX paper) | 80% peak qubit reduction |

**Deprecated/outdated:**
- **\_\_del\_\_ for resource cleanup:** PEP 442 (Python 3.4) made finalization safer, but `weakref.finalize` still preferred for explicit lifecycle
- **Strong reference dependency graphs:** Cause memory leaks; weak references are standard since Python 2.2
- **Manual inverse gate writing:** Silq (2020) showed automatic uncomputation is feasible; Unqomp (2021) provided algorithm

## Open Questions

Things that couldn't be fully resolved:

1. **Bidirectional vs unidirectional tracking**
   - What we know: Child→parent sufficient for Phase 16-19; parent→child needed for Phase 20 eager mode
   - What's unclear: Performance impact of O(N) cascade check vs 2x memory for bidirectional
   - Recommendation: Start unidirectional (simpler), refactor Phase 20 if profiling shows bottleneck

2. **Storage location: instance attribute vs centralized registry**
   - What we know: Instance attribute (`self.dependency_parents`) simpler; registry enables cross-circuit queries
   - What's unclear: Will multi-circuit support (future) need centralized view?
   - Recommendation: Instance attribute for Phase 16 (YAGNI principle), add registry if Phase 20+ requires it

3. **qint comparison dependency granularity**
   - What we know: `qint < qint` creates ancilla qubits (borrow bits, sign checks)
   - What's unclear: Should track qint operands as dependencies, or ancilla qubits, or both?
   - Recommendation: Track qint operands (user-visible); ancilla tracking handled by qubit allocator (internal)

## Sources

### Primary (HIGH confidence)
- [Python weakref module](https://docs.python.org/3/library/weakref.html) - Official Python 3.14.2 documentation (updated 2026-01-26)
- [PEP 442 – Safe object finalization](https://peps.python.org/pep-0442/) - Python Enhancement Proposal (finalization order guarantees)
- [Python graphlib module](https://docs.python.org/3/library/graphlib.html) - TopologicalSorter for dependency ordering (updated 2026-01-27)
- Codebase: `quantum_language.pyx` - Existing operator patterns and architecture

### Secondary (MEDIUM confidence)
- [Silq: High-Level Quantum Language with Safe Uncomputation](https://silq.ethz.ch/overview) - ETH Zurich (2020, PLDI) - qfree/const annotations for dependency tracking
- [Unqomp: Synthesizing Uncomputation in Quantum Circuits](https://www.sri.inf.ethz.ch/publications/paradis2021unqomp) - SRI Lab (2021) - Automated dependency graph construction
- [Qrisp Uncomputation Documentation](https://qrisp.eu/reference/Core/Uncomputation.html) - Practical implementation of auto_uncompute

### Tertiary (LOW confidence)
- [A Guide to Python's Weak References](https://martinheinz.dev/blog/112) - Blog post (2024) - Educational examples
- [Building a Dependency Graph of Python Codebase](https://www.python.org/success-stories/building-a-dependency-graph-of-our-python-codebase/) - Python.org success stories

## Metadata

**Confidence breakdown:**
- Standard stack (weakref, dict): HIGH - Official Python docs, PEP guarantees, widely used pattern
- Architecture (Python-level tracking): HIGH - Direct codebase analysis confirms stateless C, Python object lifecycle
- Quantum patterns (Silq/Unqomp): MEDIUM - Academic research, not production-tested in this codebase
- Scope tracking (contextvars): MEDIUM - Stdlib module but Phase 19 integration not yet implemented

**Research date:** 2026-01-28
**Valid until:** 90 days (stable stdlib APIs, slow-moving quantum computing research)

**Key decisions locked in by CONTEXT.md:**
- Weak references for parent storage (prevents GC issues)
- Multi-operand operations trigger tracking (`&`, `|`, `^`, comparisons)
- Single-operand operations skip tracking (`~a`)
- Layer info derived at uncomputation time (not stored on edges)
- Control context recorded (which qubits controlled creation)
- Scope tracking via `with` block depth

**Claude's discretion items for Phase 16:**
- Storage location: instance attribute (`qbool.dependency_parents`) vs centralized registry → **Recommend instance attribute** (simpler, YAGNI)
- Bidirectional tracking: child→parent only vs parent→child too → **Recommend unidirectional for Phase 16** (defer bidirectional until Phase 20 if needed)
- Scope data structure: contextvars vs manual stack → **Recommend contextvars** (thread-safe, standard)
- qint comparison tracking: track qints vs ancillas → **Recommend track qints** (user-visible dependencies)
