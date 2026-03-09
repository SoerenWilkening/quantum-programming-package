# Domain Pitfalls

**Domain:** Nested quantum controls (Toffoli AND composition), 2D qarray fixes, chess engine rewrite with `ql.compile(opt=1)`
**Researched:** 2026-03-09

## Critical Pitfalls

Mistakes that cause rewrites or major correctness issues.

### Pitfall 1: `__exit__` Unconditionally Resets Control State to (False, None)

**What goes wrong:** The current `__exit__` on line 878-879 of `qint.pyx` always sets `_set_controlled(False)` and `_set_control_bool(None)`. When nested `with` blocks are introduced, exiting an inner `with` block destroys the outer control context entirely. All operations after the inner `with` block but still inside the outer `with` block execute unconditionally instead of being controlled by the outer condition.

**Why it happens:** The current implementation was designed for single-level `with` blocks only. There is a `_list_of_controls` that `__enter__` appends to, but `__exit__` never pops from it -- the comment on line 881 literally says `# undo logical and operations (TODO from original)`.

**Consequences:** After exiting an inner `with` block, all subsequent operations in the outer `with` block are emitted as uncontrolled gates. This is a silent correctness bug -- no exception is thrown, the circuit just computes wrong results. In a chess engine with many nested conditionals, this would produce incorrect legality evaluations across the entire search tree.

**Prevention:** Implement `__exit__` as a proper stack pop:
1. On `__enter__`, push the current `(controlled, control_bool)` state onto a stack before setting the new state.
2. On `__exit__`, pop the previous state from the stack and restore it (not unconditionally reset to `(False, None)`).
3. The Toffoli AND ancilla from the inner `__enter__` must be uncomputed during `__exit__` before restoring the outer control.

**Detection:** The existing 6 xfail tests in `test_nested_with_blocks.py` will catch this. Additionally, add a test where operations appear AFTER an inner `with` block closes but still inside the outer block -- this is the case that silently fails.

### Pitfall 2: Toffoli AND Ancilla Leak on Nested Entry

**What goes wrong:** The proposed mechanism for nested `with` is: on entering an inner `with`, compute `old_control AND new_condition -> ancilla` via Toffoli gate, and use the ancilla as the new control qubit. If the ancilla is not properly uncomputed during `__exit__`, it leaks. Over many nested controls (e.g., a chess engine with dozens of conditional blocks), ancilla qubits accumulate and the circuit exceeds memory limits.

**Why it happens:** Ancilla lifecycle for the AND result is tricky. The ancilla must:
1. Be allocated at `__enter__` time
2. Remain live during the entire inner `with` body (it IS the control qubit)
3. Be uncomputed (reverse Toffoli) at `__exit__` time, AFTER all scope-local uncomputation but BEFORE restoring the outer control

If uncomputation happens in the wrong order (before inner-scope qbools are uncomputed), those uncomputation gates lose their control context. If it happens too late (after outer control is restored), the reverse Toffoli targets wrong qubits.

**Consequences:** Persistent ancilla qubits, potential circuit corruption, OOM for circuits with many nested conditionals. Research on Unqomp (ETH Zurich, PLDI 2021) confirms that automated uncomputation of ancillae in nested control structures is one of the hardest problems in quantum circuit compilation -- the uncomputation position must be after all uses but before conflicting operations on involved qubits.

**Prevention:**
1. Store the AND ancilla qbool on the scope/control stack entry, not in a global variable.
2. In `__exit__`, sequence the operations as: (a) uncompute scope-local qbools, (b) uncompute the AND ancilla via reverse Toffoli, (c) deallocate the ancilla, (d) restore outer control state.
3. Write an explicit test verifying zero ancilla leak after 3+ levels of nesting.

**Detection:** Circuit stats comparison: `num_qubits` before and after a nested `with` block should be identical (net zero ancilla). Add `assert ql.circuit_stats()['num_qubits'] == expected` after complex nested blocks.

### Pitfall 3: `_control_bool &= self` Creates a Multi-bit AND Instead of Single-bit Toffoli

