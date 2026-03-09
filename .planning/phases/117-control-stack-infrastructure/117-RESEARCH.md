# Phase 117: Control Stack Infrastructure - Research

**Researched:** 2026-03-09
**Domain:** Quantum circuit control context management (Cython/C backend refactoring)
**Confidence:** HIGH

## Summary

Phase 117 replaces the flat global control variables (`_controlled`, `_control_bool`, `_list_of_controls`) in `_core.pyx` with a stack-based `_control_stack` data structure, and adds Toffoli AND emission primitives (`emit_ccx`, `_toffoli_and`, `_uncompute_toffoli_and`) to `_gates.pyx`. This is pure internal infrastructure refactoring -- no public API changes, no new C backend code required.

The key technical challenge is maintaining perfect backward compatibility: the existing single-level `with qbool:` path must produce identical circuits. The `ccx` C function already exists in `gate.h`/`gate.c` and only needs a Cython-level wrapper. The `_toffoli_and` and `_uncompute_toffoli_and` helpers are Python-level functions that compose existing C primitives (`ccx`, `qbool` allocation, qubit deallocation).

**Primary recommendation:** Implement stack-based control context with backward-compatible accessor wrappers, add gate emission helpers to `_gates.pyx`, and update `__enter__`/`__exit__`/`circuit()` reset/`compile.py` save-restore. Validate via existing single-level tests (TestSingleLevelConditional in `test_nested_with_blocks.py`) plus new unit tests for the stack data structure.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Stack entry design: Minimal tuple format `(qbool_ref, and_ancilla_or_None)`. Stack depth implies controlled state. Active control qubit logic defined.
- `_list_of_controls` removed entirely -- replaced by stack.
- Stack stored as `cdef list _control_stack = []` in `_core.pyx`.
- Accessors: `_get_control_stack()`, `_push_control(qbool_ref, and_ancilla)`, `_pop_control()`.
- `emit_ccx` lives in `_gates.pyx` alongside other `emit_*` functions.
- `_toffoli_and` and `_uncompute_toffoli_and` also live in `_gates.pyx`.
- `_toffoli_and` allocates a `qbool` (not raw qubit) for AND-ancilla.
- Existing `&` operator on qbool left as-is.
- Backward compatibility: `_get_controlled()` = `len(_control_stack) > 0`, `_set_controlled()` = no-op, `_get_control_bool()` reads stack top, `_set_control_bool()` = no-op.
- `__enter__` calls `_push_control(self, None)` in Phase 117.
- `__exit__` calls `_pop_control()`.
- `circuit()` reset clears `_control_stack = []`, removing old globals.
- `compile.py` save/restore via `saved_stack = list(_get_control_stack())`.
- AND-ancilla allocated from main `qubit_allocator_t` via `qbool()`.
- Uncomputation ordering: scope cleanup, then uncompute AND-ancilla via reverse CCX, then pop stack.
- After reverse CCX, set `ancilla._uncomputed = True`.

### Claude's Discretion
- Exact error messages for edge cases (e.g., pop from empty stack)
- Whether to add debug logging for stack push/pop operations
- Internal organization of new accessor functions within `_core.pyx`

### Deferred Ideas (OUT OF SCOPE)
- None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CTRL-02 | Framework composes control qubits via Toffoli AND on `__enter__`, producing a combined control ancilla | Stack push/pop infrastructure in `_core.pyx`, `_toffoli_and` in `_gates.pyx`, `__enter__` update in `qint.pyx`. Note: Phase 117 pushes `(self, None)` only -- actual AND composition is Phase 118. |
| CTRL-03 | Framework uncomputes AND-ancilla and restores previous control on `__exit__` | `_pop_control()` in `_core.pyx`, `_uncompute_toffoli_and` in `_gates.pyx`, `__exit__` update in `qint.pyx`. Note: Phase 117 pops `None` ancilla (no uncomputation needed) -- actual AND-ancilla uncomputation is Phase 118. |
</phase_requirements>

## Standard Stack

