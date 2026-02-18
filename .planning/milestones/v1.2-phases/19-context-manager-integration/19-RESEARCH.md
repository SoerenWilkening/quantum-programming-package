# Phase 19: Context Manager Integration for `with` - Research

**Researched:** 2026-01-28
**Domain:** Python context managers, scope-based automatic uncomputation, quantum control flow
**Confidence:** HIGH

## Summary

Phase 19 extends the automatic uncomputation from Phase 18 to work with Python's `with` statement, enabling scope-based cleanup of quantum temporaries created inside controlled blocks. When a `with` block exits, all qbool intermediates created within that block are automatically uncomputed in LIFO order. This integrates Python's context manager protocol (`__enter__` / `__exit__`) with the existing quantum control flow (`_controlled` global state) and Phase 18's uncomputation infrastructure.

The research confirms that Python's context manager protocol provides natural semantics for quantum scope management. The `__exit__` method executes cleanup in LIFO order for nested contexts, matching quantum uncomputation requirements. The existing `__enter__` / `__exit__` implementation already manages the `_controlled` global state—Phase 19 extends this to track scope-local qbools and trigger their uncomputation on block exit.

**Primary recommendation:** Maintain a global scope stack (Python list or `collections.deque`) that tracks qbools created in each `with` block. On `__exit__`, uncompute all qbools in the current scope (while still in controlled context), then pop the scope and restore the control state. Use the existing `contextvars.ContextVar` for scope depth tracking.

## Standard Stack

### Core (Already in Codebase)

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `__enter__` / `__exit__` | Python 3.11+ | Context manager protocol | Python's standard mechanism for resource cleanup in `with` blocks |
| `contextvars.ContextVar` | stdlib | Scope depth tracking | Already used in Phase 16 (`current_scope_depth`), async-safe |
| Python `list` or `deque` | stdlib | Scope stack (LIFO) | Standard collections for stack operations |
| Phase 18 uncomputation | Existing | `.uncompute()` method, LIFO cascade | Already implemented, handles dependency graphs |
| Phase 16 dependency tracking | Existing | `_creation_order`, weak refs | Enables LIFO ordering and prevents cycles |

### Supporting (Already Implemented)

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `_controlled` global | quantum_language.pyx | Tracks active quantum control context | Phase 1 complete, used in `__enter__` / `__exit__` |
| `_control_bool` global | quantum_language.pyx | Control qubit for conditional gates | Phase 1 complete |
| `current_scope_depth` | quantum_language.pyx | Scope depth (Phase 16) | Already tracks nesting, can be incremented in `__enter__` |
| `creation_scope` field | qint class | Scope depth at creation | Phase 16 field, used to identify scope-local qbools |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Global scope stack | Thread-local storage | Thread-local is more isolated but adds complexity; global is sufficient for single-threaded circuit generation |
| Python `list` | `collections.deque` | Deque has O(1) append/pop from both ends (technically overkill for one-end stack), list is simpler and sufficient |
| Python `list` | `contextlib.ExitStack` | ExitStack is for managing nested context managers, not for tracking objects; list is more direct |
| Scope stack | `contextvars` for scope tracking | `contextvars` is for async context isolation, not LIFO scope management; list/deque is more natural |

**Installation:**
No external dependencies—all components are Python stdlib or already implemented in the codebase.

## Architecture Patterns

### Recommended Scope Management Flow

```
with qbool_condition:                 # User code
    ↓
__enter__() called                    # Python calls this
    ↓
1. Check not uncomputed
2. Update _controlled and _control_bool (existing logic)
3. Increment current_scope_depth
4. Push new scope frame to scope_stack (empty list)
5. Return self
    ↓
qbool_temp = a & b                    # User creates qbool inside with
    ↓
qint.__init__() captures scope        # Phase 16: creation_scope = current_scope_depth.get()
    ↓
Register qbool_temp in scope_stack[-1] # Phase 19: Add to active scope
    ↓
with block exits                      # Python calls __exit__
    ↓
__exit__() called
    ↓
1. Get scope_stack[-1] (qbools created in this scope)
2. Uncompute each qbool in scope (LIFO by _creation_order)
   - Uncomputation happens WHILE _controlled is still True
   - Uncomputation gates are generated inside controlled context
3. Pop scope_stack
4. Decrement current_scope_depth
5. Restore _controlled and _control_bool (existing logic)
6. Return False (don't suppress exceptions)
```