**What goes wrong:** Line 816 of `qint.pyx` executes `_control_bool &= self` inside `__enter__`. The `__iand__` operator calls `self & other` which dispatches to the full multi-bit `Q_and` C function. For 1-bit qbool values, this works functionally but allocates a full result qint with padding ancillae, qubit array setup for 3 registers, etc. For multi-bit qints used as conditions (which are possible -- any qint can be used in `with`), this creates a multi-bit AND which is semantically wrong for control composition (you want "both conditions are True", not "bitwise AND of their representations").

**Why it happens:** The `&=` operator is overloaded for bitwise AND, which coincidentally works for single-bit qbool values but is semantically incorrect for the general case and unnecessarily heavyweight.

**Consequences:** Using a multi-bit qint as a `with` condition with nesting produces wrong circuits. Even for qbool, the overhead is higher than a direct Toffoli gate. The result qint from `&=` is not tracked for uncomputation, so it leaks.

**Prevention:** The nested `__enter__` should NOT use `&=`. Instead:
1. Allocate a fresh ancilla qbool.
2. Emit a single Toffoli (CCX) gate with `old_control_qubit[63]` and `new_condition_qubit[63]` as controls and the ancilla as target.
3. Set the ancilla as the new `_control_bool`.
4. This is simpler, faster, and correct for arbitrary nesting depth.

**Detection:** Verify that the AND ancilla is always exactly 1 qubit, not `max(self.bits, other.bits)` qubits.

### Pitfall 4: Chess Engine OOM from Uncompiled Nested Loop Expansion

**What goes wrong:** The example `chess_engine.py` has triple-nested loops (`for index ... for a,b ... for wkn1,wkn2`), each containing `with` blocks. Without `ql.compile(opt=1)`, the framework expands every loop iteration into raw gates at circuit construction time. For an 8x8 board with up to 64 positions x 8 moves x 64 squares = ~32K conditional blocks, each generating comparison + conditional addition gates, the C backend's gate array grows to tens of GB.

**Why it happens:** The framework has no lazy evaluation -- every Python-level operation immediately emits gates to the C circuit. The OOM debug notes confirm: without `gc.collect()` between operations, stale qint objects accumulate, their `__del__` methods inject reverse gates into the current circuit, and memory use compounds.

**Consequences:** Process killed by OOM at ~80% through compilation. Even if compilation completes, the resulting circuit is too large to simulate or export.

**Prevention:**
1. Use `@ql.compile(opt=1)` to capture-and-replay sub-circuits instead of re-emitting gates.
2. Factor the chess engine into small compiled predicates (as chess_predicates.py already does for v8.0).
3. Add explicit `gc.collect()` between major loop sections to prevent stale qint accumulation.
4. Monitor `ql.circuit_stats()['gate_count']` during development to catch exponential blowup early.
5. The chess engine rewrite should follow the existing pattern of compiled predicate factories (make_piece_exists_predicate, etc.) rather than inline quantum logic.

**Detection:** Set a gate count budget (e.g., 100K gates) and fail fast if exceeded during circuit construction. Monitor RSS memory during test runs.

## Moderate Pitfalls

### Pitfall 5: 2D qarray `ql.array((rows, cols))` vs `ql.array(dim=(rows, cols))` API Confusion

**What goes wrong:** `ql.array((8, 8))` passes the tuple `(8, 8)` as the `data` parameter (positional arg), NOT as `dim`. The code path then calls `_detect_shape((8, 8))` which checks `isinstance(data, list)` -- a tuple is not a list, so it returns `()` (scalar shape). Then `_flatten((8, 8))` produces `[8, 8]`, and `_infer_width([8, 8])` computes `max(abs(v) for v in [8, 8])` = 8, so `width=8`. But the resulting array has shape `()` and 2 elements, which is inconsistent and produces confusing errors downstream.

The correct call is `ql.array(dim=(8, 8), dtype=ql.qbool)` which uses the `dim=` keyword path.

