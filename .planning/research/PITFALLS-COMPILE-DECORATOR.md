# Pitfalls Research: Function Compilation Decorator (`@ql.compile`)

**Domain:** Quantum circuit function compilation/tracing for existing quantum assembly framework
**Researched:** 2026-02-04
**Confidence:** HIGH (based on direct codebase analysis + ecosystem research)

## Executive Summary

Adding `@ql.compile` to this framework is significantly complicated by the system's reliance on global mutable state (the single `_circuit` pointer, `_controlled` flag, `_control_bool`, scope stack, qubit allocator, creation counters). Every operation in the existing codebase mutates global state through accessor functions in `_core.pyx`. A compilation decorator must either (a) intercept and redirect all these mutations during tracing, or (b) replay them faithfully during instantiation. Both approaches have distinct failure modes. The twelve pitfalls below are ordered roughly by severity -- the first four can cause silent correctness bugs, while later ones cause usability or performance issues.

---

## Critical Pitfalls

Issues that produce silently incorrect circuits or block the feature entirely.

### Pitfall 1: Qubit Index Collision During Replay

**What goes wrong:** During tracing (first call to a `@ql.compile`-decorated function), qubits are allocated through the global `circuit_get_allocator()`. The traced gate sequence records concrete qubit indices (e.g., qubits 0-7 for an 8-bit qint). On subsequent calls, those same concrete indices are replayed, but the allocator has moved on -- the caller's qubits now occupy indices 0-7, and the compiled function's gates stomp on them.

**Why it happens:** The C-level `run_instruction()` takes a `qubit_array[]` that maps logical qubit positions to physical qubit indices. During tracing, logical and physical are the same. During replay, they must differ. The existing system has no abstraction layer between "the qubit indices the operation was traced with" and "the qubit indices at call time."

Evidence from `qint_arithmetic.pxi` lines 18-37: operations pack qubit indices into `qubit_array` and pass directly to `run_instruction()`. The C function `run_instruction(seq, &arr[0], invert, _circuit)` uses these indices verbatim.

**Consequences:** Gates applied to wrong qubits. Circuit computes garbage. No error raised because the C layer does not validate qubit ownership.

**Prevention:**
1. During tracing, allocate "virtual" qubit indices from a separate namespace (e.g., starting at offset 100000) that cannot collide with real allocations.
2. Store the trace as a sequence of `(operation_type, virtual_qubit_indices, parameters)` tuples.
3. On replay, build a mapping from virtual indices to real indices (allocated at call time) and remap every gate before feeding to `run_instruction()`.
4. Validate that the mapping is complete -- every virtual qubit used in the trace has a corresponding real qubit.

**Warning signs:** Tests pass when the compiled function is the only thing in the circuit, but fail when called after other allocations.

**Detection:** Compare qubit indices in the compiled region against the caller's allocated ranges. Any overlap is a bug.

**Phase:** Must be solved in the core design phase (Phase 1). This is the fundamental mechanism.

---

### Pitfall 2: Width-Dependent Circuit Structure Breaks Parametric Compilation

**What goes wrong:** The user expects `@ql.compile` to compile a function once and reuse it for different inputs. But `qint` operations generate fundamentally different circuits based on `width`. For example, `CQ_add(bits=4, value=5)` produces a completely different gate sequence than `CQ_add(bits=8, value=5)`. The number of qubits, number of layers, and gate connectivity all change. A trace captured at width=4 cannot be replayed at width=8.

**Why it happens:** The C backend functions (`CQ_add`, `QQ_add`, `CQ_equal_width`, etc.) are all parameterized by `int bits` as seen in `_core.pxd` lines 14-46. The `sequence_t*` they return has different `num_layer` and gate counts for different widths. This is not a parameter that can be "filled in later" -- it changes the circuit topology.

**Consequences:** If width mismatch is not detected: wrong computation (gates applied to nonexistent qubits or missing qubits). If detected but not handled: the function must be retraced for every distinct width combination, undermining the point of compilation.

**Prevention:**
1. Make the cache key include the widths of all quantum arguments: `cache_key = (func_id, arg1.width, arg2.width, ...)`.
2. Classical `int` arguments that affect circuit structure (e.g., the value in `CQ_add`) must also be part of the cache key.
3. Document clearly: "parametric" means parametric over quantum state, not over circuit structure. Width changes require retrace.
4. Consider a `@ql.compile(parametric=['value'])` syntax where the user declares which classical arguments can vary without retrace (only those that appear as gate rotation angles, not as structural parameters).

