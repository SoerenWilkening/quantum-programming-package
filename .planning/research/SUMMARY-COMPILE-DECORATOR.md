# Research Summary: Function Compilation Decorator (v2.0)

**Feature:** `@ql.compile` decorator for quantum function compilation
**Research Date:** 2026-02-04
**Overall Confidence:** HIGH

## Executive Summary

The `@ql.compile` decorator is a record-and-replay compilation system for quantum functions that captures gate sequences during first execution, optimizes them, and replays them with qubit remapping on subsequent calls. The existing architecture already contains all necessary primitives: a global circuit accumulating gates via `add_gate()`, layer-based sequence tracking (`used_layer`), optimization infrastructure (`circuit_optimize()`), and qubit remapping patterns (`run_instruction()`). This is fundamentally tape-style capture (execute normally, observe side effects) rather than abstract tracing (JAX-style), which would require rewriting the entire Cython/C gate generation pipeline.

The recommended approach requires zero new external dependencies. Implementation happens primarily at the Python/Cython boundary, adding 2-3 helper functions to `_core.pyx` that extract gate ranges and replay them with remapped qubit indices. The critical challenge is managing the gap between Python-level objects (qint) and C-level gate sequences across capture/replay boundaries, particularly for controlled contexts (`with` blocks), uncomputation tracking, and qubit allocation.

The key architectural insight: the circuit itself IS the tape. Every operation already records gates into `_circuit.sequence`. Compilation is simply scoping this recording to function boundaries, snapshotting the result, and replaying it efficiently. This approach leverages 221K LOC of existing Cython/C infrastructure rather than fighting it.

## Key Findings

### Recommended Stack

**Zero new external dependencies required.** Everything needed exists in Python 3.11+ stdlib or the current C backend:

| Component | Version | Purpose | Why Sufficient |
|-----------|---------|---------|----------------|
| Python `functools.wraps` | stdlib | Decorator metadata preservation | Standard decorator pattern |
| Python `inspect.signature` | stdlib | Classify quantum vs classical parameters | Read type annotations |
| C `circuit_t.used_layer` | existing | Snapshot circuit depth before/after function call | Identify gate range added by function |
| C `circuit_t.layer_floor` | existing | Control gate placement boundaries | Prevent replay gate collisions |
| C `circuit_optimize()` | existing | Optimize captured gate subsequence | Post-construction merge + inverse cancellation |
| Cython `_core.pyx` | existing | Host new helper functions | Python-C bridge layer |

**New Cython functions needed** (additions to `_core.pyx`, not new modules):

1. `extract_gate_range(start_layer, end_layer)` - Read `circuit.sequence[start:end]`, return Python list of gate dicts. Pattern exists in `draw_data()` method (~30 lines).
2. `inject_remapped_gates(gate_list, qubit_map)` - Replay gates with qubit index translation via `add_gate()` (~40 lines).
3. Cache clear hook in `circuit.__init__()` - Invalidate caches on circuit reset (~5 lines).

**Tracing strategy:** Tape-style capture (PennyLane QNode pattern), NOT abstract tracing (JAX pattern). Execute function normally with real values, snapshot `used_layer` before/after, extract gate range. Abstract tracing would require rewriting every qint operator method to handle tracer types—fundamentally incompatible with the Cython/C pipeline that directly calls `add_gate()`.

### Expected Features

**Table stakes (10 features):**
- Basic decorator syntax: `@ql.compile` and `@ql.compile(optimize=True)`
- Gate sequence capture via layer tracking (`start_layer` to `end_layer`)
- Gate sequence replay with qubit remapping on subsequent calls
- Qubit remapping: map captured indices to actual argument qubits
- Return value handling: compiled function returns usable qint/qbool
- Classical parameter support: `my_func(a, 5)` where 5 is compile-time constant
- Optimization on capture: run `circuit_optimize()` on captured subsequence
- Error on unsupported operations: clear errors for measurements, non-compilable operations
- Multiple return values: `carry, sum = full_adder(a, b, cin)`
- Works with `with` blocks: compiled function callable inside controlled context

