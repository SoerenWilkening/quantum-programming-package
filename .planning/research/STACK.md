# Stack Research: v9.0 Nested Controls & Chess Engine

**Domain:** Quantum programming framework -- nested control composition, 2D qarray, chess engine compilation
**Researched:** 2026-03-09
**Confidence:** HIGH

## Scope

This research covers ONLY the stack additions/changes needed for three new capabilities:
1. Nested `with qbool:` blocks via Toffoli AND control composition at arbitrary depth
2. 2D qarray support (`ql.qarray(dim=(8,8), dtype=ql.qbool)`)
3. Chess engine rewrite with `ql.compile(opt=1)` in readable natural-programming style

The existing stack (Python 3.11+, Cython 3.x, C backend, NumPy, Pillow, rustworkx, Qiskit) is validated and does NOT change.

## Key Finding: No New Dependencies Required

All three features are implementable with the existing stack. The work is entirely in the Python/Cython layer with no new C backend changes, no new libraries, and no version bumps needed.

---

## Feature 1: Nested `with qbool:` Blocks

### Current State

The `__enter__`/`__exit__` methods on `qint` (lines 784-882 of `qint.pyx`) use three global variables:
- `_controlled` (bool) -- whether we are in ANY control context
- `_control_bool` (qint/qbool) -- the CURRENT control qubit
- `_list_of_controls` (list) -- accumulated prior controls

On nested entry (when `_controlled` is already True), the code does:
```python
_list_of_controls.append(_control_bool)
_control_bool &= self  # Toffoli AND -- produces new qbool ancilla
```

On exit, it unconditionally resets:
```python
_set_controlled(False)
_set_control_bool(None)
```

**This is broken for nesting.** The `__exit__` always resets to "not controlled" regardless of nesting depth. After exiting an inner `with`, the outer control context is lost.

### What Needs to Change

| Component | Change | Technology | Why |
|-----------|--------|------------|-----|
| `_core.pyx` globals | Replace flat `_controlled`/`_control_bool` with a **control stack** | Python list (already used for `_scope_stack`) | Stack enables push/pop semantics matching nested `with` blocks. The `_list_of_controls` already partially does this but `__exit__` discards it. |
| `qint.pyx __enter__` | Push current control state onto stack, compute AND ancilla for combined control | Toffoli AND via existing `&` operator on qbool | The `&` operator already produces correct Toffoli AND gates; current code already calls `_control_bool &= self`. The issue is state management, not gate generation. |
| `qint.pyx __exit__` | Pop control stack, restore previous control, **uncompute AND ancilla** | Existing `reverse_circuit_range` / `_do_uncompute` | AND ancilla from `_control_bool &= self` must be uncomputed on scope exit to free the qubit. This follows the same LIFO uncomputation pattern already used for scope-local qbools. |
| `_core.pyx circuit()` | Reset control stack on circuit init | Same as existing `_list_of_controls = []` reset | Already done for other state; add the new stack. |

### Stack Requirements

**No new libraries.** The control stack is a Python list, just like `_scope_stack`. The AND ancilla mechanism uses existing Toffoli AND (`Q_and` in C backend, `&` operator in Python). Uncomputation uses existing `reverse_circuit_range`.

### Data Structure Design

```python
# In _core.pyx -- replace flat globals with stack
cdef list _control_stack = []  # Stack of (control_bool, was_controlled) tuples

# __enter__ pushes:
_control_stack.append((_control_bool, _controlled))

# __exit__ pops:
prev_control, prev_was_controlled = _control_stack.pop()
_set_control_bool(prev_control)
_set_controlled(prev_was_controlled)
```

### Integration Points

- **`compile.py`:** The `extract_gate_range` / `inject_remapped_gates` already handle arbitrary gate sequences including controlled variants. The compile decorator captures control state via `_get_controlled()` / `_get_control_bool()` -- these accessors remain unchanged; they still return the "current" top-of-stack control.
- **`walk.py`:** The V-gate CCRy decomposition workaround in `_emit_cascade_h_controlled` becomes unnecessary once nested `with` blocks work natively. However, keep it for now as it is performance-optimized for the specific Ry gate decomposition case.
- **C backend:** No changes. `add_gate` already handles arbitrary `NumControls` via `large_control` array. The Python layer composes the controls; the C layer just sees gate-level controls.

### Ancilla Budget