**Warning signs:** User calls `@ql.compile`-decorated function with `qint(width=4)` then `qint(width=8)` and gets wrong results or segfault.

**Detection:** Assert that replay qubit count matches trace qubit count. Any mismatch means the cache key was insufficient.

**Phase:** Must be designed in Phase 1 (cache key design). Implementation can be phased.

---

### Pitfall 3: Uncomputation Interaction -- Double Reversal or Orphaned Intermediates

**What goes wrong:** The existing system tracks `_start_layer` and `_end_layer` on every `qint` result (see `qint.pyx` lines 243-245), and `_do_uncompute()` calls `reverse_circuit_range(_circuit, self._start_layer, self._end_layer)` to undo operations (line 387). Inside a compiled function, intermediates are created, tracked, and potentially auto-uncomputed. But:

- **Scenario A (double uncompute):** The compiled function creates an intermediate `qint`, which gets uncomputed inside the function (via `__del__` or scope exit in `__exit__` at line 651-673). The compiled trace includes both the forward and reverse gates. On replay, the function is correct internally. But if the caller ALSO tries to uncompute the function's output, the caller calls `reverse_circuit_range` on a range that includes the internal uncomputation -- reversing gates that were already balanced, creating a net-negative operation.

- **Scenario B (orphaned intermediates):** The compiled function creates intermediates that are NOT uncomputed during tracing (lazy mode, or they escape via return). On replay, these intermediates' qubits are never freed because the replay does not create Python `qint` objects with `__del__` hooks -- it just emits gates.

**Why it happens:** The current uncomputation system is deeply tied to Python object lifetime (`__del__` at line 524-568) and layer-index tracking. A compiled/replayed function bypasses both mechanisms. The layer indices recorded during tracing are meaningless in the replay context.

**Consequences:** Scenario A: Incorrect circuit (extra inverse gates). Scenario B: Qubit leak (allocated but never freed).

**Prevention:**
1. **Separate internal from external uncomputation.** The compiled trace should handle all internal intermediates (their creation and cleanup are part of the trace). The trace's "external interface" is: input qubits, output qubits, ancilla qubits (borrowed and returned clean).
2. **Ancilla protocol:** During tracing, track which qubits are allocated and freed internally. These become the function's "ancilla requirements." On replay, allocate fresh ancillas, use them, and verify they are returned to |0> state.
3. **Layer tracking for the compiled block as a whole:** On replay, record `_start_layer` and `_end_layer` for the entire compiled block (not individual operations within it). The output `qint`'s uncomputation range covers the whole compiled block.
4. **Prohibit partial uncomputation of compiled internals** from outside the compiled function.

**Warning signs:** Gate count increases unexpectedly when using `@ql.compile` vs. inline code. Qubit count grows with repeated calls to compiled function.

**Detection:** Compare circuit stats (gate count, qubit count) between inline and compiled versions of the same function.

**Phase:** Phase 2 (after basic tracing works). This is the hardest integration challenge.

---

### Pitfall 4: Control Context Leakage Between Trace and Replay

**What goes wrong:** The `with qbool:` context manager sets `_controlled = True` and `_control_bool = <the qbool>` as global state (see `__enter__` at `qint.pyx` lines 575-625). Every operation inside the `with` block reads these globals and generates controlled variants of gates (e.g., `cCQ_add` instead of `CQ_add`). If `@ql.compile` is used:

- **Tracing outside `with`:** The trace captures uncontrolled gates. Replaying inside a `with` block produces uncontrolled gates -- the control qubit is ignored.
- **Tracing inside `with`:** The trace captures controlled gates with a specific control qubit index. Replaying outside `with` or with a different control qubit produces gates controlled on the wrong qubit or a nonexistent qubit.

**Why it happens:** The controlled/uncontrolled decision is baked into which C function is called (`CQ_add` vs `cCQ_add` at `qint_arithmetic.pxi` lines 26-33). These produce different `sequence_t*` structures. The control qubit index is embedded in the `qubit_array` passed to `run_instruction()`.

**Consequences:** Gates not controlled when they should be, or controlled by wrong qubit. Silent correctness bug in conditional quantum logic.

