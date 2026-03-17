# Quantum Assembly — Project Specification

## 1. Overview

This document captures the specification for ongoing development of the Quantum Assembly framework.

The framework compiles high-level Python code (arithmetic, comparisons, `with` blocks) into quantum circuits. Users never interact with gates directly.

---

## 2. Task Areas

| Task | Area | Priority | Status |
|------|------|----------|--------|
| 1 | Code maintenance (speed, memory, stability, file sizes) | Normal | Not started |
| 2 | Codebase cleanup | Normal | Not started |
| 4 | Circuit compilation improvements | Normal | Phase 0 complete |
| 5 | DSL purity & simulate-mode cleanup | High | **Done** |
| 6 | In-place comparison operators | High | Not started |
| 7 | Compiled function control propagation | High | Not started |
| 8 | History graph inverse cancellation | Normal | Not started |

### Dependencies

- Tasks 1 and 2 are independent of each other and of Task 4.
- Task 6 requires extending the arithmetic backend (C level) for split-register operations.
- Task 7 is independent of other tasks.
- Task 8 depends on Task 4 (history graph infrastructure from Phase 1).

---

## 3. Task 1: Code Maintenance

Improve the existing codebase in terms of:

- **Speed**: Optimize hot paths, reduce overhead in gate emission and circuit construction.
- **Memory**: Reduce memory footprint of circuit representation.
- **Stability**: Fix edge cases, improve error handling at system boundaries.
- **File sizes**: Reduce bloat (e.g., the 100+ generated sequence files in `c_backend/src/sequences/`).
- **Functionality**: Extend supported operations where gaps exist.

No detailed specification yet — to be refined based on profiling and usage patterns.

---

## 4. Task 2: Codebase Cleanup

General cleanup of the codebase:

- Remove dead code and unused modules.
- Consolidate duplicated logic.
- Improve module organization.
- Clean up the `.planning/` directory (large number of deleted planning files in git status).
- Standardize naming conventions across Python and C layers.

No detailed specification yet.

---

## 5. Task 4: Circuit Compilation Improvements

### 5.1 Problem

Currently, full quantum circuits are stored in memory. For large algorithms, this is prohibitive. Gates are meant to be applied to a QPU, not stored.

### 5.2 Direction

- Use **call graphs** to store instructions at a higher level of abstraction, rather than storing every individual gate.
- The `@ql.compile` decorator and `CallGraphDAG` are partial implementations of this idea.
- Optimization flags (`opt=0`, `opt=1`, `opt=2`) exist but are incomplete.

### 5.3 Completed (Phase 0)

- Execution-order edges (replace overlap edges with qubit-aware sequential edges)
- Flat operation DAG (remove wrapper/function nodes)
- Graph immutability after capture
- Gate counts stored on `sequence_t`, including hardcoded sequences
- Gate counts wired through `_record_operation` → `DAGNode`

### 5.4 Remaining

- Complete and working optimization flags (`opt=0`, `opt=1`, `opt=2`).
- Streaming gate application (gates applied to QPU without full circuit storage).

---

## 6. Task 5: DSL Purity & Simulate-Mode Cleanup

### 6.1 Problem

The `simulate` option (`ql.option('simulate')`) controls whether `run_instruction` stores gates in the circuit or only counts them. Currently:

- `simulate` defaults to `False` after `ql.circuit()` (tracking-only mode).
- Internal helpers like `_flip_all` and `diffusion()` locally toggle `simulate=True` before executing DSL operations, then restore it. This creates a "mixed simulate mode" where some operations store gates and others don't.
- This is wrong. `simulate` is a **global option** that the user sets once. Internal code must never toggle it.

Additionally, the `&` operator (`__and__`) on qbools raises `NotImplementedError` when used inside a `with` block (controlled context). This prevents replacing recursive nested `with` patterns with flat `&`-chain patterns.

### 6.2 Changes

1. **Remove all local simulate toggles** from `_flip_all` (diffusion.py), `diffusion()` wrapper, and any other internal helper. Tests that need QASM output must set `ql.option('simulate', True)` in their fixture.

2. **Implement controlled-AND**: `&` operator inside `with` blocks. Decompose controlled Toffoli (C-CCX) into standard Toffolis + ancilla. This enables flat `&`-chain patterns to replace recursive nested `with` loops.

3. **Replace `_flip_all` single-register calls** with `^= 1` or `~reg` directly. Keep `_flip_all` only as multi-register convenience (without simulate toggle).

4. **Replace recursive nested `with` patterns** (`_nested_phase_flip`, `_apply_nested_with`) with flat `&`-chain + single `with combined:` block. Depends on controlled-AND support.

5. **Raise test qubit budget** from 17 to 21. Verified: 21-qubit statevector simulation takes ~0.2s (2M amplitudes).

6. **Future**: `qarray.all()` primitive for multi-controlled operations — replaces manual `&`-chain loops with internal AND-reduction. Fewer allocations, potential gate-level optimization.

---

## 7. Task 6: In-Place Comparison Operators

### 7.1 Problem

The current `<`, `>`, `<=`, `>=` comparisons create widened (n+1)-bit temporary copies of both operands via CNOT, perform subtraction on the copies, and extract the MSB as the result. The temporaries linger in the history graph as children. This is wasteful: two full copies of the operands plus a widened subtraction, when `==` already demonstrates that in-place subtract-then-restore works.

### 7.2 Design

Replace the copy-based approach with an in-place borrow-ancilla pattern:

1. Allocate a single ancilla qbool (initialized to |0⟩) to serve as the (n+1)th borrow bit.
2. Perform (n+1)-bit subtraction across `[a_0..a_{n-1}, ancilla]` minus `[b_0..b_{n-1}]`. The ancilla captures the borrow/underflow.
3. CNOT the ancilla into a fresh result qbool.
4. Perform (n+1)-bit addition across `[a_0..a_{n-1}, ancilla]` plus `[b_0..b_{n-1}]` to restore `a` and the ancilla to |0⟩.
5. Deallocate the ancilla.

**Result**: No copies, one temporary ancilla (deallocated immediately), both operands unchanged. Matches the subtract-check-restore pattern that `==` already uses.

**Prerequisite**: The arithmetic backend must support subtraction/addition across a qint register + a separate qbool treated as the MSB. This may require modification to the C-level adder/subtractor to accept a split register.

### 7.3 Scope

- `__lt__`, `__gt__`: rewrite to use borrow-ancilla pattern.
- `__le__`, `__ge__`: currently implemented as `~(a > b)` / `~(a < b)` — these automatically benefit.
- Remove widened temporary creation and CNOT copy logic from comparison operators.
- Remove history graph child tracking for comparison temporaries (no longer needed).
- Verify operand preservation via existing `test_operand_preservation` tests.

---

## 8. Task 7: Compiled Function Control Propagation

### 8.1 Problem

When a `@ql.compile`-decorated function is called inside a `with` block (controlled context), the control does not propagate correctly in all modes. Specifically:

- During capture, the control stack is cleared — so captured gates are always uncontrolled. This is correct.
- `_derive_controlled_block` produces a controlled variant by prepending a control index to every gate. This exists.
- However, when `simulate=True` or `opt=1`, `run_instruction` does not correctly select the controlled vs uncontrolled sequence at runtime. Both paths produce the same gate sequence.

### 8.2 Design

A single compiled function cache entry stores both uncontrolled (canonical) and derived controlled gate sequences:

1. **Capture**: First call always captures uncontrolled gates (control stack cleared during capture, as today).
2. **Derive**: Immediately derive the controlled variant via `_derive_controlled_block` (prepend control virtual index to every gate).
3. **Store**: Both sequences stored in the same cache entry. Cache key no longer needs `control_count` as a discriminator.
4. **Runtime selection**: `run_instruction` checks the current control stack. If non-empty, use the controlled sequence and map the control virtual index to the actual control qubit. If empty, use the uncontrolled sequence.
5. **Nested `with` blocks**: Multiple nested `with` blocks collapse to a single control via the AND-ancilla mechanism. The controlled sequence always has exactly one control index — it maps to whichever qubit (direct or AND-ancilla) represents the combined condition.

The gate sequences themselves are fixed — only the qubit index mapping is dynamic at runtime.

### 8.3 Scope

- Modify `run_instruction` to select controlled/uncontrolled sequence based on control stack.
- Ensure `opt=1` (DAG-only) mode also respects control context for gate injection.
- Verify with `simulate=True` that controlled and uncontrolled calls produce different gate sequences.
- Nested `with` blocks produce correct combined control.

---

## 9. Task 8: History Graph Inverse Cancellation

### 9.1 Problem

Users sometimes manually uncompute operations (e.g., `a += 3` followed later by `a -= 3`). Currently, both operations are recorded in the history graph. When the history graph is later uncomputed automatically, these redundant entries generate unnecessary inverse gates, doubling the circuit depth for operations the user already reversed.

### 9.2 Design

**Tail-only cancellation**: When an operation is performed on a qint, check if it is the exact inverse of the last entry in that qint's history graph. If so, and no active blockers exist, cancel both entries (remove the last entry and don't add the new one).

**Supported inverse pairs** (initial scope):
- `+= k` cancels `-= k` (and vice versa)
- `^= x` cancels `^= x` (XOR is self-inverse)
- `f(a)` cancels `f.inverse(a)` (compiled function and its inverse, matched by sequence pointer)

**Deferred to later**:
- `*= k` / `//= k` — multiplication/division inverse matching is more complex.

**Blocker mechanism**: Operations between a forward and its potential reverse may create entanglement dependencies that prevent cancellation. Example:

```python
a += 3       # history: [add_3]
b += a       # blocker added to a's history referencing b
a -= 3       # cannot cancel: active blocker (b depends on intermediate state)
```

- **When blockers are added**: Every time a qint appears as a source operand (right-hand side of any operation), a blocker is added to its history graph referencing the dependent qint.
- **Blocker lifecycle**: Blockers are cleared on qubit deallocation (uncomputation) of the dependent qint, not on Python garbage collection. This requires an explicit notification mechanism — when a qint's qubits are deallocated, it notifies all qints it has blockers on.
- **Cancellation check**: At the time of the potential inverse operation, walk the blockers after the last history entry. If any are still active (referenced qint's qubits are still allocated), cancellation is blocked. Add the operation as a normal history entry instead.

### 9.3 Scope

- Add `Blocker` data structure to `HistoryGraph` (reference to dependent qint + position).
- Add blocker insertion in all arithmetic/comparison/bitwise operations where a qint is a source operand.
- Add qubit-deallocation notification to clear blockers.
- Add tail-matching logic in history append path.
- Support `+=`/`-=`, `^=`, and compiled function inverse cancellation.
- Defer `*=`/`//=` to future work.
