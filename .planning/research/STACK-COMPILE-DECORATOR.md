# Stack Research: Function Compilation (@ql.compile Decorator)

**Researched:** 2026-02-04
**Confidence:** HIGH (pure Python/Cython implementation, no new dependencies needed)

## Executive Summary

The `@ql.compile` decorator requires **zero new external dependencies**. The existing three-layer architecture (C backend -> Cython -> Python) already has all the primitives needed: a global circuit that accumulates gates via `add_gate()`, `layer_floor` for controlling gate placement, `circuit_optimize()` for post-construction optimization, and the controlled-context mechanism (`_controlled`/`_control_bool`) for `with` block integration. The implementation is a pure Python-level concern -- a decorator that intercepts circuit state before/after function execution, extracts the gate subsequence, caches it, and replays it on subsequent calls. This is conceptually closest to PennyLane's tape-based QNode (queuing context captures operations) rather than JAX/PyTorch-style abstract tracing (which would require replacing concrete values with tracers -- fundamentally incompatible with the Cython/C gate generation pipeline).

## Recommended Stack

### No New Libraries Required

| Component | What Exists | Why Sufficient |
|-----------|------------|----------------|
| Python `functools.wraps` | stdlib | Decorator metadata preservation |
| Python `contextvars` | stdlib, already used in `_core.pyx` | Scope depth tracking for `with` block nesting |
| C `circuit_t` | `c_backend/include/circuit.h` | Gate storage with layer-indexed access |
| C `circuit_optimize()` | `c_backend/include/circuit_optimizer.h` | Post-construction merge + inverse cancellation |
| Cython `_core.pyx` globals | `_circuit`, `_circuit_initialized` | Circuit state access, layer tracking |
| `layer_floor` field | `circuit_s.layer_floor` | Already used by arithmetic/comparison ops to bound gate placement |

### Python Mechanisms to Use

| Mechanism | Version | Purpose | Why This One |
|-----------|---------|---------|-------------|
| `functools.wraps` | Python 3.11+ (stdlib) | Preserve decorated function metadata | Standard decorator pattern, no dependency |
| `dict` (or `weakref.WeakValueDictionary`) | Python 3.11+ (stdlib) | Cache compiled results keyed by classical args | Simple, fast; WeakValueDictionary only if caching quantum objects |
| Context manager protocol (`__enter__`/`__exit__`) | Python 3.11+ (stdlib) | Bracket gate capture regions | Already proven in the codebase for `with qbool:` blocks |
| `inspect.signature` | Python 3.11+ (stdlib) | Separate classical params from quantum params in function signature | Needed to determine which args are "parametric" (classical) vs quantum |
| `typing.get_type_hints` | Python 3.11+ (stdlib) | Read type annotations to classify parameters | Works with `qint`, `qbool`, `int`, `float` annotations |

### Existing C Backend Capabilities to Leverage

| Capability | Location | How Used for @ql.compile |
|------------|----------|--------------------------|
| `circuit_t.used_layer` | `circuit.h` line 57 | Snapshot before/after function call to identify new gates |
| `circuit_t.layer_floor` | `circuit.h` line 75 | Set floor before replay to prevent gate placement collisions |
| `circuit_optimize()` | `circuit_optimizer.h` | Optimize the captured subsequence |
| `add_gate()` | `optimizer.h` | Replay cached gates into circuit on subsequent calls |
| `run_instruction()` | `execution.h` | Existing mechanism to apply gate sequences with qubit mapping |
| `circuit_t.sequence[layer][gate]` | `circuit.h` line 55 | Direct access to gate data for extraction |

## Tracing Strategy: Why Tape-Style, Not Abstract Tracing

### The Design Decision

There are two fundamentally different approaches to capturing computation:

**1. Abstract Tracing (JAX/PyTorch style) -- REJECTED:**
- Replace concrete values with tracer/proxy objects that record operations
- JAX uses `ShapedArray` tracers that carry type-level info without values, producing a `jaxpr` intermediate representation
- PyTorch's TorchDynamo interprets Python bytecode via the CPython Frame Evaluation API, building FX graphs
- **Why NOT for this project:** The entire gate generation pipeline goes through Cython into C. Operations like `__add__` on `qint` call C functions (`CQ_add`, `QQ_add`) that directly invoke `add_gate()` on the global `circuit_t`. Inserting abstract tracers would require either (a) rewriting all Cython operator methods to check for tracer inputs, or (b) creating a completely separate tracing path. Both are massive refactors with no proportional benefit. The codebase has ~221K LOC of Cython/C that would need modification.

