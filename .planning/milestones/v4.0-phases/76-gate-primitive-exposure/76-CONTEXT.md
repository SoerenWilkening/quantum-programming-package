# Phase 76: Gate Primitive Exposure - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose Hadamard-equivalent (via Ry rotation) and gate primitives at the Python level so users can create superpositions via `branch()` method on qint/qbool, and internal gates (H, Z, MCZ) are available for diffusion operator construction in Phase 78.

</domain>

<decisions>
## Implementation Decisions

### branch() API Design
- **Parameter semantics:** theta is probability (0 to 1), not radians — 0.5 for equal superposition
- **Default argument:** `branch()` defaults to 0.5 (equal superposition)
- **Return value:** None (mutation, no chaining)
- **Multi-qubit behavior:** `x.branch(0.5)` applies same Ry(theta) to all qubits in qint
- **Single qubit via indexing:** `x[0].branch(0.3)` applies to just that qubit (returns qbool)
- **Invalid probability:** Raise ValueError if outside [0, 1]
- **Edge cases (0, 1):** Allow silently (valid edge case, no special handling)
- **Naming:** Only `branch()`, no aliases like `superpose()`
- **@ql.compile support:** Full support — works both directly and inside compiled functions

### Superposition Behavior
- **Existing state:** Just applies Ry gate regardless of current state (no reset, no error)
- **Multiple calls:** Gates accumulate (each branch() adds another Ry rotation)
- **Indexed qbool:** `x[0].branch(0.5)` works the same (affects just that qubit)
- **Ancilla qubits:** Allow branch() on ancilla — user's responsibility
- **Auto-inverse:** Yes — inverse branch() is Ry(-theta), tracked for uncomputation
- **Mid-circuit measurement:** Allow branch() anywhere, even post-measurement
- **qarray elements:** Works on qarray elements (`arr[i].branch(0.5)`)

### Internal Gate Access
- **Public API:** H and Z are internal-only, not exposed as public ql.H/ql.Z
- **Module location:** New private `_gates` module (pyx) with H, Z, Ry implementations
- **Backend:** C backend — add H/Z/Ry to existing C instruction set
- **MCZ:** Implement in this phase (76) as foundation for Phase 78 diffusion
- **MCZ ancilla:** Allow ancilla for O(n) gates if beneficial
- **Circuit trace:** Internal gates visible in visualization and QASM export
- **Controlled variants:** Implement CH, CZ, CRy (all controlled variants)
- **Arithmetic mode:** Unified/mode-agnostic — gates work the same regardless of arithmetic_mode

### Verification Approach
- **User verification:** None required — users trust the machine
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

</decisions>

<specifics>
## Specific Ideas

- User confirmed qint[index] returns qbool — leverage this for per-qubit branch()
- Probability-based API (0-1) is more intuitive than radians for non-physicists
- MCZ implementation should allow ancilla for efficiency, matching existing infrastructure

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 76-gate-primitive-exposure*
*Context gathered: 2026-02-19*