### Core (No new dependencies -- internal refactoring only)

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `_core.pyx` | `src/quantum_language/_core.pyx` | Global state management, control stack storage | Existing pattern: `cdef` globals + Python accessors |
| `_gates.pyx` | `src/quantum_language/_gates.pyx` | Gate emission helpers (`emit_ccx`, `_toffoli_and`, `_uncompute_toffoli_and`) | Existing pattern: `memset + gate builder + add_gate` |
| `qint.pyx` | `src/quantum_language/qint.pyx` | `__enter__`/`__exit__` context manager updates | Existing context manager code |
| `compile.py` | `src/quantum_language/compile.py` | Save/restore control context for capture-replay | Existing save/restore pattern |
| `gate.h` / `gate.c` | `c_backend/include/gate.h`, `c_backend/src/gate.c` | `ccx()` C function (already exists) | No new C code needed |

### Supporting

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `qbool.pyx` | AND-ancilla allocation via `qbool()` | When `_toffoli_and` allocates ancilla qubit |
| `_core.pxd` | Cython type declarations for C interop | Already declares `gate_t`, `add_gate`, etc. |
| `_gates.pxd` | Cython declarations for `_gates.pyx` | Needs `ccx` declaration added |

### No Alternatives Needed

This is a refactoring of internal infrastructure. There are no library choices -- everything uses existing project patterns and C backend.

## Architecture Patterns

### Recommended Change Map

```
src/quantum_language/
├── _core.pyx          # MODIFY: Replace flat globals with _control_stack
├── _core.pxd          # NO CHANGE (globals not cimportable anyway)
├── _gates.pyx         # MODIFY: Add emit_ccx, _toffoli_and, _uncompute_toffoli_and
├── _gates.pxd         # MODIFY: Add ccx declaration from gate.h
├── qint.pyx           # MODIFY: Update __enter__/__exit__ to use push/pop
├── compile.py         # MODIFY: Update save/restore to use stack
└── qbool.pyx          # NO CHANGE
```

### Pattern 1: Control Stack Global (in `_core.pyx`)

**What:** Replace three separate globals (`_controlled`, `_control_bool`, `_list_of_controls`) with one `_control_stack` list.

**Current state (lines 28-31 of `_core.pyx`):**
```python
cdef bint _controlled = False
cdef object _control_bool = None
cdef int _int_counter = 0
cdef object _list_of_controls = []
```

**New state:**
```python
cdef list _control_stack = []  # List of (qbool_ref, and_ancilla_or_None) tuples
cdef int _int_counter = 0
# _controlled, _control_bool, _list_of_controls REMOVED
```

**Accessor wrappers (backward-compatible):**
```python
def _get_controlled():
    """Check if in controlled context -- backward compatible."""
    return len(_control_stack) > 0

def _set_controlled(bint value):
    """No-op -- controlled state is implicit from stack depth."""
    pass  # Backward compat: callers still call this but it does nothing

def _get_control_bool():
    """Get active control qubit -- backward compatible."""
    if not _control_stack:
        return None
    entry = _control_stack[-1]
    # At depth 1: return the qbool itself (entry[0])
    # At depth 2+: return the AND-ancilla (entry[1]) if present, else entry[0]
    return entry[1] if entry[1] is not None else entry[0]

def _set_control_bool(value):
    """No-op -- managed by push/pop."""
    pass  # Backward compat

def _get_control_stack():
    """Get control stack reference."""
    return _control_stack

def _push_control(qbool_ref, and_ancilla):
    """Push control entry onto stack."""
    global _control_stack
    _control_stack.append((qbool_ref, and_ancilla))

def _pop_control():
    """Pop control entry from stack."""
    global _control_stack
    if not _control_stack:
        raise RuntimeError("Cannot pop from empty control stack")
    return _control_stack.pop()
```

**Critical detail:** `_get_list_of_controls()` and `_set_list_of_controls()` must also become no-ops or return empty list for backward compat during the transition.

### Pattern 2: Gate Emission (in `_gates.pyx`)

**What:** Add `emit_ccx` following the exact same pattern as `emit_x`, `emit_h`, etc.

**Key details from existing pattern:**
1. `memset(&g, 0, sizeof(gate_t))` to zero-init the gate struct
2. Call the C builder function (e.g., `ccx(&g, target, ctrl1, ctrl2)`)
3. `add_gate(circ, &g)` to append to circuit

