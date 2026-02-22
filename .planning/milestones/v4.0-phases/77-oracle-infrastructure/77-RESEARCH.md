# Phase 77: Oracle Infrastructure - Research

**Researched:** 2026-02-20
**Domain:** Quantum oracle decorator infrastructure (Python/Cython), compute-phase-uncompute pattern enforcement, phase kickback wrapping, and oracle caching
**Confidence:** HIGH

## Summary

Phase 77 adds a `@ql.grover_oracle` decorator that layers on top of the existing `@ql.compile` infrastructure to enforce quantum oracle semantics: correct compute-phase-uncompute ordering, zero ancilla delta on exit, automatic bit-flip-to-phase-oracle wrapping, and arithmetic-mode-aware caching. This is a **pure Python layer** -- no C backend changes are needed because all required gate primitives (X, H, Z, MCZ, Ry) already exist in `_gates.pyx` and `gate.h`, and the `@ql.compile` capture/replay machinery (including `extract_gate_range`, `inject_remapped_gates`, `_allocate_qubit`, `_deallocate_qubits`, and `circuit_stats`) already handles gate capture, virtual qubit mapping, and ancilla tracking.

The key engineering challenges are: (1) reliably detecting the compute-phase-uncompute structure in a captured gate sequence, (2) implementing the X-H-oracle-H-X phase kickback wrapping pattern that correctly manages an ancilla qubit initialized to |-> state, (3) validating zero ancilla delta by comparing allocator stats before/after oracle execution, and (4) building a cache key that includes the function's source code hash alongside arithmetic_mode and register width.

**Primary recommendation:** Implement `@ql.grover_oracle` as a new Python module `oracle.py` in `src/quantum_language/`, following the same decorator pattern as `compile.py`. The decorator wraps the user's `@ql.compile`-decorated function, performs validation at circuit generation time (first call), and caches validated oracle blocks keyed by `(source_hash, arithmetic_mode, width)`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- @ql.grover_oracle layers on top of @ql.compile -- user writes both decorators, oracle adds validation/wrapping
- Decorator accepts optional parameters (e.g., bit_flip=True, validate=False)
- Oracle function signature takes search register only: `def my_oracle(x: qint)`
- No explicit target qubit parameter -- system handles ancilla internally when needed
- Non-zero ancilla delta is always a hard error -- no warnings, no repair mode
- Compute-phase-uncompute ordering violations produce minimal error messages (short, user reads docs)
- @ql.grover_oracle(validate=False) allows advanced users to bypass validation checks
- User explicitly declares bit-flip oracles via @ql.grover_oracle(bit_flip=True)
- Default is bit_flip=False -- phase oracle assumed unless declared
- When bit_flip=True, system auto-allocates ancilla target qubit initialized to |-> internally
- If bit_flip=True but no bit-flip detected in the oracle circuit, hard error (mismatch)
- Oracle caching is purely internal -- no user-facing API surface
- Cache key includes: oracle function, arithmetic_mode (QFT vs Toffoli), and search register width
- Cache is global/persistent across @ql.compile sessions within the same Python process
- Cache key includes hash of function source code -- redefining an oracle auto-invalidates the cache