### Pattern 1: Scope Stack Management

**What:** Maintain a global list of scopes, where each scope is a list of qbools created in that `with` block.

**When to use:** Every `with` statement on a qbool/qint.

**Example (implementation pattern):**
```python
# Source: Python context manager best practices + Phase 19 requirements

# Global scope stack (at module level)
_scope_stack = []  # List of lists: [[scope1_qbools], [scope2_qbools], ...]

cdef class qint:
    def __enter__(self):
        """Enter quantum conditional context."""
        global _controlled, _control_bool, _scope_stack

        self._check_not_uncomputed()

        # Existing control state management
        if not _controlled:
            _control_bool = self
        else:
            _list_of_controls.append(_control_bool)
            _control_bool &= self
        _controlled = True

        # Phase 19: Scope tracking
        current_scope_depth.set(current_scope_depth.get() + 1)
        _scope_stack.append([])  # New scope frame (empty list of qbools)

        return self

    def __exit__(self, exc_type, exc, tb):
        """Exit quantum conditional context with scope cleanup."""
        global _controlled, _control_bool, _scope_stack

        # Phase 19: Uncompute scope-local qbools FIRST (while still controlled)
        if _scope_stack:
            scope_qbools = _scope_stack.pop()

            # Sort by _creation_order descending for LIFO
            scope_qbools.sort(key=lambda q: q._creation_order, reverse=True)

            # Uncompute each qbool in scope
            for qbool_obj in scope_qbools:
                if not qbool_obj._is_uncomputed:
                    qbool_obj._do_uncompute(from_del=False)

        # Decrement scope depth
        current_scope_depth.set(current_scope_depth.get() - 1)

        # THEN restore control state (existing logic)
        _controlled = False
        _control_bool = None

        return False  # Don't suppress exceptions
```

### Pattern 2: Automatic Scope Registration on Creation

**What:** When a qbool is created inside a `with` block, automatically register it with the active scope.

**When to use:** In `qint.__init__` after setting `creation_scope`.

**Example (implementation pattern):**
```python
# Source: Phase 16 tracking + Phase 19 scope registration

cdef class qint:
    def __init__(self, ...):
        # ... existing initialization logic ...

        # Phase 16: Capture creation scope
        self.creation_scope = current_scope_depth.get()

        # Phase 19: Register with active scope if inside a with block
        global _scope_stack
        if _scope_stack:  # If any with blocks are active
            # Only register if this qbool was created in the current scope
            # (creation_scope matches current depth)
            if self.creation_scope == current_scope_depth.get():
                _scope_stack[-1].append(self)
```

### Pattern 3: Nested Context LIFO Uncomputation

**What:** Nested `with` statements create nested scopes. Inner scope uncomputes before outer scope.

**When to use:** User writes nested `with` blocks.

**Example (usage pattern):**
```python
# Source: Python context manager nesting + quantum uncomputation requirements

a = qbool(True)
b = qbool(True)

with a:  # Outer scope (scope depth 1)
    temp1 = qbool()  # Created at scope 1

    with b:  # Inner scope (scope depth 2)
        temp2 = qbool()  # Created at scope 2
        temp3 = temp1 & temp2
    # Exiting inner with: uncomputes temp3, temp2 (in that order)
    # temp1 still alive

# Exiting outer with: uncomputes temp1
```

**Execution order:**
1. Inner `__exit__` called: uncompute temp3 (depends on temp1, temp2), then temp2
2. Outer `__exit__` called: uncompute temp1

### Pattern 4: Condition Qbool Survives Its Own Block

**What:** The qbool used as the `with` condition is NOT part of the block's scope—caller manages its lifetime.

**When to use:** Always—the condition qbool is created before the `with` statement.

**Example (usage pattern):**
```python
# Source: Phase 19 CONTEXT.md decision

condition = qbool(True)  # Created at scope 0

with condition:  # __enter__ increments scope to 1
    temp = qbool()  # Created at scope 1
    # temp is registered in scope 1
# __exit__ uncomputes temp, NOT condition

# condition still valid here
del condition  # Explicit cleanup or garbage collection
```

**Key insight:** The condition qbool's `creation_scope` is 0 (or lower than current scope), so it's not registered in the scope's qbool list.

