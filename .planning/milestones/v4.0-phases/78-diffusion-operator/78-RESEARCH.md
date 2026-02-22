# Phase 78: Diffusion Operator - Research

**Researched:** 2026-02-20
**Domain:** Quantum Grover diffusion operator, phase property on quantum registers, Cython class extension
**Confidence:** HIGH

## Summary

Phase 78 introduces two primary features: (1) the `ql.diffusion()` convenience wrapper implementing the Grover diffusion operator using the X-MCZ-X pattern with zero ancilla allocation, and (2) a new `x.phase += theta` property on quantum registers (qint, qbool, qarray) that emits no gate when uncontrolled (global phase is unobservable) but emits CP/MCP gates when inside a controlled (`with`) block. The manual `with x == 0: x.phase += pi` path for S_0 reflection uses existing comparison and controlled-context machinery.

All required infrastructure already exists in the codebase: the C backend has `mcz()`, `p()`, `cp()` gate functions; the Cython `_gates.pyx` already exposes `emit_mcz`, `emit_x`, `emit_z`, `emit_h`; the `@ql.compile` decorator supports caching and controlled-context propagation; and the OpenQASM exporter handles P gates with arbitrary control counts. The main work is: adding `emit_p`/`emit_cp` to `_gates.pyx`, implementing the `phase` property on qint/qbool/qarray, implementing the `ql.diffusion()` function, and writing tests with Qiskit simulation verification.

**Primary recommendation:** Implement `ql.diffusion()` as a `@ql.compile`-decorated function in a new `diffusion.py` module, implement the `phase` property directly in `qint.pyx` (with qbool inheriting automatically and qarray delegating), and add `emit_p`/`emit_cp` to `_gates.pyx` for the phase gate emission.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `ql.diffusion(x)` as top-level convenience wrapper, exported from `ql` namespace
- Internally decorated with `@ql.compile` for gate caching and optimization
- Cache key based on total qubit width (not individual register signatures)
- The convenience wrapper uses the zero-ancilla X-MCZ-X pattern for circuit efficiency
- New syntax `x.phase += theta` applies a global phase; also support `x.phase *= -1` as equivalent to `x.phase += pi`
- `+= theta` is the primary form; `*= -1` supported if both are manageable
- Works on qint, qbool, and qarray
- Uncontrolled: emits NO gate (global phase is unobservable)
- Controlled (inside `with` block): emits CP(theta) / MCP(theta) on the control qubit(s)
- Auto-controlled: follows existing gate propagation pattern
- No warning when used outside `with` block
- Register-agnostic: inside `with x == 0:`, both `x.phase += pi` and `y.phase += pi` have the same effect
- Manual S_0 reflection: `with x == 0: x.phase += pi` using existing comparison semantics
- `ql.diffusion()` accepts qint, qbool, and qarray; multiple registers flatten into one search register
- No overlap validation -- trust the user
- Hard error on zero-width input
- Works inside `with` blocks (controlled diffusion) -- all gates become controlled automatically
- No `.inverse` / `.adjoint` support needed (diffusion is self-adjoint)