Each nesting level allocates one AND-ancilla qubit. For depth-D nesting, D-1 ancilla qubits are needed (the first `with` uses the qbool directly, each subsequent level ANDs with the previous). These are uncomputed on `__exit__`, so the cost is transient.

For the chess engine (max depth ~3-4 nested `with` blocks), this is 2-3 ancilla qubits -- negligible.

---

## Feature 2: 2D qarray Support

### Current State

The `qarray` class in `qarray.pyx` already supports:
- `dim=(rows, cols)` construction (lines 53-80) -- **this works**
- Multi-dimensional indexing `arr[i, j]` via `_handle_multi_index` (lines 381-457) -- **this works**
- `__setitem__` for `arr[i, j] = value` (lines 241-283) -- **this works**
- Row/column slicing `arr[0, :]` and `arr[:, 0]` -- **this works**

The known bug from PROJECT.md is:
> `ql.array((rows, cols))` 2D shape fails with TypeError in `_infer_width`

This occurs when calling `ql.array((8, 8))` without the `dim=` keyword -- the tuple `(8, 8)` is passed as `data`, and `_infer_width` tries to call `.bit_length()` on a tuple element. The fix is either:
1. Detect tuple-of-ints as dimension spec in `__init__` (treat `qarray((8,8))` same as `qarray(dim=(8,8))`)
2. Or simply document that `dim=` keyword is required

### What Needs to Change

| Component | Change | Technology | Why |
|-----------|--------|------------|-----|
| `qarray.pyx __init__` | Handle `data=tuple_of_ints` as dimension constructor | Pure Python type check | Fix the TypeError by detecting `data` is a tuple of ints and routing to `dim=` codepath |
| `_qarray_utils.py _detect_shape` | Tuple input handling | Pure Python | `_detect_shape` only handles `list`, not `tuple`. Add tuple support or convert. |

### What Does NOT Need to Change

The chess engine example (`examples/chess_engine.py`) already uses the correct form:
```python
white_knight = ql.qarray(dim=(8, 8), dtype=ql.qbool)
```

This form already works in the existing codebase. The bug is only triggered by the positional argument form `ql.array((8, 8))`.

### Stack Requirements

**No new libraries.** This is a 5-10 line fix in `qarray.pyx __init__`.

### Testing

The existing test `test_create_from_dimensions` in `test_qarray.py` already passes for `dim=(3,3)`. Additional tests needed:
- `ql.array((8, 8))` positional tuple form
- Element-wise operations on 2D arrays (existing tests already cover this)
- In-place mutation `arr[i, j] += x` (existing tests cover this)

---

## Feature 3: Chess Engine Compilation with `ql.compile(opt=1)`

### Current State

The chess engine example (`examples/chess_engine.py`) shows the target programming style:
```python
@ql.compile(opt=1)
def count_legal_black_moves():
    with black_king[*index] == 1:
        ...
        with white_knight[a, b]:
            ...
```

This style requires:
1. **Nested `with` blocks** (Feature 1 above)
2. **2D qarray indexing** (Feature 2 above)
3. **`@ql.compile(opt=1)` working with nested controls** -- the compile decorator must correctly capture and replay gate sequences containing nested control contexts

### opt=1 Behavior

The `opt` parameter controls call graph optimization level:
- `opt=1` (default): Call graph DAG tracking, no merging. Each compiled function call is a separate node.
- `opt=2`: Selective sequence merging based on qubit overlap.
- `opt=3`: Full expansion (not yet implemented, deferred).

For the chess engine, `opt=1` is correct -- it captures the gate sequence once and replays with qubit remapping.

### What Needs to Change for Compile + Nested Controls

| Component | Change | Technology | Why |
|-----------|--------|------------|-----|
| `compile.py` capture path | Control stack state must be saved/restored around capture | Existing `_get_controlled` / `_set_controlled` accessors | During capture, the decorated function may enter nested `with` blocks. The captured gate sequence includes all controlled gates. On replay, the same control structure is replayed via `inject_remapped_gates`. This already works for single-level controls; it needs verification for nested controls. |
| `compile.py` controlled variant | `_make_controlled_block` must compose outer control with inner controls | Existing controlled variant derivation | When a compiled function is called inside a `with` block, each gate gets an additional control qubit. If the captured sequence already contains multi-controlled gates from nested `with` blocks, the controlled variant adds one more control level. This uses `large_control` in the C backend, which already handles arbitrary control counts. |