### Pattern 5: Exception Safety

**What:** Uncomputation happens in `__exit__` regardless of exceptions, but uncomputation failures propagate.

**When to use:** All `__exit__` implementations.

**Example (implementation pattern):**
```python
# Source: Python __exit__ exception handling + Phase 19 CONTEXT.md

def __exit__(self, exc_type, exc, tb):
    """Exit with exception safety."""
    global _scope_stack

    try:
        # Always attempt cleanup, even if exception occurred in with block
        if _scope_stack:
            scope_qbools = _scope_stack.pop()

            for qbool_obj in scope_qbools:
                if not qbool_obj._is_uncomputed:
                    # Phase 19 decision: fail loudly, don't hide bugs
                    qbool_obj._do_uncompute(from_del=False)  # Raises on error

    finally:
        # Always restore control state, even if uncomputation failed
        _controlled = False
        _control_bool = None
        current_scope_depth.set(current_scope_depth.get() - 1)

    # Return False: don't suppress exceptions
    # If uncomputation raised, that exception propagates
    # If original exception exists, it propagates
    return False
```

### Pattern 6: Uncompute Inside Controlled Context

**What:** Uncomputation gates are generated while `_controlled` is still True, so they're controlled by the condition qbool.

**When to use:** Always—ensures quantum correctness.

**Example (quantum semantics):**
```python
# Source: Phase 19 CONTEXT.md quantum correctness requirement

condition = qbool()

with condition:
    temp = a & b
    # Gates for (a & b) are controlled by condition

    # __exit__ starts:
    # 1. _controlled is still True
    # 2. temp.uncompute() generates gates (reversal of a & b)
    # 3. Because _controlled is True, uncomputation gates are controlled
    # 4. THEN _controlled is set to False
    # 5. THEN _control_bool is cleared

# Result: Both computation and uncomputation of temp happen inside
# the controlled context, which is quantum-correct.
```

### Anti-Patterns to Avoid

- **Clearing control state before uncomputation:** Uncompute FIRST, then restore `_controlled`. Otherwise uncomputation gates aren't controlled.
- **Not checking `_is_uncomputed` before uncomputing:** Qbool might already be explicitly uncomputed—check before calling `.uncompute()`.
- **Using `try/except` to suppress uncomputation errors:** Phase 19 decision is strict mode—fail loudly on uncomputation failure.
- **Registering condition qbool in its own scope:** The condition qbool is created before the `with`, so it has lower `creation_scope` and shouldn't be registered.
- **Using global variable instead of scope stack:** Need LIFO ordering and isolation between scopes—list/deque is clearer than global variable per scope.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Context manager protocol | Custom `with` implementation | Python `__enter__` / `__exit__` | Language built-in, handles exceptions, nesting, and cleanup order automatically |
| LIFO scope tracking | Custom scope manager | Python `list` with append/pop | O(1) stack operations, simple, proven |
| Scope depth counter | Manual counter variable | `contextvars.ContextVar` (existing) | Already implemented in Phase 16, async-safe, proper context isolation |
| Uncomputation logic | Custom gate reversal | Phase 18 `.uncompute()` method | Already handles dependency cascades, LIFO ordering, idempotency |
| Exception handling in cleanup | Custom try/except patterns | `__exit__` protocol | Python guarantees `__exit__` is called even on exception, has proper exception signature |

**Key insight:** Phase 18 built uncomputation infrastructure, Phase 16 built dependency tracking—Phase 19 is just adding scope-based triggers to existing machinery.

## Common Pitfalls

### Pitfall 1: Control State Restoration Order

**What goes wrong:** Restoring `_controlled = False` before uncomputing scope qbools causes uncomputation gates to be generated outside the controlled context.

**Why it happens:** Natural tendency to mirror `__enter__` logic in reverse, but quantum semantics require uncomputation INSIDE the controlled context.

**How to avoid:**
- Phase 19 decision: "Uncompute first, then restore context"
- Order in `__exit__`: 1) uncompute scope qbools, 2) pop scope, 3) restore `_controlled` / `_control_bool`
- Uncomputation happens while `_controlled` is still True

**Warning signs:**
- Circuit verification shows uncomputation gates lack control qubit
- Quantum simulation produces wrong results for nested conditionals
- Uncomputation gates appear after control context ends in circuit output