### Claude's Discretion
- Internal gate emission strategy for the X-MCZ-X pattern in the convenience wrapper
- How `phase` property is implemented on the Cython qint/qbool/qarray classes
- Test structure and Qiskit simulation verification approach
- Error message wording for invalid inputs

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GROV-03 | Diffusion operator uses X-MCZ-X pattern (zero ancilla, O(n) gates) | `emit_x` and `emit_mcz` already exist in `_gates.pyx`; the X-MCZ-X pattern is 2n X gates + 1 MCZ gate = O(n) total; `@ql.compile` caches the sequence for replay; zero ancilla verified by gate pattern (no allocation needed) |
| GROV-05 | User can manually construct S_0 reflection via `with a == 0` for custom amplitude amplification | Existing `__eq__` comparison (qint == 0) produces a qbool; existing `__enter__`/`__exit__` context manager creates controlled context; new `phase` property emits CP/MCP inside controlled context; the combination `with x == 0: x.phase += pi` produces the S_0 reflection |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language (Cython) | 0.1.0 | qint/qbool/qarray types, circuit infrastructure | Project's own Cython-based quantum type system |
| c_backend (C) | N/A | Low-level gate emission (gate.h/gate.c) | Already has mcz(), p(), cp() functions |
| compile.py | N/A | @ql.compile decorator for gate caching | Existing infrastructure for compiled quantum functions |
| _gates.pyx | N/A | Cython gate emitters (emit_x, emit_mcz, etc.) | Already exposes the needed gate primitives |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qiskit | 1.x | Simulation verification via QASM import | Testing: verify diffusion operator correctness |
| qiskit-aer | 0.15+ | AerSimulator for statevector/counts | Testing: simulation of exported QASM circuits |
| pytest | 7+ | Test framework | Test execution |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@ql.compile` internal caching | Direct gate emission every call | Loss of optimization and replay; compile is the standard pattern |
| Separate diffusion.py module | Inline in __init__.py | Module separation is cleaner; follows oracle.py pattern |
| Phase property on Cython class | Standalone function `ql.phase_flip(x, theta)` | Property syntax `x.phase += pi` is more natural; user decision locked |

## Architecture Patterns

### Recommended Project Structure
```
src/quantum_language/
├── _gates.pyx          # Add emit_p(), emit_cp() (extend existing)
├── _gates.pxd          # Add p(), cp() C declarations (extend existing)
├── qint.pyx            # Add phase property (extend existing)
├── qint.pxd            # No changes needed (phase is Python-level property)
├── qarray.pyx          # Add phase property delegation (extend existing)
├── diffusion.py        # NEW: ql.diffusion() implementation
├── __init__.py         # Add diffusion import and export
└── ...
```

### Pattern 1: Phase Property Implementation
**What:** A Python property on `qint` that returns a `PhaseProxy` object supporting `+=` and `*=` operators.
**When to use:** When `x.phase += theta` or `x.phase *= -1` is written by the user.
**Example:**
```python
# In qint.pyx (Python-level, not cdef)
class _PhaseProxy:
    """Proxy object returned by qint.phase property.

    Supports += theta (phase shift) and *= -1 (phase flip).
    When uncontrolled: emits no gate (global phase).
    When controlled: emits CP(theta) on the control qubit.
    """
    def __init__(self, owner):
        self._owner = owner

    def __iadd__(self, theta):
        # Check controlled context
        if _get_controlled():
            ctrl = _get_control_bool()
            # Emit CP(theta) targeting the control qubit itself
            # (register-agnostic: it's a global phase, only the control matters)
            emit_cp(ctrl.qubits[63], theta)  # or emit_p on ctrl with controls
        # Uncontrolled: no gate (global phase is unobservable)
        return self

    def __imul__(self, factor):
        if factor == -1:
            return self.__iadd__(math.pi)
        raise ValueError("phase *= only supports -1")

@property
def phase(self):
    return _PhaseProxy(self)
```
**Key insight:** `x.phase += theta` returns the proxy (not `self`), so Python's `+=` semantics work correctly. The proxy must return itself from `__iadd__` so `x.phase` continues to point to a valid proxy.

**CRITICAL DETAIL:** Because Python's `x.phase += theta` desugars to `x.phase = x.phase.__iadd__(theta)`, and `x.phase` is a read-only property (no setter), Python will raise `AttributeError: can't set attribute`. This requires EITHER: (a) adding a dummy setter that accepts any value (swallows the re-assignment), or (b) implementing `__iadd__` to return `self` and relying on the property setter being silently ignored. The recommended approach is **(a) add a no-op setter**.

### Pattern 2: X-MCZ-X Diffusion Pattern
**What:** The standard zero-ancilla Grover diffusion operator.
**When to use:** `ql.diffusion(x)` call.
**Example:**
```python
# In diffusion.py
@ql.compile(key=lambda *args: sum(_get_quantum_arg_width(a) for a in args))
def diffusion(*registers):
    """Apply Grover diffusion operator (X-MCZ-X pattern).

    Flattens all register qubits, applies X to all, MCZ on all, X to all.
    Zero ancilla, O(n) gates.
    """
    # Collect all qubit indices from all registers
    qubits = []
    for reg in registers:
        if isinstance(reg, qarray):
            for elem in reg:
                qubits.extend(_get_qubit_indices(elem))
        else:
            qubits.extend(_get_qubit_indices(reg))

    if not qubits:
        raise ValueError("diffusion() requires at least one qubit")

    # X on all qubits
    for q in qubits:
        emit_x(q)

    # MCZ: Z on last qubit, controlled by all others
    if len(qubits) == 1:
        emit_z(qubits[0])
    else:
        emit_mcz(qubits[-1], qubits[:-1])

    # X on all qubits
    for q in qubits:
        emit_x(q)
```