### Integration Concern: Star Unpacking in `with` Statement

The chess engine example uses `black_king[*index]` syntax. This is standard Python tuple unpacking, available since Python 3.5. It works because `__getitem__` receives the unpacked tuple. No special framework support needed.

### Stack Requirements

**No new libraries.** The compile infrastructure already handles all the gate capture/replay mechanics. The key dependency is Feature 1 (nested controls) working correctly at the gate generation level -- the compile decorator is agnostic to what gates are generated during capture.

---

## Recommended Stack (No Changes)

### Core Technologies (Unchanged)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.11+ | Frontend, API, tests | No change |
| Cython | >=3.0.11,<4.0 (current: 3.2.4) | Python/C bridge | No change |
| C (C23) | gcc/clang | Backend gate engine | No change needed -- `add_gate` already handles arbitrary `NumControls` |
| NumPy | >=1.24 | Array ops in compile/draw | No change |
| rustworkx | 0.17.1 | Call graph DAG | No change |

### Supporting Libraries (Unchanged)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| Pillow | >=9.0 | Circuit visualization | No change |
| Qiskit | >=1.0 | Verification/simulation | No change |
| qiskit-aer | >=0.13 | Statevector simulator | No change |
| scipy | >=1.10 | IQAE confidence intervals | No change |

### Development Tools (Unchanged)

| Tool | Purpose | Status |
|------|---------|--------|
| pytest >=7.0 | Test runner | No change |
| ruff >=0.1.0 | Linting/formatting | No change |
| pre-commit >=3.0 | Commit hooks | No change |

## What NOT to Add

| Avoid | Why | What to Do Instead |
|-------|-----|-------------------|
| New gate decomposition library | The V-gate CCRy decomposition in `walk.py` is a workaround for broken nesting; fixing nesting removes the need | Fix `__enter__`/`__exit__` to support proper nesting |
| Abstract syntax tree (AST) tracing for compile | Tempting for analyzing nested control structure, but the capture-replay model works fine | Continue with capture-replay; the gate-level representation already encodes all control information |
| New C backend functions for multi-controlled gates | `add_gate` with `large_control` already handles arbitrary control counts | No new C code needed |
| Control flow graph library | Overkill for tracking nested `with` state | A Python list as control stack is sufficient |
| Separate 2D array class | `qarray` already handles N-dimensional shapes internally | Fix the `__init__` bug instead |

## Installation

No new packages to install. The existing development environment is sufficient:

```bash
# Existing setup (unchanged)
pip install -e ".[dev,verification]"
```

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Cython >=3.0.11 | Python 3.11-3.14 | Current 3.2.4 is stable |
| rustworkx 0.17.1 | Python 3.9-3.13 | Stable ABI, no update needed |
| NumPy >=1.24 | Python 3.11+ | Current 2.4.2, no issues |

## Architecture Impact Summary

All three features are **Python/Cython layer changes only**:

1. **Nested controls**: ~50-80 lines changed in `qint.pyx` (`__enter__`/`__exit__`) and ~10 lines in `_core.pyx` (control stack globals). Zero C backend changes.
2. **2D qarray**: ~10 lines changed in `qarray.pyx __init__`. Zero C backend changes.
3. **Chess engine compile**: Zero framework changes beyond Features 1 and 2. The compile decorator already handles the mechanics correctly once nested controls produce correct gate sequences.

The total code change for the stack/infrastructure layer is approximately 60-90 lines of Python/Cython, all in existing files. No new files, no new dependencies, no build system changes.

## Sources

- Codebase analysis: `qint.pyx` lines 784-882 (`__enter__`/`__exit__`), `_core.pyx` lines 28-116 (control globals), `qarray.pyx` lines 38-80 (dim constructor), `compile.py` lines 725-830 (CompiledFunc), `types.h` lines 66-75 (gate_t with large_control)
- [rustworkx 0.17.1](https://www.rustworkx.org/) -- verified current version (HIGH confidence)
- [Cython releases](https://github.com/cython/cython/releases) -- latest stable 3.2.4 (HIGH confidence)
- `.planning/codebase/STACK.md` -- existing stack documentation (HIGH confidence)
- `examples/chess_engine.py` -- target chess engine style (HIGH confidence)

---
*Stack research for: v9.0 Nested Controls & Chess Engine*
*Researched: 2026-03-09*
