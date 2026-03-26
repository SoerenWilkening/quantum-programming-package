# Implementation Plan

## Phase 1: BUG-1 and BUG-2 Fixes (DONE)

Fixes for the two bugs documented in `docs/BUGS.md`. Four steps.

---

## Step 1: Add controlled dispatch for division (BUG-1)

**Issue:** Division always calls uncontrolled C functions.

**Files to change:**
- `src/quantum_language/qint_division.pxi`
- `src/quantum_language/qint_preprocessed.pyx` (sync)

**What to do:**

In `_divmod_c`, add control qubit extraction and dispatch:

1. After `cdef bint _controlled = _get_controlled()` (line 43), add control qubit extraction following the pattern from `qint_arithmetic.pxi` lines 36-38:
   ```python
   cdef unsigned int control_qubit = 0
   if _controlled:
       control_qubits = (<qint>_get_control_bool()).qubits
       control_qubit = control_qubits[63]
   ```

2. Replace the unconditional `toffoli_divmod_cq` call (line 67-69) with:
   ```python
   if _controlled:
       toffoli_cdivmod_cq(_circ, dividend_qa, n, <int64_t>divisor,
                          quotient_qa, remainder_qa, control_qubit)
   else:
       toffoli_divmod_cq(_circ, dividend_qa, n, <int64_t>divisor,
                         quotient_qa, remainder_qa)
   ```

3. Same pattern for `toffoli_divmod_qq` call (line 95-97) → dispatch to `toffoli_cdivmod_qq` with `control_qubit`.

4. Sync `qint_preprocessed.pyx`.

**Tests:**
- Verify `examples/test.py` shows different gate counts for `divmod_cq` in Controlled vs Uncontrolled sections.
- Unit test: compile a function with `a //= 3` in controlled context, confirm gate count > uncontrolled gate count.

**Depends on:** Nothing.

---

## Step 2: Fix equality compile-mode guard (BUG-2, part 1)

**Issue:** `eq_cq` records IR in Toffoli mode instead of emitting gates.

**Files to change:**
- `src/quantum_language/qint_comparison.pxi`
- `src/quantum_language/qint_preprocessed.pyx` (sync)

**What to do:**

Change line 112 from:
```python
if _is_compile_mode():
```
to:
```python
if _is_compile_mode() and _circ.arithmetic_mode != 1:
```

This matches the existing pattern at lines 303 and 635 (lt and gt comparisons).

Sync `qint_preprocessed.pyx`.

**Tests:**
- Unit test: `@ql.compile` function using `x == 2` in Toffoli mode should produce non-zero `block.original_gate_count`.
- Verify gate count matches between compiled and uncompiled execution.

**Depends on:** Nothing (parallel with Step 1).

---

## Step 3: Fix bitwise compile-mode guards (BUG-2, part 2)

**Issue:** All five bitwise ops record IR in Toffoli mode instead of emitting gates.

**Files to change:**
- `src/quantum_language/qint_bitwise.pxi`
- `src/quantum_language/qint_preprocessed.pyx` (sync)

**What to do:**

Add `and _circ.arithmetic_mode != 1` to all five locations:

| Line | Operation | Current guard |
|------|-----------|---------------|
| 61   | AND (qq/cq) | `if _is_compile_mode():` |
| 329  | OR (qq/cq) | `if _is_compile_mode():` |
| 635  | XOR (qq/cq) | `if _is_compile_mode():` |
| 831  | IXOR (qq/cq) | `if _is_compile_mode():` |
| 1026 | NOT (qq) | `if _is_compile_mode():` |

Each becomes:
```python
if _is_compile_mode() and _circ.arithmetic_mode != 1:
```

Need access to `_circ` in each location. Check that it's already available (it should be — these are methods on `qint` which is a `circuit` subclass with access to `_circuit`).

Sync `qint_preprocessed.pyx`.

**Tests:**
- Unit test: `@ql.compile` function using `a & b`, `a | b`, `a ^ b`, `~a` in Toffoli mode should produce non-zero `block.original_gate_count`.
- Verify gate count matches between compiled and uncompiled.

**Depends on:** Nothing (parallel with Steps 1 and 2).

---

## Step 4: End-to-end verification

**Issue:** Confirm both bugs are fully resolved.

**Files to change:** None (test-only).

**What to do:**

1. Run `examples/test.py` — confirm `divmod_cq` has different gate counts in Controlled vs Uncontrolled sections.
2. Run `examples/3sat/sat_walk_assembly.py` — confirm compiled and uncompiled gate counts match (both should be ~61111).
3. Run `pytest tests/python/ -v` — no regressions.
4. Write an integration test that captures the exact regression scenario: a `@ql.compile(inverse=True)` function containing `==`, `&`, `^`, `~`, and `with` blocks, verify `block.original_gate_count > 0` and matches direct execution.

**Depends on:** Steps 1, 2, 3.

---

## Dependency Graph

```
Step 1 (div controlled) ──┐
Step 2 (eq guard)      ────┼──> Step 4 (e2e verification)
Step 3 (bitwise guards) ──┘
```