**2. Tape/Snapshot Capture (PennyLane QNode style) -- RECOMMENDED:**
- Let the function execute normally with real values
- Record what gates were added by observing circuit state before/after
- Cache the gate sequence for replay
- **Why YES for this project:** The circuit already IS the tape. Every operation appends gates to `_circuit` via `add_gate()`. By snapshotting `used_layer` before the function call and reading it after, we know exactly which layers (and thus which gates) the function produced. This requires zero changes to the Cython/C pipeline.

### How Other Frameworks Do It (Relevant Patterns)

| Framework | Mechanism | Relevance to This Project |
|-----------|-----------|--------------------------|
| **PennyLane QNode (tape)** | Operations auto-register with active `QuantumTape` via queuing context manager. Tape records operations during function execution. | **Closest match.** Our `circuit_t` IS the tape. We snapshot layer count before/after, extract gate subsequence. Same "execute then inspect" pattern. |
| **PennyLane plxpr (newer)** | JAX jaxpr-based IR for hybrid quantum-classical programs, supports `qml.capture.enable()` for tracing. | Overkill. Only needed for differentiable quantum programs and JIT compilation to hardware. |
| **Qiskit ParameterVector** | `QuantumCircuit` with `Parameter` placeholders. Transpile once, then `assign_parameters()` to bind values. | **Parametric pattern is relevant:** compile with abstract classical params, bind concrete values later. Our classical args serve same role. |
| **Cirq FrozenCircuit** | `FrozenCircuit` + `CircuitOperation` for reusable, immutable subcircuits. Supports repetition, qubit remapping, nesting. | **Good pattern for cached result:** frozen/immutable compiled gate sequence, applied via replay with qubit remapping. |
| **JAX jit** | Abstract tracing with `ShapedArray` tracers; function executed once with tracers to produce `jaxpr`; compiled via XLA; cached by `(shape, dtype)` key. | **Wrong paradigm.** Requires value-agnostic tracers; our ops need actual qubit addresses to call C functions. Caching-by-key concept is relevant though. |
| **PyTorch torch.compile** | TorchDynamo: custom bytecode interpreter via CPython Frame Evaluation API. Builds FX graphs with "guards" for recompilation triggers. Supports "graph breaks" for unsupported code. | **Way too heavy.** Bytecode interception is unnecessary when we control the circuit object directly. Guard concept (recompile when args change) maps to our cache-by-classical-args approach. |

### The Concrete Approach

```python
@ql.compile
def my_func(a: qint, b: qint, n: int):
    # n is classical (parametric), a/b are quantum
    a += n
    result = a & b
    return result
```

**First call:** Execute normally, snapshot `circuit.used_layer` before/after, extract gate sequence from layers `[before..after]`, optimize it, cache keyed by classical args `(n,)`.

**Subsequent calls (same classical args):** Skip function execution entirely. Replay cached gate sequence with new qubit mappings (map old qubit addresses to current qint qubit addresses).

**Different classical args:** Execute again (different `n` produces different gate sequence via `CQ_add`), cache separately.

## Integration Points

### Layer 1: Python Decorator (`compile.py` -- new file)

```
quantum_language/
  __init__.py        # MODIFY: add `from .compile import compile` to exports
  compile.py         # NEW: @ql.compile decorator implementation (~200 LOC)
  _core.pyx          # MODIFY: expose 2-3 new helper functions
  _core.pxd          # MODIFY: declare new helper signatures
```

The decorator lives in pure Python. It:
1. Inspects function signature to classify args as quantum (`qint`/`qbool`) vs classical (`int`/`float`/etc.)
2. On first call: snapshots layer count, executes function, extracts gate range, optimizes, caches
3. On subsequent calls: maps qubits and replays cached gates

### Layer 2: Cython Helpers (additions to `_core.pyx`)

New functions needed in `_core.pyx` (small additions, not new modules):