**Key insight:** The X-MCZ-X pattern reflects about |0...0>: X maps |0> to |1>, MCZ flips sign of |1...1> (all-ones), X maps back. Net effect: phase flip on |0...0>, which is the S_0 reflection used in Grover's algorithm.

### Pattern 3: Compile Integration with Custom Key
**What:** Using `@ql.compile(key=...)` with a custom cache key based on total qubit width.
**When to use:** When the compiled function needs width-based caching regardless of register structure.
**Example:**
```python
# Cache key based on total qubit count across all args
@ql.compile(key=lambda *args: _total_width(*args))
def diffusion(*args):
    ...
```
**NOTE:** The `@ql.compile` decorator's `_classify_args` currently separates quantum and classical args. The diffusion function takes only quantum args, so the default key (classical_args=(), widths) would work too. However, a custom key based on total width is simpler when multiple registers combine.

**IMPORTANT COMPILE CAVEAT:** The current `CompiledFunc._classify_args` iterates over `args` and separates quantum/classical. For `*args` variadic quantum arguments, ALL args will be classified as quantum. The key function receives the original `(args, kwargs)` though -- need to verify the key function signature compatibility. Looking at compile.py line 606: `self._key_func(*args, **kwargs)` -- so the key function receives the same positional args. This works.

### Anti-Patterns to Avoid
- **Allocating ancilla in diffusion:** The X-MCZ-X pattern requires ZERO ancilla. Do not use the comparison-based path (`x == 0`) inside the optimized diffusion wrapper -- that path uses ancilla for the comparison result qbool.
- **Phase property emitting gates when uncontrolled:** Global phase is physically unobservable. Emitting a P gate when not inside a `with` block would waste gate budget for zero effect.
- **Implementing phase as a cdef attribute:** The `phase` property needs Python-level `__iadd__`/`__imul__` support, which requires a Python proxy object. Don't try to make this a cdef-level attribute.
- **Testing phase property outside `with` block for gate effects:** Since uncontrolled phase emits nothing, don't test for gate emission. Instead verify no gates are added.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-controlled Z gate | Custom MCX-based decomposition | `emit_mcz()` from `_gates.pyx` | C backend handles decomposition; mcz() supports arbitrary control count |
| Gate caching for diffusion | Custom cache dict | `@ql.compile` decorator | Already handles capture/replay, controlled derivation, cache eviction |
| Controlled context propagation | Manual control qubit management | Existing `_get_controlled()` / `_get_control_bool()` | `emit_x()` and `emit_mcz()` already auto-add control qubit when inside `with` block |
| Phase gate emission | Raw C-level gate construction | New `emit_p()` / `emit_cp()` in `_gates.pyx` | Follow existing pattern of emit_x, emit_h, emit_z |
| QASM export of P/CP gates | Custom QASM generation | Existing `circuit_output.c` | Already handles P gates with 0, 1, 2, and n controls in QASM export |

**Key insight:** The project already has all the low-level gate infrastructure. This phase is primarily about composing existing primitives into a higher-level API and adding the `phase` property syntax.

## Common Pitfalls

### Pitfall 1: Python Property `+=` Semantics
**What goes wrong:** `x.phase += theta` desugars to `x.phase = x.phase.__iadd__(theta)`. If `phase` is a read-only property (getter only), the re-assignment `x.phase = ...` raises `AttributeError`.
**Why it happens:** Python's augmented assignment always does the re-assignment, even for `__iadd__`.
**How to avoid:** Add a no-op setter on the `phase` property that silently discards the assignment. The actual work happens in `__iadd__`.
**Warning signs:** `AttributeError: can't set attribute` at runtime.

### Pitfall 2: PhaseProxy Lifetime
**What goes wrong:** The `_PhaseProxy` object returned by `x.phase` holds a reference to `x`. If the proxy outlives the register, use-after-uncompute could occur.
**Why it happens:** Python allows `p = x.phase; del x; p += pi`.
**How to avoid:** The proxy should check `_is_uncomputed` before emitting gates, following the existing `_check_not_uncomputed()` pattern. However, since the phase is register-agnostic (it only interacts with the control qubit in controlled context), this is a minor concern. A simple check is sufficient.
**Warning signs:** Gate emission referencing deallocated qubits.

