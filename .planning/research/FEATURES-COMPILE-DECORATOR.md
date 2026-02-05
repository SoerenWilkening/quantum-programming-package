# Features Research: Function Compilation (`@ql.compile`)

**Domain:** Quantum circuit compilation decorator for Python-embedded quantum DSL
**Researched:** 2026-02-04
**Overall confidence:** MEDIUM-HIGH (strong prior art from JAX/PennyLane/PyTorch; project-specific integration needs validation)

## Executive Summary

A `@ql.compile` decorator needs to capture quantum operations from a decorated function, produce an optimized gate sequence, and replay that sequence on subsequent calls. The existing codebase already uses an imperative "record gates as you go" model (operations on `qint`/`qbool` emit gates into a global `circuit_t`), which means tracing is effectively already happening -- the challenge is scoping it to a function boundary, snapshotting the result, and replaying it. The closest prior art is PennyLane's `@qml.qnode` (queuing-based tape capture) and JAX's `@jit` (abstract tracer substitution with caching). The critical design decision is whether `@ql.compile` uses **record-and-replay** (capture gate sequence on first call, replay on subsequent calls) or **abstract tracing** (substitute tracer objects for qint arguments). Given the existing architecture where qint operations directly emit C-level gates, record-and-replay is the natural and far simpler approach.

## Table Stakes

Features users expect from any compilation decorator. Missing any of these makes the feature feel broken.

| # | Feature | Why Expected | Complexity | Dependencies | Notes |
|---|---------|--------------|------------|--------------|-------|
| T1 | **Basic decorator syntax** (`@ql.compile` and `@ql.compile()` with optional args) | Standard Python decorator pattern; JAX, PennyLane, PyTorch all use this | Low | None | Must support both bare `@ql.compile` and `@ql.compile(optimize=True)` forms |
| T2 | **Gate sequence capture** (record all gates emitted during function body) | Core purpose of the decorator | Medium | `circuit_t` layer tracking (`get_current_layer`, `used_layer`) | Use existing `_start_layer`/`_end_layer` pattern already used for uncomputation |
| T3 | **Gate sequence replay** (emit captured gates into current circuit on subsequent calls) | Without replay, there is no compilation benefit | Medium | C-level circuit API for gate insertion | Need a way to "paste" a recorded gate sub-sequence into the current circuit at different qubit offsets |
| T4 | **Qubit remapping on replay** (map captured qubit indices to actual argument qubits) | Different calls pass different qint objects with different qubit allocations | Medium-High | Gate data structure must support qubit index rewriting | This is the hardest table-stakes feature. Captured gates reference specific qubit indices; replay must translate them |
| T5 | **Return value handling** (compiled function returns qint/qbool usable outside) | Users expect `result = my_func(a, b)` to produce a live quantum value | Medium | Qubit allocation, dependency tracking | Returned qint must own freshly-allocated qubits with gates from the replayed sequence |
| T6 | **Classical parameter support** (int arguments treated as compile-time constants or parametric) | `my_func(a, 5)` where 5 is a classical int must work | Low-Medium | Existing CQ (classical-quantum) operation paths | Classical ints already handled by `type(other) == int` branches in arithmetic |
| T7 | **Optimization on capture** (run `circuit.optimize()` on the captured sub-circuit) | Primary value proposition -- compile once, optimize once, replay fast | Low | Existing `circuit_optimize()` C function | Apply merge/cancel_inverse passes to the captured gate sequence |
| T8 | **Error on unsupported operations** (clear error if function body contains non-compilable operations like measurement) | Users need clear feedback when something cannot be compiled | Low | None | Detect and reject side effects during capture |
| T9 | **Multiple return values** (return tuples of qint/qbool) | Common pattern: `carry, sum = full_adder(a, b, cin)` | Low | T5 | Extend single-return handling to tuples |
| T10 | **Works with `with` blocks** (compiled function can be called inside a conditional context) | Existing code uses `with cond:` for controlled execution; compiled functions must participate | Medium-High | `_controlled`, `_control_bool` global state | When called inside `with qbool:`, all replayed gates must be controlled-gated. This interacts with the existing control mechanism |

## Differentiators

Features that would set `@ql.compile` apart from other quantum frameworks. Not expected but create competitive advantage.

