# Phase 52: Ancilla Tracking & Inverse Qubit Reuse - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Compiled functions (`@ql.compile`) track internal qubit allocations (ancillas) so that calling `.inverse()` targets the same physical qubits, uncomputes them to |0⟩, and deallocates them. Also support a standalone `.adjoint()` that runs the reverse circuit without requiring a prior forward call.

</domain>

<decisions>
## Implementation Decisions

### Inverse calling syntax
- `f.inverse(x)` is the only syntax for uncomputing a prior `f(x)` call — no chained `f(x).inverse()` syntax
- `f.adjoint(x)` is a separate method for running the reverse circuit standalone (no prior forward call needed)
- All arguments from the forward call must be passed to `f.inverse(x, y, ...)` — full signature match required
- `f.inverse(x)` returns None — purely side-effectful (uncompute + deallocate)
- `f.inverse(x)` must work inside controlled contexts (`with_(control_qubit, lambda: f.inverse(x))`)

### Ancilla matching rules
- Forward calls are matched by **qubit identity** — `f.inverse(x)` finds the forward call where the physical qubits of `x` were used as input
- **All** internal allocations are tracked as ancillas (including qubits backing the return value)
- Calling `f(x)` twice with the same input qubits without inverting the first is an **error**
- After `f.inverse(x)` completes, the same input qubits can be passed to `f(x)` again (error only if uninverted call is outstanding)
- Return value is **read-only** between forward and inverse calls — user's responsibility to not modify it (no enforcement)

### Lifetime & error behavior
- No warning if `f(x)` is called but `f.inverse(x)` is never called — silent, user may intentionally keep ancillas alive
- `f.inverse(x)` without a prior `f(x)` on those qubits raises a clear error
- Calling `f.inverse(x)` twice for the same forward call raises an error (ancillas already deallocated)
- No introspection API (no `f.has_pending(x)` or similar) — keep API minimal

### Return value semantics
- Return value contains only the meaningful result qubits — ancillas are tracked internally but not exposed
- Measurement of the return value between forward and inverse is allowed (but inverse after measurement doesn't make physical sense — user's responsibility)
- After `f.inverse(x)` completes, the result qint is auto-invalidated — subsequent use raises an error
- Return value looks like a normal qint with no visible compiled-origin metadata — system tracks origin internally

### Claude's Discretion
- `f.adjoint(x)` ancilla tracking behavior (whether standalone adjoint also tracks ancillas)
- Internal data structures for ancilla tracking
- Error message wording
- How controlled inverse interacts with the replay system

</decisions>

<specifics>
## Specific Ideas

- Two distinct operations with different names: `f.inverse(x)` for uncomputing a prior call, `f.adjoint(x)` for standalone reverse circuit
- Qubit identity matching is unambiguous since qint objects have physical qubit references
- Read-only constraint on return value is a convention, not enforced — mirrors quantum computing's "don't measure mid-computation" principle

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 52-ancilla-tracking-inverse-reuse*
*Context gathered: 2026-02-04*
