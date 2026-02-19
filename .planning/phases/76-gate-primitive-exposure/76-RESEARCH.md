# Phase 76: Gate Primitive Exposure - Research

**Researched:** 2026-02-19
**Domain:** Quantum gate primitives, Ry rotations, multi-controlled gates
**Confidence:** HIGH

## Summary

This phase exposes Hadamard-equivalent functionality via an Ry rotation-based `branch(probability)` method on qint/qbool, and provides internal gate primitives (H, Z, MCZ) needed for Grover's diffusion operator in Phase 78. The codebase already has substantial infrastructure for all required gates:

- **Ry gate type exists** in `types.h` (`Standardgate_t` enum includes `Ry`) and is already supported in OpenQASM export (`circuit_output.c` handles Ry with full precision)
- **H and Z gates exist** with C implementations in `gate.c` including controlled variants (ch via cy analog, cz exists)
- **MCX decomposition infrastructure** provides a pattern for MCZ implementation using AND-ancilla decomposition (`IntegerComparison.c`)
- **`@ql.compile` integration** is straightforward since the compile decorator already captures all gate types

**Primary recommendation:** Implement `branch(probability)` as a new method on qint/qbool that emits Ry gates, using probability-to-angle conversion `theta = 2 * arcsin(sqrt(probability))`. Create new `_gates.pyx` module for internal H/Z/MCZ functions. Implement MCZ using the existing AND-ancilla decomposition pattern.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Parameter semantics:** theta is probability (0 to 1), not radians - 0.5 for equal superposition
- **Default argument:** `branch()` defaults to 0.5 (equal superposition)
- **Return value:** None (mutation, no chaining)
- **Multi-qubit behavior:** `x.branch(0.5)` applies same Ry(theta) to all qubits in qint
- **Single qubit via indexing:** `x[0].branch(0.3)` applies to just that qubit (returns qbool)
- **Invalid probability:** Raise ValueError if outside [0, 1]
- **Edge cases (0, 1):** Allow silently (valid edge case, no special handling)
- **Naming:** Only `branch()`, no aliases like `superpose()`
- **@ql.compile support:** Full support - works both directly and inside compiled functions
- **Existing state:** Just applies Ry gate regardless of current state (no reset, no error)
- **Multiple calls:** Gates accumulate (each branch() adds another Ry rotation)
- **Indexed qbool:** `x[0].branch(0.5)` works the same (affects just that qubit)
- **Ancilla qubits:** Allow branch() on ancilla - user's responsibility
- **Auto-inverse:** Yes - inverse branch() is Ry(-theta), tracked for uncomputation
- **Mid-circuit measurement:** Allow branch() anywhere, even post-measurement
- **qarray elements:** Works on qarray elements (`arr[i].branch(0.5)`)
- **Public API:** H and Z are internal-only, not exposed as public ql.H/ql.Z
- **Module location:** New private `_gates` module (pyx) with H, Z, Ry implementations
- **Backend:** C backend - add H/Z/Ry to existing C instruction set
- **MCZ:** Implement in this phase (76) as foundation for Phase 78 diffusion
- **MCZ ancilla:** Allow ancilla for O(n) gates if beneficial
- **Circuit trace:** Internal gates visible in visualization and QASM export
- **Controlled variants:** Implement CH, CZ, CRy (all controlled variants)
- **Arithmetic mode:** Unified/mode-agnostic - gates work the same regardless of arithmetic_mode
- **Internal tests:** Qiskit tests via pytest that export to QASM and verify via Qiskit Aer
- **Tolerance:** Relaxed (1e-6) for floating point differences
- **Test widths:** All widths 1-8 (comprehensive coverage)
- **Inverse test:** Verify branch() + inverse restores original state
- **MCZ tests:** Test MCZ independently in this phase (not just via diffusion)
- **Controlled tests:** Test all variants (CH, CZ, CRy) with Qiskit verification
- **Compile context:** Test branch() both direct and inside @ql.compile
- **Test location:** tests/python/ with existing Python tests

### Claude's Discretion
- Exact Ry angle calculation from probability (arcsin-based)
- Internal _gates module organization and file structure
- C backend instruction encoding for new gates
- MCZ decomposition strategy (V-chain, Toffoli ladder, etc.)
- Test file naming and organization within tests/python/

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRIM-01 | User can apply Ry rotation via `qint.branch(theta)` method on all qubits | Ry gate type exists in C backend; method adds Ry to each qubit in right-aligned qubits array |
| PRIM-02 | User can apply Ry rotation via `qbool.branch(theta)` method | qbool inherits from qint with width=1; single qubit at qubits[63] |
| PRIM-03 | `branch(pi/2)` creates equal superposition (Hadamard-equivalent) | Ry(pi/2) = equal superposition when probability=0.5; theta = 2*arcsin(sqrt(0.5)) = pi/2 |
</phase_requirements>

