# Phase 20: Uncomputation Modes and User Control - Research

**Researched:** 2026-01-28
**Domain:** Quantum resource management, Python API design, global configuration
**Confidence:** HIGH

## Summary

Phase 20 adds user-facing control over automatic uncomputation behavior established in Phases 16-19. This includes:
1. **Mode API**: Global option to switch between lazy (default) and eager (qubit-saving) uncomputation
2. **Explicit control**: `.uncompute()` method for manual triggering (already implemented in Phase 18)
3. **Opt-out mechanism**: `.keep()` method to prevent automatic uncomputation
4. **Error handling**: Clear messages when uncomputation fails or qbools are misused

The research confirms that a module-level option system with per-qbool mode capture (similar to NumPy's error handling configuration) provides the cleanest API. The existing Phase 18 infrastructure (`.uncompute()`, `_do_uncompute()`) already handles explicit control—Phase 20 adds the mode flag and `.keep()` mechanism.

**Primary recommendation:** Implement `ql.option('qubit_saving', bool)` function at module level that sets a global flag, capture the flag value at qbool creation time, and use it in `__del__` to decide when to trigger uncomputation. Add `.keep()` method that sets a scope-based flag checked by `__del__`.

## Standard Stack

### Core (Python Standard Library)

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Module-level function | Python 3.11+ | Global option API (`ql.option()`) | Standard pattern (numpy.seterr, warnings.filterwarnings) |
| Boolean flags | Python native | Mode state storage | Simple, no overhead, clear semantics |
| `inspect` module | stdlib | Scope tracking for `.keep()` | Standard way to inspect call stack for scope boundaries |

### Supporting (Already Implemented)

| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `_do_uncompute()` | quantum_language.pyx | Core uncomputation logic | Phase 18 complete |
| `.uncompute()` | quantum_language.pyx | Explicit uncomputation | Phase 18 complete |
| `__del__` | quantum_language.pyx | Automatic cleanup trigger | Phase 18 complete |
| `_is_uncomputed` flag | qint class | Idempotency tracking | Phase 18 complete |
| `creation_scope` | qint class | Scope depth at creation | Phase 16 complete |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Module-level function | Class attribute (circuit.option) | Class attribute ties to circuit instance, breaks when user doesn't create circuit object explicitly |
| Global flag capture | Thread-local storage | Thread-local adds complexity; single-threaded circuit generation sufficient |
| `.keep()` method | Context manager (`with qbool.preserve():`) | Context manager more complex for simple "don't uncompute" flag |
| Boolean mode flag | Enum ('lazy', 'eager') | Enum adds clarity but overkill for two options; bool is simpler |
| Scope-based `.keep()` | Permanent `.keep()` | Permanent keep prevents all cleanup; scope-based allows cleanup when scope exits |

**Installation:**
No external dependencies—all components are Python stdlib or already implemented.

## Architecture Patterns

### Recommended Mode System Flow

```
User calls ql.option('qubit_saving', True)  # Enable eager mode
    ↓
Module-level _qubit_saving_mode = True       # Global flag set
    ↓
qbool created: result = a & b
    ↓
qint.__init__() captures mode at creation
    self._uncompute_mode = _qubit_saving_mode  # Per-instance flag
    ↓
qbool goes out of scope → __del__() called
    ↓
Check self._uncompute_mode:
  - Lazy (False): Only uncompute if in same scope as creation
  - Eager (True): Always uncompute immediately
    ↓
Trigger _do_uncompute() if mode conditions met
```

### Pattern 1: Global Option API with Get/Set Overloading

**What:** Single function that both gets and sets options based on argument count.

**When to use:** Module-level configuration that users need to query or modify.

**Example:**
```python
# Source: NumPy seterr pattern (https://numpy.org/doc/stable/reference/generated/numpy.seterr.html)

# Module-level state
_qubit_saving_mode = False  # Default: lazy mode

def option(key: str, value=None):
    """Get or set quantum language options.

    Parameters
    ----------
    key : str
        Option name. Currently supported:
        - 'qubit_saving': Enable eager uncomputation (bool)
    value : bool, optional
        New value for option. If None, returns current value.

    Returns
    -------
    bool or None
        Current value if value=None, otherwise None.

    Examples
    --------
    >>> ql.option('qubit_saving')  # Get current mode
    False
    >>> ql.option('qubit_saving', True)  # Enable eager mode
    >>> ql.option('qubit_saving')
    True

    Notes
    -----
    Mode changes affect newly created qbools only. Existing qbools
    retain their creation-time mode.
    """
    global _qubit_saving_mode

    if key == 'qubit_saving':
        if value is None:
            return _qubit_saving_mode
        elif isinstance(value, bool):
            _qubit_saving_mode = value
        else:
            raise ValueError("qubit_saving option requires bool value")
    else:
        raise ValueError(f"Unknown option: {key}")
```

**Why this pattern:**
- Matches Python ecosystem conventions (NumPy, warnings module)
- Single function simplifies API (not separate get/set functions)
- Returns current value for debugging/testing

### Pattern 2: Per-Instance Mode Capture

**What:** Capture global mode flag at qbool creation time, store as instance attribute.

**When to use:** Always—prevents mode changes from affecting existing qbools.

**Example:**
```python
# Source: Phase 20 CONTEXT.md decision + Phase 18 existing structure

cdef class qint:
    cdef bint _uncompute_mode  # True = eager, False = lazy

    def __init__(self, ...):
        global _qubit_saving_mode
        # ... existing initialization ...

        # Phase 20: Capture mode at creation
        self._uncompute_mode = _qubit_saving_mode
```

**Why per-instance:**
- Prevents mid-computation mode changes from breaking existing qbools
- Each qbool has consistent behavior for its entire lifetime
- Simplifies reasoning about uncomputation timing

### Pattern 3: Mode-Aware Automatic Uncomputation

**What:** Modify `__del__` to check mode flag and scope before uncomputing.

**When to use:** Automatic cleanup in Phase 18's `__del__` destructor.

**Example:**
```python
# Source: Phase 18 __del__ + Phase 20 mode decisions

def __del__(self):
    """Automatic uncomputation with mode awareness."""
    # Existing Phase 18 idempotency check
    if self._is_uncomputed or not self.allocated_qubits:
        return

    # Phase 20: Check if .keep() was called
    if hasattr(self, '_keep_flag') and self._keep_flag:
        return  # User opted out of automatic uncomputation

    # Phase 20: Mode-based uncomputation decision
    if self._uncompute_mode:  # Eager mode
        # Always uncompute immediately
        self._do_uncompute(from_del=True)
    else:  # Lazy mode (default)
        # Only uncompute if no longer in scope
        # Check if we're in a deeper scope than creation
        current_scope = current_scope_depth.get()
        if current_scope <= self.creation_scope:
            # Back at creation scope or shallower—safe to uncompute
            self._do_uncompute(from_del=True)
```

**Mode semantics:**
- **Lazy (default)**: Uncompute when scope exits (scope depth returns to creation level)
- **Eager**: Uncompute immediately when garbage collected (minimize peak qubits)

### Pattern 4: Scope-Based `.keep()` Method

**What:** Mark a qbool to prevent automatic uncomputation while in the current scope.

**When to use:** User needs a qbool to persist beyond normal uncomputation.

**Example:**
```python
# Source: Phase 20 CONTEXT.md decisions

def keep(self):
    """Prevent automatic uncomputation in current scope.

    Marks this qbool to skip automatic cleanup when it goes out of
    scope. Useful when you need a qbool to persist for later use.

    Notes
    -----
    - Scope-based: Only affects current Python function/block
    - Does not prevent explicit .uncompute() calls
    - Warning printed if called on already-uncomputed qbool

    Examples
    --------
    >>> result = a & b
    >>> result.keep()  # Don't auto-uncompute when scope exits
    >>> return result  # Can safely return
    """
    if self._is_uncomputed:
        import sys
        print("Warning: .keep() called on already-uncomputed qbool",
              file=sys.stderr)
        return

    # Mark to skip __del__ uncomputation
    self._keep_flag = True

    # Note: Scope tracking (clearing _keep_flag when scope exits)
    # is Claude's discretion—could use stack inspection or
    # context manager integration from Phase 19
```

**Scope semantics:**
- `.keep()` prevents `__del__` from triggering uncomputation
- Scope-based means flag is cleared when Python function/block exits
- Implementation options (Claude's choice):
  - Option A: Never clear flag (permanent keep)
  - Option B: Clear on scope exit using Phase 19 scope stack
  - Option C: Use `inspect` module to track caller frame

### Pattern 5: Enhanced Error Messages

**What:** Provide clear, actionable error messages for uncomputation failures.

**When to use:** All uncomputation error paths.

**Example:**
```python
# Source: Phase 20 CONTEXT.md error handling decisions

def _check_not_uncomputed(self):
    """Raise if qbool has been uncomputed (already in Phase 18)."""
    if self._is_uncomputed:
        raise ValueError(
            "Cannot use qbool: already uncomputed. "
            "Create a new qbool or call .keep() to prevent automatic cleanup."
        )

def uncompute(self):
    """Explicit uncomputation with reference checking (already in Phase 18)."""
    if self._is_uncomputed:
        import sys
        print("Warning: .uncompute() called on already-uncomputed qbool",
              file=sys.stderr)
        return

    # Check reference count
    import sys
    refcount = sys.getrefcount(self)
    if refcount > 2:
        raise ValueError(
            f"Cannot uncompute: qbool still in use ({refcount - 1} references exist). "
            f"Delete other references first or let automatic cleanup handle it."
        )

    self._do_uncompute(from_del=False)
```

**Error message patterns:**
- Start with "Cannot [action]:" for failures
- Explain the problem (already uncomputed, still in use)
- Provide actionable solution (create new, delete references)
- Use `ValueError` for user errors (not RuntimeError)
- Print warnings (not errors) for idempotent operations

### Anti-Patterns to Avoid

- **Circuit-level option storage:** Don't store mode in circuit object—users may not create circuit explicitly
- **Retroactive mode changes:** Don't allow mode changes to affect existing qbools—only new creations
- **Silent `.keep()` failures:** Print warning when `.keep()` called on uncomputed qbool (not silent, not error)
- **Complex scope tracking for `.keep()`:** Use simple flag, not elaborate stack inspection (unless needed)
- **Custom exception classes:** Use standard `ValueError`, not quantum-specific exceptions

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Global option API | Custom registry class | Module-level function (NumPy pattern) | Simple, familiar, no object lifecycle |
| Mode storage | Configuration file | In-memory boolean flag | No I/O overhead, immediate effect, testing-friendly |
| Scope tracking for `.keep()` | Custom scope manager | Phase 19 scope stack or simple flag | Already implemented, proven, integrated with `with` statement |
| Error messages | Raw exception strings | Formatted with context | Consistency across codebase, actionable user guidance |

**Key insight:** Phase 18 did the hard work (uncomputation logic, cascade, idempotency). Phase 20 is mostly API and configuration—keep it simple.

## Common Pitfalls

### Pitfall 1: Mode Change Affects Existing Qbools

**What goes wrong:** User changes mode with `ql.option('qubit_saving', True)` and expects all existing qbools to switch behavior.

**Why it happens:** Forgetting that qbools were created with a specific mode.

**How to avoid:**
- Phase 20 decision: "Mode changes affect new qbools only"
- Capture mode at creation time (`self._uncompute_mode = _qubit_saving_mode`)
- Document clearly that existing qbools keep their mode
- Test both scenarios (mode before creation vs mode after)

**Warning signs:**
- User reports inconsistent uncomputation behavior
- Tests fail when mode is changed mid-test
- Expected eager uncomputation doesn't happen for pre-existing qbools

### Pitfall 2: Eager Mode Uncomputes Too Early

**What goes wrong:** Eager mode uncomputes a qbool while it's still referenced by other qbools.

**Why it happens:** Python GC may run during complex operations, triggering `__del__` unexpectedly.

**How to avoid:**
- Phase 18 already has weak reference tracking—dependencies prevent premature cleanup
- Eager mode still respects Python's reference counting
- Only uncompute when refcount reaches 0 (no other live references)
- Document that eager mode minimizes peak qubits, not total qubits

**Warning signs:**
- RuntimeError "qbool has been uncomputed" during operations
- Circuit corruption from freed qubits being reused
- Tests with chained operations (a & b & c) fail in eager mode

### Pitfall 3: `.keep()` Implementation Complexity

**What goes wrong:** Implementing scope-based `.keep()` with elaborate stack inspection or frame tracking.

**Why it happens:** Over-engineering the "scope-based" requirement.

**How to avoid:**
- Phase 20 decision: "Claude's discretion" for scope implementation
- **Simplest approach:** Make `.keep()` permanent (flag never cleared)—user can call `.uncompute()` explicitly when ready
- **Phase 19 integration:** Use existing `_scope_stack` to clear `.keep()` flag on scope exit
- Document scope semantics clearly

**Recommendation:** Start with permanent flag (simpler), refactor to scope-based only if users request it.

**Warning signs:**
- Complex `inspect` module usage for frame tracking
- Performance overhead from stack inspection on every qbool operation
- Tests fail due to race conditions in scope tracking

### Pitfall 4: Mode API Naming Confusion

**What goes wrong:** Users confused by `ql.option('qubit_saving')` vs `ql.option('eager_uncompute')` or other names.

**Why it happens:** Misalignment between roadmap terminology and API naming.

**How to avoid:**
- Phase 20 decision: Use `'qubit_saving'` (matches roadmap wording)
- "Qubit-saving" clearly describes the benefit (save qubits)
- "Eager uncompute" is implementation detail
- Document both terms in docstring for searchability

**Warning signs:**
- User documentation uses different term than API
- GitHub issues asking "how do I enable eager mode?"
- Inconsistent terminology across codebase

### Pitfall 5: Error vs Warning Inconsistency

**What goes wrong:** Some idempotent operations raise errors, others print warnings.

**Why it happens:** Inconsistent handling of "already done" scenarios.

**How to avoid:**
- Phase 20 decision: "Calling `.uncompute()` or `.keep()` on already-uncomputed qbool prints warning"
- Warnings for idempotent operations (`.uncompute()` twice, `.keep()` on uncomputed)
- Errors for misuse (using uncomputed qbool in operation)
- `ValueError` for all uncomputation failures (not RuntimeError)

**Pattern:**
```python
# Idempotent—warn but continue
if self._is_uncomputed:
    print("Warning: ...", file=sys.stderr)
    return

# Misuse—raise error
if self._is_uncomputed:
    raise ValueError("Cannot use qbool: already uncomputed")
```

**Warning signs:**
- Tests with `pytest.raises(RuntimeError)` instead of `ValueError`
- Silent failures where warnings expected
- Errors raised for idempotent operations

### Pitfall 6: Lazy Mode Never Uncomputes

**What goes wrong:** Lazy mode's scope check never triggers uncomputation because scope depth never decreases.

**Why it happens:** Misunderstanding Python's scope lifetime vs `contextvars` scope depth.

**How to avoid:**
- Recognize that `__del__` is called AFTER scope exits (refcount reaches 0)
- At `__del__` time, scope may be lower than creation scope
- Lazy mode check: `current_scope_depth.get() <= self.creation_scope`
- Test lazy mode with nested functions and `with` blocks

**Warning signs:**
- Lazy mode never uncomputes (same as no uncomputation)
- Peak qubit count identical in lazy vs no-uncomputation baseline
- Tests show no difference between lazy and disabled modes

## Code Examples

Verified patterns from research and existing implementation:

### NumPy-Style Option API Pattern

```python
# Source: NumPy numpy.seterr (https://numpy.org/doc/stable/reference/generated/numpy.seterr.html)
# Adaptation for quantum_language module

# Module-level state (at top of quantum_language.pyx)
_qubit_saving_mode = False

def option(key: str, value=None):
    """Get or set quantum language options.

    Parameters
    ----------
    key : str
        Option name: 'qubit_saving'
    value : bool, optional
        New value. If None, returns current value.

    Returns
    -------
    bool or None
        Current value if getting, None if setting.

    Examples
    --------
    >>> import quantum_language as ql
    >>> ql.option('qubit_saving')
    False
    >>> ql.option('qubit_saving', True)
    >>> ql.option('qubit_saving')
    True
    """
    global _qubit_saving_mode

    if key == 'qubit_saving':
        if value is None:
            return _qubit_saving_mode
        if not isinstance(value, bool):
            raise ValueError("qubit_saving requires bool value")
        _qubit_saving_mode = value
    else:
        raise ValueError(f"Unknown option: {key}")
```

### Existing Phase 18 Explicit Uncompute (Enhancement Context)

```python
# Source: quantum_language.pyx lines 100-143 (Phase 18)
# Shows existing explicit uncomputation that Phase 20 enhances

def uncompute(self):
    """Explicitly uncompute this qbool and its dependencies.

    Raises
    ------
    ValueError
        If other references to this qbool still exist (refcount > 2).
    ValueError
        If using qbool after it has been uncomputed.

    Notes
    -----
    This method is idempotent: calling twice prints warning, not error.
    """
    import sys

    # Phase 18: Idempotent behavior
    if self._is_uncomputed:
        # Phase 20: Clarify this is warning, not error
        print("Warning: .uncompute() called on already-uncomputed qbool",
              file=sys.stderr)
        return

    # Phase 18: Reference count check
    refcount = sys.getrefcount(self)
    if refcount > 2:
        raise ValueError(
            f"Cannot uncompute qbool: {refcount - 1} references still exist. "
            f"Delete other references first or let garbage collection handle cleanup."
        )

    # Perform uncomputation
    self._do_uncompute(from_del=False)
```

### Mode-Aware __del__ Implementation

```python
# Source: Phase 18 __del__ + Phase 20 mode additions
# Modification to existing quantum_language.pyx __del__ method

def __del__(self):
    """Automatic uncomputation on garbage collection with mode awareness."""
    # Phase 18: Basic checks
    if self._is_uncomputed or not self.allocated_qubits:
        return

    # Phase 20: Check .keep() flag
    if hasattr(self, '_keep_flag') and self._keep_flag:
        return  # User opted out

    # Phase 20: Mode-based decision
    if self._uncompute_mode:
        # Eager mode: always uncompute
        self._do_uncompute(from_del=True)
    else:
        # Lazy mode: only if scope has exited
        # When __del__ is called, scope depth may be lower than creation
        current = current_scope_depth.get()
        if current <= self.creation_scope:
            self._do_uncompute(from_del=True)
```

### Simple .keep() Implementation

```python
# Source: Phase 20 CONTEXT.md decisions

def keep(self):
    """Prevent automatic uncomputation in current scope.

    Notes
    -----
    Scope-based: prevents automatic cleanup while in the same
    Python function or block where .keep() was called.

    Examples
    --------
    >>> result = a & b
    >>> result.keep()
    >>> return result  # Safe to return, won't auto-uncompute
    """
    if self._is_uncomputed:
        import sys
        print("Warning: .keep() called on already-uncomputed qbool",
              file=sys.stderr)
        return

    # Set flag to prevent __del__ uncomputation
    self._keep_flag = True

    # Scope tracking (Claude's discretion):
    # Option 1: Permanent (never clear flag)—simplest
    # Option 2: Clear on Phase 19 scope exit
    # Option 3: Use inspect module to track caller frame
```

### Test Pattern for Mode Switching

```python
# Source: Derived from test_phase13_equality.py patterns

def test_mode_switching():
    """Mode changes affect new qbools only."""
    c = ql.circuit()

    # Create qbool in default lazy mode
    a = ql.qbool(True)
    b = ql.qbool(False)
    result1 = a & b

    # Switch to eager mode
    ql.option('qubit_saving', True)

    # Create new qbool in eager mode
    c = ql.qbool(True)
    d = ql.qbool(False)
    result2 = c & d

    # result1 should have lazy behavior (mode at creation)
    assert result1._uncompute_mode == False

    # result2 should have eager behavior
    assert result2._uncompute_mode == True

def test_keep_prevents_uncompute():
    """Calling .keep() prevents automatic uncomputation."""
    c = ql.circuit()

    a = ql.qbool(True)
    b = ql.qbool(False)
    result = a & b

    result.keep()  # Prevent auto-uncompute

    # Delete result—normally would uncompute
    del result
    gc.collect()

    # Qubits should still be allocated (not freed)
    # (Verification depends on Claude's .keep() implementation)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No mode control | Lazy/eager mode option | Phase 20 (now) | Users can optimize for gate count or qubit count |
| Implicit cleanup only | Explicit `.uncompute()` + implicit | Phase 18 (v1.2) | Deterministic cleanup when needed |
| Silent cleanup | Clear error messages | Phase 20 (now) | Easier debugging of uncomputation issues |
| No opt-out | `.keep()` method | Phase 20 (now) | Users can prevent automatic cleanup when needed |
| Global behavior | Per-qbool mode capture | Phase 20 (now) | Predictable behavior, no retroactive changes |

**Quantum framework comparison:**
- **Qiskit QuantumCircuit:** No automatic uncomputation, manual reset gates
- **Cirq:** Manual uncomputation via inverse circuits
- **Q# (Microsoft):** `using` statement for automatic deallocation (scope-based, similar to Phase 19)
- **Silq (ETH Zurich):** Automatic uncomputation via type system (compiler determines when safe)
- **This framework (Phase 20):** User-controlled mode (lazy/eager) + explicit methods + scope integration

**Recent research (2024-2025):**
- [Modular Synthesis of Efficient Quantum Uncomputation](https://dl.acm.org/doi/pdf/10.1145/3689785) (Oct 2024): Automatic uncomputation via modular synthesis
- [Scalable Memory Recycling for Large Quantum Programs](https://ar5iv.labs.arxiv.org/html/2503.00822) (Mar 2025): Topological sort + liveness analysis

Phase 20's mode system is unique—most frameworks either force manual uncomputation (Qiskit, Cirq) or automatic compiler-driven uncomputation (Silq, research systems). This framework provides user choice.

## Open Questions

Things that couldn't be fully resolved:

1. **Scope-based .keep() implementation strategy**
   - What we know: .keep() should prevent uncomputation in current scope
   - What's unclear: How to detect when scope exits to clear flag
   - Recommendations (ordered by simplicity):
     1. **Permanent flag (simplest)**: Never clear `.keep()` flag—user calls `.uncompute()` when ready
     2. **Phase 19 integration**: Clear flag on scope exit using existing `_scope_stack`
     3. **Inspect module**: Use stack frame inspection to detect scope exit
   - Confidence: MEDIUM (marked as Claude's discretion in CONTEXT.md)

2. **Lazy mode scope depth comparison**
   - What we know: Lazy mode should uncompute when scope exits
   - What's unclear: At `__del__` time, what is `current_scope_depth`?
   - Hypothesis: When `__del__` runs, scope depth has already decreased (function returned)
   - Recommendation: Test empirically with nested functions and `with` blocks
   - Confidence: MEDIUM (Python GC timing is non-deterministic)

3. **Error message wording**
   - What we know: Minimal messages, start with "Cannot [action]:"
   - What's unclear: Exact phrasing for each error case
   - Recommendation: Claude's discretion—follow existing Phase 18 patterns
   - Confidence: HIGH (wording is subjective, any clear message works)

4. **Mode flag location (module vs circuit)**
   - What we know: Global option affects all circuits
   - What's unclear: Should mode be per-circuit or truly global?
   - Recommendation: Module-level global (matches decision "affects all subsequent circuits")
   - Confidence: HIGH (CONTEXT.md clear on this)

## Sources

### Primary (HIGH confidence)

- [NumPy numpy.seterr documentation](https://numpy.org/doc/stable/reference/generated/numpy.seterr.html) - Global option API pattern
- [Python warnings module](https://docs.python.org/3/library/warnings.html) - Module-level configuration pattern
- Phase 20 CONTEXT.md - Implementation decisions from user discussion
- Phase 18 RESEARCH.md - Existing uncomputation infrastructure
- Phase 19 RESEARCH.md - Scope tracking with context managers
- Phase 16 RESEARCH.md - Dependency tracking and `creation_scope`
- Existing codebase: quantum_language.pyx (`.uncompute()`, `__del__`, `_do_uncompute()`)

### Secondary (MEDIUM confidence)

- [Python global keyword documentation](https://docs.python.org/3/reference/simple_stmts.html#global) - Module-level state management
- [Python inspect module](https://docs.python.org/3/library/inspect.html) - Stack frame inspection for scope tracking
- [Q# using statement](https://learn.microsoft.com/en-us/azure/quantum/user-guide/language/statements/quantummemorymanagement) - Scope-based qubit deallocation
- [Silq automatic uncomputation](https://silq.ethz.ch/) - Compiler-driven uncomputation

### Tertiary (LOW confidence)

- Community discussions on quantum resource management (various forums)
- Comparison with classical resource management (RAII, garbage collection)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Module-level function is standard Python pattern, no external dependencies
- Architecture: HIGH - Builds directly on Phase 18 infrastructure, simple flag-based mode system
- Pitfalls: HIGH - Based on Python GC behavior documentation + Phase 18/19/20 requirements

**Research date:** 2026-01-28
**Valid until:** 90 days (Python patterns stable, codebase architecture stable)

**Phase 20 specific notes:**
- CONTEXT.md provides clear implementation decisions—low ambiguity
- Phase 18 already implements explicit `.uncompute()` and `_do_uncompute()`
- Phase 19 provides scope stack infrastructure if needed for `.keep()`
- Main work is adding option API, mode flag capture, and `.keep()` method
- Most complexity is in testing mode interactions, not implementation

**Implementation priority:**
1. **Option API** (highest priority): `ql.option('qubit_saving', bool)` function
2. **Mode capture**: Store `_uncompute_mode` flag at qbool creation
3. **Mode-aware `__del__`**: Check mode flag before calling `_do_uncompute()`
4. **.keep() method** (lowest priority): Simple flag, decide scope semantics later
5. **Error message enhancement**: Update existing messages for clarity

**Testing requirements:**
- Mode switching between lazy/eager mid-program
- Per-qbool mode retention after global mode change
- Eager mode reduces peak qubits (verify with `circuit_stats()`)
- Lazy mode reduces gate count (verify with `circuit.gate_count`)
- `.keep()` prevents automatic uncomputation
- Error messages for misuse scenarios