### Claude's Discretion
- Validation timing (decoration time vs circuit generation time)
- Compute-phase-uncompute enforcement strategy (post-hoc analysis vs syntax enforcement)
- Exact error message wording
- Ancilla target qubit lifecycle management for bit-flip wrapping
- Cache data structure and eviction policy

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ORCL-01 | User can pass @ql.compile decorated function as oracle to Grover | The `CompiledFunc` class in `compile.py` already returns a callable wrapper. `@ql.grover_oracle` wraps this further, accepting any `CompiledFunc` instance. The oracle decorator validates the inner function is a `CompiledFunc` (or applies `@ql.compile` automatically). |
| ORCL-02 | @ql.grover_oracle decorator enforces compute-then-phase-then-uncompute ordering | Post-hoc gate analysis on the captured gate sequence: partition gates into three segments based on qubit targets (param qubits vs ancilla qubits), detect Z/CZ/MCZ phase gates in the middle segment, verify the third segment is the adjoint of the first. |
| ORCL-03 | Oracle decorator validates ancilla allocation delta is zero on exit | Use `circuit_stats()['current_in_use']` before and after oracle execution. Delta must be zero. Already available via `_core.circuit_stats()`. |
| ORCL-04 | Bit-flip oracles auto-wrapped with phase kickback pattern | When `bit_flip=True`: allocate ancilla qubit, apply X then H (creating |->), run user oracle (which flips ancilla conditionally), apply H then X. This converts bit-flip to phase-flip. Emit gates via `emit_h`, `emit_z` from `_gates.pyx` or directly via `inject_remapped_gates`. |
| ORCL-05 | Oracle cache key includes arithmetic_mode (QFT vs Toffoli) | Read `arithmetic_mode` from circuit struct via `ql.option('fault_tolerant')`. Include in cache key tuple alongside source hash and register width. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `quantum_language.compile` | internal | Gate capture/replay, `CompiledFunc`, `CompiledBlock` | Already implements all capture machinery needed by oracle decorator |
| `quantum_language._core` | internal | `circuit_stats()`, `_allocate_qubit`, `_deallocate_qubits`, `extract_gate_range`, `inject_remapped_gates` | Allocator stats for ancilla delta, qubit management |
| `quantum_language._gates` | internal | `emit_h`, `emit_z`, `emit_ry`, `emit_mcz` | Gate primitives for phase kickback wrapping |
| `inspect` | stdlib | `inspect.getsource()` for function source hashing | Standard Python introspection |
| `hashlib` | stdlib | `hashlib.sha256()` for source code hash | Deterministic hashing for cache keys |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `collections.OrderedDict` | stdlib | LRU-style oracle cache | Same pattern as `CompiledFunc._cache` |
| `functools.update_wrapper` | stdlib | Preserve decorated function metadata | Same pattern as `CompiledFunc.__init__` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Post-hoc gate analysis for CPU | Syntax-level enforcement (require user to call `ql.phase_mark()`) | Post-hoc is more flexible and doesn't change user API; syntax enforcement is simpler but adds API surface |
| `inspect.getsource` hash | `id(func.__code__)` | `getsource` catches redefines across cells/imports; `id` is faster but misses redefines |

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
├── oracle.py          # NEW: @ql.grover_oracle decorator (main deliverable)
├── compile.py         # EXISTING: @ql.compile -- oracle.py imports from here
├── _gates.pyx         # EXISTING: emit_h, emit_z, emit_mcz -- used by kickback wrapping
├── _core.pyx          # EXISTING: circuit_stats, allocator -- used by ancilla validation
└── __init__.py        # MODIFIED: add `from .oracle import grover_oracle`
```

### Pattern 1: Decorator Layering
**What:** `@ql.grover_oracle` wraps a `@ql.compile`-decorated function, adding oracle-specific validation and transformation. The user writes:
```python
@ql.grover_oracle
@ql.compile
def my_oracle(x: qint):
    flag = (x == 5)
    with flag:
        # phase flip happens here via controlled-Z on |->
        pass