**Required `_gates.pxd` addition:**
```python
# In _gates.pxd, add to the gate.h extern block:
void ccx(gate_t *g, qubit_t target, qubit_t control1, qubit_t control2)
```

**Required `_gates.pyx` addition:**
```python
# In _gates.pyx, add ccx to the gate.h extern block:
void ccx(gate_t *g, unsigned int target, unsigned int control1, unsigned int control2)
```

**`emit_ccx` implementation pattern:**
```python
cpdef void emit_ccx(unsigned int target, unsigned int ctrl1, unsigned int ctrl2):
    """Emit Toffoli (CCX) gate directly to circuit.

    Unlike the & operator, this does NOT allocate intermediate qubits
    or track dependencies. Used for control stack AND composition.
    """
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
    memset(&g, 0, sizeof(gate_t))
    ccx(&g, target, ctrl1, ctrl2)
    add_gate(circ, &g)
```

Note: `emit_ccx` does NOT auto-handle controlled context (no `_get_controlled()` check). This is intentional -- it emits a raw CCX gate for internal stack management. The control stack infrastructure IS the thing that manages controlled context.

### Pattern 3: Toffoli AND Helpers (in `_gates.pyx`)

**What:** `_toffoli_and` allocates a qbool AND-ancilla and applies CCX. `_uncompute_toffoli_and` reverses the CCX and marks the ancilla as uncomputed.

**`_toffoli_and` implementation pattern:**
```python
def _toffoli_and(ctrl1_qubit, ctrl2_qubit):
    """Compute AND of two control qubits into a fresh ancilla.

    Allocates a qbool for the AND result and applies CCX(ctrl1, ctrl2, ancilla).
    Returns the qbool ancilla.

    Parameters
    ----------
    ctrl1_qubit : unsigned int
        First control qubit index
    ctrl2_qubit : unsigned int
        Second control qubit index

    Returns
    -------
    qbool
        AND-ancilla qubit (initialized to ctrl1 AND ctrl2)
    """
    from .qbool import qbool as _qbool
    ancilla = _qbool()  # Allocates 1-bit from qubit_allocator
    ancilla_qubit = ancilla.qubits[63]  # Right-aligned, bit at index 63
    emit_ccx(ancilla_qubit, ctrl1_qubit, ctrl2_qubit)
    return ancilla
```

**`_uncompute_toffoli_and` implementation pattern:**
```python
def _uncompute_toffoli_and(ancilla, ctrl1_qubit, ctrl2_qubit):
    """Uncompute AND-ancilla via reverse CCX and deallocate.

    Parameters
    ----------
    ancilla : qbool
        AND-ancilla to uncompute
    ctrl1_qubit : unsigned int
        First control qubit index
    ctrl2_qubit : unsigned int
        Second control qubit index
    """
    ancilla_qubit = ancilla.qubits[63]
    emit_ccx(ancilla_qubit, ctrl1_qubit, ctrl2_qubit)  # CCX is self-adjoint
    ancilla._is_uncomputed = True  # Prevent __del__ double-uncomputation
    # Deallocate qubit
    from ._core import _deallocate_qubits
    _deallocate_qubits(ancilla.allocated_start, 1)
    ancilla.allocated_qubits = False
```

### Pattern 4: `__enter__` Update (in `qint.pyx`)

**What:** Replace the existing `__enter__` logic with `_push_control(self, None)`.

**Current `__enter__` (lines 784-834):**
- Reads `_controlled`, `_control_bool`, `_list_of_controls`
- If not controlled: sets `_control_bool = self`
- If controlled: pushes to `_list_of_controls`, does `_control_bool &= self` (calls `__and__` -- THIS IS THE LINE THAT FAILS for nested blocks with NotImplementedError)
- Sets `_controlled = True`
- Manages scope stack

**New `__enter__` for Phase 117:**
```python
def __enter__(self):
    self._check_not_uncomputed()
    _scope_stack = _get_scope_stack()

    # Push this qbool as control (no AND-ancilla in Phase 117)
    _push_control(self, None)

    # Phase 19: Scope management - push new scope frame
    current_scope_depth.set(current_scope_depth.get() + 1)
    _scope_stack.append([])

    # Update creation_scope for intermediate expressions
    if self.operation_type is not None:
        self.creation_scope = current_scope_depth.get()

    return self
```