| # | Feature | Value Proposition | Complexity | Dependencies | Notes |
|---|---------|-------------------|------------|--------------|-------|
| D1 | **Automatic parametric compilation** (classical int args become parameters; recompile only when structure changes, not values) | JAX-style: compile once per "shape", reuse across different classical values. Avoids recompilation when only classical constants change | High | Need parametric gate representation (angles as variables, not constants) | CQ_add already takes classical int as parameter to the C function -- could key cache on (function, qint_widths) and let classical values vary. But the C-level `sequence_t` embeds the classical value in the gate sequence, so true parametric support requires gate-level changes |
| D2 | **Signature-based caching** (cache compiled result keyed on argument widths, not values) | Call `my_func(qint(x, width=4), qint(y, width=4))` many times without recompiling | Medium | T2, T3, T4 | Cache key = `(func_id, tuple_of_arg_widths, tuple_of_classical_arg_values)`. Invalidate when widths change |
| D3 | **Nested compilation** (`@ql.compile` functions calling other `@ql.compile` functions) | Composability -- build complex algorithms from compiled building blocks | Medium-High | T2, T3, T4 | Inner function's cached sequence gets inlined into outer function's capture. PennyLane supports nested QNodes with some restrictions |
| D4 | **Compile-time width inference** (auto-determine output widths from input widths without executing) | Enables static analysis and better error messages pre-execution | Medium | Type annotation inspection | Use Python type hints: `def add(a: qint[4], b: qint[4]) -> qint[4]` |
| D5 | **Debug mode** (step through compiled function showing gate-by-gate execution) | Critical for quantum algorithm development where debugging is hard | Medium | Circuit visualization (`draw_data`) | `@ql.compile(debug=True)` that prints each gate as it replays |
| D6 | **Inverse/adjoint generation** (automatically produce the inverse of a compiled function) | Essential for quantum algorithms (uncomputation, QPE). Cirq's `CircuitOperation` supports inverse | Medium | T2, existing `reverse_instruction_range` | Already have `reverse_circuit_range` in C backend -- extend to compiled sequences |
| D7 | **Controlled variant generation** (produce controlled version of compiled function) | `my_func.controlled(control_qubit)` for Grover oracles, QPE subroutines | Medium-High | T10, T6 | Convert all gates in captured sequence to controlled versions. Existing `_controlled` mechanism does this gate-by-gate; need to do it for a whole sequence |
| D8 | **Gate count / resource estimation without execution** | Let users query `my_func.gate_count(width=8)` before running | Low | T2, D2 | Just compile and count, do not emit into real circuit |
| D9 | **OpenQASM subroutine export** (compiled functions become `gate` or `def` blocks in QASM output) | Structured QASM output instead of flat gate list | Medium | `to_openqasm()` | OpenQASM 3.0 supports `gate` definitions and `def` subroutines |

## Anti-Features

Features to deliberately NOT build. Common mistakes in this domain.

| # | Anti-Feature | Why Avoid | What to Do Instead |
|---|-------------|-----------|-------------------|
| A1 | **Full abstract tracing (JAX-style)** | JAX replaces values with abstract `Tracer` objects that record operations symbolically. This requires ALL operations to handle tracer types, which would mean rewriting every `__add__`, `__mul__`, comparison, etc. in qint.pyx. The existing architecture emits C-level gates eagerly -- abstract tracing would be a fundamental rewrite. PennyLane took years to build their plxpr tracer. | **Use record-and-replay instead.** Execute the function once with real qint objects, record the gate range (`start_layer` to `end_layer`), snapshot the gate sequence, and replay it on future calls. This leverages the existing architecture rather than fighting it. |
| A2 | **Bytecode manipulation (torch.compile/Dynamo-style)** | PyTorch's Dynamo hooks into CPython's frame evaluation API (PEP 523) to rewrite bytecode. This is extremely complex, CPython-version-dependent, and fragile. Completely unnecessary for a quantum DSL where all operations go through known Python methods. | **Use standard Python decorator + first-call capture.** The function body already calls `qint.__add__` etc. which emit gates. Just capture the gate range. |
| A3 | **Automatic differentiation / gradient support** | PennyLane's QNode exists partly for autodiff integration. This project is a circuit construction library, not a variational quantum algorithm framework. Adding gradient support adds massive complexity for a use case that may not be needed. | **Focus on circuit optimization, not training.** If gradients are needed later, that is a separate feature. |
| A4 | **Hardware execution integration** | PennyLane's QNode binds to a `device` for execution. This project generates circuits (QASM export) -- execution is handled externally. Coupling compilation to execution conflates concerns. | **Keep `@ql.compile` purely about circuit construction and optimization.** Execution remains via `to_openqasm()` then external simulator/hardware. |
| A5 | **Compiling arbitrary Python control flow** | Trying to compile arbitrary Python (loops, conditionals, function calls) inside the decorated function, like JAX's requirement that all operations be JAX-compatible. | **Allow arbitrary Python in the function body** since we execute it normally on first call. The function can contain `for` loops, `if` statements, etc. -- they just execute during capture and the resulting gates are recorded. Document that control flow is "unrolled" at capture time (same as JAX without `jax.lax.cond`). |
| A6 | **Automatic parallelism / multi-device** | Some frameworks try to automatically distribute compilation across devices. Premature optimization for a research quantum language. | **Single-circuit compilation only.** |