```
**When to use:** Always -- this is the locked decision from CONTEXT.md.
**Key implementation detail:** The outer decorator receives a `CompiledFunc` instance (or a plain function, in which case it auto-wraps with `@ql.compile`). On first call, it:
1. Records `circuit_stats()['current_in_use']` (pre-allocation count)
2. Calls the inner `CompiledFunc` (which captures gates)
3. Records `circuit_stats()['current_in_use']` again (post-allocation count)
4. Validates: delta must be zero
5. Analyzes captured gates for compute-phase-uncompute structure
6. Caches the validated block

### Pattern 2: Phase Kickback Auto-Wrapping (bit_flip=True)
**What:** For bit-flip oracles (user sets `bit_flip=True`), the system wraps the user's oracle with the standard phase kickback pattern:
```
1. Allocate ancilla qubit `a`
2. X(a)  -- flip to |1>
3. H(a)  -- create |-> = (|0> - |1>)/sqrt(2)
4. Run user oracle (which should CNOT target `a` conditioned on marking)
5. H(a)  -- convert phase back
6. X(a)  -- restore to |0>
7. Deallocate ancilla `a`
```
**When to use:** When `@ql.grover_oracle(bit_flip=True)` is specified.
**Key insight:** The ancilla `a` starts at |0>, becomes |-> via X+H. When the oracle applies X(a) conditionally, it introduces a phase of -1 on marked states (because X|-> = -|->). After H+X, the ancilla returns to |0> and can be deallocated, leaving zero ancilla delta.

### Pattern 3: Compute-Phase-Uncompute Detection (Post-Hoc Analysis)
**What:** After capturing the oracle's gate sequence, analyze it to detect the three-phase structure:
1. **Compute phase:** Gates on ancilla/temporary qubits (computing the marking predicate)
2. **Phase marking:** Z, CZ, or MCZ gate(s) on the search register qubits
3. **Uncompute phase:** Adjoint of compute phase (cleaning up ancillas)

**Detection strategy (recommended):**
- Extract the captured gate list from the `CompiledBlock`
- Identify all "phase gates" (gate type Z=2, with appropriate control structure)
- The phase gate(s) partition the gate list into `before_phase` and `after_phase`
- Verify `after_phase` is the adjoint of `before_phase` (reversed order, angles negated for rotations)
- This is the same adjoint verification already implemented in `_inverse_gate_list` and `_gates_cancel`

**When to use:** At circuit generation time (first call), not decoration time.

### Pattern 4: Oracle Cache with Source Hash
**What:** Cache validated oracle blocks keyed by `(source_hash, arithmetic_mode, register_width)`.
```python
import hashlib, inspect

def _compute_source_hash(func):
    """Hash the source code of the oracle function."""
    try:
        source = inspect.getsource(func)
        return hashlib.sha256(source.encode()).hexdigest()[:16]
    except (OSError, TypeError):
        # Fallback for functions without inspectable source (lambdas, C extensions)
        return id(func)