| Function | Purpose | Complexity |
|----------|---------|------------|
| `_snapshot_circuit_state()` | Return `(used_layer, used_qubits)` tuple from `_circuit` | Trivial (~5 lines) |
| `_extract_gate_range(start_layer, end_layer)` | Extract gates from layer range as list of dicts (type, target, controls, angle) | Moderate (~30 lines, similar to `draw_data()`) |
| `_replay_gates(gate_list, qubit_map)` | Re-add gates with remapped qubit addresses via `add_gate()` | Moderate (~40 lines) |

These are thin Cython wrappers around existing C circuit struct access. The pattern is identical to the existing `draw_data()` method which already extracts gate info from `circuit_t` into Python dicts.

### Layer 3: C Backend (minimal changes)

The C backend likely needs **no changes** for the basic implementation. Existing `add_gate()` handles layer assignment. Existing `circuit_optimize()` handles optimization.

**Optional C addition (performance optimization, not v1):** A `circuit_extract_range()` function that creates a new `circuit_t` from a layer range of an existing circuit, enabling optimization of just the compiled function's gates. But for v1, extracting gates into Python dicts and replaying them is sufficient and simpler.

### Integration with `with` Blocks (Controlled Context)

The `with` block sets `_controlled = True` and `_control_bool` to the controlling qubit (see `qint.pyx` lines 575-625). When `@ql.compile` runs inside a `with` block:

- **First call inside `with`:** The controlled state is already active. Gates generated by the function will already include control qubits (each operator checks `_get_controlled()` and augments gates with control qubits). The captured gate sequence naturally includes the control.
- **Cache key must include controlled state:** `(classical_args, is_controlled, control_qubit_tuple)` to avoid replaying uncontrolled gates in a controlled context or vice versa.
- **Qubit remapping must handle control qubits:** Cached gates store qubit addresses. On replay, both target AND control qubit addresses must be remapped.

**Simpler alternative for v1:** Do NOT cache across controlled/uncontrolled boundaries. If `_controlled` state differs from the cached entry's state, re-execute. This is simpler and avoids subtle bugs around control qubit remapping. Controlled compilation can be optimized in v2.

### Integration with Uncomputation

The existing uncomputation system tracks `creation_scope` and `_creation_order` on qint objects (see `qint.pyx` lines 540-570). For compiled functions:

**v1 constraint (recommended):** `@ql.compile` functions should only operate on existing qints passed as arguments. They should NOT allocate new qints internally (because uncomputation tracking would not survive cache replay). If a compiled function needs to return a new qint, the decorator should handle allocating it OUTSIDE the compiled region and passing it in.

**v2 enhancement:** Support internal qint allocation by recording allocation/deallocation patterns alongside gates, and replaying them on cache hit.

## Parametric Compilation (Classical Args)

Following the Qiskit `ParameterVector` pattern conceptually, but simpler since we re-execute rather than symbolic-substitute:

| Classical Arg Value | Cache Behavior |
|--------------------|----------------|
| Same as previous call | Replay cached gates (fast path) |
| Different value | Re-execute function, optimize, cache new entry |

Cache structure:
```python
_cache: dict[tuple, CachedGateSequence] = {}
# Key: (classical_arg_1, classical_arg_2, ..., is_controlled)
# Value: CachedGateSequence with gate data + qubit slot mapping
```

The `CachedGateSequence` stores:
- List of gate dicts: `{type, target_slot, control_slots, angle}`
- Slot mapping: position-based references (e.g., "arg 0, qubit index 3") rather than absolute qubit addresses
- Pre/post optimization flag

**Cache eviction:** Simple LRU with configurable max size (default 16 entries). Classical arg space is typically small for quantum functions.

## What NOT to Add (and Why)

| Library/Approach | Why Rejected |
|------------------|-------------|
| **JAX** | Abstract tracing paradigm incompatible with Cython/C gate pipeline. Would require rewriting all ~50 operator methods in qint/qbool. |
| **PyTorch/TorchDynamo** | CPython bytecode-level interception is massive overkill. We control the circuit object directly. |
| **AST manipulation (`ast` module)** | Fragile, requires parsing Python source. Normal execution + snapshot is simpler and handles all Python constructs. |
| **`sys.settrace` / frame inspection** | Python tracing hooks add per-line overhead and complexity. Not needed when circuit IS the trace. |
| **Serialization (pickle, msgpack)** | Gate sequences are already accessible as C structs. Extracting to Python dicts is sufficient. No cross-process persistence needed. |
| **Caching libraries (diskcache, joblib)** | In-memory dict cache is sufficient. Compiled circuits are session-scoped, not persisted. Cross-session caching would require serializing qubit mappings. |
| **New Cython modules** | The decorator should be pure Python (`compile.py`), importing helpers from `_core`. No new `.pyx` files needed. |
| **`collections.OrderedDict`** | For LRU cache. Use `functools.lru_cache` on a helper or simple dict with size check. |
| **`typing_extensions`** | For `ParamSpec` etc. Not needed; decorator preserves signature via `functools.wraps`. |

