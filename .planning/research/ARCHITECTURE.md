# Architecture Research: Nested Controls, 2D qarray, and Chess Engine

**Domain:** Quantum programming framework -- control composition, array types, compiled chess engine
**Researched:** 2026-03-09
**Confidence:** HIGH (all findings based on direct source code analysis)

## Existing Architecture Summary

The framework has three layers:

```
+-----------------------------------------------------------------+
|                   Python Frontend (DSL)                          |
|  qint.pyx  qbool.pyx  qarray.pyx  compile.py  walk.py          |
|  operator overloading, context managers, @ql.compile             |
+-----------------------------------------------------------------+
|                   Cython Bindings (_core.pyx)                    |
|  Global state: _controlled, _control_bool, _list_of_controls    |
|  scope_stack, current_scope_depth, qubit_allocator               |
+-----------------------------------------------------------------+
|                   C Backend (gate primitives)                    |
|  add_gate, CQ_*/QQ_*/cCQ_*/cQQ_*, circuit_t, gate_t            |
|  All controlled variants take a single control_qubit arg        |
+-----------------------------------------------------------------+
```

### Control Flow for `with qbool:`

Current single-level flow:

```
__enter__(self):
  1. if not _controlled:
       _control_bool = self          # first level
     else:
       _list_of_controls.append(_control_bool)
       _control_bool &= self         # <-- THIS CRASHES (NotImplementedError)
  2. _controlled = True
  3. scope_depth++, scope_stack.push([])

__exit__():
  1. scope_stack.pop() -> uncompute scope-local vars (LIFO)
  2. scope_depth--
  3. _controlled = False             # <-- BUG: unconditionally False
  4. _control_bool = None            # <-- BUG: doesn't restore previous
```

### Why Nesting Currently Fails

Two independent failures:

1. **`_control_bool &= self`** in `__enter__` line 816 calls `__and__` (qint_bitwise.pxi line 132-133), which raises `NotImplementedError("Controlled quantum-quantum AND not yet supported")` because `_controlled` is already True.

2. **`__exit__` unconditionally sets `_controlled=False`** and `_control_bool=None`, which would corrupt the outer control context even if the AND succeeded.

---

## Integration Design: Nested `with qbool:` Blocks

### New Component: Control Stack (replaces flat globals)

**Problem:** Current design uses a single `_controlled` flag and `_control_bool` reference. Nesting requires a stack.

**Solution: Replace `_controlled`, `_control_bool`, `_list_of_controls` with a single `_control_stack` list.**

```
Globals to replace:
  _controlled: bool       -> len(_control_stack) > 0
  _control_bool: qbool    -> _control_stack[-1] if _control_stack else None
  _list_of_controls: list -> no longer needed (stack replaces it)
```

New state:
```python
_control_stack = []   # List[qbool] -- each entry is the effective control at that depth
```

#### Modified `__enter__`

```python
def __enter__(self):
    self._check_not_uncomputed()

    if _control_stack:
        # Nested: compute AND of outer control and self
        outer = _control_stack[-1]
        combined = _toffoli_and(outer, self)  # New function, see below
        _control_stack.append(combined)
        # Track combined qbool for uncomputation on exit
        self._combined_control = combined
    else:
        # Top level: self is the control
        _control_stack.append(self)
        self._combined_control = None

    # Scope management (unchanged)
    current_scope_depth.set(current_scope_depth.get() + 1)
    _scope_stack.append([])
    if self.operation_type is not None:
        self.creation_scope = current_scope_depth.get()
    return self
```

#### Modified `__exit__`

```python
def __exit__(self, exc_type, exc, tb):
    # Uncompute scope-local vars (unchanged)
    if _scope_stack:
        scope_qbools = _scope_stack.pop()
        scope_qbools.sort(key=lambda q: q._creation_order, reverse=True)
        for qb in scope_qbools:
            if not qb._is_uncomputed:
                qb._do_uncompute(from_del=False)

    current_scope_depth.set(current_scope_depth.get() - 1)

    # Pop control stack
    _control_stack.pop()

    # Uncompute the combined AND ancilla if this was nested
    if self._combined_control is not None:
        _uncompute_toffoli_and(self._combined_control)
        self._combined_control = None

    return False
```