## Feature Dependencies

```
T1 (decorator syntax)
 |
 v
T2 (gate capture) ---> T7 (optimization on capture)
 |                       |
 v                       v
T3 (gate replay) -----> D2 (signature caching)
 |                       |
 v                       v
T4 (qubit remapping) -> D3 (nested compilation)
 |
 +---> T5 (return values) --> T9 (multiple returns)
 |
 +---> T6 (classical params) --> D1 (parametric compilation)
 |
 +---> T10 (with blocks) --> D7 (controlled variant)
 |
 +---> D6 (inverse generation)

D5 (debug mode) -- independent, can add anytime
D8 (resource estimation) -- depends on T2 + D2
D9 (QASM subroutine export) -- depends on T2, independent of replay
```

## MVP Recommendation

For MVP, prioritize the record-and-replay core:

1. **T1** - Decorator syntax (trivial)
2. **T2** - Gate sequence capture (use existing layer tracking)
3. **T4** - Qubit remapping (the hard part -- need offset-based translation)
4. **T3** - Gate sequence replay (with remapping)
5. **T5** - Return value handling
6. **T6** - Classical parameter support
7. **T7** - Optimization on capture
8. **T8** - Error handling

Defer to post-MVP:
- **T10** (`with` block interaction): Complex interaction with global control state; get basic compilation working first
- **D1** (parametric compilation): Requires C-level gate structure changes
- **D3** (nested compilation): Get single-level working first
- **D6, D7** (inverse/controlled variants): Valuable but not blocking basic usage
- **D9** (QASM subroutine export): Nice-to-have, not blocking

## Prior Art

### PennyLane `@qml.qnode`
- **Mechanism:** Queuing-based tape capture. When QNode is called, a `QuantumTape` context manager activates. Operations queue themselves via `qml.apply()`. After execution, the tape is processed, optimized, and sent to a device.
- **Key insight for this project:** PennyLane re-traces on every call (no caching by default). Catalyst's `@qjit` adds JIT caching on top. We should cache by default since our circuits are deterministic for given widths.
- **What to adopt:** The "execute function normally, capture side effects" pattern. Our side effects are gate emissions into `circuit_t`.
- **What to skip:** The device binding, autodiff integration, and plxpr tracer infrastructure.
- **Confidence:** HIGH (official documentation reviewed)

### JAX `@jit`
- **Mechanism:** Abstract tracing. Replaces input arrays with `ShapedArray` tracers that have shape/dtype but no values. Operations on tracers build a Jaxpr (intermediate representation). Jaxpr is compiled to XLA.
- **Key insight for this project:** Caching keyed on `(shapes, dtypes)` is powerful. We should cache on `(function_id, arg_widths)`.
- **What to adopt:** The caching strategy. Signature = `(func, width_tuple)`. Classical args can be part of the signature (recompile on different classical values, like `static_argnums`).
- **What to skip:** Abstract tracing itself (would require rewriting all qint operations to handle tracer types).
- **Confidence:** HIGH (official documentation reviewed)