**Key insight:** In Phase 117, `_push_control(self, None)` means every stack entry has `and_ancilla=None`. The `_get_control_bool()` wrapper returns `entry[0]` (the qbool itself) when `entry[1] is None`. This produces identical behavior to the old `_control_bool = self` for single-level use.

For nested blocks (depth 2+), Phase 117 will push a second entry but `_get_control_bool()` still returns the innermost qbool. This means nested `with` blocks will use only the inner condition as control, ignoring the outer. This is a known intermediate state -- Phase 118 adds the AND composition to correctly combine controls.

### Pattern 5: `__exit__` Update (in `qint.pyx`)

**What:** Replace `_set_controlled(False)` / `_set_control_bool(None)` with `_pop_control()`.

**New `__exit__` for Phase 117:**
```python
def __exit__(self, exc__type, exc, tb):
    _scope_stack = _get_scope_stack()

    # Phase 19: Uncompute scope-local qbools FIRST
    if _scope_stack:
        scope_qbools = _scope_stack.pop()
        scope_qbools.sort(key=lambda q: q._creation_order, reverse=True)
        for qbool_obj in scope_qbools:
            if not qbool_obj._is_uncomputed:
                qbool_obj._do_uncompute(from_del=False)

    # Decrement scope depth
    current_scope_depth.set(current_scope_depth.get() - 1)

    # Pop control stack (replaces _set_controlled(False) + _set_control_bool(None))
    entry = _pop_control()
    # In Phase 117: entry[1] is always None (no AND-ancilla to uncompute)
    # Phase 118 will add: if entry[1] is not None: _uncompute_toffoli_and(...)

    return False
```

### Pattern 6: `circuit()` Reset Update (in `_core.pyx`)

**What:** In `circuit.__init__`, replace old globals with `_control_stack = []`.

**Current reset block (lines 397-401):**
```python
_controlled = False
_control_bool = None
_list_of_controls = []
```

**New reset block:**
```python
_control_stack = []
```

### Pattern 7: `compile.py` Save/Restore Update

**What:** Replace individual global save/restore with stack save/restore.

**Current (lines 1216-1227):**
```python
saved_controlled = _get_controlled()
saved_control_bool = _get_control_bool()
saved_list_of_controls = list(_get_list_of_controls())
_set_controlled(False)
_set_control_bool(None)
_set_list_of_controls([])
try:
    block = self._capture(args, kwargs, quantum_args)
finally:
    _set_controlled(saved_controlled)
    _set_control_bool(saved_control_bool)
    _set_list_of_controls(saved_list_of_controls)
```

**New pattern:**
```python
from ._core import _get_control_stack, _set_control_stack

saved_stack = list(_get_control_stack())
_set_control_stack([])  # Clear stack for uncontrolled capture
try:
    block = self._capture(args, kwargs, quantum_args)
finally:
    _set_control_stack(saved_stack)  # Restore stack
```

This requires adding `_set_control_stack(value)` to `_core.pyx`:
```python
def _set_control_stack(value):
    """Replace entire control stack (for compile.py save/restore)."""
    global _control_stack
    _control_stack = value
```

### Anti-Patterns to Avoid

- **Modifying the C backend:** The `ccx()` C function already exists. Do NOT add new C code -- everything is Cython-level wrappers.
- **Breaking `_get_controlled()` / `_get_control_bool()` signatures:** Callers throughout the codebase (especially `_gates.pyx` emit functions) rely on these returning bool and qbool respectively. The wrapper implementations must match exactly.
- **Removing `_set_controlled()` / `_set_control_bool()` entirely:** Even though they're no-ops, existing code still calls them. Keep them as no-ops for gradual transition. The compile.py code calls `_set_controlled(False)` etc. in several places.
- **Making `emit_ccx` control-aware:** Unlike `emit_x` etc., `emit_ccx` must NOT check `_get_controlled()` -- it's an internal primitive for the control stack itself.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CCX gate emission | Custom gate struct builder | `ccx()` from `gate.h` (already exists) | C function handles all gate_t fields correctly |
| Qubit allocation for AND-ancilla | Raw `_allocate_qubit()` | `qbool()` constructor | Gets proper `qubits[63]` indexing, dependency tracking, `_is_uncomputed` flag |
| Qubit deallocation | Manual allocator calls | `_deallocate_qubits()` from `_core` | Existing wrapper handles allocator safely |
| Gate reversal (for CCX uncomputation) | `reverse_circuit_range()` | Direct `emit_ccx` again | CCX is self-adjoint (its own inverse), no need for general reversal |