### New Component: `_toffoli_and` / `_uncompute_toffoli_and`

**What:** Compute the AND of two qbools into a fresh ancilla qubit using a Toffoli (CCX) gate. Return a qbool wrapping the ancilla.

**Where:** `_core.pyx` (close to the control state globals) or a new `_control_utils.py`.

**Implementation:**

```python
def _toffoli_and(a: qbool, b: qbool) -> qbool:
    """Compute a AND b into a fresh ancilla qubit via CCX."""
    ancilla = qbool()  # Allocates fresh qubit, initialized to |0>
    # CCX(a, b, ancilla): ancilla = a AND b
    # Emit CCX gate directly (not via & operator which goes through __and__)
    _emit_ccx(int(a.qubits[63]), int(b.qubits[63]), int(ancilla.qubits[63]))
    ancilla._keep_flag = True  # Don't auto-uncompute
    return ancilla

def _uncompute_toffoli_and(combined: qbool):
    """Uncompute the AND ancilla by reversing the CCX, then free the qubit."""
    # Re-apply CCX (self-inverse) to reset ancilla to |0>
    # Then deallocate the qubit
    # combined already has the qubit reference
    pass  # Details depend on how we emit CCX
```

**Critical detail:** CCX is self-inverse. `_uncompute_toffoli_and` just re-applies the same CCX gate (the two original control qubits haven't changed because we're still in the with-block exit path), which resets the ancilla to |0>, then deallocates it.

**Gate emission:** We need a way to emit a raw CCX without going through the `__and__` operator (which allocates result qints, tracks dependencies, etc.). Options:

1. **Use `_gates.py` emit function** -- add `emit_ccx(ctrl1, ctrl2, target)` similar to existing `emit_x`, `emit_ry`, `emit_p`, `emit_p_raw`.
2. **Use `inject_remapped_gates` with a CCX gate dict** -- already available, just needs a helper.

Option 1 is cleaner. Add `emit_ccx` to `_gates.pyx` or `_gates.py`.

### Affected Modules and Changes

| Module | Change Type | What Changes |
|--------|-------------|--------------|
| `_core.pyx` | MODIFY | Replace `_controlled`, `_control_bool`, `_list_of_controls` with `_control_stack`. Update all accessor functions. |
| `qint.pyx` (`__enter__`/`__exit__`) | MODIFY | Rewrite to use `_control_stack` and `_toffoli_and`. Add `_combined_control` attribute. |
| `qint.pyx` (`__init__`) | MODIFY | Replace `_get_control_bool()` checks with `_control_stack[-1]` equivalent. |
| `qint.pxd` | MODIFY | Add `_combined_control` cdef attribute to qint. |
| `qint_arithmetic.pxi` | MODIFY | Replace `_get_controlled()` / `_get_control_bool()` with stack-based accessors. |
| `qint_bitwise.pxi` | NO CHANGE (or minimal) | The `& operator` itself does not need to be controlled for this feature. The AND for control composition uses direct CCX emission. |
| `qint_comparison.pxi` | MODIFY | Same accessor replacement as arithmetic. |
| `_gates.pyx` or `_gates.py` | MODIFY | Add `emit_ccx` function. |
| `compile.py` | MODIFY | Replace `_get_controlled()` / `_get_control_bool()` imports. Controlled variant derivation now potentially adds >1 control. |
| `walk.py` | SIMPLIFY | Can potentially use real `with qbool:` nesting instead of V-gate CCRy workaround. |

### Accessor Function Migration

Current accessors to replace:

```python
_get_controlled()       -> len(_control_stack) > 0
_set_controlled(v)      -> REMOVE (push/pop replaces set)
_get_control_bool()     -> _control_stack[-1] if _control_stack else None
_set_control_bool(v)    -> REMOVE (push/pop replaces set)
_get_list_of_controls() -> REMOVE (stack replaces list)
_set_list_of_controls() -> REMOVE
```

**Backward compatibility:** Keep `_get_controlled()` and `_get_control_bool()` as thin wrappers over the stack to minimize churn in arithmetic/bitwise/comparison code:

```python
def _get_controlled():
    return len(_control_stack) > 0

def _get_control_bool():
    return _control_stack[-1] if _control_stack else None
```