**Differentiators (9 features):**
- Automatic parametric compilation: recompile only when structure changes, not classical values
- Signature-based caching: cache by `(func_id, arg_widths, classical_args)`
- Nested compilation: `@ql.compile` functions calling other `@ql.compile` functions
- Compile-time width inference: auto-determine output widths from annotations
- Debug mode: `@ql.compile(debug=True)` steps through gate replay
- Inverse/adjoint generation: automatically produce inverse of compiled function
- Controlled variant generation: `my_func.controlled(control_qubit)` for oracles
- Gate count / resource estimation: query `my_func.gate_count(width=8)` without execution
- OpenQASM subroutine export: compiled functions become `gate` blocks in QASM

**Anti-features (6 features to avoid):**
- Full abstract tracing (JAX-style): would require rewriting all Cython operator methods—use record-and-replay instead
- Bytecode manipulation (torch.compile/Dynamo): unnecessary complexity when operations go through known methods
- Automatic differentiation: circuit construction library, not variational training framework
- Hardware execution integration: keep compilation separate from execution
- Compiling arbitrary Python control flow: allow it during capture but document unrolling behavior
- Automatic parallelism/multi-device: premature optimization for research language

### Architecture Approach

**Design pattern: Capture-Optimize-Replay** at the circuit level:

**Phase 1: Capture**
1. Record `start_layer = circuit.used_layer` before function call
2. Execute function normally (all gates flow through `add_gate()` as usual)
3. Record `end_layer = circuit.used_layer` after execution
4. Extract gate range `[start_layer, end_layer)` via new Cython function
5. Build qubit mapping: abstract parameter positions to actual qubit indices

**Phase 2: Optimize**
1. Create temporary `circuit_t` containing only captured gates
2. Run `circuit_optimize()` on the temporary circuit
3. Store optimized gate list as compiled template

**Phase 3: Replay**
1. Map caller's qint qubit indices to template's abstract positions
2. Inject optimized gates via qubit remapping (`run_instruction()`-style)
3. Respect current `layer_floor` and controlled context

**Major components:**

```
quantum_language/
  __init__.py              # MODIFY: export 'compile' in __all__
  compile.py               # NEW: @ql.compile decorator (~200 LOC)
  _core.pyx                # MODIFY: add extract_gate_range, inject_remapped_gates
  _core.pxd                # MODIFY: declare new helper signatures
```

**Data structures:**

```python
class CompiledBlock:
    gates: list[dict]                          # {type, target_idx, controls[], angle}
    abstract_qubit_count: int                  # total abstract qubits used
    param_qubit_ranges: list[tuple[int, int]]  # (start, width) per parameter
    internal_qubit_count: int                  # temporaries allocated internally
    return_qubit_range: tuple[int, int] | None # abstract qubits for return value

class CompiledFunc:
    func: callable                             # original Python function
    cache: dict                                # (classical_args, widths, controlled) -> CompiledBlock
```

**Cache key:** `(classical_args_tuple, width_tuple, is_controlled)`. Quantum parameters (qint/qbool) affect only qubit remapping, not gate structure, so they're not in the key. Width must be in key since different widths produce structurally different sequences.

**Integration with existing architecture:**

- **Layer floor mechanism:** Set `layer_floor` before replay to prevent optimizer from reordering replayed gates before the operation's start point (pattern already used in `__add__`)
- **Controlled context:** Cache controlled and uncontrolled variants separately. When called inside `with qbool:`, the `_controlled` flag is already set, so capture naturally produces controlled sequences via `cCQ_add` etc.
- **Uncomputation:** Returned qint from compiled function must have correct `_start_layer`/`_end_layer` spanning the entire replayed gate range, not individual operations within

**Key architectural decisions:**

1. **Layer-range extraction** vs separate circuit buffer: Use layer range to avoid swapping global `_circuit` pointer (would break allocator continuity)
2. **Python-level cache** vs C-level: Cache includes Python objects (function identity, classical args), hot path (gate injection) already in C
3. **Re-capture for controlled variants** vs post-hoc control addition: Existing architecture uses entirely different `sequence_t` generators for controlled vs uncontrolled, re-capture is simpler
4. **Operation-level tracing** vs gate-level: Store operation metadata (ADD, MUL, widths) to enable parametric reuse and control addition at replay time

### Critical Pitfalls

**12 pitfalls identified, ordered by severity:**