## Existing Infrastructure Analysis

### Gate Type System (types.h)

The `Standardgate_t` enum already includes all needed gate types:
```c
typedef enum { X, Y, Z, R, H, Rx, Ry, Rz, P, M, T_GATE, TDG_GATE } Standardgate_t;
```

**Key insight:** Ry (index 6) is already defined. No enum extension needed.

### Gate Creation Functions (gate.c)

Existing gate creation functions provide the pattern:
```c
void h(gate_t *g, qubit_t target);           // H gate
void z(gate_t *g, qubit_t target);           // Z gate
void cz(gate_t *g, qubit_t target, qubit_t control);  // Controlled-Z
void y(gate_t *g, qubit_t target);           // Y gate
void cy(gate_t *g, qubit_t target, qubit_t control);  // Controlled-Y
```

**Missing:** `ry()`, `cry()` functions for Ry gate creation. Pattern is clear from existing implementations.

### OpenQASM Export (circuit_output.c)

Ry is already fully supported in QASM export:
```c
case Ry:
    written = sprintf(buffer + offset, "ry(%.17g) q[%d];\n", normalize_angle(g->GateValue), g->Target);
// Controlled variant:
case Ry:
    written = sprintf(buffer + offset, "cry(%.17g) q[%d], q[%d];\n", ...);
```

**Full precision preserved** via `%.17g` format specifier.

### Circuit Visualization (circuit_output.c)

Ry case exists but needs label:
```c
case Ry:
    break;  // Currently empty - need to add "Y" or "Ry" label
```

**Action needed:** Add print statement for Ry visualization.

### MCX Decomposition Pattern (IntegerComparison.c)

The AND-ancilla decomposition pattern is already implemented for MCX:
```c
static void emit_mcx_decomp_seq(sequence_t *seq, int *layer, int target,
    const qubit_t *controls, int num_controls, int anc_start) {
    if (num_controls == 2) {
        ccx(&seq->seq[*layer][...], target, controls[0], controls[1]);
    } else if (num_controls == 3) {
        // AND-ancilla pattern: compute -> apply -> uncompute
        ccx(..., and_anc, controls[0], controls[1]);  // compute
        ccx(..., target, and_anc, controls[2]);       // apply
        ccx(..., and_anc, controls[0], controls[1]);  // uncompute
    } else {
        // Recursive decomposition
    }
}
```

**MCZ follows same pattern:** Replace CCX target gates with CZ gates.

### Instruction Execution (execution.c)

The `run_instruction()` function processes sequences and adds gates to circuit. This is the main integration point for Python-to-C gate emission.

### qint Qubit Layout

Right-aligned qubit storage in qint:
```python
# qint.qubits[64-width : 64] contains the allocated qubit indices
# For 4-bit qint: qubits[60], qubits[61], qubits[62], qubits[63]
# Index 0 (LSB) is at qubits[64-width], MSB at qubits[63]
```

**For branch():** Iterate `for i in range(self.bits)` and access `self.qubits[64 - self.bits + i]`.

### @ql.compile Integration (compile.py)

The compile decorator captures gates via `extract_gate_range()` and replays via `inject_remapped_gates()`. Gate type constants include Ry:
```python
_X, _Y, _Z, _R, _H, _Rx, _Ry, _Rz, _P, _M = range(10)
_ROTATION_GATES = frozenset({_P, _Rx, _Ry, _Rz, _R})
```

**Ry already in `_ROTATION_GATES`** - adjoint (angle negation) handled automatically.

## Architecture Patterns

### Recommended Implementation Structure

```
src/quantum_language/
├── _gates.pyx           # NEW: Internal gate primitives
├── _gates.pxd           # NEW: Cython declarations
├── qint.pyx             # Add branch() method
├── qint_bitwise.pxi     # Contains __getitem__ for indexed qbool
└── qbool.pyx            # Inherits branch() from qint (width=1)

c_backend/
├── include/
│   └── gate.h           # Add ry(), cry(), mcz() declarations
└── src/
    └── gate.c           # Add ry(), cry(), mcz() implementations
```

### Pattern 1: Ry Gate Creation (C Backend)

**What:** Create Ry gate with angle parameter following existing gate pattern
**When to use:** All Ry gate emissions from Python