**Prevention:**
1. **Trace uncontrolled, apply control at replay.** Always trace the uncontrolled version of operations. At replay time, if inside a `with` block, add control qubits to every gate in the replayed sequence. This requires a `add_control_to_sequence(sequence, control_qubit)` operation that the C backend may not currently support.
2. **Alternative: include control context in cache key.** The trace is invalidated if control context changes. Simpler but means separate traces for controlled vs uncontrolled, defeating reuse.
3. **Best approach for this codebase:** Since the C backend already has separate `CQ_add` and `cCQ_add` functions, the trace should record the operation at an abstract level (e.g., "add, classical, value=5") and defer the controlled/uncontrolled decision to replay time. This requires operation-level tracing (see Pitfall 8).

**Warning signs:** Compiled function works standalone but produces wrong results inside `with` block.

**Detection:** Test every compiled function both inside and outside `with` blocks. Compare gate counts (controlled version should have more gates).

**Phase:** Phase 2 or 3. Can be deferred by initially prohibiting `@ql.compile` inside `with` blocks (with a clear error message).

---

## Integration Pitfalls

Issues specific to integrating with the existing `_core.pyx` global state architecture.

### Pitfall 5: Global State Pollution During Tracing

**What goes wrong:** Tracing a `@ql.compile` function executes the function body for real, which mutates all global state: `_num_qubits` is incremented (line 199), `_int_counter` advances (line 176), `_smallest_allocated_qubit` moves (line 271), the qubit allocator state changes, `_scope_stack` is modified (line 240), and `_global_creation_counter` increases (line 226). After tracing, these globals reflect the traced function's side effects. If the trace is then replayed (without retracing), the globals are inconsistent -- they reflect both the trace and the replay.

**Why it happens:** There are 12+ global state variables accessed through accessor functions in `_core.pyx` (lines 51-160). The existing operations were designed to always execute eagerly, not to be captured and replayed.

**Consequences:** Qubit counter drift (allocator thinks more qubits exist than actually do). Scope depth mismatch. Creation counter gaps causing assertion failures in `add_dependency()`.

**Prevention:**
1. **Snapshot-and-restore pattern:** Before tracing, snapshot all global state. After tracing completes, restore the snapshot. The trace is a recording; global state should look as if the function was never called.
2. **Or: isolated tracing context.** Create a temporary circuit and allocator for tracing. The trace records operations against this temporary circuit. On replay, operations are emitted against the real circuit. This is cleaner but requires refactoring operations to accept a circuit parameter rather than reading from `_circuit` global.
3. **Minimum viable:** At least restore `_num_qubits`, `_int_counter`, `_smallest_allocated_qubit`, `_global_creation_counter`, and `ancilla` after tracing.

**Warning signs:** `circuit_stats()['current_in_use']` shows more qubits than expected after using compiled functions. `_int_counter` jumps by unexpected amounts.

**Detection:** Assert global state invariants before and after compiled function calls.

**Phase:** Phase 1. Must be solved before any tracing works correctly.

---

### Pitfall 6: Optimizer Interaction -- Layer Indices Become Meaningless After Optimization

**What goes wrong:** The circuit optimizer (`circuit_optimize()` in `_core.pxd` line 148) creates a new optimized circuit that may have completely different layer indices. The existing system already has a known problem: "layer-based uncomputation tracking is unreliable when optimizer parallelizes gates." `@ql.compile` makes this worse because:

1. The compiled function's internal `_start_layer`/`_end_layer` are recorded during tracing.
2. On replay, the replayed gates are placed at new layer indices determined by the optimizer's parallelization.
3. Uncomputation of the compiled function's output uses layer indices that may no longer bracket the correct gates.

**Why it happens:** The `layer_floor` mechanism (seen in `__add__` at `qint_arithmetic.pxi` lines 97-100) attempts to prevent the optimizer from moving gates before a certain point. But this is a per-operation mechanism, not a per-compiled-function mechanism.

**Consequences:** Uncomputation reverses wrong gates. Circuit corruption.

**Prevention:**
1. **Do not optimize mid-compilation.** The compiled function should emit gates without optimization. Optimization happens once, after the full circuit is built.
2. **Gate-level tracking instead of layer-level.** Tag each gate with a "compiled function ID" and "operation ID" within that function. Uncomputation targets gates by tag, not by layer range. This is a deeper architectural change.
3. **Pragmatic workaround:** Set `layer_floor` at the start of the compiled function replay, preventing the optimizer from moving any of its gates before the start point. This is already the pattern used in `__add__`.

**Warning signs:** Compiled function works without optimization but produces wrong results after `c.optimize()`.

