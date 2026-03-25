# Implementation Plan: BUG-1 and BUG-2 Fixes

Fixes for the two bugs documented in `docs/BUGS.md`. Four independent steps, each a single beads issue.

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