### Pitfall 3: MCZ Control Qubit Ordering
**What goes wrong:** MCZ in the C backend expects target + controls. If the wrong qubit is designated as "target" vs "control", the gate semantics change (though for MCZ, the choice of target among the n qubits is arbitrary since MCZ is symmetric).
**Why it happens:** MCZ applies Z to target controlled by all controls. Mathematically, MCZ is symmetric in all qubits (it flips the sign of |1...1> regardless of which qubit is "target"). But the QASM export may render differently.
**How to avoid:** Consistently designate the last qubit as target and all others as controls (matching the existing `emit_mcz` API pattern).
**Warning signs:** QASM output looking different than expected (but functionally equivalent).

### Pitfall 4: Compile Key for Variable-Arity diffusion
**What goes wrong:** The default `@ql.compile` cache key includes `widths` tuple, which varies based on how many registers are passed. `diffusion(x)` vs `diffusion(x, y)` would create different cache entries even if total width is the same.
**Why it happens:** Default key function uses per-argument widths.
**How to avoid:** Use a custom `key=` function that computes total qubit width across all arguments: `key=lambda *args: sum(get_width(a) for a in args)`.
**Warning signs:** Cache misses when calling `diffusion(x, y)` after `diffusion(z)` with same total width.

### Pitfall 5: Controlled Diffusion Gate Propagation
**What goes wrong:** When `diffusion(x)` is called inside `with flag:`, all gates must become controlled. If `emit_x` and `emit_mcz` already handle controlled context, this works automatically. But the MCZ becoming CMCZ adds one more control.
**Why it happens:** `emit_x` checks `_get_controlled()` and emits CX. `emit_mcz` does NOT currently check `_get_controlled()` -- it emits the MCZ as-is.
**How to avoid:** Either (a) modify `emit_mcz` to auto-add control qubit from context (like `emit_x` does), or (b) rely on `@ql.compile`'s controlled variant derivation which adds control to all gates at the virtual level. Since `diffusion` is `@ql.compile`-decorated, option (b) works automatically -- the compile infrastructure adds control qubits during `_derive_controlled_block`.
**Warning signs:** Diffusion gates not being controlled when called inside `with` block, if not using `@ql.compile`.

### Pitfall 6: Cython Class Property in cdef Class
**What goes wrong:** Adding a Python property to a `cdef class` requires specific syntax in Cython. The property must be defined in the `.pyx` file, not the `.pxd` file.
**Why it happens:** Cython's `cdef class` has restrictions on property declarations.
**How to avoid:** Define the `phase` property as a regular Python `@property` in the `.pyx` file (already the pattern used for `width` property in qint.pyx). No `.pxd` changes needed.
**Warning signs:** Cython compilation errors if attempting to declare property in `.pxd`.

### Pitfall 7: emit_cp for Phase Property -- MCP with Multiple Controls
**What goes wrong:** Inside nested `with` blocks (`with a: with b: x.phase += pi`), there may be multiple control qubits. The current controlled context only tracks a single `_control_bool`, not a list.
**Why it happens:** The `__enter__`/`__exit__` context manager system collapses multiple controls into a single AND-reduced qbool via `_control_bool &= self`.
**How to avoid:** The single `_control_bool` already represents the AND of all nested controls. Emitting CP targeting this single control qbool is correct. No special handling for nested controls needed.
**Warning signs:** Incorrect behavior with nested `with` blocks.

## Code Examples

### Example 1: X-MCZ-X Diffusion Operator Circuit
```
For n=3 qubits (q0, q1, q2):

X q0; X q1; X q2;     -- Flip all qubits
ctrl(2) @ z q0, q1, q2; -- MCZ: flip sign of |111> (which maps from |000>)
X q0; X q1; X q2;     -- Flip back

Net effect: phase flip on |000> state only = S_0 reflection
```
Source: Standard Grover's algorithm textbook pattern (Nielsen & Chuang, Chapter 6)

### Example 2: Manual S_0 via `with x == 0: x.phase += pi`
```python
# User code for manual amplitude amplification
x = ql.qint(0, width=3)
x.branch()  # Equal superposition

# Apply oracle (marks |5>)
oracle(x)

# Manual diffusion: first reflect about |0>
with x == 0:
    x.phase += pi  # S_0 reflection

# Then branch again for full diffusion
x.branch()

# This is functionally equivalent to:
# ql.diffusion(x)
# (but the manual path uses ancilla for the comparison)
```