## Version Requirements

| Component | Required Version | Currently Used | Notes |
|-----------|-----------------|----------------|-------|
| Python | 3.11+ | 3.13 | `inspect.signature`, `functools.wraps`, `contextvars`, `typing.get_type_hints` all available |
| Cython | Any (existing) | Already in project | 2-3 new helper functions in `_core.pyx` |
| C backend | No changes | Existing | All needed primitives exist |
| NumPy | Any (existing) | Already in project | Not directly needed for this feature |

## Confidence Assessment

| Area | Confidence | Source | Notes |
|------|-----------|--------|-------|
| Tape-style capture feasibility | HIGH | Codebase analysis: `circuit_t.used_layer`, `draw_data()` precedent | Proven pattern in `draw_data()` which already extracts gate info |
| No new dependencies needed | HIGH | Codebase analysis: all primitives exist | `layer_floor`, `add_gate()`, `circuit_optimize()` all present |
| PennyLane QNode comparison | HIGH | [PennyLane docs](https://docs.pennylane.ai/en/stable/code/api/pennylane.QNode.html) | Queuing-based tape capture is well-documented |
| JAX tracing incompatibility | HIGH | [JAX tracing docs](https://docs.jax.dev/en/latest/tracing.html), codebase analysis | Abstract tracers cannot pass through Cython `cdef` typed parameters |
| PyTorch Dynamo rejection rationale | HIGH | [PyTorch Dynamo docs](https://docs.pytorch.org/docs/stable/torch.compiler_dynamo_overview.html) | Bytecode-level approach is architectural mismatch |
| Qiskit parametric pattern | MEDIUM | [Qiskit QuantumCircuit API](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.QuantumCircuit) | Concept applies but implementation differs (we re-execute vs symbolic substitution) |
| Cirq FrozenCircuit pattern | MEDIUM | [Cirq Circuits docs](https://quantumai.google/cirq/build/circuits) | Immutable cached result pattern applies |
| `with` block integration | HIGH | Codebase analysis: `qint.pyx` lines 575-670 | `_controlled`/`_control_bool` mechanism is well-understood |
| Uncomputation constraints | MEDIUM | Codebase analysis: scope tracking in `qint.pyx` | v1 constraint (no internal allocation) is safe; v2 relaxation needs more research |

## Sources

- [PennyLane QNode documentation (v0.44.0)](https://docs.pennylane.ai/en/stable/code/api/pennylane.QNode.html) -- tape-based queuing mechanism
- [PennyLane QuantumTape (v0.40.0)](https://docs.pennylane.ai/en/stable/code/qml_tape.html) -- AnnotatedQueue pattern
- [PennyLane program capture (v0.44.0)](https://docs.pennylane.ai/en/stable/news/program_capture_sharp_bits.html) -- newer plxpr approach (JAX-based, evaluated and rejected)
- [JAX tracing documentation](https://docs.jax.dev/en/latest/tracing.html) -- abstract value tracing mechanism
- [JAX JIT compilation](https://docs.jax.dev/en/latest/jit-compilation.html) -- ShapedArray tracers, compilation caching
- [PyTorch Dynamo overview (v2.9)](https://docs.pytorch.org/docs/stable/torch.compiler_dynamo_overview.html) -- bytecode interpretation approach
- [PyTorch Dynamo deep-dive (v2.9)](https://docs.pytorch.org/docs/stable/torch.compiler_dynamo_deepdive.html) -- guard-based recompilation, graph breaks
- [Qiskit QuantumCircuit API](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.QuantumCircuit) -- compose/append, ParameterVector, assign_parameters
- [Cirq Circuits documentation](https://quantumai.google/cirq/build/circuits) -- FrozenCircuit, CircuitOperation, qubit remapping
- [Cirq Circuit Transformers](https://quantumai.google/cirq/transform/transformers) -- transformer API pattern