### Pitfall 2: Scope Stack Out of Sync

**What goes wrong:** `_scope_stack` and `current_scope_depth` get out of sync (different lengths), causing crashes or wrong scope assignments.

**Why it happens:** Exception in `__enter__` before scope is pushed, or exception in `__exit__` after scope is popped but before depth is decremented.

**How to avoid:**
- Use `try/finally` in `__exit__` to guarantee scope cleanup
- Push scope in `__enter__` immediately after incrementing depth
- Pop scope in `__exit__` before decrementing depth
- Document invariant: `len(_scope_stack) == current_scope_depth.get()`

**Warning signs:**
- IndexError when accessing `_scope_stack[-1]`
- Scope depth becomes negative
- Qbools registered in wrong scope
- Tests with exceptions show scope leaks

### Pitfall 3: Pre-Existing Qbool Uncomputation

**What goes wrong:** Qbool created outside `with` block gets uncomputed when block exits because it's used inside the block.

**Why it happens:** Confusing "used in scope" with "created in scope"—only creation scope matters.

**How to avoid:**
- Phase 19 decision: "Pre-existing qbools not touched"
- Check `qbool.creation_scope == current_scope_depth.get()` before registering
- Only register qbools where creation happens at current depth
- Dependency tracking (Phase 16) is separate from scope tracking

**Warning signs:**
- Qbool becomes invalid after `with` block even though it was created before
- Tests show variables "escaping" scope get uncomputed
- RuntimeError "qbool has been uncomputed" for pre-existing qbools

### Pitfall 4: Condition Qbool Self-Uncomputation

**What goes wrong:** The qbool used as `with condition:` is uncomputed when the block exits, making it unusable.

**Why it happens:** Naively registering `self` in scope during `__enter__`.

**How to avoid:**
- Phase 19 decision: "Condition qbool survives its own `with` block"
- Don't register `self` in scope during `__enter__`
- Condition qbool's `creation_scope` is lower than current block's scope, so automatic registration skips it
- Caller manages condition qbool's lifetime

**Warning signs:**
- Cannot reuse qbool after `with` block
- Tests with multiple `with condition:` blocks fail on second use
- RuntimeError when trying to use condition qbool after block

### Pitfall 5: Cross-Scope Dependency Cascade

**What goes wrong:** Inner scope qbool depends on outer scope qbool. When inner scope exits, it tries to uncompute the outer qbool (cascade), but outer qbool should remain alive.

**Why it happens:** Phase 18 dependency cascade doesn't check if parent is scope-local or not.