**Key insight:** CCX is self-inverse. Applying `emit_ccx(target, ctrl1, ctrl2)` twice with the same arguments restores the target qubit to its original state. This means `_uncompute_toffoli_and` just calls `emit_ccx` again -- no need for adjoint gate computation.

## Common Pitfalls

### Pitfall 1: Import Cycles Between `_gates.pyx` and `qbool.pyx`

**What goes wrong:** `_toffoli_and` needs to create a `qbool()` instance, but `_gates.pyx` importing `qbool` at module level could create circular imports since `qbool` depends on `qint` which uses `_gates`.
**Why it happens:** Cython modules have strict import ordering. `_gates.pyx` is imported by `qint.pyx` (for `emit_p`), and `qbool.pyx` imports `qint.pyx`.
**How to avoid:** Use local imports inside `_toffoli_and` and `_uncompute_toffoli_and`: `from .qbool import qbool as _qbool`. This is already the pattern used in `qint.pyx` branch() method (line 689: `from quantum_language._gates import emit_ry`).
**Warning signs:** `ImportError` during module initialization.

### Pitfall 2: `_get_control_bool()` Must Return None When Stack Empty

**What goes wrong:** Code throughout the codebase checks `if _get_controlled():` before accessing `_get_control_bool()`. If the stack is empty, `_get_control_bool()` must return `None` (not crash).
**Why it happens:** Several places in `qint.pyx` constructor (lines 318-322) check `_control_bool = _get_control_bool(); if _control_bool is not None:`.
**How to avoid:** The wrapper checks `if not _control_stack: return None` FIRST.
**Warning signs:** `IndexError` accessing `_control_stack[-1]` on empty list.

### Pitfall 3: `compile.py` Uses Individual Setter Functions

**What goes wrong:** The compile.py save/restore code (line 1219) calls `_set_controlled(False)`, `_set_control_bool(None)`, `_set_list_of_controls([])`. If these are suddenly no-ops, the save/restore doesn't actually clear the control context during capture.
**Why it happens:** The no-op wrappers prevent actually modifying state.
**How to avoid:** Update compile.py to use `_set_control_stack([])` / `_set_control_stack(saved_stack)` directly, rather than relying on the individual setters.
**Warning signs:** Compiled functions emit controlled gates when they should emit uncontrolled ones.

### Pitfall 4: `_get_list_of_controls` Still Referenced

**What goes wrong:** `compile.py` imports `_get_list_of_controls` and `_set_list_of_controls` (lines 35, 41). `qint.pyx` also imports them (line 43). Removing these functions breaks imports.
**Why it happens:** Context decision says "remove `_list_of_controls`" but import sites still reference them.
**How to avoid:** Keep `_get_list_of_controls()` returning `[]` and `_set_list_of_controls()` as no-op. Remove the actual global but keep the accessor functions as stubs. Update `compile.py` imports to use stack-based accessors instead.
**Warning signs:** `ImportError` on `_get_list_of_controls`.

### Pitfall 5: `__exit__` Ordering With Scope Stack

**What goes wrong:** The CONTEXT.md specifies uncomputation ordering: (1) scope cleanup, (2) uncompute AND-ancilla, (3) pop stack. If pop happens before scope cleanup, the control context is wrong during scope qbool uncomputation.
**Why it happens:** Scope-local qbool uncomputation needs to happen while still in controlled context (so reverse gates are properly controlled).
**How to avoid:** In `__exit__`, do scope cleanup first (existing logic), THEN pop. This is already the correct order in the existing code -- just make sure `_pop_control()` is called AFTER scope stack cleanup.
**Warning signs:** Incorrect gate sequences during scope cleanup, gates not controlled when they should be.

### Pitfall 6: `circuit.__init__` Global Declaration