**Why it happens:** The `data` parameter accepts any iterable (list, tuple, numpy array). A tuple of ints looks like a flat data array, not a dimension specification. The `_detect_shape` function only recognizes `list` types, not tuples.

**Prevention:**
1. Fix `_detect_shape` to handle tuples as well as lists (or convert tuple to list early).
2. Add a guard: if `data` is a tuple of exactly 2 ints and no `width`/`dtype` is given, emit a warning suggesting `dim=` instead.
3. Document clearly in the API that `ql.array(dim=(rows, cols))` is the intended 2D constructor.
4. The chess engine example uses `ql.qarray(dim=(8,8), dtype=ql.qbool)` which is correct -- make sure the rewrite preserves this pattern.

**Detection:** Add a test: `arr = ql.array(dim=(3, 4), dtype=ql.qbool); assert arr.shape == (3, 4); assert len(arr) == 3`.

### Pitfall 6: Scope-local Uncomputation Inside Nested Controls Uses Wrong Control Qubit

**What goes wrong:** When `__exit__` uncomputes scope-local qbools (lines 861-872 of qint.pyx), it runs while the control state is still the inner (nested AND) control. But the qbools being uncomputed may have been created under the outer control or under no control at all. Uncomputing them under the wrong control qubit produces gates that are controlled by the AND ancilla instead of the correct original control, corrupting the uncomputation.

**Why it happens:** The uncomputation code assumes the current control context matches the creation context of each qbool. With nested controls, this assumption breaks -- a qbool created in the outer scope but registered in the inner scope frame would be uncomputed with the inner AND control.

**Consequences:** Silent circuit corruption. The reverse gates for a qbool comparison are emitted under a different control than the forward gates, so they do not cancel, leaving entangled garbage qubits.

**Prevention:**
1. Each qbool must record its `control_context` at creation time (the framework already captures this in `self.control_context` on line 318-322).
2. During scope-exit uncomputation, temporarily restore the qbool's original control context before emitting reverse gates, then restore the current nested context.
3. Alternatively, ensure scope frames only contain qbools created at exactly that scope depth -- never inherit from outer scopes.

**Detection:** Statevector simulation test: create a qbool comparison inside an inner `with` block, exit the inner block, verify the qbool was correctly uncomputed by checking the statevector for zero entanglement on the ancilla qubit.

### Pitfall 7: `@ql.compile` Gate Capture Misses Nested Control Context

**What goes wrong:** `@ql.compile` captures gates between `start_layer` and `end_layer` and replays them with qubit remapping. If a compiled function is called inside a nested `with` block, the Toffoli AND ancilla qubit for the nested control is part of the control context but is NOT a function argument. On replay, the qubit remapping maps the function's input qubits but leaves the control qubit as a literal physical qubit index. If the replay happens in a different control context (different ancilla qubit), the replayed gates control the wrong qubit.

**Why it happens:** The compile decorator handles single-level control via `_get_controlled()` and derives a controlled variant. But nested controls introduce additional control qubits that are not tracked by the single `_control_bool` mechanism.

**Consequences:** Compiled functions that worked in single-control contexts produce wrong circuits when called inside nested `with` blocks. This is especially dangerous for the chess engine where compiled predicates (make_piece_exists_predicate, etc.) will be called inside nested `with` blocks.

**Prevention:**
1. Extend the compile decorator's control-variant derivation to handle multi-qubit control.
2. When `_list_of_controls` has entries (nested case), all control qubits must be included in the controlled variant derivation.
3. Test: call a `@ql.compile` function inside a 2-level nested `with` block and verify via simulation that the result is controlled by BOTH conditions.

**Detection:** Test with a compiled `add_one` function called inside nested `with` blocks. Verify the result only increments when BOTH outer and inner conditions are True.

### Pitfall 8: Chess Engine Rewrite Assumes Nested `with` Works Before Implementation