**Pitfall 1: Qubit Index Collision During Replay** (CRITICAL)
- **Issue:** Traced gate sequence records concrete qubit indices. On replay, same indices are used but allocator has moved on—gates stomp caller's qubits.
- **Prevention:** Use virtual qubit namespace during tracing (offset 100000+), build mapping to real indices on replay, validate mapping completeness.
- **Phase:** Must solve in Phase 1 (core design).

**Pitfall 2: Width-Dependent Circuit Structure Breaks Parametric Compilation** (CRITICAL)
- **Issue:** `CQ_add(bits=4, value=5)` produces completely different gate sequence than `CQ_add(bits=8, value=5)`. Trace at width=4 cannot replay at width=8.
- **Prevention:** Include `(arg_widths, classical_args)` in cache key. Document: "parametric" means over quantum state, not circuit structure.
- **Phase:** Must design in Phase 1 (cache key design).

**Pitfall 3: Uncomputation Interaction - Double Reversal or Orphaned Intermediates** (CRITICAL)
- **Issue:** Compiled function creates intermediates that get uncomputed internally. Trace includes forward+reverse gates. Caller uncomputing output reverses already-balanced gates (double uncompute). Or: intermediates never freed on replay because no Python `qint.__del__` hooks execute.
- **Prevention:** Treat compiled block as single operation for uncomputation. Track `_start_layer`/`_end_layer` for entire block, not internals. Implement ancilla protocol for borrowed/returned qubits.
- **Phase:** Phase 2 (after basic tracing works). Hardest integration challenge.

**Pitfall 4: Control Context Leakage Between Trace and Replay** (CRITICAL)
- **Issue:** Tracing outside `with` captures uncontrolled gates. Replaying inside `with` produces uncontrolled gates (control qubit ignored). Or vice versa.
- **Prevention:** Cache controlled and uncontrolled variants separately via `is_controlled` in cache key. Or: trace at operation level (abstract "ADD") and apply control at replay time.
- **Phase:** Phase 2-3. Can defer by prohibiting `@ql.compile` inside `with` blocks initially.

**Pitfall 5: Global State Pollution During Tracing** (HIGH)
- **Issue:** Tracing executes function for real, mutating 12+ global state variables (`_num_qubits`, `_int_counter`, `_scope_stack`, etc.). After tracing, globals reflect both trace and replay—inconsistent state.
- **Prevention:** Snapshot-and-restore pattern for all global state before/after tracing. Minimum: restore `_num_qubits`, `_int_counter`, `_smallest_allocated_qubit`, `_global_creation_counter`.
- **Phase:** Phase 1. Must solve before tracing works correctly.

**Pitfall 6: Optimizer Interaction - Layer Indices Meaningless After Optimization** (MEDIUM)
- **Issue:** Circuit optimizer creates new circuit with different layer indices. Compiled function's `_start_layer`/`_end_layer` recorded during tracing may not bracket correct gates after optimizer parallelizes.
- **Prevention:** Set `layer_floor` at start of replay to prevent optimizer from moving gates before start point (already pattern in `__add__`).
- **Phase:** Phase 3. Can defer by documenting optimization considerations.

**Pitfall 7: Nested Compilation** (MEDIUM)
- **Issue:** `@ql.compile` function calling `@ql.compile` function creates double isolation (snapshot-restore clobbers), qubit namespace collision, cache key confusion.
- **Prevention:** Stack-based tracing context. Or: prohibit nesting in v1 with clear error.
- **Phase:** Phase 3-4. v1 can prohibit nesting.

**Pitfall 8: Gate-Level vs Operation-Level Tracing Granularity** (DESIGN)
- **Issue:** Gate-level tracing (record `run_instruction()` calls) loses semantic info—can't add control qubits later, can't reuse for different classical values, bloated traces.
- **Prevention:** Trace at operation level (ADD, MUL, widths, classical values). On replay, call appropriate C function with remapped qubits. Matches existing architecture.
- **Phase:** Phase 1 design decision.

**Pitfall 9: Return Value Lifetime and Ownership Transfer** (MEDIUM)
- **Issue:** Returned qint must own allocated qubits, have correct `_start_layer`/`_end_layer` for uncomputation, have correct `dependency_parents`, be registered in scope stack.
- **Prevention:** Explicit output protocol: create qint with `create_new=False`, set all ownership metadata, register in scope stack if inside `with` block.
- **Phase:** Phase 1 (basic) and Phase 2 (uncomputation).