### PyTorch `torch.compile` (TorchDynamo)
- **Mechanism:** Bytecode interception via PEP 523. Dynamo hooks into CPython's frame evaluator, analyzes bytecode, extracts PyTorch operations into FX graphs, compiles with backend (Inductor).
- **Key insight for this project:** "Graph breaks" -- when Dynamo encounters un-compilable code, it falls back to eager execution. This resilience pattern is informative but unnecessary for our simpler use case.
- **What to adopt:** Nothing directly. This approach is far too complex for our use case.
- **What to skip:** All of it. Bytecode manipulation is the wrong tool for a domain-specific quantum language.
- **Confidence:** HIGH (official documentation reviewed)

### Qiskit Circuit Composition
- **Mechanism:** Build small circuits, convert to `Gate` via `to_gate()`, append to larger circuits with qubit mapping.
- **Key insight for this project:** `to_gate()` + `append()` is exactly the "compile to reusable block, replay with qubit mapping" pattern we need. Qiskit does not have a decorator for this -- it is manual.
- **What to adopt:** The qubit remapping concept. A compiled function is essentially a `to_gate()` result that can be appended at different qubit offsets.
- **What to skip:** The lack of automation. Our decorator should make this seamless.
- **Confidence:** HIGH (official documentation reviewed)

### Cirq `FrozenCircuit` + `CircuitOperation`
- **Mechanism:** Freeze a circuit (immutable), wrap in `CircuitOperation` which supports qubit remapping, repetition, and nesting.
- **Key insight for this project:** `FrozenCircuit` is the exact "compiled, immutable gate sequence" we want. `CircuitOperation`'s qubit mapping is the replay mechanism.
- **What to adopt:** The frozen/immutable compiled result concept. Once captured and optimized, the gate sequence should be immutable.
- **What to skip:** The `CircuitOperation` class hierarchy (we want a simpler decorator-based API).
- **Confidence:** HIGH (official documentation reviewed)

### Qrisp / Catalyst Function Caching
- **Mechanism:** Decorator that traces a function once, caches the resulting gate sequence, replays on subsequent calls. Catalyst's `@qjit` compiles once and reuses the binary for different parameter values.
- **Key insight for this project:** This is closest to what we want to build. Both Qrisp and Catalyst solved the same "compile once, replay many" problem for imperative quantum DSLs.
- **What to adopt:** The overall approach -- record-and-replay with caching.
- **Confidence:** MEDIUM (based on published papers and blog posts, not direct API testing)

## Implementation Sketch (Record-and-Replay)

The recommended approach, based on research:

```python
@ql.compile
def my_algo(a: qint, b: qint):
    a += b
    c = a * b
    return c
```

Under the hood:

1. **First call:** Decorator intercepts `my_algo(x, y)`.
   - Records `start_layer = circuit.used_layer`
   - Calls the real function with actual qint args
   - Records `end_layer = circuit.used_layer`
   - Extracts gate sequence from `[start_layer, end_layer)`
   - Runs `circuit_optimize()` on the sub-sequence
   - Stores: `{cache_key: (gate_sequence, qubit_map, return_qubit_info)}`
   - Cache key: `(func_id, (a.width, b.width), (classical_arg_values,))`

2. **Subsequent calls:** Decorator intercepts `my_algo(x2, y2)`.
   - Computes cache key from argument widths and classical values
   - Cache hit: allocates fresh qubits for intermediates/outputs
   - Translates stored gate sequence to new qubit indices
   - Emits translated gates into current circuit
   - Returns new qint bound to output qubits

3. **Qubit remapping:** The captured gates reference absolute qubit indices from the first call. On replay:
   - Build mapping: `{first_call_qubit_idx: current_call_qubit_idx}` for inputs
   - For intermediates/output qubits: allocate fresh qubits and add to mapping
   - For each gate in sequence: replace all qubit references using mapping
   - Emitted gates use new qubit indices

4. **Key architectural decisions:**
   - Gate extraction requires a new C function to snapshot a layer range into a portable format (list of gate descriptors with relative qubit indices)
   - Replay requires a C function to emit a gate list with qubit index translation
   - The `draw_data()` method already extracts gate info to Python dicts -- this pattern can be reused

## Complexity Assessment