```
**Cache key structure:** `(source_hash, arithmetic_mode_int, register_width)`
**Eviction:** Use `collections.OrderedDict` with configurable max size (follow `CompiledFunc` pattern of 128 max).

### Anti-Patterns to Avoid
- **Modifying CompiledFunc internals:** The oracle decorator should NOT monkey-patch or subclass `CompiledFunc`. It wraps it, delegating capture/replay.
- **Validation at decoration time:** Decoration happens before any circuit exists. Validation must happen at first call when gates can be captured and analyzed.
- **Allocating ancilla without deallocating:** The bit-flip wrapping pattern MUST deallocate the ancilla qubit after H+X, otherwise ancilla delta validation will fail.
- **Ignoring controlled context:** If the oracle is called inside a `with qbool:` block, the phase kickback wrapping must propagate the controlled context correctly. The `_gates.pyx` `emit_h` and `emit_z` already handle this.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gate capture/replay | Custom gate recording | `CompiledFunc._capture` + `extract_gate_range` | Already debugged, handles virtual qubit mapping, optimization |
| Adjoint gate generation | Manual gate reversal | `_inverse_gate_list` from `compile.py` | Handles all gate types, rotation angle negation |
| Gate cancellation check | Custom comparison | `_gates_cancel` from `compile.py` | Already handles self-adjoint, rotation, measurement gates |
| Qubit allocation | Manual index tracking | `_allocate_qubit` / `_deallocate_qubits` from `_core.pyx` | Uses the circuit's allocator with proper stats tracking |
| Ancilla delta measurement | Manual qubit counting | `circuit_stats()['current_in_use']` | Allocator already tracks this precisely |
| H/X/Z gate emission | Raw gate_t construction | `emit_h`, `emit_z` from `_gates.pyx` | Already handle controlled context |
| Cache with eviction | Custom dict management | `collections.OrderedDict` with max size | Same pattern as `CompiledFunc._cache` |

**Key insight:** The existing `compile.py` infrastructure does 80% of what oracle needs. The oracle decorator adds validation, wrapping, and source-aware caching -- not gate management.

## Common Pitfalls

### Pitfall 1: Ancilla Delta Off-by-One from Bit-Flip Wrapping
**What goes wrong:** The bit-flip auto-wrapping allocates an ancilla qubit for |-> state, but if deallocation is missed or happens at the wrong time, ancilla delta validation reports non-zero delta.
**Why it happens:** The wrapping sequence is: allocate -> X -> H -> oracle -> H -> X -> deallocate. If the oracle itself allocates/frees ancillas, the "before" snapshot might not capture the correct baseline.
**How to avoid:** Take the `circuit_stats()['current_in_use']` snapshot BEFORE the bit-flip ancilla allocation, and check AFTER bit-flip ancilla deallocation. The wrapping ancilla is invisible to the delta check.
**Warning signs:** Tests with `bit_flip=True` fail ancilla validation even when the user oracle is clean.

### Pitfall 2: Compute-Phase-Uncompute Detection False Positives
**What goes wrong:** The gate analysis incorrectly identifies Z gates that are part of the compute phase (not the marking phase) as the "phase boundary."
**Why it happens:** QFT-based arithmetic uses P (phase) gates internally. Comparison operations may use Z-type gates for intermediate computation.
**How to avoid:** The phase marking gate specifically targets the search register qubits (parameter qubits in virtual space, indices 0..width-1). Compute/uncompute gates target ancilla qubits (virtual indices >= width). Only Z/CZ/MCZ gates whose target is in the parameter qubit range count as phase marking.
**Warning signs:** Phase detection works for simple oracles but fails when oracle uses arithmetic comparisons.

### Pitfall 3: `inspect.getsource` Fails for Lambdas and Dynamic Functions
**What goes wrong:** `inspect.getsource()` raises `OSError` for lambdas defined inline, `exec`-generated functions, or functions defined in interactive sessions without source files.
**Why it happens:** `inspect.getsource` reads the source file from disk, which doesn't exist for dynamically created functions.
**How to avoid:** Fall back to `id(func.__code__)` when `getsource` fails. Document that oracle caching is less reliable for dynamically generated oracles. This is acceptable because the primary use case is `@ql.grover_oracle`-decorated named functions.
**Warning signs:** Cache invalidation doesn't work in Jupyter notebooks or REPL.

### Pitfall 4: Cache Key Missing arithmetic_mode
**What goes wrong:** Oracle cached under QFT mode is replayed when `fault_tolerant=True` (Toffoli mode), producing incorrect circuit.
**Why it happens:** The `@ql.compile` cache already includes `qubit_saving` mode but NOT `arithmetic_mode` directly. The oracle cache must add this.
**How to avoid:** Read `arithmetic_mode` from the circuit struct: `ql.option('fault_tolerant')` returns `True/False`. Include in oracle cache key as `0` or `1`.
**Warning signs:** Switching between QFT and Toffoli modes produces wrong gate counts or incorrect circuits.

### Pitfall 5: Nested Controlled Context in Phase Kickback
**What goes wrong:** When `bit_flip=True` oracle is called inside a `with qbool:` block, the X and H gates for kickback wrapping should NOT be controlled, but the oracle body should be.
**Why it happens:** The wrapping gates (X, H on ancilla) prepare state and are unconditional. The oracle itself runs in whatever context the caller provides.
**How to avoid:** Save and restore the controlled context around the wrapping gates. Apply X and H outside controlled context, then restore for oracle execution.
**Warning signs:** Controlled oracle calls produce extra CX/CH gates on the kickback ancilla.

### Pitfall 6: Bit-Flip Detection (Mismatch Error)
**What goes wrong:** User sets `bit_flip=True` but oracle doesn't actually flip an ancilla qubit, or user sets `bit_flip=False` but oracle does use bit-flip pattern.
**Why it happens:** The user declaration doesn't match the oracle's actual behavior.
**How to avoid:** When `bit_flip=True`, after running the oracle, check that the captured gate sequence contains at least one X or CX gate targeting the kickback ancilla qubit. If no such gate exists, raise a hard error explaining the mismatch.
**Warning signs:** Oracle produces no marking effect despite `bit_flip=True`.

## Code Examples

Verified patterns from project codebase:

### Example 1: Basic Phase Oracle (default bit_flip=False)
```python
# User code:
@ql.grover_oracle
@ql.compile
def mark_five(x: ql.qint):
    """Phase oracle: marks |5> with a -1 phase."""
    flag = (x == 5)       # Compute: creates ancilla qbool
    with flag:             # Phase: controlled-Z on search register
        pass               # (the `with` block applies controlled gates)
    # flag uncomputed automatically by scope exit -> ancilla delta = 0