### Example 3: emit_p / emit_cp Implementation Pattern
```python
# In _gates.pyx (following existing emit_ry pattern)
cpdef void emit_p(unsigned int target, double angle):
    """Emit P(angle) gate to circuit."""
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
    memset(&g, 0, sizeof(gate_t))
    if _get_controlled():
        ctrl = _get_control_bool()
        cp(&g, target, ctrl.qubits[63], angle)
    else:
        p(&g, target, angle)
    add_gate(circ, &g)

cpdef void emit_cp(unsigned int target, unsigned int control, double angle):
    """Emit CP(angle) gate (explicit control, no auto-control context)."""
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()
    memset(&g, 0, sizeof(gate_t))
    cp(&g, target, control, angle)
    add_gate(circ, &g)
```

### Example 4: PhaseProxy with No-op Setter
```python
class _PhaseProxy:
    __slots__ = ('_owner',)

    def __init__(self, owner):
        self._owner = owner

    def __iadd__(self, double theta):
        import math
        if _get_controlled():
            ctrl = _get_control_bool()
            # Register-agnostic: emit CP on control qubit
            # The "target" is arbitrary for global phase -- use control qubit itself
            emit_p(ctrl.qubits[63], theta)  # P on ctrl = CP from outer context
        # Uncontrolled: no gate (global phase)
        return self

    def __imul__(self, factor):
        import math
        if factor == -1:
            return self.__iadd__(math.pi)
        raise ValueError("phase *= only supports -1")

# In qint class:
@property
def phase(self):
    return _PhaseProxy(self)

@phase.setter
def phase(self, value):
    pass  # No-op: absorbs x.phase = proxy re-assignment from +=
```