```c
// Add to gate.h and gate.c
void ry(gate_t *g, qubit_t target, double angle) {
    g->Gate = Ry;
    g->Target = target;
    g->GateValue = angle;
    g->NumControls = 0;
    g->large_control = NULL;
}

void cry(gate_t *g, qubit_t target, qubit_t control, double angle) {
    g->Gate = Ry;
    g->Target = target;
    g->GateValue = angle;
    g->NumControls = 1;
    g->Control[0] = control;
    g->large_control = NULL;
}
```

### Pattern 2: MCZ Decomposition

**What:** Multi-controlled Z using H-MCX-H pattern
**When to use:** MCZ with 3+ controls

```
MCZ(target, controls) = H(target) . MCX(target, controls) . H(target)
```

Alternatively, direct CZ decomposition following AND-ancilla pattern:
- MCZ(2 controls) = CCZ = single gate (native)
- MCZ(3+ controls) = AND-ancilla decomposition with CZ instead of CCX

**Recommendation:** Use H-MCX-H since MCX decomposition already exists and is well-tested.

### Pattern 3: Probability to Angle Conversion

**What:** Convert probability [0,1] to Ry rotation angle
**Formula derivation:**

For Ry(theta) applied to |0>:
```
|psi> = cos(theta/2)|0> + sin(theta/2)|1>
P(|1>) = sin^2(theta/2) = probability
theta/2 = arcsin(sqrt(probability))
theta = 2 * arcsin(sqrt(probability))
```

**Implementation:**
```python
import math

def probability_to_angle(prob: float) -> float:
    """Convert probability [0,1] to Ry angle in radians."""
    if not 0.0 <= prob <= 1.0:
        raise ValueError(f"Probability must be in [0, 1], got {prob}")
    return 2.0 * math.asin(math.sqrt(prob))
```

**Edge cases:**
- `prob=0` -> `theta=0` (no rotation, stays |0>)
- `prob=0.5` -> `theta=pi/2` (equal superposition)
- `prob=1` -> `theta=pi` (full flip to |1>)

### Pattern 4: Sequence Generation for Single Gate

**What:** Generate sequence_t for a single gate
**When to use:** Python emitting individual gates via `run_instruction()`

```c
// Pattern from Q_not in bitwise_ops.c
sequence_t *Ry_gate(double angle) {
    sequence_t *seq = malloc(sizeof(sequence_t));
    seq->num_layer = 1;
    seq->used_layer = 1;
    seq->gates_per_layer = calloc(1, sizeof(num_t));
    seq->gates_per_layer[0] = 1;
    seq->seq = calloc(1, sizeof(gate_t *));
    seq->seq[0] = calloc(1, sizeof(gate_t));
    ry(&seq->seq[0][0], 0, angle);  // target=0, remapped by run_instruction
    return seq;
}
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCX decomposition | Custom MCZ decomposition | H-MCX-H pattern | MCX decomposition already tested, handles all control counts |
| Gate inverse tracking | Manual inverse flag | `_ROTATION_GATES` in compile.py | Adjoint derivation already handles angle negation |
| Qubit index mapping | Direct qubit access | `run_instruction()` with qubit array | Handles controlled context, circuit integration |
| Gate serialization | Custom QASM generation | Existing `circuit_output.c` | Ry already supported with full precision |

**Key insight:** The codebase already has all the building blocks. Phase 76 is primarily about assembly and exposure, not new algorithms.

## Common Pitfalls

### Pitfall 1: Wrong Qubit Indexing for qint.branch()
**What goes wrong:** Iterating over wrong qubit indices
**Why it happens:** qint uses right-aligned storage (qubits[64-width:64])
**How to avoid:** Use `self.qubits[64 - self.bits + i]` for bit `i`
**Warning signs:** Tests fail with width > 1 but pass for qbool

### Pitfall 2: Angle Precision Loss
**What goes wrong:** Ry angle stored with insufficient precision
**Why it happens:** Using float32 or truncating in string conversion
**How to avoid:** Use `double` in C, `%.17g` in QASM export (already done)
**Warning signs:** Qiskit verification fails with probability mismatches

### Pitfall 3: Missing Controlled Context
**What goes wrong:** branch() inside `with` block doesn't apply control
**Why it happens:** Not using `_get_controlled()` / `_get_control_bool()` checks
**How to avoid:** Follow pattern from existing qint operations (e.g., `__iadd__`)
**Warning signs:** Controlled operations don't become CRy gates

### Pitfall 4: MCZ Gate Count Explosion
**What goes wrong:** MCZ(n) produces O(2^n) gates
**Why it happens:** Naive decomposition without AND-ancilla pattern
**How to avoid:** Use H-MCX-H with existing MCX decomposition (O(n) CCX gates)
**Warning signs:** Gate count grows exponentially with control count

### Pitfall 5: Inverse Not Tracked for Uncomputation
**What goes wrong:** branch() doesn't uncompute correctly
**Why it happens:** Missing layer tracking (_start_layer, _end_layer)
**How to avoid:** Follow pattern from qint operations that support uncomputation
**Warning signs:** Scope exit doesn't reverse branch() effects

## Code Examples

### branch() Method Implementation (qint)

```python
# In qint.pyx (or qint_bitwise.pxi)
def branch(self, prob=0.5):
    """Apply Ry rotation to create superposition.

    Parameters
    ----------
    prob : float, optional
        Probability of |1> state (default 0.5 for equal superposition).
        Must be in range [0, 1].

    Returns
    -------
    None
        Mutates self; does not return new qint.

    Examples
    --------
    >>> x = qint(0, width=4)
    >>> x.branch()  # Equal superposition on all 4 qubits
    >>> x[0].branch(0.3)  # 30% probability on LSB only
    """
    if not 0.0 <= prob <= 1.0:
        raise ValueError(f"Probability must be in [0, 1], got {prob}")

    import math
    theta = 2.0 * math.asin(math.sqrt(prob))

    # Track layer for uncomputation
    self._start_layer = get_current_layer()

    # Apply Ry to each qubit
    for i in range(self.bits):
        qubit_idx = 64 - self.bits + i
        _emit_ry(self.qubits[qubit_idx], theta)  # internal gate emission

    self._end_layer = get_current_layer()