| Component | Effort | Risk | Notes |
|-----------|--------|------|-------|
| Decorator wrapper (T1) | 0.5 day | Low | Standard Python pattern |
| Gate capture via layer range (T2) | 1-2 days | Low | Reuse existing layer tracking |
| Gate sequence extraction to portable format | 2-3 days | Medium | New C function needed; similar to `draw_data` but captures full gate info |
| Qubit remapping logic (T4) | 2-3 days | Medium-High | Core difficulty; must handle inputs, intermediates, outputs |
| Gate replay with remapping (T3) | 1-2 days | Medium | New C function to inject gates with translated indices |
| Return value handling (T5, T9) | 1-2 days | Medium | Track which qubits in capture correspond to return values |
| Classical param support (T6) | 0.5 day | Low | Already in cache key |
| Optimization on capture (T7) | 0.5 day | Low | Call existing `circuit_optimize()` on sub-circuit |
| Error handling (T8) | 0.5 day | Low | Detect measurement, print, etc. |
| **Total MVP** | **9-14 days** | **Medium** | |
| Caching (D2) | 1-2 days | Low | Dict keyed on signature |
| Inverse generation (D6) | 1-2 days | Low | Reuse `reverse_circuit_range` |
| `with` block support (T10) | 2-3 days | High | Global control state interaction |

## Open Questions

1. **Gate extraction format:** Should the portable gate sequence be a C struct array (faster) or Python list of dicts (simpler)? The `draw_data()` method already returns Python dicts -- could reuse that pattern for MVP and optimize later.

2. **In-place vs out-of-place operations in compiled functions:** If the function does `a += b` (in-place), the original `a` is modified. On replay, should we modify the caller's `a` or work on a copy? Recommendation: document that compiled functions should use out-of-place operations (`c = a + b`) and in-place ops modify the input, consistent with current behavior.

3. **Uncomputation interaction:** The existing uncomputation system (`_do_uncompute`, `_start_layer`, `_end_layer`) tracks individual qint operations. How does this interact with compiled function boundaries? Should the entire compiled function be treated as a single "operation" for uncomputation purposes?

4. **Scope/control state isolation:** During capture, the function may set/read global state (`_controlled`, `_control_bool`). On replay, this state may be different. Need to ensure replay does not corrupt or depend on capture-time global state.

## Sources

### High Confidence (Official Documentation)

- [PennyLane QNode documentation](https://docs.pennylane.ai/en/stable/code/api/pennylane.qnode.html)
- [PennyLane Architectural Overview](https://docs.pennylane.ai/en/stable/development/guide/architecture.html)
- [PennyLane Program Capture (plxpr)](https://docs.pennylane.ai/en/stable/news/program_capture_sharp_bits.html)
- [JAX Tracing Documentation](https://docs.jax.dev/en/latest/tracing.html)
- [JAX JIT Compilation](https://docs.jax.dev/en/latest/jit-compilation.html)
- [TorchDynamo Deep-Dive](https://docs.pytorch.org/docs/stable/torch.compiler_dynamo_deepdive.html)
- [TorchDynamo Overview](https://docs.pytorch.org/docs/stable/torch.compiler_dynamo_overview.html)
- [Qiskit QuantumCircuit API](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.QuantumCircuit)
- [Qiskit Construct Circuits Guide](https://docs.quantum.ibm.com/guides/construct-circuits)
- [Cirq Circuits (Subcircuits, FrozenCircuit)](https://quantumai.google/cirq/build/circuits)

### Medium Confidence (Blog Posts, Multiple Sources)

- [PennyLane JIT compilation with Catalyst](https://pennylane.ai/blog/2024/11/quantitative-advantage-of-hybrid-compilation-with-pennylane)
- [How JIT Works: Tracing and Compilation (apxml.com)](https://apxml.com/courses/getting-started-with-jax/chapter-2-accelerating-functions-jit/how-jit-works)
- [Decipher JAX Tracing and JIT (wangkuiyi.github.io)](https://wangkuiyi.github.io/jax.jit.html)

### Low Confidence (Single Source / Indirect)

- [Pandora: Ultra-Large-Scale Circuit Compilation](https://arxiv.org/html/2508.05608v1) -- mentions Qrisp function caching