**What goes wrong:** The example `chess_engine.py` uses nested `with` blocks (`with black_king[*index] == 1:` containing `with white_knight[a, b]:`). If the chess engine rewrite is attempted before nested controls are fully implemented and tested, it will hit `NotImplementedError` (current behavior) or worse, produce silently wrong circuits if the implementation is partial.

**Why it happens:** The natural way to express chess logic (if piece is here AND piece can reach there AND no check) requires nested conditionals. The v8.0 chess predicates work around this by using flat `with` blocks plus `&` operator for Toffoli AND, but the desired v9.0 style uses nested `with` blocks for readability.

**Consequences:** Wasted effort writing and debugging a chess engine against a broken foundation. Risk of declaring the chess engine "done" when it compiles without errors but produces incorrect circuits.

**Prevention:**
1. Phase ordering: implement and thoroughly test nested `with` blocks FIRST.
2. Write the chess engine rewrite only after all 6 xfail tests pass.
3. Add chess-specific integration tests that verify legality evaluation via simulation before removing the v8.0 predicate-based workaround.

**Detection:** Gate-level regression: the rewritten chess engine should produce circuits with gate count within 2x of the v8.0 predicate-based version for the same KNK position.

## Minor Pitfalls

### Pitfall 9: Toffoli AND Depth Explosion at High Nesting

**What goes wrong:** Each nested `with` level adds a Toffoli (CCX) gate on entry and exit. At depth k, there are k Toffoli gates in the critical path. If the nested controls are deep (e.g., 5+ levels), the Toffoli overhead dominates the circuit depth. With Clifford+T decomposition enabled, each CCX = 15 gates, so 5 levels = 150 extra gates in the critical path.

**Prevention:** For the chess engine, nesting should be limited to 2-3 levels (piece position, move legality, check detection). If deeper nesting is needed, refactor into compiled predicates that flatten the nesting. The `_plan_cascade_ops` pattern from `walk.py` (V-gate CCRy decomposition) is an existing workaround for deep nesting.

### Pitfall 10: `_list_of_controls` Is a Mutable Global List, Not a Stack

**What goes wrong:** `_list_of_controls` is a single global list that `__enter__` appends to. There is no per-scope isolation. If an exception occurs inside a nested `with` block and `__exit__` fails to clean up properly, the list grows stale entries that corrupt subsequent `with` blocks, even in unrelated code.

**Prevention:** Replace the single global list with a proper stack of control frames (e.g., a list of `(controlled, control_bool, and_ancilla)` tuples). Each `__enter__` pushes, each `__exit__` pops. The stack is never shared across independent control scopes.

### Pitfall 11: 2D qarray `__setitem__` for Multi-dimensional In-place Operations

**What goes wrong:** `qarray.__setitem__` (line 249-260) raises `NotImplementedError("Row assignment for multi-dimensional arrays not yet supported")` for integer keys on 2D arrays. The chess engine uses `white_knight[1, 1] += 1` which goes through the tuple indexing path and works, but `white_knight[1] = some_row` does not. If the chess engine rewrite uses row-level assignment patterns, it will fail.

**Prevention:** Document that 2D qarrays support only element-wise access via tuple indices `arr[r, c]`, not row-level operations. The chess engine should use `board[rank, file] += 1` consistently.

### Pitfall 12: `ql.compile(opt=1)` Cache Key Does Not Include Nesting Depth

**What goes wrong:** The compile cache key includes `(widths, control_count, qubit_saving) + mode_flags`. When a compiled function is called at different nesting depths (e.g., once inside a single `with` block, once inside a double-nested `with` block), the `control_count` may be the same (1 in both cases -- the current `_control_bool`) even though the circuit structure differs. This could cause incorrect replay.

**Prevention:** Include the full control stack depth (not just presence/absence of control) in the cache key. Alternatively, make the controlled variant derivation aware of multi-qubit controls so the same cached sequence can be adapted to any control depth.

### Pitfall 13: GC-Triggered Uncomputation Races with Nested Control Context