**Detection:** Test compiled functions with and without optimization. Compare output states.

**Phase:** Phase 3. Can be deferred by documenting that optimization after compiled function calls requires care.

---

### Pitfall 7: Nested Compilation -- Compiled Function Calls Compiled Function

**What goes wrong:** If `@ql.compile` function `foo()` calls `@ql.compile` function `bar()`, the tracing of `foo()` triggers the tracing (or replay) of `bar()`. This creates several problems:

1. **Double isolation:** If tracing uses snapshot-restore (Pitfall 5), the inner trace's restore clobbers the outer trace's snapshot.
2. **Qubit namespace collision:** If both traces use virtual qubit indices, the inner function's virtuals may collide with the outer function's virtuals.
3. **Cache key confusion:** The inner function may be traced with virtual qubits from the outer trace, producing a trace that only works when replayed from within the outer trace.

**Why it happens:** The tracing mechanism must be reentrant, but most implementations assume a single tracing context.

**Consequences:** Incorrect nested function behavior. Potential infinite retracing if cache keys are wrong.

**Prevention:**
1. **Stack-based tracing context.** Maintain a stack of tracing contexts. Each nested `@ql.compile` call pushes a new context. Restoring pops and restores the previous level.
2. **Flatten on replay.** When replaying `foo()`, if `foo` contains a call to `bar()`, inline `bar()`'s trace into `foo()`'s replay. This means `foo()`'s trace stores a reference to `bar()`'s trace, not the expanded gates.
3. **Simplest approach for v1:** Prohibit nesting. If `@ql.compile` detects that it is already inside a tracing context, either (a) fall through to direct execution (no compilation), or (b) raise an error. Document the limitation.

**Warning signs:** Nested compiled function calls produce different results than flat calls.

**Detection:** Test `@ql.compile` functions that call other `@ql.compile` functions.

**Phase:** Phase 3 or later. v1 can prohibit nesting with a clear error.

---

## Design Pitfalls

Architectural choices that seem right but cause problems.

### Pitfall 8: Gate-Level vs. Operation-Level Tracing Granularity

**What goes wrong:** The natural approach is to trace at the gate level -- record every `run_instruction()` call with its `sequence_t*` and `qubit_array`. This is simple to implement because `run_instruction` is the single bottleneck. But it creates problems:

1. **No semantic information.** The trace is a flat list of gates. You cannot add control qubits later (Pitfall 4) because controlled versions require different C function calls, not just extra control wires on existing gates.
2. **No parametric reuse.** If the classical value in `CQ_add(bits=8, value=5)` changes to `value=7`, the entire sequence changes -- you cannot just patch a parameter in the gate list.
3. **Bloated traces.** A single `QQ_add(8)` expands to dozens of gates. Storing and replaying at gate level is wasteful compared to storing "QQ_add, width=8, qubit_mapping" and calling the C function on replay.

**Why it happens:** Gate-level tracing is the simplest interception point (wrap `run_instruction`). Operation-level tracing requires intercepting at the Python level (wrap `__add__`, `__eq__`, etc.), which means understanding every operation's semantics.

**Consequences:** Loss of optimization opportunities. Inability to support controlled replay. Larger memory footprint for cached traces.

**Prevention:**
1. **Trace at operation level.** Record: operation type (ADD, MUL, EQ, XOR, AND, OR, NOT), operand types (quantum/classical), classical values, operand widths, qubit mappings. On replay, call the appropriate C function with remapped qubits.
2. **This matches the existing architecture.** The Cython operations (`addition_inplace`, `__eq__`, etc.) already select the right C function based on operand types and control context. The trace should record these decisions, not their gate-level output.
3. **Allow gate-level fallback.** For operations not yet supported by operation-level tracing, fall back to gate-level recording with a warning.

**Warning signs:** Compiled function cannot be used inside `with` block. Classical parameter changes require full retrace.

**Phase:** Phase 1 design decision. Must be decided before implementation begins.

---

### Pitfall 9: Return Value Lifetime and Ownership Transfer

**What goes wrong:** A compiled function returns a `qint` whose qubits are part of the compiled trace. On replay, fresh qubits are allocated for the output. But the returned `qint` Python object must:

1. Own the allocated qubits (so `__del__` can free them via `allocator_free` at line 404).
2. Have correct `_start_layer`/`_end_layer` (for uncomputation of the whole compiled block).
3. Have correct `dependency_parents` (pointing to the function's input `qint` objects, not the trace's internal objects).
4. Be registered in the current scope stack (if inside a `with` block, per `_scope_stack` logic at line 239-240).