```

### Example 2: Bit-Flip Oracle with Auto-Wrapping
```python
# User code:
@ql.grover_oracle(bit_flip=True)
@ql.compile
def mark_five_bitflip(x: ql.qint):
    """Bit-flip oracle: flips ancilla when x == 5."""
    flag = (x == 5)
    with flag:
        # This would flip the system-provided ancilla target
        # System wraps with X-H-[oracle]-H-X to convert to phase oracle
        pass
```

### Example 3: Ancilla Delta Validation
```python
# Internal implementation pattern:
from quantum_language._core import circuit_stats

def _validate_ancilla_delta(pre_stats, post_stats):
    """Validate zero ancilla delta. Hard error on violation."""
    pre_use = pre_stats['current_in_use']
    post_use = post_stats['current_in_use']
    delta = post_use - pre_use
    if delta != 0:
        raise ValueError(
            f"Oracle ancilla delta is {delta} (must be 0). "
            f"Ensure all temporary qubits are uncomputed."
        )
```

### Example 4: Oracle Cache Key Construction
```python
# Internal implementation pattern:
import hashlib, inspect

def _oracle_cache_key(func, register_width):
    """Build oracle cache key including source hash and arithmetic_mode."""
    # Source hash
    try:
        source = inspect.getsource(func)
        src_hash = hashlib.sha256(source.encode()).hexdigest()[:16]
    except (OSError, TypeError):
        src_hash = str(id(func.__code__))

    # Arithmetic mode from circuit
    arithmetic_mode = 1 if ql.option('fault_tolerant') else 0

    return (src_hash, arithmetic_mode, register_width)
```

### Example 5: Phase Kickback Wrapping (bit_flip=True)
```python
# Internal implementation pattern (conceptual):
from quantum_language._core import _allocate_qubit, _deallocate_qubits
from quantum_language._gates import emit_h, emit_z

def _wrap_bitflip_oracle(oracle_func, search_register):
    """Wrap bit-flip oracle with X-H-[oracle]-H-X phase kickback."""
    # 1. Allocate ancilla target qubit
    ancilla_q = _allocate_qubit()

    # 2. Prepare |-> state: X then H
    # (emit_z already handles controlled context via _gates.pyx)
    # Use inject_remapped_gates or direct gate emission
    _emit_x_gate(ancilla_q)   # |0> -> |1>
    emit_h(ancilla_q)          # |1> -> |->

    # 3. Run user oracle (which should CNOT the ancilla conditionally)
    oracle_func(search_register)

    # 4. Undo |-> preparation: H then X
    emit_h(ancilla_q)          # |-> -> |1>
    _emit_x_gate(ancilla_q)   # |1> -> |0>

    # 5. Deallocate ancilla (back to |0>, delta = 0)
    _deallocate_qubits(ancilla_q, 1)
```

### Example 6: Decorator Implementation Pattern
```python
# Following compile.py's decorator pattern:
def grover_oracle(func=None, *, bit_flip=False, validate=True):
    """Decorator for Grover oracle functions."""
    def decorator(fn):
        # Auto-wrap with @ql.compile if not already compiled
        if not isinstance(fn, CompiledFunc):
            fn = compile(fn)
        return GroverOracle(fn, bit_flip=bit_flip, validate=validate)

    if func is not None:
        # Called as @ql.grover_oracle (bare)
        if isinstance(func, CompiledFunc):
            return GroverOracle(func, bit_flip=bit_flip, validate=validate)
        return GroverOracle(compile(func), bit_flip=bit_flip, validate=validate)
    return decorator
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual oracle construction | Decorator-based oracle with validation | This phase (77) | Users get automatic validation and wrapping |
| No compile cache awareness of arithmetic mode | Cache key includes arithmetic_mode | This phase (77) | Correct circuit replay across mode switches |