**What goes wrong:** `circuit.__init__` declares `global _controlled, _control_bool, _list_of_controls` (line 387). After removing these globals, the `global` statement must reference `_control_stack` instead.
**Why it happens:** Cython requires explicit `global` declarations for module-level assignments.
**How to avoid:** Update the `global` statement at the top of `__init__` to include `_control_stack` and remove `_controlled`, `_control_bool`, `_list_of_controls`.
**Warning signs:** `UnboundLocalError` or silent shadowing of the module global.

## Code Examples

### Example 1: Full `_core.pyx` Global Replacement

```python
# Source: _core.pyx lines 28-31 -> replaced with:
cdef list _control_stack = []
cdef int _int_counter = 0
# _controlled, _control_bool, _list_of_controls REMOVED
```

### Example 2: `emit_ccx` in `_gates.pyx`

```python
# Source: follows pattern of emit_x (lines 60-77 of _gates.pyx)
# Note: ccx needs to be added to the cdef extern block at line 23

cpdef void emit_ccx(unsigned int target, unsigned int ctrl1, unsigned int ctrl2):
    """Emit Toffoli (CCX) gate directly to circuit.

    Does NOT check controlled context -- this is a raw gate emission
    for internal control stack use.
    """
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
    memset(&g, 0, sizeof(gate_t))
    ccx(&g, target, ctrl1, ctrl2)
    add_gate(circ, &g)
```

### Example 3: `circuit.__init__` Reset

```python
# Source: circuit.__init__ in _core.pyx, lines 387-401
# In the global declaration at top of __init__:
global _circuit_initialized, _circuit, _num_qubits, _int_counter, _smallest_allocated_qubit, _control_stack, _global_creation_counter, _scope_stack, _tradeoff_policy, _arithmetic_ops_performed

# In the reset block (replacing lines 399-401):
_control_stack = []
```

### Example 4: `compile.py` Stack Save/Restore

```python
# Source: compile.py lines 1215-1227 -> replaced with:
from ._core import _get_control_stack, _set_control_stack

if is_controlled:
    saved_stack = list(_get_control_stack())
    _set_control_stack([])
    try:
        block = self._capture(args, kwargs, quantum_args)
    finally:
        _set_control_stack(saved_stack)
else:
    block = self._capture(args, kwargs, quantum_args)
```

## State of the Art

| Old Approach | Current Approach (Phase 117) | Impact |
|--------------|------------------------------|--------|
| `_controlled` bool + `_control_bool` object + `_list_of_controls` list | `_control_stack` list of tuples | Enables arbitrary nesting depth |
| `__enter__` does `_control_bool &= self` (calls `__and__`) | `__enter__` does `_push_control(self, None)` | Eliminates NotImplementedError for nested `with` |
| `__exit__` does `_set_controlled(False)` | `__exit__` does `_pop_control()` | Correctly restores outer control context |
| No direct CCX emission from Python | `emit_ccx()` wraps C `ccx()` | Phase 118 uses this for AND composition |

## Open Questions

1. **Should `_set_controlled()` and `_set_control_bool()` emit deprecation warnings?**
   - What we know: Both become no-ops. Some internal code still calls them.
   - What's unclear: Whether any third-party or user code calls them directly.
   - Recommendation: Keep as silent no-ops. They're underscore-prefixed (private API). No deprecation warning needed.

2. **Should `_get_list_of_controls()` return the stack contents or empty list?**
   - What we know: It's imported in `compile.py` (line 35) and `qint.pyx` (line 43).
   - What's unclear: Whether any code reads the list for purposes beyond save/restore.
   - Recommendation: Return empty list `[]` as backward-compat stub. The compile.py save/restore should be updated to use `_get_control_stack()` directly, making this moot.

3. **How does Phase 117's nested `with` behavior differ from Phase 118?**
   - What we know: Phase 117 pushes `(self, None)`. `_get_control_bool()` returns the innermost qbool, ignoring outer controls.
   - What's unclear: Whether any tests expect the old NotImplementedError for nested blocks.
   - Recommendation: The existing nested tests in `test_nested_with_blocks.py` are marked `xfail(raises=NotImplementedError)`. After Phase 117, nested `with` no longer raises NotImplementedError -- they silently use only the inner control. These tests will fail with wrong results (not NotImplementedError), so the `strict=True` xfail will cause test failures. Phase 118 should update these xfail markers. For Phase 117, the tests can be updated to `xfail(strict=False)` or the reason changed to reflect the new intermediate behavior.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (configured in `pytest.ini`) |
