# Phase 78: Diffusion Operator - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the Grover diffusion operator as a reusable building block using the X-MCZ-X pattern with zero ancilla and O(n) gates. Includes introducing a new `phase` property on quantum registers and a `ql.diffusion()` convenience wrapper. Manual S_0 reflection via `with a == 0: a.phase += pi` is the user-facing primitive; the convenience wrapper provides an optimized circuit-efficient path.

</domain>

<decisions>
## Implementation Decisions

### API Surface
- `ql.diffusion(x)` as top-level convenience wrapper, exported from `ql` namespace
- Internally decorated with `@ql.compile` for gate caching and optimization
- Cache key based on total qubit width (not individual register signatures)
- The convenience wrapper uses the zero-ancilla X-MCZ-X pattern for circuit efficiency

### Phase Property (`x.phase += theta`)
- New syntax introduced in Phase 78: `x.phase += theta` applies a global phase
- Also support `x.phase *= -1` as equivalent to `x.phase += pi`
- `+= theta` is the primary form; `*= -1` supported if both are manageable
- Works on qint, qbool, and qarray
- **Uncontrolled:** emits NO gate (global phase is unobservable)
- **Controlled (inside `with` block):** emits CP(theta) / MCP(theta) on the control qubit(s)
- Auto-controlled: follows existing gate propagation pattern — inside `with flag:`, phase becomes controlled automatically
- No warning when used outside `with` block (global phase is valid quantum mechanics)
- Register-agnostic: inside `with x == 0:`, both `x.phase += pi` and `y.phase += pi` have the same effect (controlled global phase)

### Manual S_0 Reflection
- User writes: `with x == 0: x.phase += pi` for manual S_0 reflection
- `x == 0` uses existing comparison semantics (arithmetic value equals 0, same as all-qubits-zero for |0> state)
- Ancilla-based path: uses existing comparison machinery; qbool gets uncomputed on `with` exit
- Works for arbitrary states: `with x == k: x.phase += pi` reflects about |k> for any k
- This is the user-facing primitive for custom amplitude amplification

### Register Specification
- `ql.diffusion()` accepts qint, qbool, and qarray
- Multiple registers supported: `ql.diffusion(x, y, arr)` flattens all qubits into one search register
- No overlap validation — trust the user
- Hard error on zero-width input (empty register list or width-0 register)

### Compile Integration
- `ql.diffusion` is `@ql.compile` internally
- Works inside `with` blocks (controlled diffusion) — all gates become controlled automatically
- No `.inverse` / `.adjoint` support needed (diffusion is self-adjoint)
- Exported at top-level `ql.*` namespace

### Claude's Discretion
- Internal gate emission strategy for the X-MCZ-X pattern in the convenience wrapper
- How `phase` property is implemented on the Cython qint/qbool/qarray classes
- Test structure and Qiskit simulation verification approach
- Error message wording for invalid inputs

</decisions>

<specifics>
## Specific Ideas

- The diffusion operator should have two paths: optimized `ql.diffusion(x)` using X-MCZ-X (zero ancilla), and manual `with x == 0: x.phase += pi` using existing comparison (ancilla-based). Both produce correct results.
- `x.phase += theta` is fundamentally a global phase — it only materializes as a gate when inside a controlled context, where it becomes CP/MCP. This mirrors phase kickback.
- The `+= pi` form is preferred over `*= -1` as it generalizes naturally to arbitrary angles.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 78-diffusion-operator*
*Context gathered: 2026-02-20*