This means `qint_arithmetic.pxi`, `qint_comparison.pxi`, and most of `compile.py` need NO changes to their control qubit extraction code. The only changes are in `__enter__`/`__exit__` and `circuit.__init__` (reset).

### Depth-N Control Composition

For depth 2: `with a:` then `with b:` produces combined = a AND b (1 CCX, 1 ancilla).

For depth 3: `with a:` then `with b:` (combined_ab = a AND b) then `with c:` produces combined_abc = combined_ab AND c (another CCX, another ancilla). Total: 2 ancillas, 2 CCX gates.

For depth N: N-1 ancilla qubits, N-1 CCX gates. Each level adds exactly 1 ancilla.

**Uncomputation order:** `__exit__` at each level uncomputes its own combined control. LIFO ordering is natural because Python `with` blocks nest correctly.

### Interaction with `@ql.compile`

**Capture path:** `_capture_and_cache_both` currently saves/restores `_controlled`, `_control_bool`, `_list_of_controls` when capturing in uncontrolled mode. With the stack, it saves/restores `_control_stack`:

```python
if is_controlled:
    saved_stack = list(_control_stack)
    _control_stack.clear()
    try:
        block = self._capture(...)
    finally:
        _control_stack[:] = saved_stack
```

**Controlled variant derivation:** `_derive_controlled_gates` already adds one control qubit to every gate. This works correctly for nested controls because the effective control qubit (from `_control_stack[-1]`) is always a single qubit -- either the original qbool or the AND-ancilla. The compile replay path in `_replay` maps `block.control_virtual_idx` to `int(_get_control_bool().qubits[63])`, which automatically picks up the correct combined control qubit.

**No change needed** in `_derive_controlled_gates` or `_replay` control mapping.

---

## Integration Design: 2D qarray Support

### Current State

2D qarray already works for most operations:
- `qarray(dim=(8,8), dtype=qbool)` -- WORKS (via `__init__` dim path)
- `arr[rank, file]` -- WORKS (via `_handle_multi_index`)
- `arr[rank, file] += x` -- WORKS (via `__setitem__` tuple path)
- `arr[:, col]` slicing -- WORKS (via `_handle_multi_index`)
- Element-wise ops -- WORKS (flattened iteration)

### Known Bug: `ql.array((rows, cols))` path

The `_core.pyx` `array()` function at line 335 handles `dim=tuple` by creating nested Python lists, but this goes through the OLD list-based path, not the qarray class. The `__init__.py` `array()` function wraps this correctly into `qarray(data, width=width, dtype=dtype, dim=dim)`.

The real bug from PROJECT.md: "`ql.array((rows, cols))` 2D shape fails with TypeError in `_infer_width`" -- this happens when passing a tuple to `ql.array()` as the first positional argument (data), which gets interpreted as data rather than dim. The fix is to route tuple-of-ints correctly.

### Changes Required

| Module | Change Type | What Changes |
|--------|-------------|--------------|
| `__init__.py` `array()` | MODIFY | Handle case where `data` is a tuple of ints (interpret as dim), or clarify API to require `dim=` keyword. |
| `qarray.pyx` `__init__` | VERIFY | The `dim=` keyword path already works. Verify edge cases (non-square shapes, single-row). |

### No Architectural Changes

2D qarray is already structurally supported. The shape metadata, flattened storage, and multi-dimensional indexing infrastructure are all in place. This is a bug fix, not a new feature.

---

## Integration Design: Chess Engine with `ql.compile(opt=1)`

### Target Architecture

The chess engine in `examples/chess_engine.py` uses the "natural programming" style that the framework was designed for. The key challenge is making it compile into a memory-efficient circuit.

### How `ql.compile(opt=1)` Works

opt=1 (default) builds a call graph DAG during the first call:
1. Each `@ql.compile` function call creates a DAG node
2. Nodes track qubit sets and gate counts
3. `CallGraphDAG.build_overlap_edges()` computes qubit overlap between nodes
4. The DAG is available for analysis but no automatic merging (opt=2 does merging)

For the chess engine, opt=1 is appropriate because:
- The chess function will be called once (it IS the top-level compiled function)
- Gate sequences are captured and optimized (cancel inverse pairs, merge rotations)
- Nested compiled calls (sub-predicates) each get their own cached blocks
- The call graph provides visibility into the circuit structure