**What goes wrong:** When Python garbage collects a qint/qbool created inside a nested `with` block, the `__del__` method calls `_do_uncompute()` which emits reverse gates into the current circuit. If GC fires after the inner `with` `__exit__` has already restored the outer control context (or worse, after all `with` blocks have exited), the reverse gates are emitted under the wrong control -- potentially uncontrolled.

**Why it happens:** This is the same bug documented in the OOM debug notes for test_compile.py but amplified by nested controls. The `creation_scope` check in `__del__` (line 766: `if current < self.creation_scope`) only checks scope depth, not control context.

**Prevention:**
1. Use eager uncomputation (`qubit_saving=True`) inside compiled functions so qbools are uncomputed immediately at scope exit, not deferred to GC.
2. In the chess engine, wrap critical sections in compiled functions which handle their own ancilla lifecycle.
3. Add `gc.collect()` at test boundaries.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Nested `with` block implementation | Pitfall 1 (exit resets to False/None), Pitfall 2 (ancilla leak), Pitfall 3 (multi-bit AND) | Implement as stack-based push/pop. Use single Toffoli for AND, not `&=`. Sequence uncomputation correctly in exit. |
| Nested `with` + `@ql.compile` integration | Pitfall 7 (capture misses nested control context) | Extend controlled variant to handle multi-qubit control. Test compiled functions inside nested blocks. |
| 2D qarray fix | Pitfall 5 (API confusion tuple vs dim=) | Fix `_detect_shape` for tuples. Clear error message for ambiguous calls. |
| Chess engine rewrite | Pitfall 4 (OOM), Pitfall 8 (depends on nested with) | Phase AFTER nested controls proven correct. Use compiled predicates. Monitor gate count. |
| Chess engine + nested controls | Pitfall 6 (wrong control for uncomputation), Pitfall 13 (GC races) | Record control context at creation. Use eager uncomputation. |
| Deep nesting (3+ levels) | Pitfall 9 (depth explosion), Pitfall 10 (global list corruption) | Limit to 2-3 levels. Use proper control stack. |
| Compile cache with nesting | Pitfall 12 (cache key ignores nesting depth) | Include control stack depth in cache key. |

## Sources

- Codebase analysis: `qint.pyx` `__enter__`/`__exit__` (lines 784-882), `__and__` (lines 1670-1809), `_list_of_controls` usage
- Codebase analysis: `qarray.pyx` constructor (lines 38-168), `_qarray_utils.py` `_infer_width`/`_detect_shape`
- Codebase analysis: `compile.py` `CompiledFunc.__call__` and cache key construction
- Codebase analysis: `test_nested_with_blocks.py` -- 6 xfail tests documenting expected nested behavior
- Codebase analysis: `chess_engine.py` example, `chess_predicates.py` workaround patterns
- Debug notes: `.planning/debug/test-compile-oom.md` -- OOM root cause from missing gc.collect() and stale qint destructors
- [Unqomp: Synthesizing Uncomputation in Quantum Circuits (PLDI 2021)](https://dl.acm.org/doi/pdf/10.1145/3453483.3454040) -- uncomputation ordering constraints
- [Reqomp: Space-constrained Uncomputation for Quantum Circuits (ETH Zurich)](https://www.research-collection.ethz.ch/server/api/core/bitstreams/0d94612c-1514-496c-8a28-7ad6bedf87ea/content) -- ancilla reuse under control
- [Rise of Conditionally Clean Ancillae (Quantum, 2025)](https://quantum-journal.org/papers/q-2025-05-21-1752/pdf/) -- Toffoli depth vs ancilla count tradeoffs
- [Scalable Memory Recycling for Large Quantum Programs (arXiv:2503.00822)](https://arxiv.org/abs/2503.00822) -- qubit reuse strategies
- [Efficient Implementation of Multi-Controlled Quantum Gates (arXiv:2404.02279)](https://arxiv.org/pdf/2404.02279) -- MCX decomposition pitfalls
- [Optimizing Ancilla-Based Quantum Circuits with SPARE (POPL 2025)](https://dl.acm.org/doi/10.1145/3729253) -- ancilla lifecycle management