If any of these are wrong, the returned value will either (a) never be uncomputed (qubit leak), (b) be uncomputed incorrectly (wrong layer range), or (c) uncompute its dependencies prematurely.

**Why it happens:** The trace captures `qint` object creation during tracing. On replay, the function body does not execute, so no `qint` objects are created for intermediates -- only the final output needs a real `qint` wrapper.

**Consequences:** Qubit leaks, incorrect uncomputation, dangling references.

**Prevention:**
1. **Explicit output protocol.** The compiled function replay creates a new `qint` with `create_new=False` and `bit_list` pointing to the freshly allocated output qubits. Then set:
   - `allocated_qubits = True`
   - `allocated_start = <actual allocation start>`
   - `_start_layer = <layer before replay>`
   - `_end_layer = <layer after replay>`
   - `dependency_parents = [<input qints>]`
   - `operation_type = 'COMPILED'`
   - `creation_scope = current_scope_depth.get()`
2. **Register in scope stack** if `current_scope_depth > 0`.
3. **Test:** Verify that returned values are properly uncomputed when they go out of scope.

**Warning signs:** Qubit count grows monotonically even when compiled function results go out of scope.

**Detection:** Check `circuit_stats()['current_in_use']` after compiled function results are deleted.

**Phase:** Phase 1 (basic) and Phase 2 (uncomputation integration).

---

### Pitfall 10: Cache Invalidation -- When "Compile Once" Is Wrong

**What goes wrong:** The cache maps `(function_id, width_signature, classical_args)` to a trace. But the trace can become invalid when:

1. **Circuit is reset.** `circuit()` reinitializes everything (`_core.pyx` lines 261-280). Cached traces reference the old circuit's qubit namespace.
2. **Qubit saving mode changes.** `ql.option('qubit_saving', True/False)` changes uncomputation behavior (line 191-198). A trace captured in lazy mode behaves differently if replayed in eager mode (intermediates may or may not be uncomputed within the trace).
3. **Control context changes.** (Already covered in Pitfall 4, but also a cache invalidation concern.)
4. **User modifies the decorated function.** During development, the function body changes but the cache still has the old trace. This is a standard stale-cache problem but particularly dangerous because the error is silent (wrong quantum circuit, not a crash).

**Why it happens:** Standard caching problems, amplified by the quantum domain where bugs are silent (no classical assertions on quantum state).

**Consequences:** Stale cache produces wrong circuits silently.

**Prevention:**
1. **Invalidate on `circuit()` reset.** The `circuit.__init__()` method should clear all compile caches (add a hook or use a generation counter).
2. **Include mode flags in cache key.** `cache_key = (func, widths, classical_args, qubit_saving_mode)`.
3. **Source hash for development.** Hash the function's bytecode (`func.__code__.co_code`) as part of the cache key. If the function body changes, the cache misses. This adds overhead but catches stale caches during development.
4. **Provide `@ql.compile(cache=False)` escape hatch** for debugging.

**Warning signs:** Tests pass individually but fail when run in sequence (shared cache across test cases).

**Detection:** Run compiled function tests with and without cache. Results must be identical.

**Phase:** Phase 2 (caching). v1 can use a simpler invalidation strategy.

---

## Minor Pitfalls

Issues that cause friction but are fixable.

### Pitfall 11: Debugging Opacity -- Compiled Functions Hide Operation Sequence

**What goes wrong:** When debugging a quantum circuit, users inspect the circuit visualization or gate counts to understand what operations were applied. A compiled function appears as an opaque block of gates with no semantic labels. The user cannot tell which internal operation produced which gates.

**Why it happens:** The compilation flattens the operation sequence into raw gates. There is no mechanism to annotate regions of the circuit with human-readable labels. Qrisp's documentation explicitly calls this out: "code introspection is much harder in JIT mode since it is difficult to investigate intermediate results for bug-fixing purposes."

**Prevention:**
1. Add a `name` parameter: `@ql.compile(name="my_adder")`.
2. Support a `verbose=True` or `debug=True` mode that falls back to direct execution for debugging.
3. Consider adding circuit region annotations (not just for compiled functions -- useful generally).

**Phase:** Phase 3 (polish).

---

### Pitfall 12: Ancilla Management Across Compiled Boundary