```

### Internal Ry Emission (_gates.pyx)

```python
# In _gates.pyx
cdef extern from "gate.h":
    void ry(gate_t *g, qubit_t target, double angle)

def _emit_ry(unsigned int target_qubit, double angle):
    """Emit Ry gate to circuit (internal use only)."""
    cdef gate_t g
    cdef circuit_t *circ = <circuit_t*><unsigned long long>_get_circuit()

    memset(&g, 0, sizeof(gate_t))
    ry(&g, target_qubit, angle)

    # Handle controlled context
    if _get_controlled():
        ctrl = _get_control_bool()
        g.NumControls = 1
        g.Control[0] = ctrl.qubits[63]

    add_gate(circ, &g)
```

### MCZ via H-MCX-H Pattern

```python
def _emit_mcz(target: int, controls: list[int], ancilla_start: int = None):
    """Emit multi-controlled Z gate.

    Uses H-MCX-H decomposition:
    MCZ = H(target) . MCX(target, controls) . H(target)
    """
    _emit_h(target)
    _emit_mcx(target, controls, ancilla_start)  # Use existing MCX decomposition
    _emit_h(target)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw radians for rotations | Probability-based API | This phase | More intuitive for non-physicists |
| Direct H gate exposure | branch() method | This phase | Higher-level abstraction |

**Note:** This is new functionality, not replacing deprecated approaches.

## Open Questions

1. **Layer Floor Handling**
   - What we know: `_get_layer_floor()` / `_set_layer_floor()` control minimum layer placement
   - What's unclear: Should branch() respect layer floor or ignore it?
   - Recommendation: Follow existing qint operation patterns (likely respect floor)

2. **Controlled Ry in @ql.compile**
   - What we know: compile.py has `_derive_controlled_gates()` that adds controls
   - What's unclear: Does this correctly handle CRy (control added to rotation gate)?
   - Recommendation: Verify with test case; should work since Ry is in `_ROTATION_GATES`

## Sources

### Primary (HIGH confidence)
- `c_backend/include/types.h` - Gate type enumeration, Ry already exists
- `c_backend/src/gate.c` - Gate creation patterns (h, z, cz, ccx implementations)
- `c_backend/src/circuit_output.c` - QASM export for Ry with full precision
- `src/quantum_language/compile.py` - @ql.compile integration, Ry in rotation gates
- `src/quantum_language/qint.pyx` - qint structure, qubit layout, method patterns
- `c_backend/src/IntegerComparison.c` - MCX AND-ancilla decomposition pattern

### Secondary (MEDIUM confidence)
- Quantum computing theory: Ry(theta) on |0> produces `cos(theta/2)|0> + sin(theta/2)|1>`
- Probability-to-angle formula: `theta = 2 * arcsin(sqrt(prob))` is standard derivation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All infrastructure already exists in codebase
- Architecture: HIGH - Clear patterns from existing gate implementations
- Pitfalls: HIGH - Based on direct codebase analysis

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable infrastructure, 30 days)