**Deprecated/outdated:**
- N/A -- this is new infrastructure, no predecessor to deprecate

## Open Questions

1. **emit_x gate function availability**
   - What we know: `_gates.pyx` has `emit_h`, `emit_z`, `emit_ry`, `emit_mcz` but NOT `emit_x`. The C backend has `x()` in `gate.h`.
   - What's unclear: Whether to add `emit_x` to `_gates.pyx` or use `inject_remapped_gates` with a manually constructed X gate dict.
   - Recommendation: Add `emit_x` to `_gates.pyx` following the exact pattern of `emit_h` (4 lines). This is cleaner and reusable for Phase 78 diffusion operator.

2. **Bit-flip detection specifics for mismatch error**
   - What we know: User decision says "hard error if bit_flip=True but no bit-flip detected."
   - What's unclear: The exact detection criteria. A bit-flip oracle should have at least one X/CX gate targeting the ancilla qubit.
   - Recommendation: After running the oracle with kickback wrapping, check if any gate in the captured sequence targets the kickback ancilla qubit. If no gate targets it, the oracle didn't interact with the ancilla, so raise error.

3. **Interaction between oracle scoping and existing dependency tracking**
   - What we know: STATE.md flags this: "Phase 77: Interaction between oracle scoping and existing dependency tracking needs design review."
   - What's unclear: Whether the `with flag:` pattern inside an oracle will correctly uncompute the flag qbool when the oracle scope ends, given that the oracle is captured by `@ql.compile`.
   - Recommendation: Test this explicitly. The `@ql.compile` capture already handles `with` blocks (Phase 52 controlled context). The `_do_uncompute` mechanism reverses gate ranges, which should work inside a captured block. Verify with a test that creates a comparison qbool inside an oracle and checks ancilla delta.

4. **Validation bypass scope**
   - What we know: `validate=False` bypasses all validation checks.
   - What's unclear: Should `validate=False` also bypass ancilla delta check, or only the compute-phase-uncompute ordering check?
   - Recommendation: `validate=False` bypasses ALL checks (both ordering and ancilla delta). Advanced users who set this flag take full responsibility. This is the simplest interpretation and matches "bypass validation checks" (plural) from CONTEXT.md.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/compile.py` -- Full `CompiledFunc` implementation, cache key structure, gate capture/replay, adjoint generation
- `src/quantum_language/_core.pyx` -- `circuit_stats()`, `_allocate_qubit`, `_deallocate_qubits`, `option()` for arithmetic_mode
- `src/quantum_language/_gates.pyx` -- Gate emission functions: `emit_h`, `emit_z`, `emit_ry`, `emit_mcz`
- `src/quantum_language/qint.pyx` -- `__enter__`/`__exit__` controlled context, `_do_uncompute`, comparison operators
- `src/quantum_language/qint_comparison.pxi` -- `__eq__`, `__lt__`, `__gt__` comparison implementation details
- `c_backend/include/gate.h` -- C-level gate functions: `x`, `h`, `z`, `cz`, `mcz`
- `c_backend/include/types.h` -- `arithmetic_mode_t` enum, `Standardgate_t` enum

### Secondary (MEDIUM confidence)
- `src/quantum_language/qbool.pyx` -- qbool is 1-bit qint used for oracle flags
- `tests/test_compile.py` -- Test patterns for compiled function behavior
- `tests/python/test_branch_superposition.py` -- Test patterns for Qiskit-verified circuits

### Tertiary (LOW confidence)
- None -- all findings verified from codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All components exist in the codebase, no external dependencies needed
- Architecture: HIGH -- Pattern follows existing `compile.py` decorator infrastructure closely
- Pitfalls: HIGH -- All identified from actual code paths in the codebase
- Compute-phase-uncompute detection: MEDIUM -- The exact gate analysis heuristic needs validation with real oracle circuits during implementation

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (stable -- internal infrastructure, no external dependency drift)