**What goes wrong:** Many operations in the C backend use ancilla qubits (visible in the pattern `qubit_array[start: start + NUMANCILLY] = _get_ancilla()` throughout `qint_arithmetic.pxi` at lines 29, 32, 57, 60). During tracing, ancilla indices are recorded. On replay, different ancilla qubits may be in use. If the compiled trace hardcodes ancilla indices, replay uses occupied ancillas.

**Why it happens:** The ancilla array (`ancilla` in `_core.pyx` lines 203-206) is global state that shifts as qubits are allocated and freed (via `_increment_ancilla`/`_decrement_ancilla` at lines 151-159).

**Prevention:**
1. Treat ancilla qubits the same as operation qubits in the remapping (Pitfall 1).
2. Record ancilla requirements (how many, not which specific indices) in the trace.
3. On replay, allocate fresh ancillas from the allocator and remap.

**Warning signs:** Compiled function works first time but corrupts state on second call. Ancilla qubits are left dirty after compiled function returns.

**Phase:** Phase 1 (part of qubit remapping design).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Core trace mechanism | Pitfall 1 (qubit collision), Pitfall 5 (global state), Pitfall 12 (ancilla) | Virtual qubit namespace + snapshot-restore |
| Cache key design | Pitfall 2 (width-dependent), Pitfall 10 (invalidation) | Include widths + mode flags + source hash in key |
| Uncomputation integration | Pitfall 3 (double reversal), Pitfall 6 (optimizer) | Separate internal/external uncompute; layer_floor |
| Control context support | Pitfall 4 (control leakage) | Operation-level tracing (Pitfall 8) enables deferred control |
| Nesting support | Pitfall 7 (nested compilation) | Stack-based context or prohibit nesting in v1 |
| Return values | Pitfall 9 (lifetime) | Explicit output protocol with ownership transfer |
| Tracing architecture | Pitfall 8 (granularity) | Operation-level tracing from day one |
| Debugging UX | Pitfall 11 (opacity) | Name parameter + verbose fallback mode |

## Recommended Implementation Order

Based on pitfall dependencies:

1. **Phase 1: Core tracing with virtual qubits** -- Solve Pitfalls 1, 5, 8 (design decision), 12
2. **Phase 2: Cache + uncomputation** -- Solve Pitfalls 2, 3, 9, 10
3. **Phase 3: Control context + optimizer** -- Solve Pitfalls 4, 6
4. **Phase 4: Nesting + polish** -- Solve Pitfalls 7, 11

## Sources

- Direct codebase analysis:
  - `_core.pyx` (lines 25-674): global state variables, circuit initialization, scope management
  - `_core.pxd` (lines 1-164): C function declarations showing `int bits` parameters
  - `qint.pyx` (lines 1-700): qint lifecycle, `__del__`, `__enter__`/`__exit__`, uncomputation
  - `qint_arithmetic.pxi` (lines 1-150): addition operations, qubit_array packing, controlled variants
  - `qint_comparison.pxi` (lines 1-150): comparison operations, layer tracking, layer_floor pattern
  - `qbool.pyx` (lines 1-90): qbool as 1-bit qint, copy semantics
  - `.planning/codebase/ARCHITECTURE.md`: system architecture overview
  - `.planning/codebase/CONCERNS.md`: known tech debt and fragile areas
- Ecosystem research:
  - [PennyLane QNode documentation](https://docs.pennylane.ai/en/stable/code/api/pennylane.QNode.html) -- QNode caching and JAX interface behavior
  - [PennyLane JAX JIT tracer bug #6054](https://github.com/PennyLaneAI/pennylane/issues/6054) -- side effect escape during JAX tracing
  - [Qrisp Jasp tutorial](https://qrisp.eu/general/tutorial/Jasp.html) -- function caching (`qache` decorator), compilation speed limitations
  - [Qrisp quantum_inversion source](https://qrisp.eu/_modules/qrisp/environments/quantum_inversion.html) -- ancilla management in inversion environments
  - [Q-CTRL: Compilation roadblock](https://q-ctrl.com/blog/avoiding-an-unexpected-roadblock-in-quantum-computing-compilation) -- compilation pipeline issues
  - [Breaking Down Quantum Compilation (arXiv 2504.15141)](https://arxiv.org/html/2504.15141v1) -- profiling compilation bottlenecks
  - [PennyLane circuit compilation demo](https://pennylane.ai/qml/demos/tutorial_circuit_compilation) -- decorator-based compilation transforms