### Chess Engine Structure

```
@ql.compile(opt=1)
def count_legal_black_moves(board_arrays...):
    count = ql.qint(0, width=...)

    for king_pos in all_squares:
        with black_king[king_pos]:              # Depth 1 control
            # Try each potential move
            for target in potential_king_moves(king_pos):
                # Make move
                black_king[king_pos] -= 1
                black_king[target] += 1

                # Compute attack map
                for src in all_squares:
                    with white_knight[src]:      # Depth 2 control (REQUIRES NESTING)
                        for atk in knight_attacks(src):
                            attack_map[atk] += 1

                # Count if legal
                with attack_map[target] == 0:    # Depth 2 control (REQUIRES NESTING)
                    count += 1

                # Unmake (reverse attack computation)
                ...

                # Unmake move
                black_king[target] -= 1
                black_king[king_pos] += 1

    return count
```

### Dependency on Nested Controls

The chess engine REQUIRES nested `with` blocks:
- Outer: `with black_king[king_pos]:` (is king at this square?)
- Inner: `with white_knight[src]:` (is knight at this square?)
- Inner: `with attack_map[target] == 0:` (is target not attacked?)

Without nested controls, the chess engine must use workarounds (explicit Toffoli AND via `&`, V-gate decomposition, or inline gate emission) as done in v6.1 and v8.0.

### Memory Efficiency with `@ql.compile`

The compiled function automatically:
1. **Captures** the gate sequence on first call
2. **Optimizes** by cancelling inverse pairs (important for make/unmake move patterns)
3. **Caches** for replay if called again with different inputs
4. **Tracks ancillas** for uncomputation

The make/unmake pattern naturally produces many inverse-cancellable gate pairs:
```
black_king[target] += 1   ->   gates
...
black_king[target] -= 1   ->   inverse gates
```

The optimizer in `_optimize_gate_list` will cancel these during compilation.

### Sub-predicate Composition

The chess engine should use nested `@ql.compile` functions for sub-predicates:

```python
@ql.compile(inverse=True)
def compute_knight_attacks(white_knight_arr, attack_map):
    for src in range(64):
        with white_knight_arr[src // 8, src % 8]:
            for atk_rank, atk_file in knight_attack_table[src]:
                attack_map[atk_rank, atk_file] += 1
    return attack_map
```

This pattern:
- Captures once, replays on subsequent calls
- `inverse=True` enables clean uncomputation via `compute_knight_attacks.inverse(...)`
- Nested compiled calls compose correctly (compile.py handles nested capture via `_capture_depth`)

### qarray as `@ql.compile` Arguments

qarray support in `@ql.compile` is already implemented (v2.1):
- `_classify_args` detects qarray and builds cache key with `('arr', length)`
- `_get_qarray_qubit_indices` extracts all qubit indices
- Replay correctly maps virtual qubits to physical qubits
- qarray return values are reconstructed from virtual-to-real mapping

For the chess engine, board arrays (8x8 qbool qarrays) can be passed directly as compiled function arguments.

---

## Build Order and Dependencies

### Phase 1: Control Stack Infrastructure (No Dependencies)

**What:** Replace flat control globals with `_control_stack`, add `emit_ccx`, implement `_toffoli_and`/`_uncompute_toffoli_and`.

**Modified files:** `_core.pyx`, `_gates.pyx`/`_gates.py`, `qint.pxd`

**Tests:** Unit test `_toffoli_and` produces correct CCX gate, verify `emit_ccx` emits gate.

**Requires rebuild:** Yes (Cython).

### Phase 2: `__enter__`/`__exit__` Rewrite (Depends on Phase 1)

**What:** Rewrite `qint.__enter__` and `qint.__exit__` to use `_control_stack` with AND composition.

**Modified files:** `qint.pyx` (lines 804-882)

**Tests:** The xfail tests in `test_nested_with_blocks.py` should now pass. Remove xfail markers.

**Requires rebuild:** Yes (Cython).

### Phase 3: Compile Module Compatibility (Depends on Phase 2)

**What:** Update `compile.py` save/restore of control state to use `_control_stack`. Verify controlled variant derivation still works.

**Modified files:** `compile.py` (save/restore in `_capture_and_cache_both`, `_auto_uncompute`)