### Example 5: Qiskit Verification Pattern for Diffusion
```python
def test_diffusion_3qubit():
    """Verify diffusion operator flips sign of |000> via Qiskit simulation."""
    ql.circuit()
    x = ql.qint(0, width=3)
    x.branch()  # Equal superposition
    ql.diffusion(x)

    qasm = ql.to_openqasm()
    # Import into Qiskit, get statevector
    circuit = qiskit.qasm3.loads(qasm)
    sim = AerSimulator(method='statevector')
    circuit.save_statevector()
    result = sim.run(transpile(circuit, sim)).result()
    sv = result.get_statevector()

    # After H-diffusion-H on |0>, state should concentrate on |0>
    # (One iteration of Grover without oracle = just diffusion = reflects about mean)
    # Verify amplitudes have expected structure
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| H-X-MCZ-X-H diffusion | X-MCZ-X diffusion (H is part of branch/superposition, not diffusion) | Project design decision | Separates superposition creation from reflection; cleaner abstraction |
| Ancilla-based multi-controlled gates | Zero-ancilla MCZ via C backend | Phase 66+ | MCZ in gate.c handles arbitrary control count directly |

**Note:** The project separates `branch()` (Ry rotation for superposition) from `diffusion()` (reflection about mean). The classical textbook Grover diffusion includes Hadamards, but this project's diffusion is purely the S_0 reflection (X-MCZ-X), with the superposition creation handled separately by `branch()`. The full Grover iteration is: oracle -> branch -> diffusion -> branch (or equivalently, oracle -> H -> S_0 -> H where S_0 = X-MCZ-X).

**CORRECTION:** Re-reading the CONTEXT.md more carefully, `ql.diffusion(x)` is the complete diffusion operator. The X-MCZ-X pattern IS the standard S_0 reflection, which combined with the initial superposition state gives the full diffusion operator D = 2|psi><psi| - I. The standard decomposition is: D = H^n * (2|0><0| - I) * H^n = H^n * S_0 * H^n. So the diffusion wrapper should include the branch() (H) calls too -- OR -- the X-MCZ-X alone IS the complete diffusion when the initial state preparation is understood to be separate. Looking at the success criteria: "Diffusion operator uses X-MCZ-X pattern with zero ancilla allocation" -- this confirms X-MCZ-X is the full scope of the diffusion wrapper. The user applies branch() before and after as needed, or the higher-level `ql.grover()` (Phase 79) handles the full iteration.

**WAIT -- re-reading again:** The X-MCZ-X pattern reflects about |0...0> state. The full Grover diffusion operator D = 2|s><s| - I (where |s> is uniform superposition) is decomposed as H^n * (2|0><0| - I) * H^n. The (2|0><0| - I) part is the "S_0 reflection" which is exactly X-MCZ-X (up to global phase). So `ql.diffusion(x)` = X-MCZ-X = S_0 reflection. The Hadamard/branch sandwiching is done at the Grover iteration level (Phase 79).

## Open Questions

1. **PhaseProxy defined in Cython or Python?**
   - What we know: qint is a `cdef class` in Cython. Properties can be Python-level within `cdef class` (like `width`). The `_PhaseProxy` class can be a plain Python class.
   - What's unclear: Whether `_PhaseProxy` should be defined inside `qint.pyx` or in a separate Python module.
   - Recommendation: Define `_PhaseProxy` as a Python class at module level in `qint.pyx` (before the `cdef class qint` definition). This keeps it close to the `phase` property and avoids circular imports.

2. **emit_p inside controlled context for phase property**
   - What we know: `x.phase += theta` inside `with flag:` should emit CP(theta). The "target" is somewhat arbitrary since it's a global phase.
   - What's unclear: Which qubit to designate as "target" for the CP gate when the phase is register-agnostic.
   - Recommendation: Use `emit_p(ctrl.qubits[63], theta)` which auto-adds control from context. This makes the control qubit serve as both control and implicit target reference. Alternatively, emit P on any qubit of the register -- but since the phase is global, the simplest approach is to target the control qubit and let the context add the control.
   - **Refined answer:** Actually, for `x.phase += theta` inside `with flag:`, we want CP(theta) with `flag` as control. The most natural implementation: call `emit_p(some_qubit, theta)` where `some_qubit` is any qubit from x. Since `emit_p` auto-adds the control from context, this becomes CP(theta) ctrl=flag, target=some_qubit. This is equivalent to a controlled global phase. Any qubit works, but using x's first qubit is cleanest.
   - **FINAL ANSWER:** Re-reading the CONTEXT.md: "Register-agnostic: inside `with x == 0:`, both `x.phase += pi` and `y.phase += pi` have the same effect (controlled global phase)." This means the target qubit doesn't matter -- it's just a vehicle for the controlled phase. Use any qubit (e.g., owner's first qubit, or the control qubit itself).

3. **Does `emit_mcz` need to handle controlled context?**
   - What we know: `emit_x`, `emit_ry`, `emit_h`, `emit_z` all check `_get_controlled()` and auto-add control. `emit_mcz` currently does NOT.
   - What's unclear: Whether diffusion inside `with` block needs emit_mcz to be context-aware.
   - Recommendation: Since `ql.diffusion` is `@ql.compile`-decorated, the compile infrastructure handles controlled derivation at the virtual gate level (adding control qubit to all cached gates). So `emit_mcz` does NOT need to be modified. The compile replay path handles this correctly.

## Sources

### Primary (HIGH confidence)
- `src/quantum_language/_gates.pyx` -- Existing emit_x, emit_mcz, emit_h, emit_z implementations verified
- `src/quantum_language/_gates.pxd` -- Cython declarations for C gate functions
- `c_backend/include/gate.h` -- C declarations for p(), cp(), mcz() verified
- `c_backend/src/gate.c` -- C implementations of mcz(), p(), cp() verified
- `src/quantum_language/compile.py` -- Full @ql.compile infrastructure verified (capture, replay, controlled derivation, custom key)
- `src/quantum_language/qint.pyx` -- Cython cdef class with property pattern (width property at line 310)
- `src/quantum_language/qint_comparison.pxi` -- __eq__ implementation for `x == 0` path verified
- `c_backend/src/circuit_output.c` -- QASM export handles P gates with 0-n controls verified

### Secondary (MEDIUM confidence)
- Standard Grover's algorithm: X-MCZ-X = S_0 reflection (textbook pattern, widely documented)
- Python `+=` desugaring for properties: confirmed behavior in CPython docs

### Tertiary (LOW confidence)
- None -- all findings verified from codebase source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components verified in codebase source
- Architecture: HIGH -- patterns follow existing compile.py and oracle.py conventions
- Pitfalls: HIGH -- identified from direct code analysis of Cython class patterns and Python property semantics

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (stable internal architecture)