| Config file | `pytest.ini` |
| Quick run command | `pytest tests/python/test_nested_with_blocks.py::TestSingleLevelConditional -x -v` |
| Full suite command | `pytest tests/python/ -v --timeout=120` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CTRL-02 | `_push_control` adds entry to stack, `_get_controlled()` returns True | unit | `pytest tests/python/test_control_stack.py::test_push_makes_controlled -x` | Wave 0 |
| CTRL-02 | `emit_ccx` emits a Toffoli gate to the circuit | unit | `pytest tests/python/test_control_stack.py::test_emit_ccx_gate_count -x` | Wave 0 |
| CTRL-02 | `_toffoli_and` allocates qbool ancilla and applies CCX | unit | `pytest tests/python/test_control_stack.py::test_toffoli_and_allocation -x` | Wave 0 |
| CTRL-03 | `_pop_control` restores previous state, `_get_controlled()` returns False for empty stack | unit | `pytest tests/python/test_control_stack.py::test_pop_restores_uncontrolled -x` | Wave 0 |
| CTRL-03 | `_uncompute_toffoli_and` applies reverse CCX and marks ancilla uncomputed | unit | `pytest tests/python/test_control_stack.py::test_uncompute_toffoli_and -x` | Wave 0 |
| CTRL-02/03 | Single-level `with` blocks produce identical circuits to old implementation | regression | `pytest tests/python/test_nested_with_blocks.py::TestSingleLevelConditional -x -v` | Exists |
| CTRL-02/03 | `circuit()` reset clears control stack | unit | `pytest tests/python/test_control_stack.py::test_circuit_reset_clears_stack -x` | Wave 0 |
| CTRL-02/03 | `compile.py` save/restore works with stack | unit | `pytest tests/python/test_control_stack.py::test_compile_save_restore -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_nested_with_blocks.py::TestSingleLevelConditional -x -v`
- **Per wave merge:** `pytest tests/python/ -v --timeout=120`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/python/test_control_stack.py` -- unit tests for stack push/pop, emit_ccx, toffoli_and, uncompute_toffoli_and, circuit reset, compile save/restore
- [ ] Update `tests/python/test_nested_with_blocks.py` xfail markers -- nested tests no longer raise NotImplementedError after Phase 117

*(Existing `TestSingleLevelConditional` tests in `test_nested_with_blocks.py` provide regression coverage for single-level behavior.)*

## Sources

### Primary (HIGH confidence)
- `_core.pyx` (lines 28-31, 91-116, 387-401) -- current global state and accessor implementation
- `_gates.pyx` (lines 1-207) -- existing gate emission pattern (emit_ry, emit_x, emit_h, emit_z, emit_p)
- `qint.pyx` (lines 784-882) -- current `__enter__`/`__exit__` implementation
- `compile.py` (lines 1215-1227) -- current save/restore control context
- `gate.h` (line 45) -- `ccx()` C function declaration: `void ccx(gate_t *g, qubit_t target, qubit_t control1, qubit_t control2)`
- `gate.c` (lines 264-271) -- `ccx()` C implementation
- `_core.pxd` (lines 1-346) -- Cython type declarations, `add_gate` declaration
- `_gates.pxd` (lines 1-21) -- Cython declarations for gate primitives
- `qint.pxd` (lines 1-29) -- qint cdef class attribute declarations
- `qbool.pyx` (lines 1-89) -- qbool constructor and copy
- `test_nested_with_blocks.py` -- existing single-level and nested test cases
- `117-CONTEXT.md` -- locked implementation decisions from discussion phase

### Secondary (MEDIUM confidence)
- CCX self-adjoint property -- standard quantum computing knowledge, verified by `gates_are_inverse()` in `gate.c`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure internal refactoring
- Architecture: HIGH -- all patterns directly derived from existing codebase code
- Pitfalls: HIGH -- identified from reading actual code import chains and call sites
- Code examples: HIGH -- derived from actual source code with line references

**Research date:** 2026-03-09
**Valid until:** Indefinite (internal refactoring of existing code, no external dependencies)