Steps 1, 2, 3 are fully independent and can be implemented in parallel.

---
---

## Phase 2: Complete Call Graph Visibility

The call graph DAG and `report()` currently undercount gates because two categories of operations are invisible:

1. **Inverse compiled-function calls** (`f.inverse(x)`) — `_InverseProxy.__call__` bypasses `CompiledFunc.__call__` entirely, so no DAG node is created.
2. **Automatic uncomputation** — when a qbool/qint goes out of scope, `__del__` → `history.uncompute()` → `_run_inverted_on_circuit()` calls `run_instruction` directly without `record_operation`, so no DAG node is created.

Both contribute real gates to `get_gate_count()` but are absent from `report()` and `call_graph.aggregate()`.

---

### Step 5: Add DAG nodes for inverse compiled-function calls

**Issue:** `_InverseProxy.__call__` dispatches to `_ancilla_path` or `_standalone_path`, neither of which creates a DAG node. Inverse calls (e.g. `make_move.inverse` in `_evaluate_validity`) are invisible in the report.

**Files to change:**
- `src/quantum_language/compile/_inverse.py`

**What to do:**

Add DAG node creation to `_InverseProxy.__call__`, mirroring the pattern in `CompiledFunc.__call__` / `_add_nested_call_dag_node`:

1. At the top of `__call__`, check if a DAG context is active (`current_dag_context() is not None`).
2. After the ancilla/standalone path completes, add a call node to the active DAG with:
   - `func_name` = `self._cf._func.__name__ + "_inv"` (e.g. `"make_move_inv"`)
   - Gate count from the forward block's `original_gate_count` (inverse has the same cost)
   - `is_call_node=True`
   - U/C assignment based on the current calling context (same logic as `_add_nested_call_dag_node`)
3. If there is a parent compile block active (`_get_active_compile_block()`), append the node index to `parent_block._dag_node_indices` so it appears in `report()`.

The ancilla path uses `inject_remapped_gates` which already updates `get_gate_count()`. The standalone path calls `_replay` which also updates gate counts. The DAG node just makes this visible in the report.

**Tests:**
- Compile a function that calls `f(x)` then `f.inverse(x)`. Verify `report()` shows both `f` and `f_inv` entries.
- Verify `call_graph.aggregate()["gates"]` matches `get_gate_count()` delta.

**Depends on:** Nothing.

---

### Step 6: Add DAG nodes for automatic uncomputation

**Issue:** `_run_inverted_on_circuit` (called by `HistoryGraph.uncompute()` when qbool/qint goes out of scope) calls `run_instruction(..., invert=True)` directly without calling `record_operation`, so the gate cost is invisible in the DAG.

**Files to change:**
- `src/quantum_language/qint.pyx` (the `_run_inverted_on_circuit` function)
- `src/quantum_language/qint_preprocessed.pyx` (sync)

**What to do:**

After the `run_instruction` call in `_run_inverted_on_circuit` (line 139), call `record_operation` when a DAG context is active:

1. Import `record_operation` from `call_graph` and `current_dag_context` (or use the existing `_dag_builder_stack` check that makes `record_operation` a no-op when no context is active).
2. After `run_instruction(_seq, _qa, True, _circ)`, call:
   ```python
   record_operation(
       "uncompute",
       tuple(qubit_mapping),
       gate_count=_seq.total_gate_count,
       sequence_ptr=seq_ptr,
       invert=True,
       controlled=False,
   )
   ```
3. The `record_operation` call is a no-op outside `@ql.compile` capture (no DAG context active), so this is safe to call unconditionally.

**Note:** Auto-uncomputation fires during `__del__`, which may happen at unpredictable times (garbage collection). During `@ql.compile` capture, temporaries go out of scope at deterministic points (end of `with` blocks, end of function body), so the DAG nodes will appear in the correct position. Outside capture, `record_operation` is a no-op.

**Tests:**
- Compile a function that creates a temporary qbool (e.g. `cond = (x == 5)` used in a `with` block). Verify the DAG contains an `uncompute` node after the `with` block.
- Verify `call_graph.aggregate()["gates"]` matches `get_gate_count()` delta.

**Depends on:** Nothing (parallel with Step 5).

---

### Step 7: End-to-end verification of call graph completeness

**Issue:** Confirm the report accounts for all gates.

**Files to change:** None (test-only).

**What to do:**

1. Run `examples/3sat/sat_walk_assembly.py` — verify `report()` total matches `get_gate_count()`.
2. Write an integration test: compile a function containing forward calls, inverse calls, and temporary qbools. Assert `call_graph.aggregate()["gates"]` equals the `get_gate_count()` delta from before to after execution.
3. Verify that the `make_move_inv` entries now appear in the sat_walk report alongside `make_move` and `is_valid`.

**Depends on:** Steps 5 and 6.

---

### Dependency Graph (Phase 2)

```
Step 5 (inverse DAG nodes) ──┐
                              ├──> Step 7 (e2e verification)
Step 6 (uncompute DAG nodes) ┘
```

Steps 5 and 6 are fully independent and can be implemented in parallel.