**How to avoid:**
- Phase 19 decision (Claude's discretion): Only uncompute scope-local qbools, not their dependencies
- Modify cascade logic to only cascade within same scope OR
- Trust Python GC: parent has references from outer scope, so won't be collected until outer scope exits
- **Recommended:** Don't cascade across scope boundaries—only uncompute qbools directly in scope list

**Warning signs:**
- Outer scope variable becomes invalid while still in scope
- Premature uncomputation of shared dependencies
- Tests with nested scopes fail when inner depends on outer

### Pitfall 6: Exception Suppression by `__exit__`

**What goes wrong:** `__exit__` returns `True`, suppressing exceptions from the `with` block, hiding bugs.

**Why it happens:** Misunderstanding `__exit__` return value semantics—returning `True` suppresses exceptions.

**How to avoid:**
- Phase 19 decision: "Always strict mode—no silent error suppression"
- Always `return False` in `__exit__`
- Let exceptions propagate naturally
- Only suppress exceptions if explicitly required by design (not the case here)

**Warning signs:**
- Tests pass silently even when they should fail
- Exceptions inside `with` blocks disappear
- Debugging shows exceptions were raised but not caught

## Code Examples

Verified patterns from existing implementation and Python documentation:

### Existing Context Manager Implementation (Current)

```python
# Source: python-backend/quantum_language.pyx lines 767-828
def __enter__(self):
    """Enter quantum conditional context."""
    global _controlled, _control_bool
    self._check_not_uncomputed()
    if not _controlled:
        _control_bool = self
    else:
        # Nested control: AND of control qbools
        _list_of_controls.append(_control_bool)
        _control_bool &= self
    _controlled = True
    return self

def __exit__(self, exc_type, exc, tb):
    """Exit quantum conditional context."""
    global _controlled, _control_bool, ancilla, _smallest_allocated_qubit
    _controlled = False
    _control_bool = None
    # TODO: undo logical and operations
    return False  # Do not suppress exceptions
```

### Python Context Manager LIFO Order (Standard Library)

```python
# Source: https://docs.python.org/3/library/contextlib.html
# ExitStack example showing LIFO behavior

from contextlib import ExitStack

with ExitStack() as outer_stack:
    outer_stack.callback(print, "Callback: from outer context")

    with ExitStack() as inner_stack:
        inner_stack.callback(print, "Callback: from inner context")
        print("Leaving inner context")

    print("Leaving outer context")

# Output:
# Leaving inner context
# Callback: from inner context
# Leaving outer context
# Callback: from outer context
```

### Scope Depth Tracking (Existing Phase 16)

```python
# Source: python-backend/quantum_language.pyx lines 35-36
# Module-level context variable for scope depth
current_scope_depth = contextvars.ContextVar('scope_depth', default=0)

# In qint.__init__:
self.creation_scope = current_scope_depth.get()
```

### Uncomputation with Exception Handling (Existing Phase 18)

```python
# Source: python-backend/quantum_language.pyx lines 667-697
def uncompute(self):
    """Explicitly uncompute this qbool and its dependencies."""
    if self._is_uncomputed:
        return  # Idempotent: calling twice is no-op

    # Check reference count
    import sys
    refcount = sys.getrefcount(self)
    if refcount > 2:
        raise RuntimeError(
            f"Cannot explicitly uncompute qbool: {refcount - 1} references still exist"
        )

    # Perform uncomputation (raises on failure)
    self._do_uncompute(from_del=False)
```

### LIFO Sort by Creation Order (Existing Phase 18)

```python
# Source: python-backend/quantum_language.pyx lines 637-643
# In _do_uncompute method:
live_parents = self.get_live_parents()

# Sort by _creation_order descending for LIFO order
live_parents.sort(key=lambda p: p._creation_order, reverse=True)

# Recursively uncompute parents
for parent in live_parents:
    if not parent._is_uncomputed:
        parent._do_uncompute(from_del=from_del)
```

### Stack Operations in Python

```python
# Source: Python list operations (standard library)
# List as stack with O(1) append/pop at end

scope_stack = []

# Push new scope
scope_stack.append([])  # Empty list for new scope

# Add item to current scope
scope_stack[-1].append(qbool_obj)

# Pop scope
current_scope = scope_stack.pop()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual cleanup outside `with` | Automatic uncomputation on `__exit__` | Phase 19 (now) | Scope-based automatic cleanup, no manual tracking |
| Uncompute all on `__del__` only | Uncompute scope-local on `__exit__` | Phase 19 (now) | Earlier cleanup, deterministic timing within `with` |
| No scope tracking | Scope stack with registration | Phase 19 (now) | Enables scope-local cleanup decisions |
| Control state only | Control state + scope state | Phase 19 (now) | Separate concerns: control (quantum) vs scope (lifetime) |
| Pre-existing `__enter__` / `__exit__` | Extended with scope management | Phase 19 (now) | Additive change, preserves control flow semantics |

**Python context manager evolution:**
- Python 2.5 (2006): `with` statement added (PEP 343)
- Python 3.1 (2009): Multiple context managers in single `with`
- Python 3.3 (2012): `contextlib.ExitStack` for dynamic context management
- Python 3.7 (2018): `contextlib.asynccontextmanager` for async contexts
- Python 3.10 (2021): Parenthesized context managers for readability
- Python 3.14 (2025): Context variable tokens as context managers

**Quantum language integration:**
- Phase 1 (v1.0): Basic `with` for quantum conditionals (control qubits)
- Phase 16 (v1.2): Dependency tracking with scope depth
- Phase 18 (v1.2): Automatic uncomputation on garbage collection
- Phase 19 (now): Scope-based uncomputation integrated with `with` statement

## Open Questions

Things that couldn't be fully resolved:

1. **Cross-scope dependency cascade behavior**
   - What we know: Inner scope qbool can depend on outer scope qbool (e.g., `temp = outer_var & inner_var`)
   - What's unclear: Should uncomputing inner scope trigger cascade to outer dependencies, or only uncompute scope-local qbools?
   - Recommendation: **Don't cascade across scopes**. Only uncompute qbools directly in the scope list. Outer dependencies will be uncomputed when their scope exits. This prevents premature cleanup and respects scope boundaries.
   - Confidence: MEDIUM (marked as Claude's discretion in CONTEXT.md)

2. **Scope stack data structure choice**
   - What we know: Need LIFO stack with O(1) append/pop
   - What's unclear: Python `list` vs `collections.deque` vs custom structure
   - Recommendation: Use Python `list`—simpler, sufficient for one-end stack operations, widely understood. Deque optimization (O(1) from both ends) is unnecessary here.
   - Confidence: HIGH (both work, list is simpler)

3. **Integration with existing `_list_of_controls` TODO**
   - What we know: Existing `__enter__` has TODO for nested control AND operations
   - What's unclear: How scope stack interacts with control list for deeply nested `with` statements
   - Recommendation: Scope stack is orthogonal to control list. Each scope has its own control context. Phase 19 focuses on scope cleanup, control list AND is separate concern (defer to future phase).
   - Confidence: HIGH (separate concerns)

4. **Performance impact of scope registration**
   - What we know: Every qbool creation checks if `_scope_stack` is non-empty and conditionally appends
   - What's unclear: Performance overhead for deeply nested scopes or many qbools
   - Recommendation: Negligible—list append is O(1), scope depth check is integer comparison. Measure if concerned, but unlikely to be bottleneck compared to quantum gate operations.
   - Confidence: HIGH (Python list operations well-optimized)

## Sources

### Primary (HIGH confidence)

- [Python 3 contextlib documentation](https://docs.python.org/3/library/contextlib.html) - Context manager utilities, ExitStack LIFO behavior
- [Python's with Statement: Manage External Resources Safely](https://realpython.com/python-with-statement/) - Context manager protocol, `__enter__` / `__exit__` semantics
- [Python Data Model: Context Managers](https://docs.python.org/3/reference/datamodel.html) - Official `__enter__` / `__exit__` specification
- [Python contextvars documentation](https://docs.python.org/3/library/contextvars.html) - Context variables for scope tracking
- Existing codebase: quantum_language.pyx lines 767-828 (`__enter__` / `__exit__` implementation)
- Existing codebase: quantum_language.pyx line 36 (`current_scope_depth` ContextVar)
- Existing codebase: Phase 18 uncomputation infrastructure (`.uncompute()`, `_do_uncompute()`)

### Secondary (MEDIUM confidence)

- [Python's deque: Implement Efficient Queues and Stacks](https://realpython.com/python-deque/) - Stack data structure options
- [ExitStack in Python | Redowan's Reflections](https://rednafi.com/python/exitstack/) - Advanced ExitStack patterns
- [PEP 521: Managing global context via 'with' blocks](https://peps.python.org/pep-0521/) - Context manager best practices for global state
- [Using context manager for C malloc/free (Cython)](https://groups.google.com/g/cython-users/c/axMr9XONBVs) - Cython context manager patterns
- Phase 19 CONTEXT.md - User decisions and implementation constraints

### Tertiary (LOW confidence)

- [Context manager protocol extension (2nd attempt)](https://discuss.python.org/t/context-manager-protocol-extension-2nd-attempt/44888) - Future Python enhancements (not yet adopted)
- Community discussions on context manager patterns (various sources)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python context manager protocol is stable, `contextvars` already in codebase, Phase 18 uncomputation complete
- Architecture: HIGH - Pattern follows Python's LIFO context manager model exactly, existing `__enter__` / `__exit__` provides foundation
- Pitfalls: HIGH - Based on Python context manager documentation warnings + Phase 18/19 quantum-specific requirements

**Research date:** 2026-01-28
**Valid until:** 90 days (Python context manager protocol stable, codebase architecture stable)

**Phase 19 specific notes:**
- CONTEXT.md provides clear implementation decisions from user discussion—no ambiguity on core semantics
- Phase 18 uncomputation infrastructure is complete and tested—Phase 19 extends it with scope triggers
- Python `__enter__` / `__exit__` protocol is well-documented and proven
- Main implementation challenge is orchestrating scope tracking with control state management
- All Python patterns are standard library (no external dependencies)