**Pitfall 10: Cache Invalidation** (MEDIUM)
- **Issue:** Cached trace becomes invalid when circuit resets, qubit saving mode changes, control context changes, or user modifies function during development.
- **Prevention:** Invalidate on `circuit()` reset (hook in `circuit.__init__()`), include mode flags in cache key, optionally hash function bytecode for development.
- **Phase:** Phase 2 (caching).

**Pitfall 11: Debugging Opacity** (LOW)
- **Issue:** Compiled function appears as opaque gate block with no semantic labels. Hard to inspect intermediate results.
- **Prevention:** Add `name` parameter, support `debug=True` fallback to direct execution, consider circuit region annotations.
- **Phase:** Phase 3 (polish).

**Pitfall 12: Ancilla Management Across Compiled Boundary** (MEDIUM)
- **Issue:** Operations use ancilla qubits via global `ancilla` array. During tracing, ancilla indices are recorded. On replay, different ancillas in use—hardcoded indices use occupied ancillas.
- **Prevention:** Treat ancillas same as operation qubits in remapping. Record ancilla requirements (count, not indices), allocate fresh on replay.
- **Phase:** Phase 1 (part of qubit remapping).

## Implications for Roadmap

The research strongly suggests a four-phase build order following dependency chains: core tracing infrastructure first (can't compile without it), cache and uncomputation second (correctness requirements), control context and optimizer integration third (advanced interactions), nesting and polish fourth (nice-to-have enhancements).

### Suggested Phases

**Phase 1: Core Capture-Replay Mechanism**

**Rationale:** Establish fundamental tracing infrastructure before adding complexity. Validate the record-and-replay approach works with the existing architecture. Must solve qubit remapping and global state management before anything else.

**Delivers:**
- Cython `extract_gate_range(start_layer, end_layer)` function
- Cython `inject_remapped_gates(gate_list, qubit_map)` function
- Python `@ql.compile` decorator with basic caching
- Qubit remapping via virtual qubit namespace (offset-based)
- Global state snapshot-and-restore for tracing
- Ancilla qubit remapping
- Return value handling with ownership transfer

**Features:** T1 (decorator syntax), T2 (gate capture), T3 (gate replay), T4 (qubit remapping), T5 (return values), T6 (classical params)

**Pitfalls addressed:** #1 (qubit collision), #5 (global state), #8 (operation-level tracing decision), #9 (return value ownership), #12 (ancilla remapping)

**Phase 2: Optimization and Uncomputation**

**Rationale:** After basic compilation works, integrate with existing optimization and uncomputation systems. This is the hardest integration challenge—must handle compiled blocks as atomic units for uncomputation tracking.

**Delivers:**
- Optimization on capture (T7): run `circuit_optimize()` on captured subsequence
- Uncomputation integration: track `_start_layer`/`_end_layer` for entire compiled block
- Cache invalidation on circuit reset
- Width-dependent cache keys
- Multiple return values (T9)

**Features:** T7 (optimization), T8 (error handling), T9 (multiple returns)

**Pitfalls addressed:** #2 (width-dependent structure), #3 (uncomputation interaction), #10 (cache invalidation)

**Phase 3: Controlled Context and Optimizer Integration**

**Rationale:** Controlled execution (`with` blocks) requires separate cache entries or operation-level replay. Optimizer interaction needs `layer_floor` management during replay. Both are advanced features that can defer until core compilation is stable.

**Delivers:**
- `with` block support (T10): separate cache for controlled variants
- Controlled context in cache key
- Layer floor management during replay
- Nested compilation support (or prohibition with clear error)

**Features:** T10 (`with` blocks)

**Pitfalls addressed:** #4 (control context leakage), #6 (optimizer interaction), #7 (nested compilation)

**Phase 4: Differentiators and Polish**

**Rationale:** After all table stakes are complete and integration challenges solved, add advanced features that differentiate this implementation from other quantum frameworks.

**Delivers:**
- Debug mode (D5): `@ql.compile(debug=True)` steps through replay
- Inverse/adjoint generation (D6): automatically produce function inverse
- Controlled variant generation (D7): `my_func.controlled(control_qubit)`
- Gate count estimation (D8): query without execution
- Name parameter for debugging (Pitfall #11 mitigation)
- Signature-based caching improvements (D2)

**Features:** D2 (signature caching), D5 (debug mode), D6 (inverse), D7 (controlled variant), D8 (resource estimation)

**Pitfalls addressed:** #11 (debugging opacity)

### Phase Dependencies

```
Phase 1 (Core Capture-Replay)
    |
    v
Phase 2 (Optimization & Uncomputation) --> Can test with optimized circuits
    |
    v
Phase 3 (Controlled Context & Optimizer) --> Can use inside `with` blocks
    |
    v
Phase 4 (Differentiators & Polish) --> Production-ready features
```

**Critical path:** Phase 1 must complete before anything else. Phase 2 required for correctness with existing uncomputation system. Phase 3 required for integration with controlled execution. Phase 4 is pure enhancement.

### Research Flags

**Needs deeper research during implementation:**
- **Phase 2 only:** Uncomputation integration testing. The existing system has known fragility around layer-based tracking (documented in CONCERNS.md). Need comprehensive test suite to ensure compiled blocks don't break uncomputation.

**Standard patterns (no additional research needed):**
- **Phase 1:** Cython data extraction follows `draw_data()` pattern. Qubit remapping follows `run_instruction()` pattern. Both are well-understood in codebase.
- **Phase 3:** Controlled context mechanism is well-documented in `qint.pyx` lines 575-670. Cache invalidation is standard Python pattern.
- **Phase 4:** All differentiators use primitives established in earlier phases.

### Testing Strategy

**Phase 1 tests:**
- Round-trip: extract gates, inject them back, verify identical circuit via `draw_data()`
- Qubit remapping: compiled function with different qint arguments produces correct results
- Global state: assert invariants before/after compilation
- Return values: verify returned qints work in subsequent operations

**Phase 2 tests:**
- Optimization: verify optimized replay produces functionally equivalent but smaller circuits
- Uncomputation: verify compiled function results are properly uncomputed when they go out of scope
- Width variation: same function with different widths produces correct separate cache entries
- Circuit reset: cache invalidation on `circuit()` call

**Phase 3 tests:**
- Controlled execution: compiled function inside `with` block produces correct controlled gates
- Nesting: nested `@ql.compile` functions (or prohibition error)
- Optimizer interaction: compiled functions work correctly after `c.optimize()`

**Phase 4 tests:**
- Debug mode: verify `debug=True` falls back to direct execution
- Inverse generation: verify `my_func.inverse()` produces correct reversed gates
- Resource estimation: verify `gate_count()` matches actual execution

## Confidence Assessment

| Area | Confidence | Source Quality | Notes |
|------|------------|---------------|-------|
| **Stack** | HIGH | Codebase analysis + official documentation | All primitives exist: `used_layer`, `layer_floor`, `add_gate()`, `circuit_optimize()`. PennyLane/JAX docs clarify tracing paradigms. |
| **Features** | MEDIUM-HIGH | PennyLane/JAX/PyTorch patterns + codebase capabilities | Table stakes clear from prior art. Differentiators validated against existing architecture. Anti-features justified by architectural constraints. |
| **Architecture** | HIGH | Direct codebase analysis | Capture-optimize-replay pattern proven in `draw_data()` (extraction), `run_instruction()` (remapping), `circuit_optimize()` (optimization via copy-through-add_gate). |
| **Pitfalls** | HIGH | Codebase analysis + ecosystem research | All 12 pitfalls validated from existing code patterns or documented issues in PennyLane/Qrisp. Global state pollution evident from `_core.pyx`. Uncomputation fragility documented in CONCERNS.md. |

**Overall confidence:** HIGH

### Gaps to Address

**Parametric classical values:** Research recommends caching by classical parameter values, but this means recompilation when values change. Phase 4 could explore true parametric compilation (gate sequences with value placeholders), but this requires C-level gate structure changes—defer to v2.1+.

**Nested compilation semantics:** Research identifies nesting as complex (double isolation, qubit namespace collision) but doesn't fully design the stack-based context solution. Phase 3 should either implement stack-based contexts properly or prohibit nesting with clear error message. Recommend prohibition for v2.0, revisit in v2.1 based on user demand.

**Controlled variant generation API:** Research suggests `my_func.controlled(control_qubit)` syntax but doesn't detail implementation. Phase 4 should design API: method on compiled function object? Separate decorator parameter? Needs user feedback on expected syntax.

**Optimization passes for compiled blocks:** Research uses existing `circuit_optimize()` which does merge+inverse cancellation. Compiled blocks could benefit from more aggressive optimization (since they're executed many times). Phase 4 could explore compiled-specific optimization passes—but only after measuring performance bottlenecks.

## Sources

### Stack Research

**High confidence (official documentation):**
- [PennyLane QNode documentation (v0.44.0)](https://docs.pennylane.ai/en/stable/code/api/pennylane.QNode.html) — tape-based queuing mechanism
- [PennyLane QuantumTape (v0.40.0)](https://docs.pennylane.ai/en/stable/code/qml_tape.html) — AnnotatedQueue pattern
- [JAX tracing documentation](https://docs.jax.dev/en/latest/tracing.html) — abstract value tracing mechanism
- [JAX JIT compilation](https://docs.jax.dev/en/latest/jit-compilation.html) — ShapedArray tracers, compilation caching
- [PyTorch Dynamo overview (v2.9)](https://docs.pytorch.org/docs/stable/torch.compiler_dynamo_overview.html) — bytecode interpretation approach
- [Qiskit QuantumCircuit API](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.QuantumCircuit) — compose/append, ParameterVector
- [Cirq Circuits documentation](https://quantumai.google/cirq/build/circuits) — FrozenCircuit, CircuitOperation

**Codebase analysis:**
- `c_backend/include/circuit.h` lines 54-81 — `circuit_t` structure with `used_layer`, `layer_floor`
- `c_backend/include/optimizer.h` line 22 — `add_gate()` signature
- `c_backend/include/circuit_optimizer.h` — `circuit_optimize()` function
- `src/quantum_language/_core.pyx` lines 25-674 — global state, circuit class
- `src/quantum_language/qint.pyx` lines 575-670 — controlled context mechanism

### Features Research

**High confidence:**
- [PennyLane QNode documentation](https://docs.pennylane.ai/en/stable/code/api/pennylane.qnode.html)
- [PennyLane Architectural Overview](https://docs.pennylane.ai/en/stable/development/guide/architecture.html)
- [JAX Tracing Documentation](https://docs.jax.dev/en/latest/tracing.html)
- [TorchDynamo Deep-Dive](https://docs.pytorch.org/docs/stable/torch.compiler_dynamo_deepdive.html)
- [Cirq Circuits (FrozenCircuit)](https://quantumai.google/cirq/build/circuits)

**Medium confidence:**
- [PennyLane JIT compilation with Catalyst](https://pennylane.ai/blog/2024/11/quantitative-advantage-of-hybrid-compilation-with-pennylane)
- [Pandora: Ultra-Large-Scale Circuit Compilation](https://arxiv.org/html/2508.05608v1) — mentions Qrisp function caching

### Architecture Research

**High confidence (codebase analysis):**
- `c_backend/include/types.h` lines 56-83 — `gate_t`, `sequence_t` definitions
- `c_backend/src/optimizer.c` lines 167-220 — `add_gate()` with layer_floor
- `c_backend/src/execution.c` lines 14-53 — `run_instruction()` qubit remapping
- `c_backend/src/circuit_optimizer.c` lines 17-34, 89-98 — `copy_circuit()`, `circuit_optimize()`
- `src/quantum_language/qint_arithmetic.pxi` lines 5-121 — gate flow with controlled variants
- `src/quantum_language/qbool.pyx` lines 76-88 — ownership transfer pattern

### Pitfalls Research

**High confidence:**
- Direct codebase analysis of `_core.pyx`, `qint.pyx`, `qint_arithmetic.pxi`, `qint_comparison.pxi`
- `.planning/codebase/CONCERNS.md` — documented tech debt and fragile areas
- [PennyLane JAX JIT tracer bug #6054](https://github.com/PennyLaneAI/pennylane/issues/6054) — side effect escape
- [Qrisp Jasp tutorial](https://qrisp.eu/general/tutorial/Jasp.html) — function caching limitations

---

**Research completed:** 2026-02-04
**Ready for roadmap:** Yes
**Next step:** Define requirements and create implementation roadmap for Phase 1