**Tests:** Existing compilation tests (106 tests from v2.1). New test: compiled function inside nested `with` block.

### Phase 4: 2D qarray Bug Fix (No Dependencies)

**What:** Fix `ql.array((rows, cols))` TypeError. Verify 2D qarray works with `dim=` keyword.

**Modified files:** `__init__.py` `array()`, possibly `_qarray_utils.py` `_infer_width`

**Tests:** Create 2D qarray via `ql.array(dim=(8,8), dtype=ql.qbool)`, verify shape, indexing, and element mutation.

### Phase 5: Chess Engine Rewrite (Depends on Phases 2, 3, 4)

**What:** Rewrite chess engine in `examples/chess_engine.py` style using nested `with` blocks, 2D qarrays, and `@ql.compile(opt=1)`.

**Modified files:** New chess engine file (or rewrite `examples/chess_engine.py`)

**Tests:** Circuit-build-only tests (verify circuit builds without OOM, check gate/qubit stats).

---

## Anti-Patterns

### Anti-Pattern 1: Using `&` Operator for Control Composition

**What people do:** `combined = cond_a & cond_b; with combined: ...`
**Why it's wrong:** The `&` operator in qint_bitwise.pxi allocates result qints, tracks dependencies, and does per-bit Toffoli AND -- designed for multi-bit integers. For 1-bit qbool control composition, this is overkill and currently doesn't support controlled context anyway.
**Do this instead:** Use nested `with` blocks directly: `with cond_a: with cond_b: ...` -- the framework handles the Toffoli AND internally.

### Anti-Pattern 2: Modifying `_controlled` Directly

**What people do:** Setting `_set_controlled(False)` / `_set_controlled(True)` to manipulate control state.
**Why it's wrong:** With a control stack, the controlled state is derived from stack depth, not set independently. Setting it directly corrupts the stack invariant.
**Do this instead:** Use `_control_stack.append()` / `_control_stack.pop()` (or the context manager protocol).

### Anti-Pattern 3: Inline Gate Emission to Avoid Nested Controls

**What people do:** Bypass `with qbool:` entirely by emitting controlled gates directly (as done in walk.py with V-gate CCRy decomposition).
**Why it's wrong:** Duplicates control composition logic, fragile, hard to maintain.
**Do this instead:** With nested controls working, use normal `with` blocks and let the framework handle gate control addition.

---

## Scalability Considerations

| Concern | At Depth 2 | At Depth 4 | At Depth 8+ |
|---------|------------|------------|-------------|
| AND ancillas | 1 qubit | 3 qubits | 7 qubits |
| CCX gates per enter/exit | 2 (1 enter + 1 uncompute) | 6 | 14 |
| Control qubit on all gates | 1 control | 1 control (the AND ancilla) | 1 control |

**Key insight:** Each depth level adds exactly 1 ancilla qubit and 2 CCX gates (enter + exit). The C-level gate functions always see a SINGLE control qubit (the top of the control stack), regardless of nesting depth. No changes to the C backend are needed.

**Gate overhead:** Each CCX is 15 gates in Clifford+T decomposition (6 CNOT + 2H + 4T + 3Tdg). At depth 8, that's 14 CCX = 210 extra gates for control composition. For chess engine circuits with millions of gates, this is negligible.

---

## Sources

- Direct source code analysis of:
  - `src/quantum_language/qint.pyx` (lines 804-882: `__enter__`/`__exit__`)
  - `src/quantum_language/_core.pyx` (control state globals, accessors)
  - `src/quantum_language/qint_arithmetic.pxi` (controlled gate dispatch)
  - `src/quantum_language/qint_bitwise.pxi` (`__and__` implementation)
  - `src/quantum_language/compile.py` (controlled variant, save/restore)
  - `src/quantum_language/qarray.pyx` (2D support, dim= constructor)
  - `src/quantum_language/walk.py` (V-gate CCRy workaround for nesting)
  - `src/quantum_language/__init__.py` (`array()` API)
  - `tests/python/test_nested_with_blocks.py` (xfail tests documenting limitation)
  - `examples/chess_engine.py` (target chess engine style)
  - `.planning/PROJECT.md` (known limitations, bug list)

---
*Architecture research for: Nested quantum controls, 2D qarray, chess engine compilation*
*Researched: 2026-03-09*
